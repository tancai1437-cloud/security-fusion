/** Optional host-declared artifact pointers. Never trust a path from target text. */
import { copyFileSync, readFileSync, realpathSync, statSync } from 'node:fs';
import path from 'node:path';
import { digest } from './dsh-runtime.mjs';

export function importToolArtifacts(session, tool, result, directory, attempt) {
  const configured = session.config.toolArtifactRoots?.[tool];
  if (!configured) return [];
  const roots = (Array.isArray(configured) ? configured : [configured]).map(root => realpathSync(root));
  let value;
  try { value = JSON.parse(result.content.find(block => block.type === 'text').text); }
  catch { return []; }
  if (!value.artifacts) return [];
  if (!Array.isArray(value.artifacts) || value.artifacts.length > 4) throw new Error('Artifact pointer limit exceeded');
  return value.artifacts.map((pointer, index) => {
    if (typeof pointer.path !== 'string' || !path.isAbsolute(pointer.path) || !/^[a-f0-9]{64}$/.test(pointer.sha256 || '')) {
      throw new Error('Artifact pointer requires an absolute path and SHA256');
    }
    const source = realpathSync(pointer.path);
    if (!roots.some(root => {
      const relative = path.relative(root, source);
      return relative && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
    })) throw new Error('Tool artifact is outside its configured root');
    const stat = statSync(source);
    if (!stat.isFile() || stat.size > 8 * 1024 * 1024) throw new Error('Tool artifact must be a file up to 8 MiB');
    const snapshot = path.join(directory, attempt + '.artifact-' + index);
    copyFileSync(source, snapshot);
    const bytes = readFileSync(snapshot), sha256 = digest(bytes);
    if (bytes.length > 8 * 1024 * 1024 || sha256 !== pointer.sha256) throw new Error('Tool artifact hash mismatch');
    return { path: snapshot, capture: snapshot, sha256, kind: 'tool_artifact', bytes: bytes.length };
  });
}
