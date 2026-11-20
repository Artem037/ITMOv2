import { expect, test, type Page } from '@playwright/test';

const reviewEndpoint = '**/api/issue-review';
const createEndpoint = '**/api/issues';
const recommendation = { type: 'bug', confidence: 0.94 };
const issue = { number: 42, url: 'https://github.com/Artem037/ITMOv2/issues/42' };
const draft = { title: 'Ошибка при сохранении', body: 'Сервер возвращает 500.' };

function holdResponse() {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  return { pending, release };
}

async function enterDraft(page: Page) {
  await page.getByLabel('Заголовок').fill(draft.title);
  await page.getByLabel('Описание').fill(draft.body);
}

async function reviewDraft(page: Page) {
  await page.route(reviewEndpoint, route => route.fulfill({ status: 200, json: recommendation }));
  await enterDraft(page);
  await page.getByRole('button', { name: 'Проверить Issue' }).click();
  await expect(page.getByText(/^94\s*%$/)).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.route(reviewEndpoint, route => route.abort());
  await page.route(createEndpoint, route => route.abort());
  await page.goto('/');
});

test('загружает разные примеры и позволяет редактировать черновик', async ({ page }) => {
  const title = page.getByLabel('Заголовок');
  const example = page.getByRole('button', { name: 'Загрузить пример' });
  await expect(page.getByRole('heading', { name: 'Черновик Issue' })).toBeVisible();
  await expect(page.getByText('Результата пока нет')).toBeVisible();

  for (const expected of [/Ошибка/, /CSV/, /README/, /Нужна помощь/]) {
    await example.click();
    await expect(title).toHaveValue(expected);
  }
  await expect(page.getByLabel('Описание')).toHaveValue('');
  await title.fill(draft.title);
  await expect(title).toHaveValue(draft.title);
});

for (const [name, value] of [['пустой', ''], ['из пробелов', '   ']]) {
  test(`заголовок (${name}) не отправляется и получает фокус`, async ({ page }) => {
    const requests: string[] = [];
    page.on('request', request => requests.push(request.url()));
    const title = page.getByLabel('Заголовок');
    await title.fill(value);
    await page.getByRole('button', { name: 'Проверить Issue' }).click();
    await expect(page.getByRole('alert')).toHaveText('Введите заголовок Issue.');
    await expect(title).toHaveAttribute('aria-invalid', 'true');
    await expect(title).toBeFocused();
    expect(requests.some(url => url.endsWith('/api/issue-review'))).toBe(false);
  });
}

test('показывает загрузку и блокирует повторную проверку', async ({ page }) => {
  let requests = 0;
  const response = holdResponse();
  await page.route(reviewEndpoint, async route => {
    requests++;
    await response.pending;
    await route.fulfill({ status: 200, json: recommendation });
  });

  await enterDraft(page);
  await page.getByLabel('Заголовок').press('Enter');
  await expect(page.getByRole('button', { name: 'Проверяем…' })).toBeDisabled();
  await page.getByLabel('Заголовок').press('Enter');
  response.release();
  await expect(page.getByText(/^94\s*%$/)).toBeVisible();
  expect(requests).toBe(1);
});

