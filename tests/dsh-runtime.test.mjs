import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, symlinkSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { FusionSession, validateArgs, visibleRecovery, formatRecovery, RECOVERY_MAX_CHARS, replaceRecovery } from '../adapters/dsh-runtime.mjs';
import { executeStep, closeStep, guardReason, stopCorrection, recordTurnOutcome, recoverCaptured } from '../adapters/dsh-execution.mjs';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = mkdtempSync(path.join(os.tmpdir(), 'fusion-host-test-'));
const config = { skillRoot, stateDir: path.join(root, 'private'), python: process.env.FUSION_TEST_PYTHON || 'python' };

test('host ownership cannot be overridden, including argparse abbreviations', () => {
  for (const flag of ['--case=x', '--workspace', '--session=other', '--ca', '--work']) {
    assert.throws(() => validateArgs('run', [flag]), /supplied by the host/);
  }
  assert.doesNotThrow(() => validateArgs('run', ['--check', 'check', '--', 'child', '--case', 'legitimate-child-arg']));
});

test('host-wrapped execFile preserves the actual CLI result without a promisify symbol', async () => {
  const original = childProcess.execFile;
  childProcess.execFile = (...args) => original(...args);
  syncBuiltinESMExports();
  try {
    const session = new FusionSession(config, 'wrapped-host', root);
    const result = await session.call('catalog', ['--capability', 'http.request']);
    assert.equal(result.capability, 'http.request');
  } finally {
    childProcess.execFile = original;
    syncBuiltinESMExports();
  }
});

