import { useRef, useState, type FormEvent } from 'react';
import { Check, CircleAlert, Copy, ExternalLink, FileText, LoaderCircle, Sparkles, Tag } from 'lucide-react';
import { AlertDialog } from 'radix-ui';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  createIssue, IssueCreationError, repository, repositoryIssuesUrl, requestReview,
  type CreatedIssue, type Draft, type Recommendation,
} from './issue-review';

type ReviewState =
  | { status: 'idle' | 'loading' | 'empty' | 'error' }
  | { status: 'success'; result: Recommendation };

type PublicationState =
  | { status: 'idle' | 'publishing' }
  | { status: 'error'; detail?: string }
  | { status: 'published'; issue: CreatedIssue };

const examples: readonly Draft[] = [
  {
    title: 'Ошибка при сохранении профиля',
    body: 'После смены имени и нажатия «Сохранить» сервер возвращает ошибку 500, а имя остаётся прежним.',
  },
  {
    title: 'Добавить экспорт заказа в CSV',
    body: 'Нужна новая возможность выгружать позиции заказа и итоговую сумму в CSV.',
  },
  {
    title: 'Обновить инструкцию запуска в README',
    body: 'Опишите существующие команды make demo и make test и укажите, из какой папки их запускать.',
  },
  { title: 'Нужна помощь', body: '' },
  {
    title: 'Скидка увеличивает сумму заказа',
    body: 'Добавляю товар за 100 ₽ и применяю скидку 10%. Ожидаю итог 90 ₽, калькулятор показывает 110 ₽.',
  },
  {
    title: 'Добавить фильтр по автору в отчёт Issues',
    body: 'Хочу выбирать автора перед формированием отчёта, чтобы видеть статистику только по его обращениям.',
  },
  {
    title: 'Уточнить порядок запуска тестов',
    body: 'В проекте уже есть make test. Из какой папки запускать эту команду и какие зависимости нужно установить?',
  },
  { title: 'Что-то нужно проверить', body: 'Не уверен, с чего начать.' },
];

const tips: Record<Recommendation['label'], string> = {
  bug: 'Добавьте шаги воспроизведения и укажите, какой результат ожидали.',
  task: 'Уточните, что нужно сделать с существующей функцией.',
  'feature-request': 'Опишите, кому пригодится новая возможность и как она должна работать.',
  'needs-triage': 'Уточните цель или добавьте детали для ручного разбора.',
};

const percent = new Intl.NumberFormat('ru-RU', { style: 'percent', maximumFractionDigits: 1 });

