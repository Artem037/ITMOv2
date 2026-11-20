import { execFile } from 'node:child_process';
import { lstat, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { randomUUID } from 'node:crypto';
import { discountResults, mergeAllowed, parseReport, regressionFailures, replaceExpression } from './discount-checks.mjs';

const exec = promisify(execFile);
const repo = process.env.ITMO_AUTOFIX_REPO ?? 'Artem037/itmo-7-2-bugfix-demo';
const base = 'master';
const file = 'discount.mjs';
const label = 'autofix';
const runs = new Map();
let busy = false;

if (!/^[A-Za-z0-9-]+\/itmo-7-2-bugfix-demo$/u.test(repo)) {
  throw new Error('Configure a dedicated itmo-7-2-bugfix-demo repository.');
}
const owner = repo.split('/')[0];

async function command(binary, args, options = {}) {
  const subprocess = exec(binary, args, { maxBuffer: 512_000, timeout: 45_000, ...options });
  subprocess.child.stdin.end();
  const { stdout } = await subprocess;
  return stdout.trim();
}

async function github(path, args = []) {
  const resource = path ? `/${path}` : '';
  return JSON.parse(await command('gh', ['api', `repos/${repo}${resource}`, ...args]));
}

async function baseHead() {
  return (await github(`git/ref/heads/${base}`)).object.sha;
}

async function sourceAt(sha) {
  if (!/^[a-f0-9]{40}$/u.test(sha)) throw new Error('Expected a Git commit SHA.');
  const data = await github(`contents/${file}?ref=${sha}`);
  if (data.type !== 'file' || data.encoding !== 'base64') throw new Error('Expected a regular source file.');
  return Buffer.from(data.content, 'base64').toString('utf8');
}

function schema(properties) {
  return { type: 'object', properties, required: Object.keys(properties), additionalProperties: false };
}

async function askCodex(prompt, outputSchema) {
  const cwd = await mkdtemp(join(tmpdir(), 'itmo-72-model-'));
  const schemaFile = join(cwd, 'schema.json');
  const outputFile = join(cwd, 'output.json');
  await writeFile(schemaFile, JSON.stringify(outputSchema), { mode: 0o600 });
  await command('codex', [
    'exec', '--sandbox', 'read-only', '--ephemeral', '--skip-git-repo-check',
    '--output-schema', schemaFile, '--output-last-message', outputFile, prompt,
  ], { cwd, timeout: 150_000 });
  return JSON.parse(await readFile(outputFile, 'utf8'));
}

async function nextReport() {
  const issues = await github(`issues?state=open&labels=${label}&per_page=30&sort=created&direction=asc`);
  for (const issue of issues) {
    if (issue.pull_request || issue.user?.login !== owner ||
        !Number.isSafeInteger(issue.number) || !issue.labels?.some(entry => entry.name === label) ||
        Array.from(runs.values()).some(run => run.issue.number === issue.number)) continue;

    const branch = `codex/issue-${issue.number}`;
    const head = encodeURIComponent(`${owner}:${branch}`);
    const previous = await github(`pulls?state=all&head=${head}`);
    if (previous.length) continue;

    const runId = randomUUID();
    const pinnedBase = await baseHead();
    const source = await sourceAt(pinnedBase);
    const run = { issue, branch, source, pinnedBase, stage: 'blocked' };
    runs.set(runId, run);
    try {
      run.report = parseReport(issue.body ?? '');
    } catch (error) {
      return { status: 'blocked', issue: issue.html_url, reason: error.message };
    }
    const [failure] = regressionFailures(source, run.report);
    if (!failure || failure.total !== run.report.total || failure.percent !== run.report.percent) {
      return { status: 'blocked', issue: issue.html_url, reason: 'The reported case already passes.' };
    }
    run.stage = 'ready';
    run.failure = failure;
    return { runId, status: 'ready', issue: issue.html_url, base: pinnedBase, observed: failure };
  }
  return { status: 'idle' };
}

function getRun(runId, stage) {
  const run = runs.get(runId);
  if (run?.stage !== stage) throw new Error(`The repair is not at stage ${stage}.`);
  return run;
}

async function propose(runId) {
  const run = getRun(runId, 'ready');
  const currentReturn = run.source.split('\n').find(line => line.startsWith('  return '));
  const proposal = await askCodex(
    'Propose a repair for the pure JavaScript applyDiscount(total, percent) function. ' +
    'A discount reduces the original total. Keep the signature. For 100% the balance must be exactly zero, including for decimal totals. Scale percentage before multiplying by very large totals to avoid overflow. ' +
    'In expression, put only JavaScript arithmetic using total and percent, with no return keyword, trailing semicolon or code fences. Add a short reason. Use no tools. ' +
    `Current return statement: ${currentReturn}\nFailing cases: ${JSON.stringify(regressionFailures(run.source, run.report))}`,
    schema({ expression: { type: 'string' }, reason: { type: 'string' } }),
  );
  run.patched = replaceExpression(run.source, proposal.expression);
  const checks = discountResults(run.patched, run.report);
  const failures = checks.filter(check => !check.passed);
  if (failures.length) {
    run.stage = 'blocked';
    return { runId, status: 'blocked', reason: 'The proposed expression failed regression checks.', failures };
  }
  run.stage = 'tested';
  return { runId, status: 'tested', expression: proposal.expression, reason: proposal.reason, checks: checks.length };
}

async function pushRepair(runId) {
  const run = getRun(runId, 'tested');
  if (await baseHead() !== run.pinnedBase) throw new Error('master changed before the push.');
  const cwd = await mkdtemp(join(tmpdir(), 'itmo-72-checkout-'));
  const git = (...args) => command('git', [
    '-c', 'credential.helper=',
    '-c', 'credential.https://github.com.helper=!gh auth git-credential',
    '-c', `user.name=${owner}`,
    '-c', `user.email=${owner}@users.noreply.github.com`,
    '-c', 'core.hooksPath=/dev/null',
    ...args,
  ], { cwd, env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } });

  await git('clone', '--depth', '1', '--branch', base, `https://github.com/${repo}.git`, '.');
  if (await git('rev-parse', 'HEAD') !== run.pinnedBase) throw new Error('The cloned base differs from the tested base.');
  await git('switch', '-c', run.branch);
  const target = join(cwd, file);
  if (!(await lstat(target)).isFile() || await readFile(target, 'utf8') !== run.source) {
    throw new Error('The checked-out file differs from the tested source.');
  }
  await writeFile(target, run.patched);
  await git('add', '--', file);
  await git('commit', '-m', `Fix discount calculation (issue #${run.issue.number})`);
  run.pushedHead = await git('rev-parse', 'HEAD');
  await git('push', 'origin', `HEAD:refs/heads/${run.branch}`);
  run.pull = await github('pulls', [
    '--method', 'POST', '-f', `title=Fix discount calculation (#${run.issue.number})`,
    '-f', `head=${run.branch}`, '-f', `base=${base}`,
    '-f', `body=Fixes #${run.issue.number}\n\nn8n generated the change after reproducing the reported case. An independent review and regression checks gate the merge.`,
  ]);
  run.stage = 'pushed';
  return { runId, status: 'pushed', branch: run.branch, head: run.pushedHead, pullRequest: run.pull.html_url };
}

