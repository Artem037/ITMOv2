import assert from 'node:assert/strict';
import test from 'node:test';
import { mergeAllowed, parseReport, regressionFailures, replaceExpression } from './discount-checks.mjs';

const reportText = 'component: discount\ntotal: 100\npercent: 10\nexpected: 90';
const report = { total: 100, percent: 10, expected: 90 };
const oldModule = 'export function applyDiscount(total, percent) {\n  return total + total * percent / 100;\n}\n';
const firstPatch = 'export function applyDiscount(total, percent) {\n  return total - total * percent / 100;\n}\n';
const newModule = 'export function applyDiscount(total, percent) {\n  return total * (1 - percent / 100);\n}\n';

test('extracts a reproducible discount case from the report', () => {
  assert.deepEqual(parseReport(reportText), report);
});

test('rejects an invalid percentage or an unrelated component', () => {
  assert.throws(() => parseReport(reportText.replace('percent: 10', 'percent: 110')));
  assert.throws(() => parseReport(reportText.replace('discount', 'stock')));
});

test('replaces only the discount return expression', () => {
  assert.equal(replaceExpression(oldModule, 'total - total * percent / 100'), firstPatch);
});

test('accepts a model response formatted as a single return statement', () => {
  assert.equal(replaceExpression(oldModule, 'return total - total * percent / 100;'), firstPatch);
  assert.throws(() => replaceExpression(oldModule, 'return process.exit(0);'));
});

test('rejects proposed changes that are outside arithmetic', () => {
  assert.throws(() => replaceExpression(oldModule, 'process.exit(0)'));
  assert.throws(() => replaceExpression(oldModule, 'total.constructor'));
});

test('detects the original bug with a literal expected result', () => {
  assert.deepEqual(regressionFailures(oldModule, report)[0], { ...report, actual: 110 });
  assert.deepEqual(regressionFailures(newModule, report), []);
});

test('catches a patch that fits one report but regresses a boundary', () => {
  const patch = replaceExpression(oldModule, '90');
  assert.ok(regressionFailures(patch, report).some(failure => failure.percent === 100));
});

test('requires an exact zero balance with a full discount on a fractional total', () => {
  const fullDiscount = { total: 1.333, percent: 100, expected: 0 };
  assert.equal(regressionFailures(firstPatch, fullDiscount)[0]?.actual, 2.220446049250313e-16);
  assert.deepEqual(regressionFailures(newModule, fullDiscount), []);
});

const verified = {
  review: { approved: true, seriousIssues: [] },
  failures: [],
  actualHead: 'abc',
  reviewedHead: 'abc',
  actualBase: 'def',
  reviewedBase: 'def',
};

test('permits a reviewed patch only while the reviewed heads match', () => {
  assert.equal(mergeAllowed(verified), true);
  assert.equal(mergeAllowed({ ...verified, actualHead: 'changed' }), false);
  assert.equal(mergeAllowed({ ...verified, actualBase: 'changed' }), false);
});

test('blocks serious review findings or failed regression checks', () => {
  assert.equal(mergeAllowed({
    ...verified,
    review: { approved: true, seriousIssues: ['100 percent behaves incorrectly'] },
  }), false);
  assert.equal(mergeAllowed({ ...verified, failures: [report] }), false);
});