test('real CLI execution, disk recovery, negative evidence and cross-session isolation', async () => {
  const receipts = [];
  const server = http.createServer((req, res) => {
    receipts.push(req.url);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ protected_access: false, fixture: req.url }));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const a = new FusionSession(config, 'session-a', root);
    const b = new FusionSession(config, 'session-b', root);
    const target = `http://127.0.0.1:${server.address().port}/alpha`;
    const task = { project: 'host-test', targets: [target], entry: target,
      config: { mission_id: 'pentest', objective: 'Check alpha only', scope: target, constraints: ['No beta'] } };
    const started = await a.call('start', ['--execute-local'], JSON.stringify(task));
    assert.equal(started.execution.status, 'review');
    assert.match(started.evidence_preview.text, /protected_access/);
    assert.deepEqual(receipts, ['/alpha']);
    const restored = await new FusionSession(config, 'session-a', root).recovery();
    assert.equal(restored.state.current.status, 'review');
    assert.equal(restored.state.current.target, target);
    assert.equal(await b.recovery(), null);
    assert.notEqual(a.casePath, b.casePath);
    await a.call('review', ['--attempt', started.execution.attempt_id, '--verdict', 'done', '--valid-for', '600', '--summary', 'No protected access observed']);
    const completed = await a.recovery();
    assert.equal(completed.state.stored_status_counts.done, 1);
    assert.equal(completed.state.current, null);
    assert.match(completed.state.next, /resume --check/);
    assert.match(completed.state.next, /Artifact IDs are not paths/);
    assert.deepEqual(receipts, ['/alpha'], 'restoration must not repeat target requests');
    await assert.rejects(a.call('start', ['--execute-local'], JSON.stringify(task)), /already owns a case/);
    const otherCwd = path.join(root, 'other'); mkdirSync(otherCwd);
    assert.throws(() => new FusionSession(config, 'session-a', otherCwd).state(), /binding mismatch/);
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('visible source detection ignores quoted summaries and detects removal by compaction', () => {
  const events = [
    { type: 'user/message', data: { source: { kind: 'security-fusion-state', digest: 'key' } } },
    { type: 'user/message', data: { source: { kind: 'compaction' }, text: 'quoted security-fusion-state' } },
  ];
  const session = { surface: { nodes: [0, 1] }, eventAt: i => events[i] };
  assert.equal(visibleRecovery(session, 'key'), true);
  session.surface.nodes = [1];
  assert.equal(visibleRecovery(session, 'key'), false);
});

test('tool faults survive process recreation; stable turns do not request repeated snapshots', () => {
  const a = new FusionSession(config, 'fault-test', root);
  a.activate();
  const initial = a.recoveryKey(1);
  a.observe('web_fetch', { isError: true, error: { message: 'missing dependency' } });
  const after = new FusionSession(config, 'fault-test', root);
  assert.notEqual(after.recoveryKey(1), initial);
  assert.equal(after.recoveryKey(1), a.recoveryKey(1));
  assert.notEqual(after.recoveryKey(2), after.recoveryKey(1));
  assert.equal(after.state().tool_errors.web_fetch, 'missing dependency');
  after.observe('web_fetch', { isError: false });
  assert.equal(after.recoveryKey(1), initial);
});

test('observed host execution binds once, deduplicates after restart and requires actual delivery', async () => {
  const hits = [];
  const server = http.createServer((req, res) => { hits.push(req.url); res.end('{"protected_access":false}'); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const target = `http://127.0.0.1:${server.address().port}/alpha`;
    const session = new FusionSession(config, 'observed-execution', root);
    const request = { objective: 'Check controlled alpha', scope: target, target, skill: 'fusion-web',
      capability: 'http.request', work: { key: 'baseline', conditions: { control: 'original' } }, purpose: 'Observe baseline', tool: 'http_reader', arguments: { url: target },
      deliverables: ['answer.md'] };
    const ids = [];
    const dispatch = async (tool, args, id) => {
      ids.push(id); assert.equal(tool, 'http_reader');
      return { isError: false, content: [{ type: 'text', text: await (await fetch(args.url)).text() }] };
    };
    const first = await executeStep(session, request, dispatch);
    assert.equal(first.status, 'review');
    assert.match(first.observed.text, /protected_access/);
    const capture = JSON.parse(readFileSync(first.observed.capture));
    assert.equal(capture.tool_call_id, ids[0]);
    await assert.rejects(closeStep(session, 'finish', { summary: 'Review is still missing', report: 'answer.md' }),
      error => error.message.includes(first.attempt_id) && error.message.includes('execute request={review:'));
    assert.equal((await executeStep(session, request, dispatch)).decision, 'hold');
    const restored = new FusionSession(config, 'observed-execution', root);
    const repeat = await executeStep(restored, { ...request, purpose: 'Renamed purpose must not bypass reuse',
      review: { attempt: first.attempt_id, summary: 'Actual baseline remains protected' } }, dispatch);
    assert.equal(repeat.decision, 'reuse');
    assert.deepEqual(hits, ['/alpha']);
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Missing deliverable', report: 'answer.md' }), /ENOENT/);
    writeFileSync(path.join(restored.casePath, 'answer.md'), 'Fixture report cites fabricated CALL-00000000000000000000000000000000');
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Cannot submit fabricated receipt', report: 'answer.md' }), /unobserved execution/);
    writeFileSync(path.join(restored.casePath, 'answer.md'), 'Fixture report: protected_access=false. Observed ' + first.attempt_id);
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Stage files still missing', report: 'answer.md' }), /Specialist deliverables missing/);
    const partial = await closeStep(restored, 'finish', { summary: 'Explicitly incomplete stage files', report: 'answer.md', status: 'partial' });
    assert.equal(partial.status, 'partial');
    assert.equal(partial.delivery_gaps.length, 2);
    const stage = path.join(restored.casePath, 'specialists/fusion-web');
    mkdirSync(stage, { recursive: true });
    for (const file of ['web-checks.json', 'candidates.json']) writeFileSync(path.join(stage, file), '[]');
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Files alone are insufficient', report: 'answer.md' }), /Goal acceptance remains incomplete/);
    const end = await closeStep(restored, 'finish', { summary: 'Fixture inspected', report: 'answer.md',
      assessment: [{ criterion: 'objective', attempts: [first.attempt_id], summary: 'Controlled response directly shows protected_access=false' }] });
    assert.equal(end.status, 'submitted');
    assert.deepEqual(end.delivery_gaps, []);
    assert.equal(end.deliverables.length, 1);
    assert.equal(stopCorrection(restored, 2), undefined);
    assert.equal((await restored.recovery()).closure.report.sha256, end.report.sha256);
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('same cwd outputs are isolated, immutable versions are retrievable, and escapes never dispatch', async () => {
  const a = new FusionSession(config, 'output-a', root);
  const b = new FusionSession(config, 'output-b', root);
  writeFileSync(path.join(root, 'shared-output.md'), 'shared source must remain unchanged');
  let writes = 0;
  const dispatch = async (_tool, args) => {
    writes++; mkdirSync(path.dirname(args.file_path), { recursive: true });
    writeFileSync(args.file_path, args.content);
    return { isError: false, content: [{ type: 'text', text: 'Actual file written' }] };
  };
  const request = target => ({ objective: 'Save fixture', scope: target, target, skill: 'fusion-web',
    capability: 'evidence.persist', purpose: 'Persist stage output', tool: 'write',
    work: { key: 'parent-question', conditions: { control: 'shared observation' } },
    arguments: { file_path: 'shared-output.md', content: target }, deliverables: ['shared-output.md'] });
  const first = await executeStep(a, request('alpha'), dispatch);
  await executeStep(b, request('beta'), dispatch);
  assert.equal(readFileSync(path.join(a.casePath, 'shared-output.md'), 'utf8'), 'alpha');
  assert.equal(readFileSync(path.join(b.casePath, 'shared-output.md'), 'utf8'), 'beta');
  assert.equal(readFileSync(path.join(root, 'shared-output.md'), 'utf8'), 'shared source must remain unchanged');
  await assert.rejects(executeStep(a, { ...request('alpha'), arguments: { file_path: path.join(root, 'shared-output.md'), content: 'wrong' } }, dispatch), /inside this session/);
  await assert.rejects(executeStep(a, { ...request('alpha'), arguments: { file_path: '../escape.md', content: 'wrong' } }, dispatch), /inside this session/);
  assert.equal(writes, 2);
  const sibling = await executeStep(a, { ...request('alpha'), arguments: { file_path: 'second-output.md', content: 'second file' } }, dispatch);
  assert.equal(sibling.status, 'done', 'sharing a parent work key must not deduplicate distinct files');
  assert.match(sibling.completion_scope, /file_persistence_only/);
  assert.equal(readFileSync(path.join(a.casePath, 'second-output.md'), 'utf8'), 'second file');
  assert.equal(writes, 3);
  await executeStep(a, { review: { attempt: first.attempt_id, summary: 'Alpha content observed on disk' } }, dispatch);
  const updated = await executeStep(a, { ...request('alpha'), arguments: { file_path: 'shared-output.md', content: 'alpha v2' } }, dispatch);
  assert.equal(readFileSync(first.outputs[0].capture, 'utf8'), 'alpha');
  assert.equal(readFileSync(updated.outputs[0].capture, 'utf8'), 'alpha v2');
  const artifacts = await a.call('query', ['--kind', 'artifacts', '--check', first.check_id]);
  const output = artifacts.items.find(e => e.sha256 === first.outputs[0].sha256);
  assert.equal((await a.call('artifact', ['--artifact', output.id])).text, 'alpha');
  await assert.rejects(b.call('artifact', ['--artifact', output.id]), /Unknown artifact/);
});

test('replacement projection retains one full state block and preserves original journal data', () => {
  // Small surface fixture; the optional host integration also exercises DSH's actual Session implementation.
  const events = [], nodes = [];
  const session = { surface: { nodes }, eventAt: seq => events[seq], append(type, data, intent) {
    const seq = events.length; events.push({ type, data, seq, ...intent });
    if (intent.surfaceOp === 'append') nodes.push(seq);
    else nodes.splice(nodes.indexOf(intent.surfaceOp.start), 1, seq);
  } };
  session.append('user/message', { source: { kind: 'user' }, content: 'original task' }, { surfaceOp: 'append' });
  session.append('user/message', { source: { kind: 'security-fusion-state', digest: 'old' }, content: 'old facts' }, { surfaceOp: 'append' });
  for (let n = 0; n < 12; n++) {
    assert.equal(replaceRecovery(session, { source: { kind: 'security-fusion-state', digest: String(n) }, content: 'current facts' }), true);
    assert.equal(nodes.length, 2);
    assert.equal(visibleRecovery(session, String(n)), true);
  }
  assert.equal(events[0].data.content, 'original task');
  assert.equal(events[1].data.content, 'old facts');
  assert.equal(events.length, 14);
});

test('structured writers reject linked escapes and only auto-review exact requested bytes', async () => {
  const session = new FusionSession(config, 'writer-validation', root);
  const request = { objective: 'Save a local file', scope: 'local fixture', target: 'fixture', skill: 'fusion-web',
    capability: 'evidence.persist', purpose: 'Write fixture', tool: 'write', arguments: { file_path: 'file.md', content: 'expected' } };
  const mismatch = await executeStep(session, request, async (_name, args) => {
    writeFileSync(args.file_path, 'different');
    return { isError: false, content: [{ type: 'text', text: 'Tool claimed success' }] };
  });
  assert.equal(mismatch.status, 'review', 'a success message cannot prove file content');
  const outside = path.join(root, 'linked-outside'); mkdirSync(outside);
  symlinkSync(outside, path.join(session.casePath, 'linked'), process.platform === 'win32' ? 'junction' : 'dir');
  let calls = 0;
  await assert.rejects(executeStep(session, { ...request, arguments: { file_path: 'linked/escape.md', content: 'no' } }, async () => calls++), /inside this session/);
  assert.equal(calls, 0);
});

test('automatic experience retrieval shares reviewed methods but separates same-named project paths', async () => {
  const cwd = path.join(root, 'memory-project'); mkdirSync(cwd);
  const unrelated = path.join(root, 'other-parent', 'memory-project'); mkdirSync(unrelated, { recursive: true });
  const a = new FusionSession(config, 'experience-a', cwd);
  const b = new FusionSession(config, 'experience-b', cwd);
  const c = new FusionSession(config, 'experience-c', unrelated);
  const request = target => ({ objective: 'Compare ownership control', scope: target, target, skill: 'fusion-web',
    capability: 'http.request', purpose: 'Observe ownership control', tool: 'fixture_reader',
    arguments: {}, work: { key: 'control', conditions: { identity_ref: 'test-account' } } });
  const dispatch = async () => ({ isError: false, content: [{ type: 'text', text: 'Offline fixture: access denied' }] });
  const observed = await executeStep(a, request('alpha'), dispatch);
  await a.call('review', ['--attempt', observed.attempt_id, '--verdict', 'done', '--summary', 'Control denied access']);
  assert.equal(a.state().last_execution.status, 'done', 'legacy review uses the native validity default and updates recovery');
  const note = await a.call('note', ['--kind', 'negative', '--text', 'Ownership control requires a distinct identity',
    '--check', observed.check_id, '--evidence', observed.evidence_ids[0]]);
  const method = await a.call('memory-add', ['--note', note.note_id], JSON.stringify({
    title: 'Ownership control', lesson: 'Compare ownership under distinct test identities',
    conditions: ['An object API with test accounts'], counterexamples: ['A status code alone proves no access'],
    tags: ['ownership', 'control'], skill_id: 'fusion-web' }));
  await a.call('memory-review', ['--memory', method.memory_id, '--verdict', 'accept', '--scope', 'project',
    '--validation', 'Method and source evidence checked; target details removed', '--redacted', '--valid-for', '3600']);
  for (const session of [b, c]) await executeStep(session, request('beta'), dispatch);
  const same = await b.recovery(), different = await c.recovery();
  assert.equal(same.state.experience_hints[0].memory_id, method.memory_id);
  assert.equal(same.state.results.length, 0, 'case A target facts never become case B results');
  assert.deepEqual(different.state.experience_hints, []);
  assert.ok(formatRecovery(same).length <= RECOVERY_MAX_CHARS);
});

test('native execution rejects tool/capability mismatch, secrets and unbound MCP before dispatch', async () => {
  const session = new FusionSession(config, 'invalid-execute', root);
  let calls = 0;
  const dispatch = async () => { calls++; };
  const request = { objective: 'test', scope: 'fixture', target: 'fixture', skill: 'fusion-web',
    purpose: 'test', capability: 'js.runtime', tool: 'reader', arguments: {} };
  await assert.rejects(executeStep(session, request, dispatch), /Allowed capabilities/);
  await assert.rejects(executeStep(session, { ...request, capability: 'http.request', arguments: { headers: { Authorization: 'test-secret' } } }, dispatch), /inline Authorization/);
  await assert.rejects(executeStep(session, { ...request, capability: 'http.request', tool: 'mcp__browser__read' }, dispatch), /context_slot/);
  assert.equal(calls, 0);
});

test('failed and interrupted receipts never become semantic success and changed files are rejected', async () => {
  const request = { objective: 'test', scope: 'fixture', target: 'fixture', skill: 'fusion-js',
    purpose: 'Execute local fixture', work: { key: 'sample', conditions: { revision: 'fixture-v1' } }, capability: 'js.runtime', tool: 'test_runner', arguments: {} };
  const a = new FusionSession(config, 'failed-execute', root);
  const failed = await executeStep(a, request, async () => ({ isError: true, error: { code: 'TEST_FAILURE' }, content: [] }));
  assert.equal(failed.status, 'failed');
  await assert.rejects(closeStep(a, 'checkpoint', { summary: 'incorrect', next: 'later',
    review: { attempt: failed.attempt_id, summary: 'claim success' } }), /cannot be marked done/);
  const b = new FusionSession(config, 'uncertain-execute', root);
  const uncertain = await executeStep(b, request, async () => { throw new Error('Connection lost after dispatch'); });
  assert.equal(uncertain.status, 'unknown');
  let repeats = 0;
  assert.equal((await executeStep(new FusionSession(config, 'uncertain-execute', root), request, async () => repeats++)).decision, 'hold');
  assert.equal(repeats, 0);
  const c = new FusionSession(config, 'tampered-execute', root);
  const ok = await executeStep(c, request, async () => ({ isError: false, content: [{ type: 'text', text: 'fixture result' }] }));
  writeFileSync(ok.observed.capture, 'changed');
  await assert.rejects(closeStep(c, 'checkpoint', { summary: 'check', next: 'later', review: { attempt: ok.attempt_id, summary: 'accept' } }), /capture changed/);
  const other = new FusionSession(config, 'other-owner', root);
  await assert.rejects(closeStep(other, 'checkpoint', { summary: 'wrong owner', next: 'later', review: { attempt: ok.attempt_id, summary: 'accept' } }), /ENOENT/);
});

test('guard persists across recreation, allows scoped skill preparation, and respects suspension', async () => {
  const session = new FusionSession(config, 'guarded', root); session.activate();
  const raw = { name: 'pwsh', arguments: { command: 'fixture' } };
  assert.match(guardReason(new FusionSession(config, 'guarded', root), raw), /execute/);
  const readSkill = { name: 'read', arguments: { file_path: path.join(skillRoot, 'specialists/fusion-js/SKILL.md') } };
  assert.equal(guardReason(session, readSkill), undefined);
  session.update({ preparations: 2 });
  assert.match(guardReason(session, readSkill), /execute/);
  assert.equal(guardReason(session, { name: 'fusion' }), undefined);
  assert.equal(guardReason(new FusionSession(config, 'unrelated-owner', root), raw), undefined);
  assert.equal(stopCorrection(session, 1), undefined, 'loading for analysis does not authorize forced execution');
  session.update({ mode: 'executing' });
  assert.ok(stopCorrection(session, 1)); assert.ok(stopCorrection(session, 1));
  assert.equal(stopCorrection(session, 1), undefined);
  assert.equal(session.state().adherence, 'incomplete_at_turn_end');
  await closeStep(session, 'suspend', { reason: 'User requested analysis of another subject' });
  assert.equal(guardReason(session, raw), undefined);
  assert.equal(stopCorrection(session, 2), undefined);
});

test('hard model limits remain observable even when a prior phase was paused', () => {
  const session = new FusionSession(config, 'hard-limit', root);
  session.update({ mode: 'paused', task: { target: 'fixture' } });
  recordTurnOutcome(session, 2, 'max-tokens');
  const restored = new FusionSession(config, 'hard-limit', root).state();
  assert.deepEqual(restored.last_turn, { turn: 2, reason: 'max-tokens' });
  assert.equal(restored.adherence, 'interrupted_without_delivery');
  assert.equal(restored.mode, 'paused', 'does not silently resume work or claim completion');
  recordTurnOutcome(new FusionSession(config, 'never-activated', root), 1, 'max-tokens');
  assert.equal(new FusionSession(config, 'never-activated', root).state(), null);
});

test('semantic work survives compaction, switches tools without repeats, and separates changed conditions', async () => {
  const hits = [];
  const server = http.createServer((req, res) => { hits.push(req.url); res.end('control denied'); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const target = `http://127.0.0.1:${server.address().port}/alpha`;
    const initial = new FusionSession(config, 'semantic-work', root);
    const request = { objective: 'Compare controlled fixture', scope: target, target, skill: 'fusion-web',
      capability: 'http.request', purpose: 'Read anonymous baseline',
      work: { key: 'anonymous-baseline', conditions: { resource: '/alpha', control: 'original' } },
      tool: 'http_reader', arguments: { url: target }, next: 'Compare the authorized second control' };
    const dispatch = async (_tool, args) => ({ isError: false, content: [{ type: 'text', text: await (await fetch(args.url)).text() }] });
    await assert.rejects(executeStep(initial, { ...request, work: undefined }, dispatch), /require work/);
    assert.equal(hits.length, 0, 'missing work never dispatches a target call');
    const first = await executeStep(initial, request, dispatch);
    assert.equal(first.deduplication, 'work_conditions');
    await executeStep(initial, { review: { summary: 'Anonymous control denied access' } }, dispatch);
    for (let turn = 1; turn <= 12; turn++) {
      const fresh = new FusionSession(config, 'semantic-work', root);
      // A compacted conversation omits the original state source and method text.
      assert.equal(visibleRecovery({ surface: { nodes: [] } }, fresh.recoveryKey(turn)), false);
      const recovery = await fresh.recovery();
      assert.ok(formatRecovery(recovery).length <= RECOVERY_MAX_CHARS);
      assert.equal(recovery.state.current, null);
      assert.equal(recovery.state.guidance.specialist.skill_id, 'fusion-web');
      assert.equal(recovery.state.results[0].attempt_id, first.attempt_id);
      assert.equal(recovery.state.results[0].summary, 'Anonymous control denied access');
      assert.equal(recovery.continuation.next, request.next);
      const reuse = await executeStep(fresh, { ...request, tool: 'different_http_tool',
        arguments: { url: target, implementation: turn }, purpose: 'Rephrased observation' }, dispatch);
      assert.equal(reuse.decision, 'reuse');
      assert.equal(reuse.check_id, first.check_id);
    }
    assert.deepEqual(hits, ['/alpha']);
    const changed = await executeStep(initial, { ...request,
      work: { ...request.work, conditions: { ...request.work.conditions, control: 'second' } },
      arguments: { url: target + '?control=second' } }, dispatch);
    assert.notEqual(changed.check_id, first.check_id);
    assert.deepEqual(hits, ['/alpha', '/alpha?control=second']);
    const other = new FusionSession(config, 'semantic-other-owner', root);
    await executeStep(other, request, dispatch);
    assert.equal(hits.length, 3, 'another session never silently reuses this case');
  } finally { await new Promise(resolve => server.close(resolve)); }
});

test('settled capture after ledger-write crash is recovered exactly once without redispatch', async () => {
  const a = new FusionSession(config, 'record-crash', root);
  const request = { objective: 'Local crash fixture', scope: 'local fixture', target: 'fixture', skill: 'fusion-js',
    capability: 'js.runtime', purpose: 'Run fixed sample', work: { key: 'sample', conditions: { revision: 'v1' } },
    tool: 'fixture-reader', arguments: {}, next: 'Analyze the captured control' };
  let calls = 0;
  const dispatch = async () => { calls++; return { isError: false, content: [{ type: 'text', text: 'fixed local observation' }] }; };
  const cli = a.cli.bind(a);
  a.cli = async (action, ...args) => {
    if (action === 'record') throw new Error('Injected process exit before ledger record');
    return cli(action, ...args);
  };
  await assert.rejects(executeStep(a, request, dispatch), /Injected process exit/);
  const restored = new FusionSession(config, 'record-crash', root);
  assert.equal((await restored.recovery()).state.next_action.action, 'reconcile');
  await recoverCaptured(restored);
  await recoverCaptured(restored);
  const recovery = await restored.recovery();
  assert.equal(recovery.state.next_action.action, 'review');
  assert.equal(recovery.continuation.next, request.next);
  assert.equal(restored.state().executed_count, 1);
  await executeStep(restored, { review: { summary: 'Fixed observation verified' } }, dispatch);
  assert.equal((await executeStep(restored, { ...request, tool: 'replacement-reader' }, dispatch)).decision, 'reuse');
  assert.equal(calls, 1);
});

test('unobserved crash remains unresolved and completed checkpoints do not steer later work', async () => {
  const a = new FusionSession(config, 'unknown-crash', root);
  const request = { objective: 'Local interruption fixture', scope: 'fixture', target: 'fixture', skill: 'fusion-web',
    capability: 'evidence.persist', purpose: 'Local reading', tool: 'reader', arguments: {} };
  let calls = 0;
  await executeStep(a, request, async () => { calls++; throw new Error('uncertain outcome'); });
  await recoverCaptured(a);
  assert.equal((await a.recovery()).state.next_action.action, 'reconcile');
  assert.equal((await executeStep(a, request, async () => calls++)).decision, 'hold');
  assert.equal(calls, 1);
  await closeStep(a, 'checkpoint', { summary: 'Interrupted read needs reconciliation', next: 'Inspect prior capture' });
  const clean = await executeStep(a, { ...request, arguments: { different_local_file: true } },
    async () => ({ isError: false, content: [{ type: 'text', text: 'independent local content' }] }));
  assert.equal(clean.status, 'review');
  assert.equal(a.state().checkpoint, null, 'old checkpoint must not route new work backward');
});

test('recovery bounds the entire host message including tool faults and survives unicode', async () => {
  const a = new FusionSession(config, 'message-budget', root);
  await executeStep(a, { objective: 'Bound recovery ' + '测试🔎'.repeat(50), scope: 'local fixture', target: 'fixture',
    skill: 'fusion-js', capability: 'evidence.persist', purpose: 'Read fixture', tool: 'reader', arguments: {} },
    async () => ({ isError: false, content: [{ type: 'text', text: 'local observation' }] }));
  for (let n = 0; n < 60; n++) a.observe('reader-' + n, { isError: true, error: { message: 'x'.repeat(300) } });
  const recovery = await a.recovery();
  assert.ok(formatRecovery(recovery).length <= RECOVERY_MAX_CHARS);
  assert.equal(recovery.omitted_tool_errors, 57);
  assert.equal(recovery.state.next_action.action, 'review');
  assert.equal(recovery.state.guidance.specialist.skill_id, 'fusion-js');
  assert.equal(JSON.parse(readFileSync(recovery.details_path)).tool_errors['reader-0'].length, 300);
});
