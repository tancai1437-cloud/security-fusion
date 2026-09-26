// Optional tests against the installed DSH SDK; no SDK dependency is bundled.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const runtime = process.env.FUSION_DSH_RUNTIME;
test('real DSH schema accepts encoded objects, rejects invalid leaf args before ledger creation, and replaces only state',
  { skip: !runtime }, async () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
    const temporary = mkdtempSync(path.join(os.tmpdir(), 'fusion-sdk-'));
    const packageUrl = name => pathToFileURL(path.join(runtime, 'node_modules/@deepseek-ai', name, 'lib/index.js')).href;
    for (const name of ['dsh.mjs', 'dsh-runtime.mjs', 'dsh-execution.mjs', 'dsh-routing.mjs']) {
      let code = readFileSync(path.join(root, 'adapters', name), 'utf8');
      for (const pkg of ['dsh-tools', 'dsh-llm']) code = code.replaceAll(`'@deepseek-ai/${pkg}'`, JSON.stringify(packageUrl(pkg)));
      writeFileSync(path.join(temporary, name), code);
    }
    const { apply } = await import(pathToFileURL(path.join(temporary, 'dsh.mjs')));
    const { Session } = await import(packageUrl('dsh-session'));
    const { createUserMessage } = await import(packageUrl('dsh-llm'));
    const { replaceRecovery } = await import(pathToFileURL(path.join(temporary, 'dsh-runtime.mjs')));
    const stored = Session.create('sdk-surface');
    const user = createUserMessage({ source: { kind: 'user' }, content: [{ type: 'text', text: 'Original task' }] });
    stored.append('user/message', user, { surfaceOp: 'append' });
    for (let n = 0; n < 2; n++) stored.append('user/message', createUserMessage({
      source: { kind: 'security-fusion-state', digest: 'legacy-' + n }, content: [{ type: 'text', text: 'Legacy full state' }],
    }), { surfaceOp: 'append' });
    for (let n = 0; n < 12; n++) {
      const message = createUserMessage({ source: { kind: 'security-fusion-state', digest: String(n) },
        content: [{ type: 'text', text: 'Current state ' + n }] });
      if (!replaceRecovery(stored, message)) stored.append('user/message', message, { surfaceOp: 'append' });
    }
    assert.equal(stored.surface.nodes.length, 3, 'one user message, one short retirement marker, one full state');
    assert.equal(stored.surface.nodes.filter(seq => stored.eventAt(seq).data.source.kind === 'security-fusion-state').length, 1);
    assert.equal(stored.snapshotEvents().length, 16);
    assert.equal(stored.deriveMessages()[0].content[0].text, 'Original task');
    let fusion;
    const ctx = { on() {}, tools: { register(tool) { fusion = tool; }, guard() {}, get() {
      return { parameters: { type: 'object', properties: { description: { type: 'string' } }, required: ['description'] } };
    } } };
    const stateDir = path.join(temporary, 'state');
    apply(ctx, { skillRoot: root, stateDir });
    const exec = { agent: { session: { id: 'sdk-input', header: { cwd: temporary } } }, signal: AbortSignal.timeout(15000) };
    await assert.rejects(fusion.execute({ action: 'execute', request: JSON.stringify({ tool: 'fixture', arguments: {} }) }, exec),
      /description.*No target call or failed check/s);
    assert.equal(existsSync(stateDir), false, 'invalid tool arguments must not start a case or reserve an attempt');
    await assert.rejects(fusion.execute({ action: 'execute', request: '{"unexpected":true}' }, exec), /unexpected/);
    const suspended = JSON.parse(await fusion.execute({ action: 'suspend', request: '{"reason":"Analysis only"}' }, exec));
    assert.equal(suspended.status, 'suspended');
  });

