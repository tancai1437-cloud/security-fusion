/** Prepare a method and an observed host tool BEFORE dispatch, not after it. */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { digest } from './dsh-runtime.mjs';
import { rejectInlineCredentials } from './dsh-execution.mjs';

const HOST_TOOLS = {
  'code.inspect': ['read', 'grep', 'glob'],
  'js.source': ['read', 'grep', 'glob'],
  'evidence.persist': ['read', 'write', 'edit', 'grep', 'glob', 'web_search', 'web_fetch'],
  'report.compose': ['read', 'write', 'edit'],
};
const CONTROL = /^(fusion|skill|create_goal|update_goal|get_goal|todo_write|request_user_input)$|subagent|workflow|ralph/;
const DEFAULT_FIELDS = ['objective', 'scope', 'target', 'skill', 'capability', 'purpose', 'work', 'arguments',
  'tool', 'tool_reason', 'procedure', 'next', 'criteria', 'constraints', 'deliverables', 'identity_ref',
  'context_slot', 'depends_on'];

function catalog(session, file, key) {
  return JSON.parse(readFileSync(path.join(session.config.skillRoot, 'manifests', file), 'utf8'))[key];
}

export function expandRoute(session, request) {
  if (!request.route_id) return { ...request };
  const saved = (session.state()?.prepared_routes || []).find(r => r.id === request.route_id);
  if (!saved) throw new Error('Unknown/expired route_id for this session; use route again. No tool was called.');
  if (request.review && Object.keys(request).every(k => ['route_id', 'review'].includes(k))) {
    return { review: request.review }; // A review plus a locator is not a request to replay saved arguments.
  }
  if (saved.used && request.arguments !== undefined && saved.defaults.capability !== 'evidence.persist' && !request.work) {
    throw new Error('Reusing a route with arguments requires this call\'s work:{key,conditions}; do not silently inherit an old test condition.');
  }
  for (const field of ['skill', 'capability', 'tool', 'procedure']) {
    if (request[field] !== undefined && request[field] !== saved.defaults[field]) {
      throw new Error('route_id binds ' + field + '; use route to change the method/tool.');
    }
  }
  return { ...saved.defaults, ...request };
}

function selection(session, request) {
  const modules = catalog(session, 'specialists.json', 'modules');
  const procedure = request.procedure && catalog(session, 'procedures.json', 'procedures').find(p => p.id === request.procedure);
  if (request.procedure && !procedure) throw new Error('Unknown procedure');
  if (procedure && ((request.skill && request.skill !== procedure.skill_id) ||
      (request.capability && request.capability !== procedure.capability_id))) throw new Error('Procedure does not match this specialist/capability');
  const skill = procedure?.skill_id || request.skill || session.state()?.last_skill;
  const module = modules.find(m => m.id === skill);
  if (!module) return { response: { status: 'specialist_required', target_action_executed: false,
    specialists: modules.map(m => ({ skill: m.id, when: m.applicable_when })),
    next: 'Choose the specialist for the current user question, then route(request={skill,capability,purpose}). Do not traverse all specialists.' } };
  const capability = procedure?.capability_id || request.capability;
  if (!capability) return { response: { status: 'capability_required', target_action_executed: false,
    skill, capabilities: module.execution_routes, next: 'Select the capability for the next concrete evidence question, then route.' } };
  if (!module.execution_routes.includes(capability)) throw new Error(`Allowed capabilities for ${skill}: ${module.execution_routes.join(', ')}`);
  const route = catalog(session, 'execution-routes.json', 'routes').find(r => r.id === capability);
  const sourceHash = digest(readFileSync(path.join(session.config.skillRoot, module.path), 'utf8'));
  return { module, route, procedure, skill, capability, sourceHash };
}

function bindingSource(session, route, tool) {
  if (session.config.capabilityTools?.[route.id]?.includes(tool.name)) return 'host_config';
  if (HOST_TOOLS[route.id]?.includes(tool.name)) return 'host_interface';
  const leaf = tool.name.split('__').at(-1);
  if (tool.name.startsWith('mcp__') && route.choices.some(c => c.provider !== 'host' && c.tool_candidates.includes(leaf))) {
    return 'manifest_name_match'; // Candidate, not a health probe or proof of semantics.
  }
}

function chooseTool(session, route, request, tools) {
  const available = tools.filter(t => !CONTROL.test(t.name));
  const matches = available.flatMap(tool => {
    const source = bindingSource(session, route, tool);
    return source ? [{ tool, source }] : [];
  });
  if (request.tool) {
    const tool = available.find(t => t.name === request.tool);
    if (!tool) throw new Error('Tool is not visible/callable in this session: ' + request.tool);
    const source = bindingSource(session, route, tool);
    if (source) return { tool, source };
    if (typeof request.tool_reason === 'string' && request.tool_reason.trim() && request.tool_reason.length <= 600) {
      return { tool, source: 'agent_explained_fallback', reason: request.tool_reason };
    }
    return { status: 'tool_reason_required', candidates: [{ name: tool.name, description: tool.description?.slice(0, 240) }],
      next: 'This tool has no known binding to this capability. Use a matching tool, or route with tool_reason explaining its actual operation and limits. Registration alone is not a capability match.' };
  }
  if (matches.length === 1) return matches[0];
  return { status: matches.length ? 'tool_choice_required' : 'tool_unavailable',
    candidates: matches.slice(0, 6).map(({ tool, source }) => ({ name: tool.name, source, description: tool.description?.slice(0, 180) })),
    omitted_candidates: Math.max(0, matches.length - 6),
    next: matches.length ? 'Choose one current tool and call route with tool; do not probe every candidate.'
      : 'No known matching tool is exposed by this Agent. If a real equivalent local tool exists, route with tool and tool_reason. Otherwise save the concrete blocker; never invent a tool name.' };
}