test('обрабатывает пустую рекомендацию', async ({ page }) => {
  await page.route(reviewEndpoint, route => route.fulfill({ status: 204 }));
  await enterDraft(page);
  await page.getByRole('button', { name: 'Проверить Issue' }).click();
  await expect(page.getByText('Рекомендация отсутствует')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Создать Issue' })).toHaveCount(0);
});

test('сохраняет черновик при ошибке проверки и позволяет её повторить', async ({ page }) => {
  await page.route(reviewEndpoint, route => route.fulfill({ status: 200, json: recommendation }));
  await page.route(reviewEndpoint, route => route.fulfill({ status: 500 }), { times: 1 });
  await enterDraft(page);
  await page.getByRole('button', { name: 'Проверить Issue' }).click();
  await expect(page.getByText('Не удалось получить рекомендацию')).toBeVisible();
  await expect(page.getByLabel('Заголовок')).toHaveValue(draft.title);
  await expect(page.getByLabel('Описание')).toHaveValue(draft.body);
  await page.getByRole('button', { name: 'Повторить проверку' }).click();
  await expect(page.getByText(/^94\s*%$/)).toBeVisible();
});

test('отмена и Escape закрывают подтверждение без запроса', async ({ page }) => {
  await reviewDraft(page);
  const requests: string[] = [];
  page.on('request', request => requests.push(request.url()));
  const create = page.getByRole('button', { name: 'Создать Issue' });
  await create.click();
  const dialog = page.getByRole('alertdialog');
  await expect(dialog.getByText(draft.title)).toBeVisible();
  const cancel = dialog.getByRole('button', { name: 'Отмена' });
  await expect(cancel).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(create).toBeFocused();
  await page.keyboard.press('Enter');
  await cancel.click();
  await expect(dialog).toHaveCount(0);
  expect(requests.some(url => url.endsWith('/api/issues'))).toBe(false);
});

test('проходит от черновика до ссылки на GitHub с одним запросом публикации', async ({ page }) => {
  const publicationRequests: { method: string; body: unknown }[] = [];
  const response = holdResponse();
  await page.route(createEndpoint, async route => {
    const request = route.request();
    publicationRequests.push({ method: request.method(), body: request.postDataJSON() });
    await response.pending;
    await route.fulfill({ status: 201, json: issue });
  });
  const reviewRequestPending = page.waitForRequest(reviewEndpoint);
  await reviewDraft(page);
  const reviewRequest = await reviewRequestPending;
  expect(reviewRequest.method()).toBe('POST');
  expect(reviewRequest.postDataJSON()).toEqual(draft);
  await expect(page.getByText('bug', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Создать Issue' }).click();
  await page.getByRole('alertdialog').getByRole('button', { name: 'Подтвердить публикацию' }).click();
  await expect(page.getByRole('button', { name: 'Публикуем…' })).toBeDisabled();
  await expect(page.getByLabel('Заголовок')).toHaveJSProperty('readOnly', true);
  await page.keyboard.press('Enter');
  response.release();

  const link = page.getByRole('link', { name: 'Открыть Issue #42 на GitHub' });
  await expect(page.getByText('Issue создан', { exact: true })).toBeVisible();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('href', issue.url);
  await expect(page.getByRole('button', { name: 'Создать Issue' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Проверить Issue' })).toBeDisabled();
  expect(publicationRequests).toEqual([{ method: 'POST', body: draft }]);
});

test('после ошибки публикации сохраняет черновик и даёт подтвердить повтор', async ({ page }) => {
  await page.route(createEndpoint, route => route.fulfill({ status: 201, json: issue }));
  await page.route(createEndpoint, route => route.fulfill({
    status: 502, json: { code: 'github_unavailable' },
  }), { times: 1 });
  await reviewDraft(page);

  const confirm = page.getByRole('alertdialog').getByRole('button', { name: 'Подтвердить публикацию' });
  await page.getByRole('button', { name: 'Создать Issue' }).click();
  await confirm.click();
  await expect(page.getByText('Не удалось создать Issue')).toBeVisible();
  await expect(page.getByLabel('Заголовок')).toHaveValue(draft.title);
  await expect(page.getByLabel('Описание')).toHaveValue(draft.body);

  await page.getByRole('button', { name: 'Повторить публикацию' }).click();
  await confirm.click();
  await expect(page.getByRole('link', { name: 'Открыть Issue #42 на GitHub' })).toBeVisible();
});

test('после изменения черновика требует новую рекомендацию', async ({ page }) => {
  await reviewDraft(page);
  await page.getByLabel('Описание').fill('Уточнение к ошибке');
  await expect(page.getByRole('button', { name: 'Создать Issue' })).toHaveCount(0);
  await expect(page.getByText('Результата пока нет')).toBeVisible();
});

test('показывает подтверждение на узком экране', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await reviewDraft(page);
  await page.getByRole('button', { name: 'Создать Issue' }).click();
  const dialog = page.getByRole('alertdialog');
  await expect(dialog).toBeInViewport();
  await expect(dialog.getByRole('button', { name: 'Подтвердить публикацию' })).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
});
