const $ = selector => document.querySelector(selector);
const form = $('form');
const result = $('#result');
const fields = {
  'departure_window.start': ['#window-start', '#start-error'],
  'departure_window.end': ['#window-end', '#end-error'],
  boarding_buffer_minutes: ['#buffer', '#buffer-error'],
  max_options: ['#max-options', '#max-error'],
};
let metadata = null;
let revision = 0;
let sequence = 0;
let active = null;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function setState(state, message) {
  document.body.dataset.state = state;
  $('#status').textContent = message;
}

function clearResult() {
  result.replaceChildren();
  $('#empty').hidden = false;
}

function clearErrors() {
  $('#form-error').textContent = '';
  for (const [control, message] of Object.values(fields)) {
    $(control).removeAttribute('aria-invalid');
    $(message).textContent = '';
  }
}

function showErrors(errors) {
  for (const [field, text] of errors) {
    const target = fields[field];
    if (target) {
      $(target[0]).setAttribute('aria-invalid', 'true');
      $(target[1]).textContent = text;
    } else $('#form-error').textContent = text;
  }
  const first = fields[errors[0]?.[0]];
  if (first) $(first[0]).focus();
}

function dateText(value) {
  const [year, month, day] = value.slice(0, 10).split('-');
  return `${day}.${month}.${year}`;
}

function clock(value) {
  const text = value.slice(11, 19);
  return text.endsWith(':00') ? text.slice(0, 5) : text;
}

function moment(value) { return `${dateText(value)}, ${clock(value)} МСК`; }
function minutes(value) { return `${String(value).replace('.', ',')} мин`; }

function calendarValue(value) {
  const match = /^([0-9]{2})\.([0-9]{2})\.([0-9]{4}) ([0-9]{2}):([0-9]{2})$/.exec(value);
  if (!match) return null;
  const [day, month, year, hour, minute] = match.slice(1).map(Number);
  if (year < 1) return null;
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(hour, minute, 0, 0);
  const valid = date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day && date.getUTCHours() === hour && date.getUTCMinutes() === minute;
  return valid ? `${match[3]}-${match[2]}-${match[1]}T${match[4]}:${match[5]}:00+03:00` : null;
}

function parameters() {
  const errors = [];
  const values = {};
  for (const [field, [selector]] of Object.entries(fields)) {
    const value = $(selector).value;
    if (field.startsWith('departure_window.')) {
      const normalized = calendarValue(value);
      if (!normalized) errors.push([field, 'Укажите корректные дату и время по Москве: ДД.ММ.ГГГГ ЧЧ:ММ.']);
      else values[field] = normalized;
    } else {
      const bounds = metadata.limits[field];
      const number = Number(value);
      if (!/^[0-9]+$/.test(value) || !Number.isSafeInteger(number) || number < bounds.min || number > bounds.max) {
        errors.push([field, `Введите целое число от ${bounds.min} до ${bounds.max}.`]);
      } else values[field] = number;
    }
  }
  if (values['departure_window.start'] && values['departure_window.end'] && values['departure_window.end'] < values['departure_window.start']) {
    errors.push(['departure_window.end', 'Конец окна должен быть не раньше начала.']);
  }
  return { errors, payload: {
    departure_window: { start: values['departure_window.start'], end: values['departure_window.end'] },
    boarding_buffer_minutes: values.boarding_buffer_minutes,
    max_options: values.max_options,
  } };
}