function signature(selected, choice) {
  return digest(JSON.stringify({ skill: selected.skill, capability: selected.capability,
    source: selected.sourceHash, route: selected.route, procedure: selected.procedure,
    tool: choice.tool.name, schema: choice.tool.parameters, source_binding: choice.source, reason: choice.reason }));
}

function remember(session, request, selected, choice, stamp) {
  const defaults = Object.fromEntries(DEFAULT_FIELDS.filter(k => request[k] !== undefined).map(k => [k, request[k]]));
  Object.assign(defaults, { skill: selected.skill, capability: selected.capability, tool: choice.tool.name });
  const id = 'ROUTE-' + digest(session.owner + stamp).slice(0, 24);
  const record = { id, signature: stamp, defaults, source: selected.module.path,
    source_sha256: selected.sourceHash, binding_source: choice.source };
  const prior = (session.state()?.prepared_routes || []).filter(r => r.id !== id);
  session.update({ route_contract: 'prepared-v1', mode: session.state()?.task ? 'executing' : 'ready',
    prepared_routes: [...prior.slice(-5), record],
    current_route: { id, skill: selected.skill, capability: selected.capability, tool: choice.tool.name,
      source: selected.module.path, source_sha256: selected.sourceHash, binding_source: choice.source,
      procedure: selected.procedure?.id, status: 'prepared_not_executed' } });
  return record;
}

/** Does not execute, create a case/check, or assert the tool is healthy. */
export async function prepareRoute(session, request, tools, signal) {
  rejectInlineCredentials(request.arguments);
  rejectInlineCredentials(request.work);
  if (request.target && session.state()?.task && request.target !== session.state().task.target) {
    throw new Error('Target differs from this session. Use a separate session; do not switch the existing case.');
  }
  session.activate();
  const selected = selection(session, request);
  if (selected.response) return selected.response;
  const choice = chooseTool(session, selected.route, request, tools);
  const card = (await session.cli('catalog', ['--skill', selected.skill], signal)).action_card;
  const guidance = { specialist: card, capability: { id: selected.capability,
    required_input: selected.route.required_input, expected_output: selected.route.expected_output },
    ...(selected.procedure ? { procedure: selected.procedure } : {}) };
  if (!choice.tool) return { ...choice, skill: selected.skill, capability: selected.capability,
    target_action_executed: false, guidance };
  const stamp = signature(selected, choice);
  // Do not echo large write contents or raw command payloads into model context.
  const record = remember(session, request, selected, choice, stamp);
  const schema = JSON.stringify(choice.tool.parameters).length <= 3000
    ? { parameters: choice.tool.parameters }
    : { parameters_omitted: true, parameters_source: 'Current host definition of ' + choice.tool.name,
      next: 'Use that already-exposed tool schema; it is revalidated before dispatch. No schema was truncated into a misleading partial schema.' };
  return { status: 'route_ready', route_id: record.id, target_action_executed: false, guidance,
    execution: { tool: choice.tool.name, binding_source: choice.source, fallback_reason: choice.reason,
      ...schema, health: 'not_probed',
      context_required: choice.tool.name.startsWith('mcp__') && (!session.config.boundTools?.[choice.tool.name] ||
        session.config.boundTools[choice.tool.name] !== (request.target || session.state()?.task?.target)) },
    next_call: { action: 'execute', request: { route_id: record.id } },
    next: 'Use the returned method NOW. execute with this route_id; supply arguments, purpose and work if not already supplied. First execution also needs objective,scope,target. Unchanged fields are restored from this route; review is never replayed. Route preparation is not a target call or completion.' };
}

/** Return a ready receipt or a route response for the model to read first. */
export async function requireRoute(session, request, tools, signal) {
  const selected = selection(session, request);
  if (selected.response) return { response: selected.response };
  const choice = chooseTool(session, selected.route, request, tools);
  if (choice.tool) {
    const stamp = signature(selected, choice);
    const saved = (session.state()?.prepared_routes || []).find(r => r.signature === stamp);
    if (saved) return { receipt: { id: saved.id, skill: selected.skill, capability: selected.capability,
      tool: choice.tool.name, source: saved.source, source_sha256: saved.source_sha256,
      binding_source: choice.source, procedure: selected.procedure?.id } };
  }
  return { response: await prepareRoute(session, request, tools, signal) };
}
