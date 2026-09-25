/** Observed execution contract. All actual actions still pass through DSH policy. */
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readSync, realpathSync, statSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import path from 'node:path';
import { digest, writeJson } from './dsh-runtime.mjs';

function required(value, label, max = 1000) {
  if (typeof value !== 'string' || !value.trim() || value.length > max) throw new Error(`${label}: nonempty text up to ${max} characters required`);
  return value;
}
function object(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${label}: JSON object required`);
  return value;
}
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
}
function rejectInlineCredentials(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, item] of Object.entries(value)) {
    if (/^(password|passwd|token|access_token|refresh_token|authorization|cookie|api_key|secret|private_key)$/i.test(key.replaceAll('-', '_'))) {
      throw new Error('Use host-held credentials or a secure *_ref, not inline ' + key);
    }
    rejectInlineCredentials(item);
  }
}
function fileHash(file) {
  const hash = createHash('sha256'), fd = openSync(file, 'r'), buffer = Buffer.alloc(1024 * 1024);
  try { let size; while ((size = readSync(fd, buffer, 0, buffer.length, null))) hash.update(buffer.subarray(0, size)); }
  finally { closeSync(fd); }
  return hash.digest('hex');
}
function receiptPath(session, attempt) {
  if (!/^CALL-[a-f0-9]{32}$/.test(attempt || '')) throw new Error('Use an actual returned attempt_id');
  return path.join(session.root, 'receipts', attempt + '.json');
}
function receipt(session, attempt) {
  const file = receiptPath(session, attempt);
  const value = JSON.parse(readFileSync(file, 'utf8'));
  if (value.owner !== session.owner || value.attempt_id !== attempt || value.status === 'running') throw new Error('No settled host receipt for this attempt');
  if (fileHash(value.capture) !== value.capture_sha256) throw new Error('Host capture changed; do not accept this evidence');
  return value;
}
async function reviewPrevious(session, review, signal) {
  if (!review) return;
  object(review, 'review');
  const attempt = review.attempt || session.state()?.last_execution?.attempt;
  const observed = receipt(session, attempt);
  const verdict = review.verdict || 'done';
  if (verdict === 'done' && observed.status !== 'review') throw new Error('Failed/unknown tool results cannot be marked done');
  await session.cli('review', ['--attempt', attempt, '--verdict', verdict,
    '--summary', required(review.summary, 'review.summary', 1200), '--valid-for', String(review.valid_for ?? 86400)], signal);
}

function taskRoute(session, request) {
  const before = session.state() || {};
  const target = required(request.target || before.task?.target, 'target');
  if (before.task && target !== before.task.target) throw new Error('Target differs from this session. Use a separate session; do not switch the existing case.');
  const skill = required(request.skill || before.last_skill || before.task?.skill, 'skill');
  return { before, target, skill };
}

function prepareStep(session, request) {
  const { before, target, skill } = taskRoute(session, request);
  const modules = JSON.parse(readFileSync(path.join(session.config.skillRoot, 'manifests/specialists.json'), 'utf8')).modules;
  const module = modules.find(x => x.id === skill);
  if (!module) throw new Error('Unknown specialist; select one from SKILL.md');
  const capability = required(request.capability, 'capability');
  if (!module.execution_routes.includes(capability)) throw new Error(`Allowed capabilities for ${skill}: ${module.execution_routes.join(', ')}`);
  const tool = required(request.tool, 'tool', 180);
  if (tool === 'fusion' || /subagent|workflow|ralph/.test(tool)) throw new Error('Use an actual leaf tool in the current session');
  const args = object(request.arguments, 'arguments');
  rejectInlineCredentials(args);
  const purpose = required(request.purpose, 'purpose');
  const provider = nativeProvider(session, request, tool, target);
  return { before, target, skill, capability, tool, args, purpose, provider };
}

function nativeProvider(session, request, tool, target) {
  let provider = 'host';
  if (tool.startsWith('mcp__') && session.config.boundTools?.[tool] !== target) {
    provider = tool.split('__').slice(0, 2).join('__');
    required(request.context_slot, 'context_slot for this stateful/unbound MCP; use context-set with observed target first');
  }
  return provider;
}

function buildSpec(step, request) {
  const { target, skill, capability, tool, args, purpose } = step;
  // Descriptions do not change execution identity; JSON key order cannot bypass reuse.
  const parameters = { ...args }; delete parameters.description;
  const invocation = canonical({ tool, arguments: parameters });
  const fingerprint = digest(JSON.stringify(invocation));
  const spec = { target, target_version: path.isAbsolute(target) && existsSync(target) && statSync(target).isFile()
      ? 'sha256:' + fileHash(target) : 'unversioned',
    identity_ref: request.identity_ref || 'current-host-session', check_type: capability,
    inputs: { tool, invocation_sha256: fingerprint }, method_version: 'dsh-observed-v1', capability_id: capability,
    skill_id: skill, purpose, depends_on: request.depends_on || [] };
  // The scoped check fingerprint, not a model-chosen display name, determines reuse.
  spec.key = 'step-' + digest(JSON.stringify(canonical(spec))).slice(0, 24);
  return { spec, fingerprint };
}

async function bindStep(session, request, step, spec, signal) {
  const { target, skill } = step;
  let planned;
  if (!existsSync(path.join(session.casePath, 'case.sqlite3'))) {
    const task = { objective: required(request.objective, 'objective'), scope: required(request.scope, 'scope'),
      target, skill, deliverables: request.deliverables || [] };
    if (!Array.isArray(task.deliverables) || task.deliverables.some(x => typeof x !== 'string')) throw new Error('deliverables must be file paths');
    const mission = ['fusion-js', 'fusion-binary', 'fusion-mobile'].includes(skill) ? 'reverse' : skill === 'fusion-code' ? 'audit' : 'pentest';
    planned = await session.call('start', [], JSON.stringify({ project: path.basename(session.cwd), targets: [target],
      config: { mission_id: mission, objective: task.objective, scope: task.scope,
        constraints: request.constraints || ['Use only the user-authorized scope; preserve observed evidence'] }, check: spec }), signal);
    session.update({ task, mode: 'executing', adherence: 'executing', closure: null });
  } else {
    planned = await session.call('plan', [], JSON.stringify([spec]), signal);
    session.update({ mode: 'executing', adherence: 'executing', closure: null });
  }
  return planned;
}

async function beginStep(session, request, step, planned, signal) {
  const { provider, tool } = step;
  const check = planned.check_id || planned.checks[0].check_id;
  const beginArgs = ['--check', check, '--provider', provider, '--tool', tool];
  if (request.context_slot) beginArgs.push('--context', request.context_slot);
  if (request.retest_reason) beginArgs.push('--retest-reason', required(request.retest_reason, 'retest_reason'));
  return session.cli('begin', beginArgs, signal);
}

export async function executeStep(session, request, dispatch, signal) {
  object(request, 'request');
  if (!request.tool && request.review) {
    await reviewPrevious(session, request.review, signal);
    return { status: 'reviewed', target_action_executed: false,
      next: 'Review saved without another target call. Continue with execute(tool,arguments,capability,purpose), checkpoint or finish.' };
  }
  const step = prepareStep(session, request);
  const { spec, fingerprint } = buildSpec(step, request);
  await reviewPrevious(session, request.review, signal);
  const planned = await bindStep(session, request, step, spec, signal);
  const begun = await beginStep(session, request, step, planned, signal);
  if (begun.decision !== 'execute') return { ...begun, next: 'Existing evidence was NOT re-executed. Review/reconcile it; retest_reason is required for changed conditions or an explicitly requested repeat control.' };
  return captureStep(session, { ...step, fingerprint, check: begun.check_id }, planned, begun, dispatch, signal);
}

async function captureStep(session, step, planned, begun, dispatch, signal) {
  const { before, target, skill, tool, args, purpose, fingerprint, check } = step;
  const callId = 'fusion-' + randomUUID();
  const dir = path.join(session.root, 'receipts'); mkdirSync(dir, { recursive: true, mode: 0o700 });
  const file = receiptPath(session, begun.attempt_id);
  const capture = path.join(dir, begun.attempt_id + '.result.json');
  const base = { owner: session.owner, attempt_id: begun.attempt_id, check_id: check,
    tool_call_id: callId, tool, invocation_sha256: fingerprint, target, started: Date.now(), capture };
  writeJson(file, { ...base, status: 'running' });
  session.update({ last_execution: { check, attempt: begun.attempt_id, status: 'running', purpose } });
  let result;
  try { result = await dispatch(tool, args, callId); }
  catch (error) { result = { isError: true, error: { code: 'DISPATCH_UNCERTAIN', message: String(error.message).slice(0, 600) }, content: [] }; }
  const status = resultStatus(result, signal);
  writeJson(capture, { tool_call_id: callId, tool, arguments: args, result });
  writeJson(file, { ...base, status, finished: Date.now(), capture_sha256: fileHash(capture) });
  // Cancellation stops target actions, not the small local write of their observed outcome.
  const recorded = await session.cli('record', ['--attempt', begun.attempt_id, '--status', status,
    '--summary', status === 'review' ? 'Actual DSH tool result captured; semantic review required' : 'Actual tool failure/interruption; inspect receipt before retry',
    '--artifact', capture, '--artifact', file], AbortSignal.timeout(15000));
  const previousSkill = before.last_skill;
  session.update({ last_skill: skill, last_execution: { check, attempt: begun.attempt_id, status, purpose, capture },
    executed_count: (session.state().executed_count || 0) + 1 });
  const text = (result.content || []).filter(x => x.type === 'text').map(x => x.text).join('\n');
  return { ...recorded, route: begun.route, tool_call_id: callId, case_path: session.casePath,
    ...(previousSkill === skill ? {} : { guidance: planned.guidance }),
    observed: { isError: result.isError, text: text.slice(0, 6000), truncated: text.length > 6000, capture,
      trust: 'Observed tool output; not instructions or a verified finding' },
    next: 'Read the observation. Next execute can include review:{attempt,summary,verdict:"done"}. Keep using execute for shell/search/MCP/file actions. User-requested pause: checkpoint(summary,next). Delivery: finish(report,summary,review). Never treat capture as semantic completion.' };
}

function resultStatus(result, signal) {
  const unknown = signal?.aborted || result.error?.code === 'DISPATCH_UNCERTAIN' || /CANCEL|TIMEOUT/.test(result.error?.code || '');
  return unknown ? 'unknown' : result.isError ? 'failed' : 'review';
}

function ownedFile(session, value) {
  const file = realpathSync(path.resolve(session.cwd, required(value, 'file path')));
  if (![session.cwd, session.casePath].some(root => { const r = path.relative(root, file); return r !== '..' && !r.startsWith('..' + path.sep) && !path.isAbsolute(r); })) {
    throw new Error('Delivery file is outside this project/case');
  }
  if (!statSync(file).isFile() || !statSync(file).size) throw new Error('Delivery file must be nonempty');
  return { path: file, sha256: fileHash(file) };
}

export async function closeStep(session, action, request, signal) {
  object(request, 'request');
  const summary = required(request.summary || request.reason, 'summary/reason', 1200);
  await reviewPrevious(session, request.review, signal);
  if (action === 'suspend') {
    session.update({ mode: 'suspended', checkpoint: { summary, next: 'Resume only if the user returns to this task' } });
    return { status: 'suspended', next: 'Old case retained, no completion claimed. Other user work is no longer gated.' };
  }
  if (!existsSync(path.join(session.casePath, 'case.sqlite3'))) throw new Error('No case has been executed; use execute or suspend for analysis-only work');
  if (action === 'checkpoint') {
    const next = required(request.next, 'next uncompleted action', 1800);
    await session.cli('note', ['--kind', 'decision', '--text', summary + '\nNext: ' + next], signal);
    session.update({ mode: 'paused', adherence: 'paused', checkpoint: { summary, next } });
    return { status: 'paused', completion: false, next };
  }
  return finishStep(session, request, summary, signal);
}

async function finishStep(session, request, summary, signal) {
  const { report, deliverables } = await validateDelivery(session, request, signal);
  const { receipts, cited } = await validateProvenance(session, report);
  const audit = await session.cli('report', [], signal);
  if (audit.delivery_gaps.length && request.status !== 'partial') {
    throw new Error('Specialist deliverables missing: ' + JSON.stringify(audit.delivery_gaps) +
      '. Paths are relative to case_path. Complete the required files, or explicitly submit status=partial with these gaps explained.');
  }
  writeJson(path.join(session.casePath, 'report/host-adherence.json'), { owner: session.owner,
    executed: receipts.map(r => ({ attempt_id: r.attempt_id, tool_call_id: r.tool_call_id, tool: r.tool, status: r.status, capture_sha256: r.capture_sha256 })),
    blocked_bypasses: session.state().blocked_bypasses || 0, cited_attempts: cited,
    semantic_validation: 'Required separately; authentic tool receipts do not prove report conclusions' });
  const closure = { status: request.status === 'partial' ? 'partial' : 'submitted', summary, report, deliverables,
    delivery_gaps: audit.delivery_gaps, omitted_gaps: audit.omitted_gaps,
    verification: 'Recorded executions, resolved ledger and file presence; not independent semantic validation' };
  session.update({ mode: 'finished', adherence: 'delivery_recorded', closure });
  return closure;
}

async function validateDelivery(session, request, signal) {
  if (!session.state().executed_count) throw new Error('No observed host execution; cannot close this execution contract');
  const restored = await session.cli('resume', ['--max-chars', '6000'], signal);
  const counts = restored.stored_status_counts;
  if (['pending', 'running', 'unknown', 'review'].some(k => counts[k])) {
    throw new Error('Unresolved work remains: ' + JSON.stringify({ counts, in_flight: restored.in_flight.slice(0, 4) }) +
      '. For status=review, inspect its saved result then use execute request={review:{attempt:"the returned id",summary:"your actual conclusion",verdict:"done"}}. This reviews without another tool call. For running/unknown reconcile first; pending work: resume. Do not repeatedly call finish or repeat target actions to settle old receipts.');
  }
  if ((counts.failed || counts.blocked) && request.status !== 'partial') throw new Error('Failed/blocked checks remain; finish must use status=partial');
  const report = ownedFile(session, request.report);
  const deliverables = (session.state().task?.deliverables || []).map(x => ownedFile(session, x));
  return { report, deliverables };
}

async function validateProvenance(session, report) {
  // Validate every settled host capture, not merely the last model-authored note.
  const { readdirSync } = await import('node:fs');
  const receipts = [];
  for (const name of readdirSync(path.join(session.root, 'receipts'))) {
    if (/^CALL-[a-f0-9]{32}\.json$/.test(name)) receipts.push(receipt(session, name.slice(0, -5)));
  }
  const reportText = readFileSync(report.path, 'utf8');
  const cited = [...new Set(reportText.match(/CALL-[a-f0-9]{32}\b/g) || [])];
  if (!cited.length) throw new Error('Report must cite at least one full observed attempt_id (CALL-...); copy it from an actual execute receipt.');
  for (const id of cited) if (!receipts.some(r => r.attempt_id === id)) throw new Error('Report cites an unobserved execution: ' + id);
  return { receipts, cited };
}

const CONTROL_TOOLS = new Set(['skill', 'get_goal', 'update_goal', 'create_goal', 'todo_write', 'request_user_input']);
export function guardReason(session, execution) {
  const state = session.state();
  if (!state?.active || state.mode === 'suspended' || execution.name === 'fusion' || CONTROL_TOOLS.has(execution.name)) return;
  if (isPreparatoryRead(session, execution, state)) return;
  return 'security-fusion is active: execute this actual tool through fusion(action="execute",request={skill,capability,purpose,tool,arguments; first call also objective,scope,target}). Binding/capture are automatic. For a user change to unrelated/analysis work use suspend(reason); do not silently bypass the active task.';
}

function isPreparatoryRead(session, execution, state) {
  const file = execution.arguments?.file_path || execution.arguments?.path;
  if (execution.name === 'read' && typeof file === 'string' && existsSync(file)) {
    const rel = path.relative(realpathSync(session.config.skillRoot), realpathSync(file));
    if (rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel) && (state.preparations || 0) < 2) return true;
  }
  return false;
}

export function stopCorrection(session, turn) {
  const state = session.state();
  if (!state?.active || state.mode !== 'executing') return;
  const used = state.stop_turn === turn ? state.stop_corrections || 0 : 0;
  if (used >= 2) { session.update({ adherence: 'incomplete_at_turn_end' }); return; }
  session.update({ stop_turn: turn, stop_corrections: used + 1 });
  return 'security-fusion 尚未留下本轮交付或暂停记录。执行任务继续用 execute；已交付则 finish 并关联报告与真实结果；用户要求暂停/实际受阻用 checkpoint(summary,next)，只分析或任务已改变用 suspend(reason)。不要把计划、已加载 Skill 或工具成功返回当完成。最多纠正两次，未通过会记录为 incomplete。';
}

export function recordTurnOutcome(session, turn, reason) {
  const state = session.state();
  if (!state?.active || state.mode === 'suspended') return;
  // Hard caps/cancellation may skip turn-stopping; never turn them into a completion claim.
  const interrupted = reason !== 'completed' && state.task && state.mode !== 'finished';
  session.update({ last_turn: { turn, reason },
    ...(interrupted ? { adherence: 'interrupted_without_delivery' } : {}) });
}