const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const strings = value => Array.isArray(value) && value.every(item => typeof item === 'string');
const finite = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const validDate = value => typeof value === 'string' && /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value) && Boolean(calendarValue(`${dateText(value)} 00:00`));
function validMoment(value) {
  if (typeof value !== 'string') return false;
  const match = /^([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?\+03:00$/.exec(value);
  return Boolean(match && validDate(match[1]) && Number(match[2]) < 24 && Number(match[3]) < 60 && Number(match[4]) < 60);
}

function validSource(source) {
  if (!record(source) || typeof source.id !== 'string' || !validMoment(source.checked_at) ||
      !strings(source.valid_dates) || !source.valid_dates.every(validDate) || typeof source.verified !== 'boolean' ||
      !['fixture', 'manual', 'live'].includes(source.mode)) return false;
  try { return ['http:', 'https:'].includes(new URL(source.url).protocol); } catch { return false; }
}

function validMetadata(data) {
  if (!record(data) || !record(data.route) ||
      !['id', 'origin', 'destination'].every(key => typeof data.route[key] === 'string' && data.route[key].length > 0) ||
      data.timezone !== 'Europe/Moscow' || !['fixture', 'real', 'mixed'].includes(data.data_kind) ||
      !Array.isArray(data.schedule_dates) || !data.schedule_dates.every(validDate) ||
      !Array.isArray(data.sources) || !data.sources.every(validSource) ||
      !record(data.defaults) || !record(data.defaults.departure_window) || !record(data.limits)) return false;
  const window = data.defaults.departure_window;
  if (!validMoment(window.start) || !validMoment(window.end) || window.end < window.start) return false;
  for (const [field, minimum, maximum] of [['boarding_buffer_minutes', 0, 1440], ['max_options', 1, 5]]) {
    const bounds = data.limits[field];
    const value = data.defaults[field];
    if (!record(bounds) || bounds.min !== minimum || bounds.max !== maximum ||
        !Number.isInteger(value) || value < minimum || value > maximum) return false;
  }
  return true;
}

function validResult(data) {
  if (!record(data) || !['ok', 'no_routes', 'needs_data'].includes(data.status) ||
      !Array.isArray(data.options) || !strings(data.warnings) ||
      !Array.isArray(data.sources) || !data.sources.every(validSource) ||
      !['fixture', 'real', 'mixed'].includes(data.data_kind) || !record(data.search_scope)) return false;
  const scope = data.search_scope;
  if (typeof scope.complete !== 'boolean' || !strings(scope.chains) ||
      typeof scope.claim !== 'string' || !Number.isInteger(scope.max_scheduled_stages) ||
      !record(scope.departure_window) || !validMoment(scope.departure_window.start) || !validMoment(scope.departure_window.end)) return false;
  if ((data.status === 'ok') !== (data.options.length > 0) ||
      (data.status === 'no_routes' && !scope.complete) ||
      (data.status === 'needs_data' && scope.complete)) return false;
  return data.options.every(option => record(option) &&
    ['chain_id', 'origin', 'destination'].every(key => typeof option[key] === 'string') &&
    validMoment(option.leave_at) && validMoment(option.arrive_at) &&
    finite(option.total_minutes) && finite(option.waiting_minutes) &&
    Number.isInteger(option.transfer_count) && option.transfer_count >= 0 &&
    Array.isArray(option.timeline) && option.timeline.every(event => record(event) &&
      ['access', 'wait', 'walk', 'ride', 'egress'].includes(event.kind) &&
      validMoment(event.start) && validMoment(event.end) && finite(event.minutes) && typeof event.description === 'string'));
}

function renderOption(option, index) {
  const section = node('section', undefined, 'option');
  section.append(node('h2', `Вариант ${index + 1}`));
  const clocks = node('div', undefined, 'clocks');
  for (const [label, time] of [['Выход', option.leave_at], ['Прибытие', option.arrive_at]]) {
    if (clocks.children.length) clocks.append(node('span', '→', 'separator'));
    const group = node('div', undefined, 'clock-group');
    const stamp = node('time', clock(time)); stamp.dateTime = time;
    group.append(node('span', `${label} ${dateText(time)}`), stamp); clocks.append(group);
  }
  section.append(clocks);
  const metrics = node('dl', undefined, 'metrics');
  for (const [label, value] of [
    ['Полное время', minutes(option.total_minutes)],
    ['Ожидание на участках с расписаниями', minutes(option.waiting_minutes)],
    ['Пересадки между участками с расписаниями', String(option.transfer_count)],
  ]) {
    const group = node('div'); group.append(node('dt', label), node('dd', value)); metrics.append(group);
  }
  section.append(metrics);
  const timeline = node('ol', undefined, 'timeline');
  for (const event of option.timeline) {
    const item = node('li');
    item.append(node('div', `${moment(event.start)} – ${clock(event.end)} · ${minutes(event.minutes)}`, 'event-time'));
    item.append(node('p', event.description));
    if (event.from_name && event.to_name) item.append(node('p', `${event.from_name} → ${event.to_name}`, 'hint'));
    if (event.estimated) item.append(node('p', `Оценка${event.basis ? `: ${event.basis}` : ''}`, 'hint'));
    if (event.buffer_minutes !== undefined) item.append(node('p', `Запас пересадки: ${minutes(event.buffer_minutes)}`, 'hint'));
    if (event.source_id) {
      const link = node('a', `Источник ${event.source_id}`); link.href = `#source-${encodeURIComponent(event.source_id)}`; item.append(link);
    }
    timeline.append(item);
  }
  section.append(timeline);
  return section;
}

function renderResult(data, sent) {
  clearResult(); $('#empty').hidden = true;
  result.append(node('p', `Окно выхода: ${moment(sent.departure_window.start)} — ${moment(sent.departure_window.end)}. Запас: ${minutes(sent.boarding_buffer_minutes)}. Не более ${sent.max_options} вариантов.`, 'summary'));
  if (data.status !== 'ok') result.append(node('h2', data.status === 'no_routes' ?
    'В этом окне нет подходящих вариантов среди переданных подтверждённых цепочек' : 'Не хватает подтверждённых данных на запрошенное окно'));
  if (!data.search_scope.complete) result.append(node('p', 'Покрытие данных неполное. Вывод относится к имеющимся подтверждённым данным.', 'notice'));
  data.options.forEach((option, index) => result.append(renderOption(option, index)));
  if (data.options.length) result.append(node('p', 'Ожидание и пересадки внутри оценочного городского подхода включены в его оценку.', 'hint'));
  result.append(node('h3', 'Предупреждения'));
  const warnings = node('ul', undefined, 'warnings');
  for (const text of data.warnings) warnings.append(node('li', text));
  result.append(warnings, node('h3', 'Источники'));
  const sourceList = node('ul', undefined, 'source-list');
  for (const source of data.sources) {
    const item = node('li'); item.id = `source-${encodeURIComponent(source.id)}`;
    const link = node('a', `${source.mode === 'fixture' ? 'Учебный источник' : 'Источник'} ${source.id}`);
    link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    item.append(link, node('p', `Режим: ${source.mode}. Даты расписания: ${source.valid_dates.map(dateText).join(', ')}. Проверка: ${moment(source.checked_at)}.`));
    item.append(node('p', `Подтверждён${source.mode === 'fixture' ? ' внутри учебного снимка' : ''}: ${source.verified ? 'да' : 'нет'}.`));
    sourceList.append(item);
  }
  result.append(sourceList, node('p', `Происхождение данных: ${data.data_kind}${data.data_kind === 'real' ? '. Это не обещание актуальности на сегодня.' : ' — присутствуют вымышленные данные.'}`, 'hint'));
  const scope = node('section', undefined, 'scope');
  scope.append(node('h3', 'Область поиска'), node('p', `${data.search_scope.claim}; не поиск по всей транспортной сети.`));
  const details = node('dl');
  for (const [label, value] of [
    ['Цепочки', data.search_scope.chains.join(', ')],
    ['Окно', `${moment(data.search_scope.departure_window.start)} — ${moment(data.search_scope.departure_window.end)}`],
    ['Этапов с расписаниями, не более', data.search_scope.max_scheduled_stages],
    ['Полнота', data.search_scope.complete ? 'полное покрытие' : 'неполное покрытие'],
  ]) details.append(node('dt', label), node('dd', String(value)));
  scope.append(details); result.append(scope);
}

function current(token) { return active === token && token.revision === revision; }

form.addEventListener('input', () => {
  if (!metadata) return;
  revision += 1;
  if (active) clearTimeout(active.timer);
  active = null;
  clearErrors(); clearResult();
  $('#calculate').disabled = false;
  setState('editing', 'Параметры изменены — нажмите «Рассчитать».');
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!metadata || (active && active.revision === revision)) return;
  clearErrors(); clearResult();
  const { errors, payload } = parameters();
  if (errors.length) {
    setState('invalid', 'Проверьте параметры поездки.'); showErrors(errors); return;
  }
  const controller = new AbortController();
  const token = { revision, sequence: ++sequence };
  active = token; $('#calculate').disabled = true;
  setState('pending', 'Рассчитываем…');
  token.timer = setTimeout(() => {
    if (!current(token)) return;
    active = null; controller.abort(); clearResult(); $('#calculate').disabled = false;
    setState('transport_error', 'Ответ не получен за 10 секунд. Повторите расчёт.');
  }, 10000);
  try {
    const response = await fetch('/api/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal });
    const data = await response.json();
    if (!current(token)) return;
    if (!response.ok) {
      if (response.status === 422 && record(data.error) && typeof data.error.message === 'string') {
        setState('invalid', 'Проверьте параметры поездки.'); showErrors([[data.error.field, data.error.message]]);
      } else setState('transport_error', 'Не удалось выполнить расчёт. Повторите запрос.');
      return;
    }
    if (!validResult(data)) throw new Error('Unusable calculation response');
    renderResult(data, payload);
    setState(data.status === 'ok' ? 'success' : data.status, data.status === 'ok' ?
      `Найдено вариантов: ${data.options.length}.` : data.status === 'no_routes' ? 'Подходящих вариантов нет.' : 'Нужны подтверждённые данные.');
  } catch {
    if (current(token)) { clearResult(); setState('transport_error', 'Не удалось получить результат. Повторите расчёт.'); }
  } finally {
    clearTimeout(token.timer);
    if (current(token)) { active = null; $('#calculate').disabled = false; }
  }
});

async function loadMetadata() {
  $('#reload').hidden = true; $('#controls').disabled = true; $('#calculate').disabled = true;
  setState('loading', 'Загружаем данные…');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch('/api/trip', { signal: controller.signal });
    const data = await response.json();
    if (!response.ok || !validMetadata(data)) throw new Error('Unusable metadata');
    metadata = data;
    $('#origin').textContent = data.route.origin; $('#destination').textContent = data.route.destination;
    $('#snapshot-meta').textContent = `Расписание на ${data.schedule_dates.map(dateText).join(', ')}. Проверка источников: ${data.sources.map(source => moment(source.checked_at)).join(', ')}.`;
    $('#window-start').value = `${dateText(data.defaults.departure_window.start)} ${clock(data.defaults.departure_window.start)}`;
    $('#window-end').value = `${dateText(data.defaults.departure_window.end)} ${clock(data.defaults.departure_window.end)}`;
    $('#buffer').value = data.defaults.boarding_buffer_minutes;
    $('#max-options').value = data.defaults.max_options;
    $('#controls').disabled = false; $('#calculate').disabled = false;
    setState('initial', 'Параметры загружены. Можно рассчитать поездку.');
  } catch {
    metadata = null; $('#reload').hidden = false;
    setState('transport_error', 'Не удалось загрузить учебный маршрут. Повторите загрузку.');
  } finally { clearTimeout(timer); }
}

$('#reload').addEventListener('click', loadMetadata);
loadMetadata();