async function reviewRepair(runId) {
  const run = getRun(runId, 'pushed');
  const pullPath = `pulls/${run.pull.number}`;
  const pull = await github(pullPath);
  const changes = await github(`${pullPath}/files`);
  const actual = await sourceAt(pull.head.sha);
  if (pull.head.sha !== run.pushedHead || pull.base.sha !== run.pinnedBase || changes.length !== 1 ||
      changes[0].filename !== file || actual !== run.patched) {
    throw new Error('The remote PR differs from the tested patch.');
  }
  const checks = discountResults(actual, run.report);
  const failures = checks.filter(check => !check.passed);
  const diff = changes[0].patch.split('\n').filter(line => /^[-+]  return /u.test(line)).join('\n');
  const review = await askCodex(
    'Independently review this JavaScript discount-calculation PR. Approve only if it reduces the total by the specified percentage, preserves the interface and handles 0%, 100%, zero total and decimal inputs without regressions. Use no tools. ' +
    `Report: ${JSON.stringify(run.failure)}\nPR patch:\n${diff}\nVerification cases with expected and actual values: ${JSON.stringify(checks)}`,
    schema({
      approved: { type: 'boolean' },
      seriousIssues: { type: 'array', items: { type: 'string' } },
      summary: { type: 'string' },
    }),
  );
  const approval = {
    review, failures, reviewedHead: pull.head.sha, reviewedBase: pull.base.sha,
    actualHead: pull.head.sha, actualBase: pull.base.sha,
  };
  const decision = mergeAllowed(approval) ? 'approved' : 'blocked';
  const posted = await github(`${pullPath}/reviews`, [
    '--method', 'POST', '-f', 'event=COMMENT', '-f', `commit_id=${pull.head.sha}`,
    '-f', `body=Independent Codex review: ${decision}.\n\n${review.summary}\n\nSerious findings: ${review.seriousIssues.join(' | ') || 'none'}.\nRegression failures: ${failures.length}.`,
  ]);
  run.approval = approval;
  run.stage = decision;
  return { runId, status: run.stage, reviewedHead: pull.head.sha, review: posted.html_url, summary: review.summary, checks, failures };
}

