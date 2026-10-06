import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, existsSync, mkdirSync, readFileSync, writeFileSync, cpSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FusionSession, formatRecovery, RECOVERY_MAX_CHARS, sameTarget, digest } from '../adapters/dsh-runtime.mjs';
import { importToolArtifacts } from '../adapters/dsh-artifacts.mjs';
import { expandRoute, prepareRoute, requireRoute } from '../adapters/dsh-routing.mjs';
import { executeStep, guardReason, stopCorrection, recordTurnOutcome, closeStep, resolveReceiptCitations, resolveReviewAttempt } from '../adapters/dsh-execution.mjs';

const pack = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = mkdtempSync(path.join(os.tmpdir(), 'fusion-route-'));
const config = { skillRoot: pack, stateDir: path.join(root, 'private'), python: process.env.FUSION_TEST_PYTHON || 'python' };
const read = { name: 'read', description: 'Read a file', parameters: { type: 'object', properties: { file_path: { type: 'string' } }, required: ['file_path'] } };

test('bound HTTP reads infer exact invocation identity without inheriting semantic conditions', async () => {
  const target = 'http://localhost:8092', tool = { ...read, name: 'mcp__fixture__http' };
  const boundConfig = { ...config, capabilityTools: { 'http.request': [tool.name] }, boundTools: { [tool.name]: target } };
  const session = new FusionSession(boundConfig, 'automatic-read', root);
  const ready = await prepareRoute(session, { target, objective: 'Compare controlled responses', scope: 'Local fixture only',
    mission: 'src', skill: 'fusion-api', capability: 'http.request', purpose: 'Observe response' }, [tool]);
  let calls = 0;
  const dispatch = async () => { calls++; return { isError: false, content: [{ type: 'text', text: 'fixture response' }] }; };
  const firstRequest = expandRoute(session, { route_id: ready.route_id, arguments: { url: target + '/one', method: 'GET' },
    work: { key: 'control', conditions: { role: 'anonymous', resource: '/one' } } });
  const routing = (await requireRoute(session, firstRequest, [tool])).receipt;
  const first = await executeStep(session, firstRequest, dispatch, undefined, routing);
  const secondRequest = expandRoute(session, { arguments: { url: target + '/two', method: 'GET' }, review: { summary: 'First fixture observed' } });
  assert.equal(secondRequest.work, undefined, 'old resource /one must not be inherited by /two');
  assert.equal(secondRequest.route_id, ready.route_id);
  const second = await executeStep(session, secondRequest, dispatch, undefined, routing);
  const checkpointPath = path.join(session.casePath, second.checkpoint);
  const capturedCheckpoint = readFileSync(checkpointPath, 'utf8');
  assert.match(capturedCheckpoint, new RegExp(second.attempt_id));
  assert.match(capturedCheckpoint, /"status": "review"/);
  assert.ok(capturedCheckpoint.length < 8000, 'checkpoint contains the latest bounded state, not raw tool output');
  assert.equal(second.deduplication, 'invocation_only');
  assert.notEqual(first.check_id, second.check_id);
  assert.equal(calls, 2);
  await executeStep(session, { review: { summary: 'Second fixture observed', attempt: 'latest' } }, dispatch);
  assert.match(readFileSync(checkpointPath, 'utf8'), /"status": "done"/);
  const reopened = new FusionSession(boundConfig, 'automatic-read', root);
  assert.equal((await executeStep(reopened, expandRoute(reopened, { arguments: { method: 'GET', url: target + '/two' } }), dispatch, undefined, routing)).decision, 'reuse');
  assert.equal(calls, 2, 'restoration and JSON key ordering must not repeat the target call');
  const third = await executeStep(reopened, expandRoute(reopened, { arguments: { method: 'GET', url: target + '/two', auth_ref: 'other-test-role' } }), dispatch, undefined, routing);
  assert.notEqual(third.check_id, second.check_id, 'a changed identity reference changes the invocation');
  assert.throws(() => expandRoute(reopened, { route_id: ready.route_id, arguments: { method: 'POST', url: target + '/two' } }), /this call's work/);
  assert.throws(() => expandRoute(reopened, { route_id: ready.route_id, arguments: { method: 'GET', url: 'http://localhost:8093/two' } }), /this call's work/);
  assert.equal(expandRoute(new FusionSession(boundConfig, 'automatic-other', root), { arguments: { method: 'GET', url: target + '/two' } }).tool, undefined);
});

test('mismatched specialist gives concrete alternatives without preparing or dispatching a wrong route', async () => {
  const session = new FusionSession(config, 'mismatched-capability', root);
  await assert.rejects(prepareRoute(session, { skill: 'fusion-recon', capability: 'http.request', purpose: 'Read entry' }, [read]),
    error => /fusion-recon\/web.crawl/.test(error.message) && /fusion-api\/http.request/.test(error.message));
  assert.equal(session.state().current_route, undefined);
  assert.equal(existsSync(path.join(session.casePath, 'case.sqlite3')), false);
});

test('review accepts scoped short references and rejects a mistyped ID before dispatch', async () => {
  const session = new FusionSession(config, 'review-reference', root);
  let calls = 0;
  const dispatch = async () => { calls++; return { isError: false, content: [{ type: 'text', text: 'fixed sample' }] }; };
  const request = { target: 'fixture', objective: 'Observe fixture', scope: 'Local fixture', skill: 'fusion-js',
    capability: 'js.source', purpose: 'Read sample', tool: 'read', arguments: { file_path: 'sample.js' },
    work: { key: 'sample', conditions: { version: 'one' } } };
  const actual = await executeStep(session, request, dispatch);
  assert.equal(resolveReviewAttempt(session, actual.review_ref), actual.attempt_id);
  assert.equal(resolveReviewAttempt(session, 'latest'), actual.attempt_id);
  const wrong = actual.attempt_id.slice(0, -1) + (actual.attempt_id.endsWith('0') ? '1' : '0');
  await assert.rejects(executeStep(session, { ...request, review: { attempt: wrong, summary: 'Would review wrong ID' } }, dispatch),
    error => error.message.includes('Unknown review.attempt') && error.message.includes(actual.attempt_id) && !error.message.includes('ENOENT'));
  assert.equal(calls, 1, 'a bad review cannot dispatch the next action');
  await executeStep(session, { review: { attempt: actual.review_ref, summary: 'Observed the fixed sample' } }, dispatch);
  assert.equal(session.state().last_execution.status, 'done');
  assert.throws(() => resolveReviewAttempt(new FusionSession(config, 'foreign-review', root), actual.review_ref), /Unknown/);
  const prefix = 'CALL-' + 'a'.repeat(8);
  for (const tail of ['0', '1']) writeFileSync(path.join(session.root, 'receipts', prefix + tail.repeat(24) + '.json'), '{}');
  assert.throws(() => resolveReviewAttempt(session, prefix), /Ambiguous/);
});

test('current route reuse needs fresh arguments and conditions and never borrows another session', async () => {
  const a = new FusionSession(config, 'implicit-a', root), b = new FusionSession(config, 'implicit-b', root);
  const selected = await prepareRoute(a, { skill: 'fusion-js', capability: 'js.source', target: 'fixture',
    purpose: 'Inspect current source', objective: 'Understand fixture', scope: 'Local fixture only' }, [read]);
  const fresh = { arguments: { file_path: 'fixture.js' }, work: { key: 'source', conditions: { revision: 'v2' } } };
  const restored = new FusionSession(config, 'implicit-a', root);
  const expanded = expandRoute(restored, fresh);
  assert.equal(expanded.route_id, selected.route_id);
  assert.equal(expanded.tool, 'read'); assert.deepEqual(expanded.arguments, fresh.arguments);
  assert.deepEqual(expandRoute(b, fresh), fresh);
  const missingWork = expandRoute(restored, { arguments: fresh.arguments });
  assert.equal(missingWork.tool, 'read', 'the current method remains identifiable even when conditions are missing');
  await assert.rejects(executeStep(restored, missingWork, () => { throw new Error('must not dispatch'); }), /require work/);
  assert.equal(expandRoute(restored, { review: { summary: 'Observed' } }).tool, undefined);
  assert.equal(expandRoute(restored, { ...fresh, capability: 'binary.profile' }).route_id, undefined);
  const changedSchema = { ...read, parameters: { type: 'object', properties: { path: { type: 'string' } } } };
  assert.equal((await requireRoute(restored, expanded, [changedSchema])).response.status, 'route_ready');
  assert.equal(existsSync(path.join(a.casePath, 'case.sqlite3')), false, 'route preparation/recovery never executes');
});

test('stage delivery writes real Markdown and lists missing planned outputs without settling observations', async () => {
  const session = new FusionSession(config, 'stage-delivery', root);
  const result = await executeStep(session, { target: 'fixture', objective: 'Inspect fixture', scope: 'Local fixture only',
    mission: 'src', skill: 'fusion-api', capability: 'http.request', purpose: 'Read controlled observation', tool: 'fixture',
    arguments: {}, work: { key: 'control', conditions: { sample: 'v1' } }, deliverables: ['REPORT.md'] },
  async () => ({ isError: false, content: [{ type: 'text', text: 'Controlled observation, no interpretation yet' }] }));
  const pause = await closeStep(session, 'checkpoint', { summary: 'Fixture read', next: 'Review the existing observation' });
  assert.ok(pause.artifacts.includes('report/stage.md'));
  const longSummary = 'Captured fixture observations. '.repeat(60) + 'Actual impact remains unverified.';
  const final = await closeStep(session, 'deliver', { summary: longSummary });
  assert.equal(final.status, 'partial'); assert.equal(final.unresolved.review, 1);
  assert.equal(session.state().closure.summary, longSummary, 'full delivery text must remain on disk');
  const recovered = await session.recovery();
  assert.match(recovered.closure.summary, /Full delivery summary/);
  assert.ok(formatRecovery(recovered).length <= RECOVERY_MAX_CHARS);
  assert.equal(final.deliverables[0].status, 'missing');
  assert.match(readFileSync(final.report.path, 'utf8'), new RegExp(result.attempt_id));
  assert.equal(digest(readFileSync(final.report.path)), final.report.sha256);
  session.update({ task: { ...session.state().task, deliverables: ['../foreign.md'] } });
  await assert.rejects(closeStep(session, 'deliver', { summary: 'Cannot export foreign path' }), /inside this session/);
});

test('equivalent root URLs bind once, while ports, paths, queries and foreign tools remain separated', async () => {
  assert.ok(sameTarget('HTTP://LOCALHOST:80/', 'http://localhost'));
  for (const other of ['http://localhost:81', 'https://localhost', 'http://localhost/app', 'http://localhost/?x=1', 'http://localhost/#/other']) {
    assert.equal(sameTarget('http://localhost/', other), false);
  }
  assert.equal(sameTarget('http://localhost/app', 'http://localhost/app/'), false);
  const a = { ...read, name: 'mcp__a__http' }, b = { ...read, name: 'mcp__b__http' };
  const session = new FusionSession({ ...config, requireMission: true,
    capabilityTools: { 'web.crawl': [a.name, b.name] }, boundTools: { [a.name]: 'http://localhost:8080', [b.name]: 'http://localhost:8081' } }, 'url-alias', root);
  const request = { target: 'http://localhost:8080/', mission: 'src', objective: 'Observe local entry', scope: 'Only this origin',
    skill: 'fusion-recon', capability: 'web.crawl', purpose: 'Baseline', arguments: { file_path: 'unused-fixture' }, work: { key: 'baseline', conditions: { resource: '/' } } };
  const missing = { ...request }; delete missing.mission;
  assert.equal((await prepareRoute(session, missing, [a, b])).status, 'mission_required');
  const ready = await prepareRoute(session, request, [b, a]);
  assert.equal(ready.execution.tool, a.name); assert.equal(ready.execution.context_required, false);
  let calls = 0;
  const actual = await executeStep(session, expandRoute(session, { route_id: ready.route_id }), async () => {
    calls++; return { isError: false, content: [{ type: 'text', text: 'controlled observation' }] };
  });
  assert.equal(actual.status, 'review'); assert.equal(calls, 1);
  assert.equal(session.state().task.target, 'http://localhost:8080');
  assert.equal((await prepareRoute(session, request, [a, b])).execution.context_required, false);
  await assert.rejects(prepareRoute(session, { ...request, tool: b.name }, [a, b]), /another target/);
  await assert.rejects(prepareRoute(session, { ...request, target: 'http://localhost:8081' }, [a, b]), /Target differs/);
  await assert.rejects(executeStep(session, { ...request, tool: b.name }, () => { calls++; }), /another target/);
  assert.equal(calls, 1);
});

test('collection methods cannot silently carry account writes; the same tool remains usable under API routing', async () => {
  const tool = { ...read, name: 'mcp__fixture__http_request' }, target = 'http://localhost:8088';
  const session = new FusionSession({ ...config, boundTools: { [tool.name]: target },
    capabilityTools: { 'web.crawl': [tool.name], 'http.request': [tool.name] } }, 'method-boundary', root);
  const request = { mission: 'src', target, skill: 'fusion-recon', capability: 'web.crawl', purpose: 'Observe entry',
    arguments: { method: 'get', url: target } };
  const ready = await prepareRoute(session, request, [tool]);
  assert.match(ready.route_id, /^ROUTE-[a-f0-9]{8}$/);
  const wrong = expandRoute(session, { route_id: ready.route_id, arguments: { method: 'POST', url: target } });
  await assert.rejects(requireRoute(session, wrong, [tool]), /entry collection/);
  const correct = await prepareRoute(session, { ...wrong, skill: 'fusion-api', capability: 'http.request' }, [tool]);
  assert.equal(correct.execution.tool, tool.name);
  assert.equal(correct.execution.context_required, false);
  const retry = await prepareRoute(session, { skill: 'fusion-api', capability: 'http.request', target }, [tool]);
  const restored = expandRoute(session, { route_id: retry.route_id });
  assert.equal(restored.purpose, wrong.purpose);
  assert.equal(restored.arguments, undefined, 'method recovery must not replay old arguments');
  assert.throws(() => expandRoute(session, { route_id: 'ROUTE-invented' }), error => error.message.includes(retry.route_id));
  const legacyId = retry.route_id + '0123456789abcdef';
  session.update({ prepared_routes: session.state().prepared_routes.map(r => r.id === retry.route_id ? { ...r, id: legacyId } : r) });
  assert.equal((await prepareRoute(session, { skill: 'fusion-api', capability: 'http.request', target }, [tool])).route_id, legacyId,
    'existing integrations retain their already-issued long IDs');
  assert.equal(existsSync(path.join(session.casePath, 'case.sqlite3')), false, 'route correction makes no target call');
});

test('existing bound tools use recent outcomes; explicit alternatives remain possible without automatic retries', async () => {
  const a = { ...read, name: 'mcp__first__http' }, b = { ...read, name: 'mcp__second__http' };
  const target = 'http://localhost:8090';
  const session = new FusionSession({ ...config, capabilityTools: { 'http.request': [a.name, b.name] },
    boundTools: { [a.name]: target, [b.name]: target } }, 'ranked-tools', root);
  session.activate(); session.observe(a.name, { isError: true }, target); session.observe(b.name, { isError: false }, target);
  const request = { target, skill: 'fusion-api', capability: 'http.request', purpose: 'Controlled request' };
  const selected = await prepareRoute(session, request, [a, b]);
  assert.equal(selected.execution.tool, b.name);
  assert.equal(selected.target_action_executed, false);
  assert.deepEqual(selected.execution.alternatives, [a.name]);
  assert.equal((await prepareRoute(session, { ...request, tool: a.name }, [a, b])).execution.tool, a.name);
  assert.equal(existsSync(path.join(session.casePath, 'case.sqlite3')), false, 'selection is never an implicit retry');
});

test('local reads and literal searches are flexible only for owned files; case writes still need capture', async () => {
  const a = new FusionSession(config, 'managed-a', root), b = new FusionSession(config, 'managed-b', root);
  a.activate(); b.activate(); mkdirSync(a.casePath); mkdirSync(b.casePath);
  const own = path.join(a.casePath, 'body.js'), foreign = path.join(b.casePath, 'body.js');
  writeFileSync(own, 'controlled source'); writeFileSync(foreign, 'other case');
  for (const name of ['read', 'grep']) {
    const args = file => name === 'read' ? { file_path: file } : { path: file, pattern: 'source' };
    assert.equal(guardReason(a, { name, arguments: args(own) }), undefined);
    assert.match(guardReason(a, { name, arguments: args(foreign) }), /protected/);
  }
  assert.match(guardReason(a, { name: 'write', arguments: { file_path: own, content: 'change' } }), /protected/);
  assert.match(guardReason(a, { name: 'grep', arguments: { path: a.root, pattern: 'source' } }), /protected/, 'recursive traversal is not an implicit read exception');
});

test('external artifacts require a tool-specific host root and immutable hash', () => {
  const sourceRoot = path.join(root, 'mcp-owned'); mkdirSync(sourceRoot);
  const source = path.join(sourceRoot, 'body.js'); writeFileSync(source, 'observed source');
  const session = new FusionSession({ ...config, toolArtifactRoots: { mcp__owned__read: sourceRoot } }, 'artifact-import', root);
  session.activate();
  const result = pointer => ({ content: [{ type: 'text', text: JSON.stringify({ artifacts: [pointer] }) }] });
  const pointer = { path: source, sha256: digest('observed source') };
  const [saved] = importToolArtifacts(session, 'mcp__owned__read', result(pointer), session.root, 'CALL-fixture');
  writeFileSync(source, 'changed later'); assert.equal(readFileSync(saved.capture, 'utf8'), 'observed source');
  assert.deepEqual(importToolArtifacts(session, 'mcp__foreign__read', result(pointer), session.root, 'CALL-foreign'), []);
  assert.throws(() => importToolArtifacts(session, 'mcp__owned__read', result(pointer), session.root, 'CALL-changed'), /hash mismatch/);
  assert.throws(() => importToolArtifacts(session, 'mcp__owned__read', result({ path: path.join(pack, 'SKILL.md'), sha256: pointer.sha256 }), session.root, 'CALL-escape'), /outside/);
});

test('report citation prefixes must resolve to one actual receipt and return canonical IDs', () => {
  const first = { attempt_id: 'CALL-' + 'a'.repeat(31) + '0' }, second = { attempt_id: 'CALL-' + 'a'.repeat(31) + '1' };
  assert.deepEqual(resolveReceiptCitations('Observed CALL-aaaaaaaa', [first]), [first.attempt_id]);
  assert.throws(() => resolveReceiptCitations('Observed CALL-aaaaaaaa', [first, second]), /Ambiguous/);
  assert.throws(() => resolveReceiptCitations('Observed CALL-bbbbbbbb', [first]), /unobserved/);
  assert.throws(() => resolveReceiptCitations('Observed CALL-aaaaaaa', [first]), /must cite/);
});

test('partial delivery preserves unresolved observations instead of declaring them done', async () => {
  const session = new FusionSession(config, 'partial-observation', root);
  const actual = await executeStep(session, { target: 'fixture', objective: 'Assess a fixture', scope: 'Local fixture only',
    mission: 'src', skill: 'fusion-api', capability: 'http.request', purpose: 'Read controlled response', tool: 'fixture',
    arguments: {}, work: { key: 'control', conditions: { sample: 'v1' } }, deliverables: ['REPORT.md'] },
  async () => ({ isError: false, content: [{ type: 'text', text: 'Observation awaiting judgement' }] }));
  writeFileSync(path.join(session.casePath, 'REPORT.md'), 'Partial: observation not yet reviewed. ' + actual.attempt_id.slice(0, 13));
  const done = await closeStep(session, 'finish', { status: 'partial', report: 'REPORT.md', summary: 'Observation remains unresolved' });
  assert.equal(done.status, 'partial'); assert.equal(done.unresolved.review, 1);
  const restored = await session.cli('resume', []);
  assert.equal(restored.stored_status_counts.review, 1); assert.equal(restored.stored_status_counts.done || 0, 0);
});

test('unprepared dispatch returns the source method first; restart restores the exact route and actual receipt', async () => {
  const session = new FusionSession(config, 'read-route', root);
  const sample = path.join(root, 'sample.js'); writeFileSync(sample, 'const control = "controlled-fixture";');
  const request = { skill: 'fusion-js', capability: 'js.source', purpose: 'Read actual sample source',
    target: sample, objective: 'Identify fixture control', scope: 'Only this local fixture', tool: 'read',
    arguments: { file_path: sample }, work: { key: 'source', conditions: { revision: 'fixture-v1' } } };
  const first = await requireRoute(session, request, [read]);
  assert.equal(first.response.status, 'route_ready');
  assert.equal(first.response.target_action_executed, false);
  assert.equal(first.response.guidance.composition.host, 'dsh');
  assert.deepEqual(first.response.guidance.composition.components, ['evidence', 'isolation']);
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
  assert.equal(actual.routing.composition_sha256.length, 64);
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
  const bookkeeping = await prepareRoute(session, { ...request, capability: 'evidence.persist' }, [read, { ...read, name: 'write' }]);
  assert.equal(bookkeeping.status, 'tool_choice_required', 'read and write are not interchangeable alternatives');
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
  const components = path.join(local, 'manifests/components.json');
  const data = JSON.parse(readFileSync(components, 'utf8')); data.selection_policy += ' fixture revision';
  writeFileSync(components, JSON.stringify(data));
  assert.equal((await requireRoute(session, expanded, [shell])).response.status, 'route_ready', 'changed composition invalidates a prepared route');
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
