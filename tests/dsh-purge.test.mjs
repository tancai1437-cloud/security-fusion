import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, symlinkSync, readdirSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { FusionSession } from '../adapters/dsh-runtime.mjs';
import { engagementFor, wrapDataTool, PURGE_TOOLS } from '../adapters/dsh-purge-bridge.mjs';
import { composePreset } from '../adapters/dsh-purge-preset.mjs';

const pack = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
function setup() {
  const cwd = mkdtempSync(path.join(os.tmpdir(), 'fusion-purge-'));
  const config = { skillRoot: pack, stateDir: path.join(cwd, 'private'), dshHome: cwd, runtime: cwd };
  const session = new FusionSession(config, 'A', cwd);
  session.update({ task: { target: 'fixture-A.invalid', scope: 'Fixture A only' }, mode: 'executing' });
  return { cwd, config, session };
}
function storeFixture(root) {
  const records = new Map(); let current = 'unrelated';
  return { root, records, get current() { return current; }, listEngagements: () => [...records.values()],
    openEngagement(name, scope, opts) { assert.equal(opts.bindCurrent, false); const item = { id: name, name, scope }; records.set(name, item); return item; } };
}

test('durable per-session Drill binding ignores global current and rejects missing/changed stores', () => {
  const { config, cwd, session } = setup(), store = storeFixture(cwd);
  const a = engagementFor(session, store);
  assert.equal(store.current, 'unrelated');
  const restarted = new FusionSession(config, 'A', cwd);
  assert.deepEqual(engagementFor(restarted, store), a);
  const second = new FusionSession(config, 'B', cwd);
  second.update({ task: { target: 'fixture-B.invalid', scope: 'B only' }, mode: 'executing' });
  const b = engagementFor(second, store);
  assert.notEqual(a.id, b.id); assert.equal(store.records.size, 2);
  restarted.update({ task: { target: 'changed', scope: 'A only' } });
  assert.throws(() => engagementFor(restarted, store), /binding changed/);
  store.records.delete(b.id);
  assert.throws(() => engagementFor(second, store), /is missing/);
});

test('data calls receive an explicit engagement and semantic failures are not successful receipts', async () => {
  const { config, cwd, session } = setup(), store = storeFixture(cwd);
  let received;
  const tool = wrapDataTool({ name: 'redteam_asset_query', description: 'Fixture',
    execute(args) { received = args; return JSON.stringify({ ok: true, items: [] }); } }, config, store);
  const exec = { agent: { session: { id: 'A', header: { cwd } } } };
  const result = JSON.parse(await tool.execute({ limit: 1 }, exec));
  assert.equal(received.engagement, session.state().purge.id);
  assert.equal(result.fusion_binding.target, 'fixture-A.invalid');
  await assert.rejects(tool.execute({ engagement: 'other' }, exec), /Cross-case/);
  const failed = wrapDataTool({ name: 'redteam_asset_query', description: '',
    execute: () => JSON.stringify({ ok: false, error: 'DB unavailable' }) }, config, store);
  await assert.rejects(failed.execute({}, exec), /DB unavailable/);
  const inventory = wrapDataTool({ name: 'redteam_preflight', description: '', execute: () => JSON.stringify({
    ok: false, onboarding: { missing: ['fixture tool'], configured: { fofa_key: 'configured(ABCD…WXYZ)' } } }) }, config, store);
  const gaps = JSON.parse(await inventory.execute({ include: 'fixture' }, exec));
  assert.equal(gaps.ready, false); assert.deepEqual(gaps.onboarding.missing, ['fixture tool']);
  assert.equal(gaps.onboarding.configured.fofa_key, 'configured');
  session.update({ mode: 'suspended' });
  await assert.rejects(tool.execute({}, exec), /Start\/resume/);
});

test('preset reuses one compaction owner, limits skill discovery and excludes delegation/anchor controller', () => {
  const { config } = setup();
  const standard = ['persona', 'skill-filesystem', 'tool-skill', 'tool-fs', 'tool-web', 'compaction', 'delegation', 'anchor-gate']
    .map(id => ({ id, name: id, config: id === 'compaction' ? [{ id: 'compaction-basic' }] : {} }));
  const original = JSON.stringify(standard), preset = composePreset(standard, config);
  assert.equal(JSON.stringify(standard), original);
  assert.equal(preset.plugins.filter(r => r.id === 'compaction').length, 1);
  assert.equal(preset.plugins.some(r => ['delegation', 'anchor-gate'].includes(r.id)), false);
  const discovery = preset.plugins.find(r => r.id === 'skill-filesystem').config;
  assert.equal(discovery.includeDefaultRoots, false); assert.equal(discovery.customSkillDirs[0], pack);
  const adapter = preset.plugins.find(r => r.id === 'fusion-execution');
  assert.deepEqual(new Set(adapter.config.capabilityTools['evidence.persist']), PURGE_TOOLS);
  assert.throws(() => composePreset(standard.filter(r => r.id !== 'compaction'), config), /changed/);
});

