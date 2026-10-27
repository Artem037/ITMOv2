import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const require = createRequire(import.meta.url);
const homework = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(homework, '../../..');
const bundled = join(homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || (existsSync(bundled) ? bundled : 'playwright'));
const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const executablePath = process.env.BROWSER_EXECUTABLE || (existsSync(chrome) ? chrome : undefined);
const examples = JSON.parse(readFileSync(join(homework, 'evidence/contract-examples.json')));
let browser, server, url;

before(async () => {
  server = spawn('uv', ['run', '--project', 'practices/practice_04/homework', '--locked', '--offline', 'python', 'practices/practice_05/homework/web/server.py', '--port', '0'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  url = await new Promise((resolveUrl, reject) => {
    let output = '';
    const timer = setTimeout(() => reject(new Error(`Server did not start: ${output}`)), 10000);
    server.stdout.on('data', bytes => {
      output += bytes.toString();
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); resolveUrl(match[0]); }
    });
    server.stderr.on('data', bytes => { output += bytes.toString(); });
    server.on('exit', code => { clearTimeout(timer); reject(new Error(`Server exited ${code}: ${output}`)); });
  });
  browser = await chromium.launch({ headless: true, executablePath });
});

after(async () => {
  await browser?.close();
  server?.kill('SIGTERM');
});

async function screen(t, options = {}) {
  const context = await browser.newContext({ timezoneId: 'Europe/Moscow', ...options });
  t.after(() => context.close());
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  return page;
}

async function open(page) {
  await page.goto(url);
  assert.equal(await page.getByRole('button', { name: 'Рассчитать', exact: true }).count(), 1, 'Calculation screen is not implemented');
  await page.waitForFunction(() => !document.querySelector('#calculate').disabled);
}

async function state(page, wanted) {
  await page.waitForFunction(value => document.body.dataset.state === value, wanted);
}

async function calculate(page) {
  await page.getByRole('button', { name: 'Рассчитать', exact: true }).click();
}

async function until(condition) {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    assert.ok(Date.now() < deadline, 'Expected delayed request did not arrive');
    await new Promise(resolveTick => setTimeout(resolveTick, 10));
  }
}

async function holdCalculations(page) {
  const pending = [];
  await page.route('**/api/plan', async route => {
    const response = await route.fetch();
    const body = await response.json();
    await new Promise(resolveRoute => {
      pending.push(async override => {
        await route.fulfill(override || { response, json: body });
        resolveRoute();
      });
    });
  });
  return pending;
}

test('real form calculates, changes buffer and preserves warnings, timeline and source', async t => {
  const page = await screen(t);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await open(page);
  assert.equal(await page.locator('#window-start').inputValue(), '14.10.2026 06:00');
  assert.equal(await page.locator('#buffer').inputValue(), '10');
  assert.match(await page.locator('body').innerText(), /Учебные данные/);
  assert.equal(await page.locator('#result').innerText(), '');
  await calculate(page); await state(page, 'success');
  let text = await page.locator('#result').innerText();
  assert.match(text, /09:35/); assert.match(text, /11:50/); assert.match(text, /135/);
  assert.match(text, /Вымышленная оценка для теста/);
  assert.match(text, /Лучшие среди переданных/);
  assert.equal(await page.locator('#result a[href="https://example.org/synthetic-timetable"]').count(), 1);
  assert.equal(await page.locator('.timeline li').count(), 4);
  if (process.env.HW5_SCREENSHOTS_DIR) {
    mkdirSync(process.env.HW5_SCREENSHOTS_DIR, { recursive: true });
    await page.screenshot({ path: join(process.env.HW5_SCREENSHOTS_DIR, 'demo-success.png'), fullPage: true });
  }
  await page.locator('#buffer').fill('20');
  assert.equal(await page.locator('#result').innerText(), '');
  await calculate(page); await state(page, 'success');
  text = await page.locator('#result').innerText();
  assert.match(text, /09:25/); assert.match(text, /145/); assert.doesNotMatch(text, /09:35/);
  assert.deepEqual(errors, []);
});

