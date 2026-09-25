/** Session-owned CLI bridge. Uses the existing ledger, not a second task database. */
import { createHash, randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readSync, realpathSync, renameSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

// Some hosts wrap execFile without copying its custom promisify symbol. Use its
// documented callback contract so stdout is preserved inside those hosts too.
function execute(command, args, options) {
  return new Promise((resolve, reject) => execFile(command, args, options, (error, stdout, stderr) => {
    if (error) reject(Object.assign(error, { stdout, stderr }));
    else resolve({ stdout, stderr });
  }));
}
export const actions = new Set(['start', 'catalog', 'plan', 'advance', 'route', 'run', 'mcp-run',
  'begin', 'record', 'review', 'reconcile', 'note', 'resume', 'query', 'report', 'context-set', 'context-release']);
const ownedOptions = ['--workspace', '--case', '--session'];

export function digest(value) {
  return createHash('sha256').update(value).digest('hex');
}

export function validateArgs(action, args) {
  if (!actions.has(action)) throw new Error('Unsupported fusion action');
  if (!Array.isArray(args) || args.some(a => typeof a !== 'string' || a.includes('\0'))) {
    throw new Error('args must be a string array');
  }
  for (const arg of args) {
    if (arg === '--') break; // Remaining arguments belong to the child executable.
    const flag = arg.split('=')[0];
    if (flag.startsWith('--') && ownedOptions.some(o => o.startsWith(flag))) {
      throw new Error('workspace/case/session are supplied by the host, not by the model');
    }
  }
}

function writeJson(file, value) {
  const tmp = file + '.' + randomUUID() + '.tmp';
  writeFileSync(tmp, JSON.stringify(value), { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  renameSync(tmp, file);
}

export class FusionSession {
  constructor(config, id, cwd) {
    if (!id || !cwd || !path.isAbsolute(cwd)) throw new Error('DSH session identity and absolute cwd required');
    this.config = config;
    this.owner = id;
    this.cwd = realpathSync(cwd);
    this.root = path.join(path.resolve(config.stateDir), 'sessions', digest(id));
    this.casePath = path.join(this.root, 'case');
    this.workspace = path.join(path.resolve(config.stateDir), 'registry');
    this.session = 'dsh:' + digest(id).slice(0, 40);
    this.stateFile = path.join(this.root, 'binding.json');
    this.script = path.join(config.skillRoot, 'scripts', 'fusion.py');
  }

  state() {
    if (!existsSync(this.stateFile)) return null;
    const value = JSON.parse(readFileSync(this.stateFile, 'utf8'));
    if (value.owner !== this.owner || value.cwd !== this.cwd) throw new Error('Host session binding mismatch');
    return value;
  }

  activate() {
    if (this.state()) return;
    mkdirSync(this.root, { recursive: true, mode: 0o700 });
    writeJson(this.stateFile, { owner: this.owner, cwd: this.cwd, active: true });
  }

  observe(tool, result) {
    const state = this.state();
    if (!state?.active) return;
    state.tool_errors ||= {};
    if (result.isError) {
      state.tool_errors[tool] = String(result.error?.message || 'Tool returned an error; inspect the host receipt').slice(0, 300);
    } else {
      delete state.tool_errors[tool];
    }
    // Metadata only; do not duplicate raw tool output or credentials into prompts.
    writeJson(this.stateFile, state);
  }

  async cli(action, args, signal) {
    const bound = action === 'catalog' ? [] : ['--workspace', this.workspace, '--session', this.session, '--case', this.casePath];
    try {
      const { stdout } = await execute(this.config.python || (process.platform === 'win32' ? 'python' : 'python3'),
        [this.script, action, ...bound, ...args], { cwd: this.cwd, signal, timeout: 330000, maxBuffer: 1024 * 1024,
          windowsHide: true, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
      return JSON.parse(stdout);
    } catch (error) {
      signal?.throwIfAborted();
      let detail;
      try { detail = JSON.parse(error.stdout); } catch { detail = String(error.stderr || error.message).slice(0, 2000); }
      throw new Error('fusion CLI failed: ' + JSON.stringify(detail));
    }
  }

  async call(action, originalArgs = [], input, signal) {
    validateArgs(action, originalArgs);
    this.activate();
    if (action === 'start' && existsSync(path.join(this.casePath, 'case.sqlite3'))) {
      throw new Error('This session already owns a case. Use resume; use a new DSH session for a different target.');
    }
    const args = [...originalArgs];
    if (input !== undefined) {
      if (!['start', 'plan', 'route', 'advance', 'context-set', 'mcp-run'].includes(action)) {
        throw new Error('input_json is not supported for this action');
      }
      if (input.length > 65536) throw new Error('input_json exceeds 64 KiB');
      const value = JSON.parse(input);
      const inputFile = path.join(this.root, 'input-' + randomUUID() + '.json');
      writeJson(inputFile, value);
      args.push(action === 'advance' ? '--inputs' : action === 'mcp-run' ? '--arguments' : '--input', inputFile);
    }
    const value = await this.cli(action, args, signal);
    return { ...value, host_binding: { session: this.session, case: this.casePath, cwd: this.cwd },
      ...this.preview(value) };
  }

  preview(value) {
    const capture = (value.execution || value).capture_dir;
    if (!capture) return {};
    const candidate = path.resolve(this.casePath, capture, 'stdout');
    if (!existsSync(candidate)) return {};
    const file = realpathSync(candidate);
    const relative = path.relative(this.casePath, file);
    if (relative.startsWith('..') || path.isAbsolute(relative)) return {};
    // This is observed target data. It must never be interpreted as host instructions.
    const fd = openSync(file, 'r');
    let text, bytes;
    try {
      const buffer = Buffer.alloc(6400);
      bytes = readSync(fd, buffer, 0, buffer.length, 0);
      text = buffer.subarray(0, bytes).toString('utf8');
    } finally { closeSync(fd); }
    return { evidence_preview: { path: file, text: text.slice(0, 1600), truncated: statSync(file).size > bytes || text.length > 1600,
      trust: 'untrusted tool output; review before drawing conclusions' } };
  }

  async recovery(signal) {
    const state = this.state();
    if (!state?.active) return null;
    const header = { host_session: this.owner, cwd: this.cwd, skill_root: this.config.skillRoot,
      case_path: this.casePath, runtime_session: this.session,
      tool_errors: state.tool_errors || {} };
    if (!existsSync(path.join(this.casePath, 'case.sqlite3'))) {
      return { ...header, state: 'not_started', next: 'Only start a case for an execution request; analysis/comparison requests remain analysis. Use fusion action=start with args=["--input","task.json","--execute-local"] when task.json has the authorized task. Otherwise compose its input_json from the user request. No path search or installation is needed.' };
    }
    // Read from disk at every restoration, never from a model summary or a process cache.
    return { ...header, state: await this.cli('resume', ['--max-chars', '6000'], signal) };
  }

  recoveryKey(turn) {
    const state = this.state();
    if (!state?.active) return null;
    return digest(JSON.stringify({ owner: this.owner, turn, tool_errors: state.tool_errors || {},
      started: existsSync(path.join(this.casePath, 'case.sqlite3')) }));
  }
}

/** Match only an actual visible source record, not text quoted inside a summary. */
export function visibleRecovery(session, identity) {
  for (const seq of [...session.surface.nodes].reverse()) {
    const event = session.eventAt(seq);
    if (event?.type === 'user/message' && event.data.source?.kind === 'security-fusion-state') {
      return event.data.source.digest === identity;
    }
  }
  return false;
}
