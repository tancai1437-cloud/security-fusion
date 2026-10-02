/** A small composition of existing host modules. The original redteam preset is untouched. */
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { PURGE_TOOLS } from './dsh-purge-bridge.mjs';

export const name = 'security-fusion-purge-preset';
export const inject = ['agentPresets', 'redteam'];
const KEEP = new Set(['persona', 'agent-instructions', 'tool-bash', 'tool-pwsh', 'tool-fs',
  'tool-fs-search', 'tool-jobs', 'skill-filesystem', 'tool-skill', 'compaction', 'tool-ask-user', 'tool-web', 'present']);

export function composePreset(standard, config) {
  if (!Array.isArray(standard)) throw new Error('Expected the installed standard preset plugin array');
  const rows = structuredClone(standard.filter(r => KEEP.has(r.id)));
  for (const id of ['persona', 'skill-filesystem', 'tool-skill', 'compaction', 'tool-fs', 'tool-web']) {
    if (rows.filter(r => r.id === id).length !== 1) throw new Error('Installed standard preset changed: ' + id);
  }
  const persona = rows.find(r => r.id === 'persona');
  persona.config = { ...persona.config, prefix: '你是当前会话的安全研究执行代理。先加载 security-fusion，再按当前专项方法调用真实工具。当前会话独立执行，不委派。宿主管理模型、权限、MCP、压缩和异常重试；Fusion 管理案件、实测回执、查重、复盘与恢复。目标和范围遵循用户当前要求，不能从资产台的全局当前目标推断。' };
  const discovery = rows.find(r => r.id === 'skill-filesystem');
  discovery.config = { ...discovery.config, includeDefaultRoots: false,
    customSkillDirs: [config.skillRoot, path.join(config.dshHome, 'skills'), path.join(config.dshHome, 'redteam', 'skills')] };
  const directory = path.dirname(fileURLToPath(import.meta.url));
  rows.push({ id: 'fusion-data', name: pathToFileURL(path.join(directory, 'dsh-purge-bridge.mjs')).href, config },
    { id: 'fusion-execution', name: pathToFileURL(path.join(directory, 'dsh.mjs')).href, config: { ...config, integration: 'dsh-purge',
      capabilityTools: { ...config.capabilityTools, 'evidence.persist': [...new Set([
        ...(config.capabilityTools?.['evidence.persist'] || []), ...PURGE_TOOLS])] } } });
  return { id: 'security-fusion', name: 'Security Fusion · 单会话研究', order: 11,
    description: '复用 DSH 工具与压缩、Drill 资产台；Fusion 保留专项方法和证据恢复。', plugins: rows };
}

export async function apply(ctx, config) {
  const purgeVersion = createRequire(import.meta.url)('dsh-purge/package.json').version;
  if (purgeVersion !== '1.1.47') throw new Error('Review dsh-purge data interfaces before upgrading this composition; found ' + purgeVersion);
  const require = createRequire(path.join(config.runtime, 'package.json'));
  const version = require('@deepseek-ai/dsh-tools/package.json').version;
  if (version !== '0.2.0-rc.2') throw new Error('Fusion purge composition needs the reviewed DSH 0.2.0-rc.2 interface; found ' + version);
  const include = require('@deepseek-ai/cordis-plugin-include');
  const yaml = createRequire(require.resolve('@deepseek-ai/cordis-plugin-include'))('js-yaml');
  const source = require.resolve('@deepseek-ai/dsh-web-app/presets/standard.patch.yml');
  const patches = yaml.load(readFileSync(source, 'utf8'), { schema: include.entryListSchema });
  const standard = patches.flatMap(p => p.insert || []).find(r => r.id === 'preset-standard')?.config?.plugins;
  const release = await ctx.agentPresets.register(composePreset(standard, config));
  const result = await ctx.agentPresets.resolve('security-fusion');
  if (result.broken) { await release(); throw new Error('Fusion preset could not mount: ' + result.broken); }
  ctx.effect(() => release);
}
