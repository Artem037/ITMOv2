const modulePattern = /^(?<prefix>(?:\/\/[^\r\n]*\n)?export function applyDiscount\(total, percent\) \{\n  return )(?<expression>[^\r\n;]+)(?<suffix>;\n\}\n?)$/u;
const arithmeticTokens = /total|percent|\d+(?:\.\d+)?|[ +*/()-]/gu;
const boundaries = [
  { total: 80, percent: 0, expected: 80 },
  { total: 120, percent: 100, expected: 0 },
  { total: 1.333, percent: 100, expected: 0 },
  { total: 0, percent: 15, expected: 0 },
  { total: 24.5, percent: 12.5, expected: 21.4375 },
  { total: 200, percent: 25, expected: 150 },
  { total: 1e308, percent: 50, expected: 5e307 },
];

export function parseReport(body) {
  const fields = /^component: discount\ntotal: (\d+(?:\.\d+)?)\npercent: (\d+(?:\.\d+)?)\nexpected: (\d+(?:\.\d+)?)$/u
    .exec(body.replace(/\r\n/g, '\n').trim());
  if (!fields) throw new Error('Expected a discount report with total, percent and expected.');

  const [total, percent, expected] = fields.slice(1).map(Number);
  if (![total, percent, expected].every(Number.isFinite) || percent > 100 ||
      !sameNumber(total * (1 - percent / 100), expected)) {
    throw new Error('The report does not describe a valid discount.');
  }
  return { total, percent, expected };
}

function asArithmetic(expression) {
  if (typeof expression !== 'string' || !expression || expression.length > 160 ||
      expression.replace(arithmeticTokens, '') ||
      /\+\+|--|\/\/|\/\*/u.test(expression)) {
    throw new Error('The return expression must contain only arithmetic on total and percent.');
  }
  return new Function('total', 'percent', `return (${expression});`);
}

function moduleParts(source) {
  const parts = modulePattern.exec(source)?.groups;
  if (!parts) throw new Error('Unexpected discount module structure.');
  return parts;
}

export function replaceExpression(source, expression) {
  const { prefix, suffix } = moduleParts(source);
  const value = typeof expression === 'string'
    ? expression.trim().replace(/^return +/u, '').replace(/;$/u, '').trim()
    : expression;
  asArithmetic(value);
  return prefix + value + suffix;
}

function sameNumber(a, b) {
  if (b === 0) return a === 0;
  return Number.isFinite(a) && Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(b));
}

export function discountResults(source, report) {
  const applyDiscount = asArithmetic(moduleParts(source).expression);
  return [report, ...boundaries].map(example => {
    const { total, percent, expected } = example;
    const actual = applyDiscount(total, percent);
    return { ...example, actual, passed: sameNumber(actual, expected) };
  });
}

export function regressionFailures(source, report) {
  return discountResults(source, report).filter(result => !result.passed)
    .map(({ passed, ...failure }) => failure);
}

export function mergeAllowed({ review, failures, actualHead, reviewedHead, actualBase, reviewedBase }) {
  return review?.approved === true && Array.isArray(review.seriousIssues) && !review.seriousIssues.length &&
    !failures.length && Boolean(reviewedHead) && actualHead === reviewedHead &&
    Boolean(reviewedBase) && actualBase === reviewedBase;
}