test('real negative windows remain no_routes and needs_data, and equal boundary succeeds', async t => {
  const page = await screen(t); await open(page);
  await page.locator('#window-start').fill('14.10.2026 09:36');
  await page.locator('#window-end').fill('14.10.2026 10:00');
  await calculate(page); await state(page, 'no_routes');
  assert.match(await page.locator('#result').innerText(), /среди переданных подтверждённых цепочек/);
  await page.locator('#window-start').fill('15.10.2026 06:00');
  await page.locator('#window-end').fill('15.10.2026 12:00');
  await calculate(page); await state(page, 'needs_data');
  assert.match(await page.locator('#result').innerText(), /Не хватает подтверждённых данных/);
  assert.match(await page.locator('#result').innerText(), /14\.10\.2026/);
  if (process.env.HW5_SCREENSHOTS_DIR) await page.screenshot({ path: join(process.env.HW5_SCREENSHOTS_DIR, 'demo-needs-data.png'), fullPage: true });
  await page.locator('#window-start').fill('14.10.2026 09:35');
  await page.locator('#window-end').fill('14.10.2026 09:35');
  await calculate(page); await state(page, 'success');
  assert.match(await page.locator('#result').innerText(), /09:35/);
});

test('invalid fields retain input and keyboard correction returns to real success', async t => {
  const page = await screen(t); await open(page);
  for (const value of ['', '1.5', 'word', '-1', '1441']) {
    await page.locator('#buffer').fill(value);
    await calculate(page); await state(page, 'invalid');
    assert.equal(await page.locator('#buffer').inputValue(), value);
    assert.equal(await page.locator('#buffer').getAttribute('aria-invalid'), 'true');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'buffer');
  }
  await page.locator('#buffer').fill('10');
  await page.locator('#window-end').fill('14.10.2026 05:00');
  await calculate(page); await state(page, 'invalid');
  assert.match(await page.locator('#end-error').innerText(), /не раньше начала/);
  await page.locator('#window-end').fill('14.10.2026 12:00');
  await page.locator('#buffer').focus(); await page.keyboard.press('Enter');
  await state(page, 'success');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'buffer');
  assert.match(await page.locator('#result').innerText(), /135/);
  assert.equal(await page.locator('label[for="window-start"]').count(), 1);
});

test('computer timezone cannot shift Moscow inputs or output', async t => {
  const page = await screen(t, { timezoneId: 'America/New_York' }); await open(page);
  const request = page.waitForRequest('**/api/plan');
  await calculate(page);
  assert.equal((await request).postDataJSON().departure_window.start, '2026-10-14T06:00:00+03:00');
  await state(page, 'success');
  assert.match(await page.locator('#result').innerText(), /09:35/);
});

test('24-hour Moscow input is explicit even in an English browser locale', async t => {
  const page = await screen(t, { locale: 'en-US' }); await open(page);
  assert.equal(await page.locator('#window-start').inputValue(), '14.10.2026 06:00');
  assert.equal(await page.locator('#window-end').inputValue(), '14.10.2026 12:00');
});

test('unusable nested metadata cannot enable the form and reload recovers', async t => {
  const page = await screen(t);
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.route('**/api/trip', async route => {
    const response = await route.fetch();
    const data = await response.json(); data.limits = {};
    await route.fulfill({ response, json: data });
  });
  await page.goto(url);
  await page.waitForFunction(() => document.body.dataset.state !== 'loading');
  assert.equal(await page.getByRole('button', { name: 'Повторить загрузку' }).isVisible(), true, 'Unusable metadata must offer reload');
  assert.equal(await page.locator('#calculate').isDisabled(), true);
  await page.unroute('**/api/trip');
  await page.getByRole('button', { name: 'Повторить загрузку' }).click();
  await page.waitForFunction(() => !document.querySelector('#calculate').disabled);
  await calculate(page); await state(page, 'success');
  assert.deepEqual(errors, []);
});

