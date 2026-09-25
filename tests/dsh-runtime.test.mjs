import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { FusionSession, validateArgs, visibleRecovery } from '../adapters/dsh-runtime.mjs';
import { executeStep, closeStep, guardReason, stopCorrection, recordTurnOutcome } from '../adapters/dsh-execution.mjs';

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
      capability: 'http.request', purpose: 'Observe baseline', tool: 'http_reader', arguments: { url: target },
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
    writeFileSync(path.join(root, 'answer.md'), 'Fixture report cites fabricated CALL-00000000000000000000000000000000');
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Cannot submit fabricated receipt', report: 'answer.md' }), /unobserved execution/);
    writeFileSync(path.join(root, 'answer.md'), 'Fixture report: protected_access=false. Observed ' + first.attempt_id);
    await assert.rejects(closeStep(restored, 'finish', { summary: 'Stage files still missing', report: 'answer.md' }), /Specialist deliverables missing/);
    const partial = await closeStep(restored, 'finish', { summary: 'Explicitly incomplete stage files', report: 'answer.md', status: 'partial' });
    assert.equal(partial.status, 'partial');
    assert.equal(partial.delivery_gaps.length, 2);
    const stage = path.join(restored.casePath, 'specialists/fusion-web');
    mkdirSync(stage, { recursive: true });
    for (const file of ['web-checks.json', 'candidates.json']) writeFileSync(path.join(stage, file), '[]');
    const end = await closeStep(restored, 'finish', { summary: 'Fixture inspected', report: 'answer.md' });
    assert.equal(end.status, 'submitted');
    assert.deepEqual(end.delivery_gaps, []);
    assert.equal(end.deliverables.length, 1);
    assert.equal(stopCorrection(restored, 2), undefined);
    assert.equal((await restored.recovery()).closure.report.sha256, end.report.sha256);
  } finally { await new Promise(resolve => server.close(resolve)); }
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
    purpose: 'Execute local fixture', capability: 'js.runtime', tool: 'test_runner', arguments: {} };
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
