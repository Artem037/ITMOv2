import { spawn } from 'node:child_process';
import { appendFile, mkdir } from 'node:fs/promises';
import { join, relative, resolve } from 'node:path';

// OpenCode 1.18.x plugin API. The runner is fixed; tool arguments are paths only.
export default async function CheckAfterEdit({ directory }, options = {}) {
  const root = resolve(directory);
  const timeoutMs = options.timeoutMs ?? 30_000;
  let queue = Promise.resolve();

  function relevant(input) {
    if (!['write', 'edit', 'apply_patch'].includes(input.tool)) return false;
    const paths = [input.args?.filePath];
    if (typeof input.args?.patchText === 'string') {
      for (const match of input.args.patchText.matchAll(/^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$/gm)) paths.push(match[1]);
    }
    return paths.filter(p => typeof p === 'string').some(p => {
      const local = relative(root, resolve(root, p));
      return local.startsWith('practices/practice_03/lab/demo/') ||
        local.startsWith('scripts/') || local === '.pre-commit-config.yaml';
    });
  }

  function run() {
    return new Promise(resolveResult => {
      let output = '';
      let timedOut = false;
      const child = spawn('sh', [join(root, 'scripts/check.sh')], {
        cwd: root, detached: true, stdio: ['ignore', 'pipe', 'pipe'],
      });
      const collect = chunk => { output = (output + chunk.toString()).slice(-24_000); };
      child.stdout.on('data', collect);
      child.stderr.on('data', collect);
      const timer = setTimeout(() => {
        timedOut = true;
        try { process.kill(-child.pid, 'SIGKILL'); } catch { child.kill('SIGKILL'); }
      }, timeoutMs);
      child.on('error', error => {
        clearTimeout(timer);
        resolveResult({ exitCode: null, timedOut, output: output + error.message });
      });
      child.on('close', code => {
        clearTimeout(timer);
        resolveResult({ exitCode: code, timedOut, output: output + (timedOut ? '\nRunner timed out.' : '') });
      });
    });
  }

  return {
    'tool.execute.after': async (input, output) => {
      if (!relevant(input)) return;
      const pending = queue.then(run);
      queue = pending.catch(() => {});
      const check = await pending;
      const status = check.exitCode === 0 && !check.timedOut ? 'PASS' : 'FAIL';
      output.output += `\n\n[Practice 4 check: ${status}; exit=${check.exitCode}]\n${check.output}`;
      output.metadata = { ...output.metadata, practice4Check: { status, exitCode: check.exitCode, timedOut: check.timedOut } };
      // Compact local trace; no source content, commands from the model or credentials.
      try {
        const logDir = join(root, '.opencode', 'logs');
        await mkdir(logDir, { recursive: true });
        await appendFile(join(logDir, 'check-after-edit.jsonl'), JSON.stringify({
          time: new Date().toISOString(), sessionID: input.sessionID,
          callID: input.callID, tool: input.tool, status,
          exitCode: check.exitCode, timedOut: check.timedOut,
        }) + '\n');
      } catch (error) {
        output.output += `\nHook log unavailable: ${error.message}`;
      }
    },
  };
}