async function mergeRepair(runId) {
  const run = getRun(runId, 'approved');
  const pull = await github(`pulls/${run.pull.number}`);
  const actualBase = await baseHead();
  if (pull.state !== 'open' || pull.base.ref !== base ||
      !mergeAllowed({ ...run.approval, actualHead: pull.head.sha, actualBase })) {
    throw new Error('The reviewed revision or base changed. Merge was stopped.');
  }
  const result = await github(`pulls/${pull.number}/merge`, [
    '--method', 'PUT', '-f', `sha=${run.approval.reviewedHead}`, '-f', 'merge_method=merge',
  ]);
  if (result.merged !== true) throw new Error('GitHub declined the tested merge.');
  run.stage = 'merged';
  return { runId, status: 'merged', issue: run.issue.html_url, pullRequest: pull.html_url, base, mergeCommit: result.sha };
}

const operations = new Map([
  ['/next', nextReport], ['/propose', propose], ['/push', pushRepair],
  ['/review', reviewRepair], ['/merge', mergeRepair],
]);

const metadata = await github('');
if (!metadata.private || metadata.default_branch !== base ||
    metadata.full_name.toLowerCase() !== repo.toLowerCase() ||
    (await command('gh', ['api', 'user', '--jq', '.login'])) !== owner) {
  throw new Error('The dedicated private repository must belong to the authenticated account and use master.');
}

createServer(async (request, response) => {
  const send = (code, value) => {
    response.writeHead(code, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify(value));
  };
  if (request.method === 'GET' && request.url === '/health') return send(200, { status: 'ready', repo });
  const operation = operations.get(request.url);
  if (request.method !== 'POST' || !operation) return send(404, { status: 'not-found' });
  if (busy) return send(409, { status: 'busy' });

  busy = true;
  try {
    let body = '';
    for await (const chunk of request) {
      body += chunk;
      if (body.length > 4096) throw new Error('Unexpected request size.');
    }
    const data = JSON.parse(body || '{}');
    const result = await operation(data.runId);
    console.log(JSON.stringify({ endpoint: request.url, ...result }));
    send(200, result);
  } catch (error) {
    const reason = error.code || (error.cmd ? 'external command failed' : error.message);
    console.error(JSON.stringify({ endpoint: request.url, status: 'error', reason }));
    send(500, { status: 'error', reason });
  } finally {
    busy = false;
  }
}).listen(8763, '127.0.0.1', () => console.log(`Worker ready for ${repo}`));
