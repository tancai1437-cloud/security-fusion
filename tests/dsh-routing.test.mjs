import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, existsSync, mkdirSync, readFileSync, writeFileSync, cpSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FusionSession, formatRecovery, RECOVERY_MAX_CHARS } from '../adapters/dsh-runtime.mjs';
import { expandRoute, prepareRoute, requireRoute } from '../adapters/dsh-routing.mjs';
import { executeStep, guardReason, stopCorrection, recordTurnOutcome, closeStep } from '../adapters/dsh-execution.mjs';

const pack = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = mkdtempSync(path.join(os.tmpdir(), 'fusion-route-'));
const config = { skillRoot: pack, stateDir: path.join(root, 'private'), python: process.env.FUSION_TEST_PYTHON || 'python' };
const read = { name: 'read', description: 'Read a file', parameters: { type: 'object', properties: { file_path: { type: 'string' } }, required: ['file_path'] } };

test('unprepared dispatch returns the source method first; restart restores the exact route and actual receipt', async () => {
  const session = new FusionSession(config, 'read-route', root);
  const sample = path.join(root, 'sample.js'); writeFileSync(sample, 'const control = "controlled-fixture";');
  const request = { skill: 'fusion-js', capability: 'js.source', purpose: 'Read actual sample source',
    target: sample, objective: 'Identify fixture control', scope: 'Only this local fixture', tool: 'read',
    arguments: { file_path: sample }, work: { key: 'source', conditions: { revision: 'fixture-v1' } } };
  const first = await requireRoute(session, request, [read]);
  assert.equal(first.response.status, 'route_ready');
  assert.equal(first.response.target_action_executed, false);
  assert.ok(readFileSync(first.response.guidance.specialist.source, 'utf8').replaceAll('\r\n', '\n').includes(first.response.guidance.specialist.method));
  assert.equal(first.response.execution.parameters.required[0], 'file_path');
  assert.equal(existsSync(path.join(session.casePath, 'case.sqlite3')), false, 'routing must not fake an execution/check');
  const restarted = new FusionSession(config, 'read-route', root);
  const recovery = await restarted.recovery();
  assert.equal(recovery.current_route.id, first.response.route_id);
  assert.equal(recovery.current_route.status, 'prepared_not_executed');
  assert.ok(formatRecovery(recovery).length <= RECOVERY_MAX_CHARS);
  const expanded = expandRoute(restarted, { route_id: first.response.route_id });
  const ready = await requireRoute(restarted, expanded, [read]);
  let calls = 0;
  const dispatch = async (_tool, args) => { calls++; return { isError: false, content: [{ type: 'text', text: readFileSync(args.file_path, 'utf8') }] }; };
  const actual = await executeStep(restarted, expanded, dispatch, undefined, ready.receipt);
  assert.equal(actual.routing.id, first.response.route_id);
  assert.equal(actual.routing.source_sha256, first.response.guidance.specialist.source_sha256);
  assert.equal(actual.status, 'review'); assert.equal(calls, 1);
  assert.equal(restarted.state().current_route.status, 'executed');
  assert.throws(() => expandRoute(restarted, { route_id: first.response.route_id, arguments: { file_path: 'changed.js' } }), /this call's work/);
  await executeStep(restarted, { review: { summary: 'The fixed fixture declares controlled-fixture' } }, dispatch);
  assert.equal((await executeStep(restarted, expanded, dispatch, undefined, ready.receipt)).decision, 'reuse');
  assert.equal(calls, 1);
  assert.throws(() => expandRoute(new FusionSession(config, 'other-session', root), { route_id: first.response.route_id }), /this session/);
  assert.throws(() => expandRoute(restarted, { route_id: first.response.route_id, tool: 'write' }), /binds tool/);
});

test('tools must be visible and matched; ambiguous, missing and fallback bindings remain explicit', async () => {
  const session = new FusionSession(config, 'tool-selection', root);
  const request = { skill: 'fusion-web', capability: 'http.request', purpose: 'Observe controlled response' };
  const a = { ...read, name: 'mcp__burpA__send_http1_request' }, b = { ...read, name: 'mcp__burpB__send_http1_request' };
  const ambiguous = await prepareRoute(session, request, [a, b, read]);
  assert.equal(ambiguous.status, 'tool_choice_required');
  assert.deepEqual(ambiguous.candidates.map(x => x.name), [a.name, b.name]);
  assert.equal((await prepareRoute(session, request, [read])).status, 'tool_unavailable');
  await assert.rejects(prepareRoute(session, { ...request, tool: a.name }, [read]), /not visible/);
  assert.equal((await prepareRoute(session, { ...request, tool: 'read' }, [read])).status, 'tool_reason_required');
  const shell = { ...read, name: 'bash' };
  const fallback = await prepareRoute(session, { ...request, tool: 'bash', tool_reason: 'Run installed curl against only the authorized URL; does not replace browser state.' }, [shell]);
  assert.equal(fallback.execution.binding_source, 'agent_explained_fallback');
  assert.equal(fallback.execution.health, 'not_probed');
  const large = { ...shell, parameters: { type: 'object', description: 'large schema description'.repeat(200) } };
  const compact = await prepareRoute(session, { ...request, tool: 'bash', tool_reason: 'Run the installed explicit reader', retest_reason: 'one retry only' }, [large]);
  assert.equal(compact.execution.parameters_omitted, true);
  assert.equal(compact.execution.parameters, undefined);
  assert.equal(expandRoute(session, { route_id: compact.route_id }).retest_reason, undefined, 'retry permission cannot be replayed');
  const native = await prepareRoute(session, request, [a]);
  assert.equal(native.execution.tool, a.name);
  assert.equal(native.execution.context_required, true, 'registry visibility does not prove target binding');
  await assert.rejects(prepareRoute(session, { ...request, tool: 'fusion' }, [{ ...read, name: 'fusion' }]), /not visible/);
  await assert.rejects(prepareRoute(session, { ...request, arguments: { password: 'fixture-not-a-secret' } }, [a]), /credentials/);
});

test('procedure binds specialist and capability; changed schema or method requires preparation again', async () => {
  const local = path.join(root, 'copy'); mkdirSync(local);
  cpSync(path.join(pack, 'manifests'), path.join(local, 'manifests'), { recursive: true });
  cpSync(path.join(pack, 'specialists'), path.join(local, 'specialists'), { recursive: true });
  cpSync(path.join(pack, 'scripts'), path.join(local, 'scripts'), { recursive: true });
  const session = new FusionSession({ ...config, skillRoot: local }, 'fresh-route', root);
  const request = { procedure: 'binary-profile', tool: 'bash', tool_reason: 'Invoke the installed read-only profiling script on the supplied sample' };
  const shell = { ...read, name: 'bash' };
  const first = await prepareRoute(session, request, [shell]);
  assert.equal(first.guidance.specialist.skill_id, 'fusion-binary');
  assert.equal(first.guidance.capability.id, 'binary.profile');
  const expanded = expandRoute(session, { route_id: first.route_id });
  assert.equal((await requireRoute(session, expanded, [shell])).receipt.id, first.route_id);
  await assert.rejects(prepareRoute(session, { ...request, skill: 'fusion-api' }, [shell]), /does not match/);
  const changed = { ...shell, parameters: { ...shell.parameters, required: ['different'] } };
  assert.equal((await requireRoute(session, expanded, [changed])).response.status, 'route_ready');
  const method = path.join(local, 'specialists/fusion-binary/SKILL.md');
  writeFileSync(method, readFileSync(method, 'utf8') + '\nUpdated fixture method\n');
  assert.equal((await requireRoute(session, expanded, [shell])).response.status, 'route_ready');
});

test('zero execution is corrected finitely and recorded; analysis suspension remains unrestricted', async () => {
  const session = new FusionSession(config, 'zero-execution', root); session.activate();
  assert.match(stopCorrection(session, 1), /suspend/); assert.ok(stopCorrection(session, 1));
  assert.equal(stopCorrection(session, 1), undefined);
  recordTurnOutcome(session, 1, 'completed');
  assert.equal(session.state().adherence, 'loaded_without_execution');
  assert.equal(existsSync(path.join(session.casePath, 'case.sqlite3')), false);
  await closeStep(session, 'suspend', { reason: 'User only asked for explanation' });
  assert.equal(stopCorrection(session, 2), undefined);
});

test('restoring managed instructions does not add manual review work; target source and failures still require judgement', async () => {
  const session = new FusionSession(config, 'managed-reads', root);
  const request = { target: 'fixture', objective: 'Read local materials', scope: 'Local test only', skill: 'fusion-js',
    capability: 'evidence.persist', purpose: 'Restore instructions', tool: 'read', arguments: { file_path: path.join(pack, 'SKILL.md') } };
  const dispatch = async (_, args) => ({ isError: false, content: [{ type: 'text', text: readFileSync(args.file_path, 'utf8') }] });
  const managed = await executeStep(session, request, dispatch);
  assert.equal(managed.status, 'done');
  assert.match(managed.completion_scope, /not a target assessment/);
  const source = path.join(root, 'target-source.js'); writeFileSync(source, 'const fixture = 1;');
  const target = await executeStep(session, { ...request, arguments: { file_path: source } }, dispatch);
  assert.equal(target.status, 'review', 'arbitrary target source cannot be auto-validated as managed material');
  const failed = await executeStep(session, { ...request, arguments: { file_path: path.join(pack, 'README.md') } },
    async () => ({ isError: true, content: [{ type: 'text', text: 'Controlled reader failure' }] }));
  assert.equal(failed.status, 'failed', 'unsuccessful reads are never automatically reviewed done');
});

test('suspension releases unrelated work but cannot unlock the old target or private case files', async () => {
  const session = new FusionSession({ ...config, boundTools: { mcp__fixture__read: 'http://127.0.0.1:8080/owned' } }, 'suspend-scope', root);
  session.update({ task: { target: 'http://127.0.0.1:8080/owned' } });
  await closeStep(session, 'suspend', { reason: 'User switched to unrelated work' });
  assert.equal(guardReason(session, { name: 'read', arguments: { file_path: path.join(root, 'unrelated-source.js') } }), undefined);
  for (const args of [
    { file_path: path.join(session.casePath, 'REPORT.md') },
    { file_path: path.join(session.root, 'receipts/capture.json') },
    { path: path.join(config.stateDir, 'sessions/some-guessed-owner') },
    { command: 'Read ' + path.join(session.casePath, 'REPORT.md') },
    { url: session.state().task.target },
  ]) assert.match(guardReason(session, { name: 'read', arguments: args }), /suspend releases only unrelated/);
  assert.match(guardReason(session, { name: 'mcp__fixture__read', arguments: {} }), /case is protected/, 'implicit fixed target is protected too');
  assert.equal(guardReason(session, { name: 'fusion', arguments: {} }), undefined);
});