test('adapter intercepts entry reads, prepares before dispatch and records the selected route using real SDK schemas',
  { skip: !runtime }, async () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
    const temporary = mkdtempSync(path.join(os.tmpdir(), 'fusion-route-sdk-'));
    const packageUrl = name => pathToFileURL(path.join(runtime, 'node_modules/@deepseek-ai', name, 'lib/index.js')).href;
    for (const name of ['dsh.mjs', 'dsh-runtime.mjs', 'dsh-execution.mjs', 'dsh-routing.mjs']) {
      let code = readFileSync(path.join(root, 'adapters', name), 'utf8');
      for (const pkg of ['dsh-tools', 'dsh-llm']) code = code.replaceAll(`'@deepseek-ai/${pkg}'`, JSON.stringify(packageUrl(pkg)));
      writeFileSync(path.join(temporary, name), code);
    }
    const { apply } = await import(pathToFileURL(path.join(temporary, 'dsh.mjs')));
    const { defineTool } = await import(packageUrl('dsh-tools'));
    const { FusionSession } = await import(pathToFileURL(path.join(temporary, 'dsh-runtime.mjs')));
    const registered = new Map(), events = new Map(); let guard, calls = 0;
    registered.set('read', defineTool({ name: 'read', description: 'Read fixture file',
      parameters: { file_path: { type: 'string', required: true } },
      output: { schema: { type: 'string' }, render: (_, value) => [{ type: 'text', text: value }] },
      execute(args) { calls++; return readFileSync(args.file_path, 'utf8'); } }));
    registered.set('write', defineTool({ name: 'write', description: 'Write actual fixture output',
      parameters: { file_path: { type: 'string', required: true }, content: { type: 'string', required: true } },
      output: { schema: { type: 'string' }, render: (_, value) => [{ type: 'text', text: value }] },
      execute(args) { calls++; mkdirSync(path.dirname(args.file_path), { recursive: true }); writeFileSync(args.file_path, args.content); return 'Written'; } }));
    const ctx = { on(name, fn) { events.set(name, fn); }, tools: {
      register(tool) { registered.set(tool.name, tool); }, guard(fn) { guard = fn; },
      get(name) { return registered.get(name); },
      schemas() { return [...registered.values()].map(({ name, description, parameters }) => ({ name, description, parameters })); },
      async execute(exec) {
        assert.equal(guard(exec), undefined, 'actual child remains within host execution guard');
        const tool = registered.get(exec.name), value = await tool.execute(exec.arguments, exec);
        return { isError: false, content: tool.output.render(exec.arguments, value) };
      },
    } };
    const config = { skillRoot: root, stateDir: path.join(temporary, 'state') };
    apply(ctx, config);
    const agent = { session: { id: 'route-sdk', header: { cwd: temporary } } };
    const session = new FusionSession(config, agent.session.id, temporary);
    assert.equal(guard({ agent, name: 'read', arguments: { file_path: 'unrelated' } }), undefined);
    events.get('tools/result')({ agent, name: 'read', arguments: { file_path: path.join(root, 'SKILL.md') } }, { isError: false });
    assert.equal(session.state().active, true);
    assert.match(guard({ agent, name: 'read', arguments: { file_path: 'unrelated' } }), /route/);
    const sample = path.join(temporary, 'fixture.js'); writeFileSync(sample, 'const actual = 27;');
    const tool = registered.get('fusion');
    const exec = { agent, signal: AbortSignal.timeout(20000), rootCallId: 'root', token: { id: 'parent' }, deferContext() {} };
    const request = { target: sample, scope: 'This local fixture only', objective: 'Read the constant',
      skill: 'fusion-js', capability: 'js.source', purpose: 'Inspect source',
      work: { key: 'fixture', conditions: { sample: 'v1' } }, tool: 'read', arguments: { file_path: sample } };
    const ready = JSON.parse(await tool.execute({ action: 'execute', request }, exec));
    assert.equal(ready.status, 'route_ready'); assert.equal(calls, 0);
    await assert.rejects(tool.execute({ action: 'run', args: ['--check', 'fake', '--', 'echo', 'bypass'] }, exec), /cannot bypass/);
    await assert.rejects(tool.execute({ action: 'advance', args: ['--execute-l'] }, exec), /cannot bypass/);
    const actual = JSON.parse(await tool.execute({ action: 'execute', request: { route_id: ready.route_id } }, exec));
    assert.equal(actual.routing.id, ready.route_id); assert.equal(calls, 1);
    assert.match(actual.observed.text, /actual = 27/);
    const reviewOnly = JSON.parse(await tool.execute({ action: 'execute', request: {
      route_id: ready.route_id, review: { summary: 'Actual source declares constant 27' } } }, exec));
    assert.equal(reviewOnly.status, 'reviewed'); assert.equal(calls, 1, 'review with a route locator must never replay the tool');
    const alias = JSON.parse(await tool.execute({ action: 'review', request: {
      review: { attempt: actual.attempt_id, summary: 'The same captured source observation' } } }, exec));
    assert.equal(alias.status, 'reviewed'); assert.equal(calls, 1, 'structured review and CLI review must not be confused');
    const next = JSON.parse(await tool.execute({ action: 'execute', request: { ...request,
      capability: 'evidence.persist', review: { summary: 'The source declares the constant 27' } } }, exec));
    assert.equal(next.status, 'route_ready'); assert.equal(next.previous_review, 'reviewed');
    assert.equal(session.state().last_execution.status, 'done', 'preparation must not swallow the previous review');
    assert.equal(explicitReviewSaved(session), false, 'route defaults never replay judgement');
    const content = '# Actual report\nQuotes: "controlled", nested JSON: {"result":27}\n中文\\path\n';
    const preparedSave = JSON.parse(await tool.execute({ action: 'save', file_path: 'REPORT.md', content }, exec));
    assert.equal(preparedSave.status, 'route_ready');
    const saved = JSON.parse(await tool.execute({ action: 'execute', request: { route_id: preparedSave.route_id } }, exec));
    assert.equal(saved.status, 'done');
    assert.equal(readFileSync(path.join(session.casePath, 'REPORT.md'), 'utf8'), content);
    const again = JSON.parse(await tool.execute({ action: 'save', file_path: 'second.md', content }, exec));
    assert.equal(again.status, 'done', 'known writer route should save immediately without repeated preparation');
    assert.equal(readFileSync(path.join(session.casePath, 'second.md'), 'utf8'), content);
    session.update({ mode: 'paused' });
    await assert.rejects(tool.execute({ action: 'execute', request: '{broken JSON' }, exec), /JSON|property/);
    assert.equal(session.state().mode, 'executing', 'an explicit attempted continuation must not retain a completed pause status after parameter failure');
    events.get('tools/result')({ agent, name: 'fusion', arguments: { action: 'execute' } },
      { isError: true, error: { message: 'Invalid request shape' } });
    assert.equal(session.state().tool_errors.fusion, 'Invalid request shape');
  });

function explicitReviewSaved(session) {
  return session.state().prepared_routes.some(r => r.defaults.review !== undefined);
}
