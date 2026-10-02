/** Use the installed Drill store and tool definitions; never import purge's patch entrypoint. */
import { realpathSync } from 'node:fs';
import { FusionSession, digest } from './dsh-runtime.mjs';

export const PURGE_TOOLS = new Set(['redteam_preflight', 'redteam_asset_add', 'redteam_asset_query',
  'redteam_asset_get', 'redteam_asset_stats', 'redteam_asset_timeline', 'redteam_http_evidence_add', 'redteam_report']);
export const name = 'security-fusion-purge-data';
export const inject = ['tools', 'redteam'];

/** A case projection in Drill, not a second task ledger. No global current-pointer fallback. */
export function engagementFor(session, store) {
  const state = session.state();
  if (!state?.task || state.mode === 'suspended') throw new Error('Start/resume the Fusion case before using Drill data tools');
  const root = realpathSync(store.root);
  const saved = state.purge;
  if (saved) {
    if (saved.root !== root || saved.target !== state.task.target || saved.scope !== state.task.scope) {
      throw new Error('Drill binding changed; do not guess another case or use the global current engagement');
    }
    if (!store.listEngagements().some(e => e.id === saved.id)) throw new Error('Bound Drill engagement is missing; restore it before writing');
    return saved;
  }
  // Distinct host sessions stay distinct even when they share cwd or target text.
  // Retrying after a crash before binding.json was saved reopens the SAME slug.
  const label = String(state.task.target).replace(/[\r\n\0]/g, ' ').slice(0, 60);
  const key = 'fusion-' + digest(session.owner + '\0' + session.cwd).slice(0, 32) + ' ' + label;
  const opened = store.openEngagement(key, [], { bindCurrent: false });
  const binding = { id: opened.id, root, target: state.task.target, scope: state.task.scope,
    authority: 'Fusion case owns scope and raw evidence; Drill holds derived asset records' };
  session.update({ purge: binding });
  return binding;
}

export function wrapDataTool(tool, config, store) {
  return { ...tool,
    description: (tool.name === 'redteam_preflight'
      ? 'Inspect installed Drill resources only when the current method lacks a tool; use include for relevant skills. Missing unrelated resources do not block independent work. This inspection does not install tools or verify target reachability.'
      : tool.description) + '\nFusion case projection: engagement is supplied by the bridge. Query results are historical records, not new target tests. Use fusion.execute; do not create or switch global engagements.',
    async execute(args, exec) {
      if (!exec.agent) throw new Error('An owning DSH session is required');
      const session = new FusionSession(config, exec.agent.session.id, exec.agent.session.header.cwd);
      const binding = engagementFor(session, store);
      if (args.engagement !== undefined && args.engagement !== binding.id) throw new Error('Cross-case Drill engagement rejected');
      const scoped = tool.name === 'redteam_preflight' ? args : { ...args, engagement: binding.id };
      const value = await tool.execute(scoped, exec);
      const parsed = JSON.parse(value);
      if (tool.name === 'redteam_preflight') {
        // A completed inventory with missing resources is a useful negative observation.
        // Preserve its concrete gaps while removing the upstream partial credential display.
        const configured = parsed.onboarding?.configured;
        if (configured?.fofa_key) configured.fofa_key = configured.fofa_key === 'missing' ? 'missing' : 'configured';
        parsed.inspection_completed = true;
        parsed.ready = parsed.ok === true;
      }
      // Upstream returns JSON ok:false as a successful string tool value. Surface it as an actual failure.
      if (parsed.ok === false && tool.name !== 'redteam_preflight') throw new Error('Drill returned failure: ' + String(parsed.error || parsed.note || 'unknown data failure').slice(0, 400));
      return JSON.stringify({ ...parsed, fusion_binding: { engagement: binding.id, target: binding.target,
        scope: binding.scope, case_path: session.casePath, evidence_authority: 'Fusion CALL receipts; Drill fields remain agent-authored' } });
    } };
}

export async function apply(ctx, config) {
  const native = await import('dsh-purge/redteam/tools');
  const selected = new Set();
  // Register only data tools in this preset scope. No extra MCP client, agent slots or controller.
  const registry = { register(tool) {
    if (!PURGE_TOOLS.has(tool.name)) return () => {};
    selected.add(tool.name);
    return ctx.tools.register(wrapDataTool(tool, config, ctx.redteam));
  } };
  const view = { redteam: ctx.redteam, tools: registry, get: ctx.get.bind(ctx),
    on: ctx.on.bind(ctx), logger: ctx.logger };
  await native.apply(view);
  const missing = [...PURGE_TOOLS].filter(n => !selected.has(n));
  if (missing.length) throw new Error('Installed dsh-purge data interface changed: ' + missing.join(', '));
}
