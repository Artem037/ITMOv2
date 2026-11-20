export type Draft = { title: string; body: string };
export type CreatedIssue = { number: number; url: string };
export const repository = 'Artem037/ITMOv2';
export const repositoryIssuesUrl = `https://github.com/${repository}/issues`;

const labels = {
  bug: 'bug',
  task: 'task',
  feature: 'feature-request',
  unknown: 'needs-triage',
} as const;

export type Recommendation = {
  label: (typeof labels)[keyof typeof labels];
  confidence: number;
};

export async function requestReview(draft: Draft): Promise<Recommendation | null> {
  const response = await fetch('/api/issue-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) throw new Error('Не удалось получить рекомендацию');
  if (response.status === 204) return null;

  const data: unknown = await response.json();
  if (data === null) return null;
  if (typeof data !== 'object' || !('type' in data) || !('confidence' in data)) {
    throw new Error('Некорректный ответ классификатора');
  }

  const { type, confidence } = data;
  if (typeof type !== 'string' || !Object.hasOwn(labels, type) ||
      typeof confidence !== 'number' || !Number.isFinite(confidence) ||
      confidence < 0 || confidence > 1) {
    throw new Error('Некорректный ответ классификатора');
  }

  return {
    label: confidence < 0.8 ? 'needs-triage' : labels[type as keyof typeof labels],
    confidence,
  };
}

export class IssueCreationError extends Error {}

export async function createIssue(draft: Draft): Promise<CreatedIssue> {
  const response = await fetch('/api/issues', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(draft),
    signal: AbortSignal.timeout(30_000),
  });

  if (response.status === 503) {
    const data = await response.json().catch(() => null);
    if (data?.code === 'publication_not_configured') {
      throw new IssueCreationError('Подключите сценарий публикации n8n. Черновик сохранён.');
    }
  }
  if (response.status >= 400 && response.status < 500) {
    throw new IssueCreationError('Сервер отклонил публикацию. Черновик сохранён. Можно повторить попытку.');
  }
  if (response.status !== 201) throw new Error();

  const data: unknown = await response.json();
  if (data === null || typeof data !== 'object' || !('number' in data) || !('url' in data) ||
      typeof data.number !== 'number' || !Number.isSafeInteger(data.number) || data.number < 1 ||
      data.url !== `${repositoryIssuesUrl}/${data.number}`) {
    throw new Error();
  }
  return { number: data.number, url: data.url };
}