const purgeRoot = process.env.FUSION_PURGE_SOURCE, sdk = process.env.FUSION_DSH_RUNTIME;
test('installed SDK + actual upstream Drill tools/SQLite keep two targets separate across bridge restart',
  { skip: !purgeRoot || !sdk }, async () => {
    const { config, cwd, session } = setup();
    const profile = path.join(cwd, 'profiles', 'web'); mkdirSync(profile, { recursive: true });
    writeFileSync(path.join(profile, 'package.json'), '{}');
    symlinkSync(path.join(sdk, 'node_modules'), path.join(profile, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
    const previous = process.env.DSH_HOME; process.env.DSH_HOME = cwd;
    try {
      const { RedteamStore } = await import(pathToFileURL(path.join(purgeRoot, 'lib/redteam/store-core.js')));
      const native = await import(pathToFileURL(path.join(purgeRoot, 'lib/redteam/tools.js')));
      const store = new RedteamStore(path.join(cwd, 'redteam'));
      try {
        store.openEngagement('unrelated-active', []);
        const registry = new Map();
        native.apply({ redteam: store, on() {}, get: () => null, tools: { register(t) { registry.set(t.name, t); } } });
        assert.ok([...PURGE_TOOLS].every(n => registry.has(n)));
        const call = (id, name, args) => wrapDataTool(registry.get(name), config, store).execute(args,
          { agent: { session: { id, header: { cwd } } } });
        await call('A', 'redteam_asset_add', { ip: '192.0.2.11', provenance: 'passive', tool: 'local fixture, no network' });
        const other = new FusionSession(config, 'B', cwd);
        other.update({ task: { target: 'fixture-B.invalid', scope: 'Fixture B only' }, mode: 'executing' });
        await call('B', 'redteam_asset_add', { ip: '192.0.2.22', provenance: 'passive', tool: 'local fixture, no network' });
        store.setActiveEngagement(other.state().purge.id);
        const a = JSON.parse(await call('A', 'redteam_asset_query', { limit: 5 }));
        const b = JSON.parse(await call('B', 'redteam_asset_query', { limit: 5 }));
        assert.deepEqual(a.items.map(x => x.ip), ['192.0.2.11']);
        assert.deepEqual(b.items.map(x => x.ip), ['192.0.2.22']);
        assert.equal(a.engagement, session.state().purge.id);
        await assert.rejects(call('A', 'redteam_asset_query', { engagement: b.engagement }), /Cross-case/);
        await assert.rejects(call('A', 'redteam_asset_get', { id: 99999 }), /asset not found/);
        const restarted = new FusionSession(config, 'A', cwd);
        assert.equal(engagementFor(restarted, store).id, a.engagement);
      } finally { store.close(); }
    } finally { if (previous === undefined) delete process.env.DSH_HOME; else process.env.DSH_HOME = previous; }
  });

test('composition parses the pinned official 0.2 preset using the host YAML schema without evaluating !!js',
  { skip: !sdk || !process.env.FUSION_DSH_SOURCE }, () => {
    const require = createRequire(path.join(sdk, 'package.json'));
    const { entryListSchema } = require('@deepseek-ai/cordis-plugin-include');
    const yaml = createRequire(require.resolve('@deepseek-ai/cordis-plugin-include'))('js-yaml');
    const source = path.join(process.env.FUSION_DSH_SOURCE, 'packages/bundle/web-app/presets/standard.patch.yml');
    const rows = yaml.load(readFileSync(source, 'utf8'), { schema: entryListSchema });
    const definition = rows.flatMap(r => r.insert || []).find(r => r.id === 'preset-standard');
    const preset = composePreset(definition.config.plugins, setup().config);
    assert.equal(preset.plugins.filter(r => r.id === 'compaction').length, 1);
    assert.ok(preset.plugins.some(r => r.name === '@deepseek-ai/dsh-tool-bash'));
    assert.equal(preset.plugins.some(r => /subagent|workflow|ralph/.test(r.name)), false);
    assert.deepEqual(preset.plugins.find(r => r.id === 'tool-bash').disabled, { __jsExpr: "process.platform === 'win32'" });
  });

test('actual Cordis/ToolRuntime dispatches fusion routes into native Drill and records failed data calls',
  { skip: !purgeRoot || !sdk }, async () => {
    const { config, cwd } = setup();
    const require = createRequire(path.join(sdk, 'package.json'));
    const load = name => import(pathToFileURL(require.resolve('@deepseek-ai/' + name)));
    const { Context } = await load('cordis');
    const { default: SystemPrompt } = await load('dsh-system-prompt');
    const { default: ToolRuntime } = await load('dsh-tools');
    const ctx = new Context();
    await ctx.plugin(SystemPrompt); await ctx.plugin(ToolRuntime);
    const { default: SkillRegistry } = await load('dsh-skill');
    const SkillFilesystem = await load('dsh-skill-filesystem');
    await ctx.plugin(SkillRegistry);
    await ctx.plugin(SkillFilesystem, { includeDefaultRoots: false, customSkillDirs: [pack], watch: false });
    assert.deepEqual((await ctx.skills.list({ cwd })).map(s => s.name), ['security-fusion']);
    assert.match((await ctx.skills.get('security-fusion', { cwd })).content, /fusion\(action="route"/);
    const profile = path.join(cwd, 'profiles', 'web'); mkdirSync(profile, { recursive: true });
    writeFileSync(path.join(profile, 'package.json'), '{}');
    symlinkSync(path.join(sdk, 'node_modules'), path.join(profile, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
    const previous = process.env.DSH_HOME; process.env.DSH_HOME = cwd;
    let store;
    try {
      for (const filename of readdirSync(path.join(pack, 'adapters')).filter(n => n.endsWith('.mjs'))) {
        let code = readFileSync(path.join(pack, 'adapters', filename), 'utf8');
        for (const pkg of ['dsh-tools', 'dsh-llm', 'dsh-session']) code = code.replaceAll(`'@deepseek-ai/${pkg}'`, JSON.stringify(pathToFileURL(require.resolve('@deepseek-ai/' + pkg)).href));
        code = code.replace("'dsh-purge/redteam/tools'", JSON.stringify(pathToFileURL(path.join(purgeRoot, 'lib/redteam/tools.js')).href));
        writeFileSync(path.join(cwd, filename), code);
      }
      const { RedteamStore } = await import(pathToFileURL(path.join(purgeRoot, 'lib/redteam/store-core.js')));
      store = new RedteamStore(path.join(cwd, 'redteam')); ctx.provide('redteam', store);
      const bridge = await import(pathToFileURL(path.join(cwd, 'dsh-purge-bridge.mjs')));
      const adapter = await import(pathToFileURL(path.join(cwd, 'dsh.mjs')));
      await bridge.apply(ctx, config);
      adapter.apply(ctx, { ...config, integration: 'dsh-purge', capabilityTools: { 'evidence.persist': [...PURGE_TOOLS] } });
      assert.equal(ctx.tools.schemas().filter(t => t.name.startsWith('redteam_')).length, PURGE_TOOLS.size);
      const agent = { session: { id: 'pipeline', header: { cwd } } };
      let seq = 0;
      const call = async (action, request) => {
        const result = await ctx.tools.execute({ name: 'fusion', arguments: { action, ...(request ? { request } : {}) },
          agent, callId: 'pipeline-' + (++seq), signal: AbortSignal.timeout(15000) });
        assert.equal(result.isError, false, JSON.stringify(result));
        return JSON.parse(result.content[0].text);
      };
      const ready = await call('route', { skill: 'fusion-recon', capability: 'evidence.persist', tool: 'redteam_asset_add',
        target: 'fixture.invalid', scope: 'Local fixture records only', objective: 'Record one controlled asset',
        purpose: 'Persist fixture asset', arguments: { ip: '192.0.2.31', provenance: 'passive', tool: 'fixture' } });
      const actual = await call('execute', { route_id: ready.route_id });
      assert.equal(actual.status, 'review'); assert.ok(actual.attempt_id.startsWith('CALL-'));
      const restored = new FusionSession(config, 'pipeline', cwd);
      assert.equal(store.listAssets(restored.state().purge.id, { limit: 5 }).items[0].ip, '192.0.2.31');
      const denied = await ctx.tools.execute({ name: 'redteam_asset_query', arguments: {}, agent,
        callId: 'direct-bypass', signal: AbortSignal.timeout(15000) });
      assert.equal(denied.isError, true, 'native registry guard must cover direct Drill calls');
      const bad = await call('route', { skill: 'fusion-recon', capability: 'evidence.persist',
        tool: 'redteam_asset_get', purpose: 'Read absent controlled record', arguments: { id: 99999 } });
      const failure = await call('execute', { route_id: bad.route_id });
      assert.equal(failure.status, 'failed', 'JSON ok:false must remain a failed capture in the real ledger');
    } finally {
      store?.close(); await ctx.fiber.dispose();
      if (previous === undefined) delete process.env.DSH_HOME; else process.env.DSH_HOME = previous;
    }
  });
