import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import CheckAfterEdit from '../.opencode/plugins/check-after-edit.js';

async function fixture(t, runner, options) {
  const root = await mkdtemp(join(tmpdir(), 'practice4-hook-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(join(root, 'scripts'));
  await writeFile(join(root, 'scripts/check.sh'), runner);
  const hooks = await CheckAfterEdit({ directory: root }, options);
  return { root, after: hooks['tool.execute.after'] };
}

const event = (args, tool = 'edit') => ({ tool, args, sessionID: 'test-session', callID: 'test-call' });
const result = () => ({ title: 'edited', output: 'Original edit result', metadata: {} });

test('checks homework code, tests, dependencies, skill and environment configuration', async t => {
  const { after } = await fixture(t, 'echo "Homework verified"\n');
  for (const filePath of [
    'practices/practice_04/homework/trip_planner/planner.py',
    'practices/practice_04/homework/tests/test_planner.py',
    'practices/practice_04/homework/tests/fixtures/rare_connections.json',
    'practices/practice_04/homework/pyproject.toml',
    'practices/practice_04/homework/uv.lock',
    'practices/practice_04/homework/Makefile',
    '.opencode/skills/transit-trip-planner/SKILL.md',
    '.opencode/skills/transit-trip-planner/references/input-and-sources.md',
    '.opencode/plugins/check-after-edit.js',
    'tests/check-after-edit.test.mjs', 'opencode.json', 'Makefile', 'AGENTS.md',
  ]) {
    const output = result();
    await after(event({ filePath }), output);
    assert.equal(output.metadata.practice4Check?.status, 'PASS', filePath);
    assert.match(output.output, /Homework verified/);
  }
});

test('ignores homework evidence, reports, environments and files outside project', async t => {
  const { root, after } = await fixture(t, 'touch called\n');
  for (const filePath of [
    'practices/practice_04/homework/evidence/hook.txt',
    'practices/practice_04/homework/REPORT.md',
    'practices/practice_04/homework/.venv/script.py',
    '../other/practices/practice_04/homework/trip_planner/planner.py',
    '.opencode/logs/check-after-edit.jsonl',
  ]) {
    const output = result();
    await after(event({ filePath }), output);
    assert.equal(output.output, 'Original edit result', filePath);
  }
  await assert.rejects(readFile(join(root, 'called')), { code: 'ENOENT' });
});

test('returns a real failing runner result to the agent without losing edit output', async t => {
  const { after } = await fixture(t, 'echo "behavior failed" >&2\nexit 7\n');
  const output = result();
  await after(event({ filePath: 'practices/practice_03/lab/demo/service.py' }), output);
  assert.match(output.output, /Original edit result/);
  assert.match(output.output, /FAIL/);
  assert.match(output.output, /behavior failed/);
  assert.equal(output.metadata.practice4Check.exitCode, 7);
});

test('checks apply_patch changes from an absolute project path and reports PASS', async t => {
  const { root, after } = await fixture(t, 'echo "8 tests passed"\n');
  const output = result();
  const file = join(root, 'practices/practice_03/lab/demo/test_service.py');
  await after(event({ patchText: `*** Begin Patch\n*** Update File: ${file}\n@@\n-a\n+b\n*** End Patch` }, 'apply_patch'), output);
  assert.match(output.output, /PASS/);
  assert.match(output.output, /8 tests passed/);
  assert.equal(output.metadata.practice4Check.exitCode, 0);
});

test('ignores evidence edits and reads, so logging cannot recursively run the check', async t => {
  const { root, after } = await fixture(t, 'touch called\n');
  for (const e of [event({ filePath: 'practices/practice_04/evidence/hook.txt' }), event({ filePath: 'practices/practice_03/lab/demo/service.py' }, 'read')]) {
    const output = result();
    await after(e, output);
    assert.equal(output.output, 'Original edit result');
  }
  await assert.rejects(readFile(join(root, 'called')), { code: 'ENOENT' });
});

test('reports a timeout as FAIL and stops a stuck runner', async t => {
  const { after } = await fixture(t, 'sleep 60\n', { timeoutMs: 100 });
  const output = result();
  const start = Date.now();
  await after(event({ filePath: 'scripts/check.sh' }), output);
  assert.match(output.output, /FAIL/);
  assert.match(output.output, /timed out/i);
  assert.equal(output.metadata.practice4Check.timedOut, true);
  assert.ok(Date.now() - start < 3000);
});