export function App() {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [invalid, setInvalid] = useState(false);
  const [state, setState] = useState<ReviewState>({ status: 'idle' });
  const [publication, setPublication] = useState<PublicationState>({ status: 'idle' });
  const requestPending = useRef(false);
  const nextExample = useRef(0);
  const titleField = useRef<HTMLInputElement>(null);
  const loading = state.status === 'loading';
  const publishing = publication.status === 'publishing';
  const locked = loading || publishing;
  const published = publication.status === 'published';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (requestPending.current || published) return;

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setInvalid(true);
      titleField.current?.focus();
      return;
    }

    requestPending.current = true;
    setInvalid(false);
    setPublication({ status: 'idle' });
    setState({ status: 'loading' });
    try {
      const result = await requestReview({ title: trimmedTitle, body: body.trim() });
      setState(result ? { status: 'success', result } : { status: 'empty' });
    } catch {
      setState({ status: 'error' });
    } finally {
      requestPending.current = false;
    }
  }

  async function publish() {
    if (state.status !== 'success' || requestPending.current || published) return;

    requestPending.current = true;
    setPublication({ status: 'publishing' });
    try {
      const issue = await createIssue({ title: title.trim(), body: body.trim() });
      setPublication({ status: 'published', issue });
    } catch (error) {
      setPublication({
        status: 'error',
        detail: error instanceof IssueCreationError ? error.message : undefined,
      });
    } finally {
      requestPending.current = false;
    }
  }

  function clearResult() {
    setState({ status: 'idle' });
    setPublication({ status: 'idle' });
  }

  function changeTitle(value: string) {
    setTitle(value);
    if (value.trim()) setInvalid(false);
    clearResult();
  }

  function loadExample() {
    const example = examples[nextExample.current];
    nextExample.current = (nextExample.current + 1) % examples.length;
    changeTitle(example.title);
    setBody(example.body);
    titleField.current?.focus();
  }

  return (
    <>
      <header className="site-header">
        <div className="shell brand">
          <span className="brand-icon"><CircleAlert aria-hidden="true" /></span>
          <span>Issue Review</span>
        </div>
      </header>
      <main>
        <section className="hero" aria-labelledby="page-title">
          <div className="shell hero-inner">
            <h1 id="page-title">Проверка Issue <span>перед публикацией</span></h1>
            <p>Узнайте, какой лейбл подходит черновику, прежде чем создать Issue на GitHub.</p>
          </div>
        </section>

        <div className="shell review-grid">
          <Card className="review-card">
            <CardHeader className="review-header">
              <div className="heading">
                <span className="card-icon"><FileText aria-hidden="true" /></span>
                <h2 id="draft-heading">Черновик Issue</h2>
              </div>
              <Button
                variant="outline" size="sm" className="example-button" type="button" disabled={locked}
                onClick={loadExample}
              >
                <Copy aria-hidden="true" /> Загрузить пример
              </Button>
            </CardHeader>
            <CardContent className="review-content">
              <form id="issue-form" onSubmit={submit} aria-labelledby="draft-heading" noValidate>
                <div className="field">
                  <label htmlFor="issue-title">Заголовок <span aria-hidden="true">*</span></label>
                  <Input
                    id="issue-title" ref={titleField} name="title" value={title} required maxLength={120}
                    aria-invalid={invalid} aria-describedby={invalid ? 'title-error' : undefined}
                    placeholder="Например, ошибка при сохранении" readOnly={locked}
                    onChange={event => changeTitle(event.target.value)}
                  />
                  {invalid && <p id="title-error" className="field-error" role="alert">Введите заголовок Issue.</p>}
                </div>
                <div className="field">
                  <div className="label-line">
                    <label htmlFor="issue-description">Описание</label>
                    <span>Необязательно</span>
                  </div>
                  <Textarea
                    id="issue-description" name="body" value={body} rows={3} maxLength={2000}
                    aria-describedby="description-limit" readOnly={locked}
                    placeholder="Что произошло? Добавьте шаги и ожидаемый результат."
                    onChange={event => {
                      setBody(event.target.value);
                      clearResult();
                    }}
                  />
                  <span id="description-limit" className="field-note">{body.length} / 2000</span>
                </div>
                <Button className="check-button" type="submit" disabled={locked || published}>
                  {loading ? <LoaderCircle className="spinner" aria-hidden="true" /> : <Sparkles aria-hidden="true" />}
                  {loading ? 'Проверяем…' : 'Проверить Issue'}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="review-card result-card">
            <CardHeader className="review-header">
              <div className="heading">
                <span className="card-icon"><Tag aria-hidden="true" /></span>
                <h2 id="result-title">Рекомендация</h2>
              </div>
            </CardHeader>
            <CardContent className="review-content result-content" role="region" aria-labelledby="result-title">
              <div role="status" aria-live="polite" aria-atomic="true">
                {state.status === 'idle' && (
                  <div className="result-placeholder">
                    <Tag aria-hidden="true" />
                    <h3>Результата пока нет</h3>
                    <p>Заполните черновик и нажмите «Проверить Issue».</p>
                  </div>
                )}
                {state.status === 'loading' && (
                  <div className="result-placeholder">
                    <LoaderCircle className="spinner" aria-hidden="true" />
                    <h3>Подбираем лейбл</h3>
                    <p>Это может занять несколько секунд.</p>
                  </div>
                )}
                {state.status === 'empty' && (
                  <Alert className="feedback">
                    <Tag aria-hidden="true" />
                    <AlertTitle>Рекомендация отсутствует</AlertTitle>
                    <AlertDescription>Дополните черновик и попробуйте ещё раз.</AlertDescription>
                  </Alert>
                )}
                {state.status === 'error' && (
                  <Alert className="feedback error-feedback" variant="destructive">
                    <CircleAlert aria-hidden="true" />
                    <AlertTitle>Не удалось получить рекомендацию</AlertTitle>
                    <AlertDescription>Текст черновика сохранён. Попробуйте ещё раз.</AlertDescription>
                  </Alert>
                )}
                {state.status === 'success' && (
                  <div className="recommendation">
                    <div className="result-line">
                      <span>Рекомендуемый лейбл</span>
                      <Badge className="result-label">{state.result.label}</Badge>
                    </div>
                    <div className="result-line">
                      <label htmlFor="confidence">Уверенность модели</label>
                      <strong>{percent.format(state.result.confidence)}</strong>
                    </div>
                    <progress id="confidence" value={state.result.confidence} max={1} />
                    <Alert className="feedback">
                      <Sparkles aria-hidden="true" />
                      <AlertDescription>{tips[state.result.label]}</AlertDescription>
                    </Alert>
                  </div>
                )}
              </div>
              {state.status === 'error' && (
                <Button className="retry-button" type="submit" form="issue-form" variant="outline">
                  Повторить проверку
                </Button>
              )}
              {state.status === 'success' && publication.status !== 'published' && (
                <section className="publication-actions" aria-label="Публикация">
                  {publication.status === 'error' && (
                    <Alert className="feedback error-feedback" role="alert" variant="destructive">
                      <CircleAlert aria-hidden="true" />
                      <AlertTitle>Не удалось создать Issue</AlertTitle>
                      <AlertDescription>
                        {publication.detail ?? (
                          <p>Черновик сохранён. Перед повтором проверьте, появился ли Issue в <a href={repositoryIssuesUrl} target="_blank" rel="noreferrer">репозитории</a>.</p>
                        )}
                      </AlertDescription>
                    </Alert>
                  )}
                  <AlertDialog.Root>
                    <AlertDialog.Trigger asChild>
                      <Button className="publish-button" type="button" disabled={publishing}>
                        {publishing && <LoaderCircle className="spinner" aria-hidden="true" />}
                        {publishing ? 'Публикуем…' : publication.status === 'error' ? 'Повторить публикацию' : 'Создать Issue'}
                      </Button>
                    </AlertDialog.Trigger>
                    <AlertDialog.Portal>
                      <AlertDialog.Overlay className="publish-overlay" />
                      <AlertDialog.Content className="publish-dialog">
                        <AlertDialog.Title>Создать Issue на GitHub?</AlertDialog.Title>
                        <AlertDialog.Description>
                          Черновик будет опубликован в репозитории <strong>{repository}</strong>.
                        </AlertDialog.Description>
                        <p className="publish-draft">{title.trim()}</p>
                        <div className="dialog-actions">
                          <AlertDialog.Cancel asChild>
                            <Button className="example-button" type="button" variant="outline">Отмена</Button>
                          </AlertDialog.Cancel>
                          <AlertDialog.Action asChild>
                            <Button className="publish-button" type="button" onClick={publish}>Подтвердить публикацию</Button>
                          </AlertDialog.Action>
                        </div>
                      </AlertDialog.Content>
                    </AlertDialog.Portal>
                  </AlertDialog.Root>
                </section>
              )}
              {publication.status === 'published' && (
                <Alert className="feedback published-feedback" role="status">
                  <Check aria-hidden="true" />
                  <AlertTitle>Issue создан</AlertTitle>
                  <AlertDescription>
                    <a href={publication.issue.url} target="_blank" rel="noreferrer">
                      Открыть Issue #{publication.issue.number} на GitHub <ExternalLink aria-hidden="true" />
                    </a>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
