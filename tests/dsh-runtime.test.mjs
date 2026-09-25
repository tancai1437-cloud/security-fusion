import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { FusionSession, validateArgs, visibleRecovery } from '../adapters/dsh-runtime.mjs';

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