for (const order of ['old-first', 'new-first', 'late-old-error']) {
  test(`editing stays available and stale responses cannot replace the current result: ${order}`, async t => {
    const page = await screen(t); await open(page);
    const pending = await holdCalculations(page);
    await calculate(page); await until(() => pending.length === 1);
    assert.equal(await page.locator('#buffer').isEnabled(), true);
    await page.locator('#buffer').fill('20');
    await calculate(page); await until(() => pending.length === 2);
    if (order === 'old-first') {
      await pending[0]();
      assert.equal(await page.locator('#result').innerText(), '');
      await pending[1]();
    } else {
      await pending[1](); await state(page, 'success');
      await pending[0](order === 'late-old-error' ? {
        status: 500, json: { error: { code: 'internal_error', message: 'Старая ошибка' } }
      } : undefined);
    }
    await state(page, 'success');
    const text = await page.locator('#result').innerText();
    assert.match(text, /09:25/); assert.doesNotMatch(text, /09:35|Старая ошибка/);
    assert.match(await page.locator('#status').innerText(), /Найден/);
  });
}

test('double submission of the same revision has one current request', async t => {
  const page = await screen(t); await open(page);
  const pending = await holdCalculations(page);
  await page.locator('form').evaluate(form => { form.requestSubmit(); form.requestSubmit(); });
  await until(() => pending.length > 0);
  assert.equal(pending.length, 1);
  assert.equal(await page.locator('#calculate').isDisabled(), true);
  await pending[0](); await state(page, 'success');
});

test('broken transport or malformed result can be retried without a stale summary', async t => {
  const page = await screen(t); await open(page);
  await calculate(page); await state(page, 'success');
  for (const bad of ['network', 'malformed']) {
    await page.route('**/api/plan', route => bad === 'network' ? route.abort('failed') : route.fulfill({ json: { status: 'unknown' } }));
    await calculate(page); await state(page, 'transport_error');
    assert.equal(await page.locator('#result').innerText(), '');
    await page.unroute('**/api/plan');
    await calculate(page); await state(page, 'success');
    assert.match(await page.locator('#result').innerText(), /135/);
  }
});

test('ten second timeout allows a manual retry', async t => {
  const page = await screen(t); await page.clock.install(); await open(page);
  let held;
  await page.route('**/api/plan', route => { held = route; });
  await calculate(page); await until(() => held);
  await page.clock.fastForward(10001); await state(page, 'transport_error');
  assert.match(await page.locator('#status').innerText(), /Повторите/);
  await page.unroute('**/api/plan');
  await calculate(page); await state(page, 'success');
});

test('partial success and fractional durations preserve full displayed information', async t => {
  const page = await screen(t); await open(page);
  for (const name of ['partial', 'fractional']) {
    const result = examples.cases.find(row => row.case === name).observed_core_result;
    await page.route('**/api/plan', route => route.fulfill({ json: result }));
    await calculate(page); await state(page, 'success');
    const text = await page.locator('#result').innerText();
    assert.match(text, name === 'partial' ? /Покрытие данных неполное/ : /135,5/);
    if (name === 'fractional') assert.match(text, /11:50:30/);
    await page.unroute('**/api/plan');
  }
});

test('metadata failure offers reload and a narrow screen has no horizontal overflow', async t => {
  const page = await screen(t, { viewport: { width: 390, height: 844 } });
  await page.route('**/api/trip', route => route.abort('failed'));
  await page.goto(url);
  assert.equal(await page.locator('#calculate').count(), 1, 'Calculation screen is not implemented');
  await page.getByRole('button', { name: 'Повторить загрузку' }).waitFor({ state: 'visible' });
  assert.equal(await page.locator('#calculate').isDisabled(), true);
  await page.unroute('**/api/trip');
  await page.getByRole('button', { name: 'Повторить загрузку' }).click();
  await page.waitForFunction(() => !document.querySelector('#calculate').disabled);
  await calculate(page); await state(page, 'success');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
  if (process.env.HW5_SCREENSHOTS_DIR) await page.screenshot({ path: join(process.env.HW5_SCREENSHOTS_DIR, 'demo-mobile.png'), fullPage: true });
});
