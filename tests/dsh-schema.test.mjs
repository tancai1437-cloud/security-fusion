// Optional tests against the installed DSH SDK; no SDK dependency is bundled.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const runtime = process.env.FUSION_DSH_RUNTIME;
test('real DSH schema accepts encoded objects, rejects invalid leaf args before ledger creation, and replaces only state',
  { skip: !runtime }, async () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
    const temporary = mkdtempSync(path.join(os.tmpdir(), 'fusion-sdk-'));
    const packageUrl = name => pathToFileURL(path.join(runtime, 'node_modules/@deepseek-ai', name, 'lib/index.js')).href;
    for (const name of ['dsh.mjs', 'dsh-runtime.mjs', 'dsh-execution.mjs']) {
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
