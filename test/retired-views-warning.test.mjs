import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { retiredViewsDiagnostics } from '../archify/renderers/shared/retired-views.mjs';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'archify');
const cli = path.join(skillRoot, 'bin/archify.mjs');
const EXAMPLES = {
  architecture: 'web-app.architecture.json',
  workflow: 'agent-tool-call.workflow.json',
  sequence: 'cache-miss-request.sequence.json',
  dataflow: 'product-analytics.dataflow.json',
  lifecycle: 'agent-run.lifecycle.json',
};
const FIRST_NODE_IDS = {
  architecture: (d) => d.components.map((n) => n.id),
  workflow: (d) => d.nodes.map((n) => n.id),
  sequence: (d) => d.participants.map((n) => n.id),
  dataflow: (d) => d.nodes.map((n) => n.id),
  lifecycle: (d) => d.states.map((n) => n.id),
};
const VIEWS = (focus) => [
  { id: 'main-path', label: 'Main path', focus, note: 'Generic chapter note.' },
  { id: 'overview', label: 'Overview', focus },
];

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'archify-retired-views-'));
test.after(() => fs.rmSync(tmp, { recursive: true, force: true }));

function fixture(type, { views } = {}) {
  const document = JSON.parse(fs.readFileSync(path.join(skillRoot, 'examples', EXAMPLES[type]), 'utf8'));
  if (views) document.meta.views = VIEWS(FIRST_NODE_IDS[type](document).slice(0, 1));
  else delete document.meta.views;
  const input = path.join(tmp, `${type}-${views ? 'views' : 'plain'}.json`);
  fs.writeFileSync(input, JSON.stringify(document));
  return input;
}

function run(args, env = {}) {
  return spawnSync(process.execPath, [cli, ...args], {
    cwd: skillRoot,
    encoding: 'utf8',
    env: { ...process.env, ARCHIFY_UPDATE_CACHE_DIRECTORY: path.join(tmp, 'update-cache'), ...env },
  });
}

const WARNING = /^archify: meta\.views is retired in Archify 3\.x and ignored: 2 chapters will not appear in the output \(1 with a note that will not appear\): "Main path" \(id main-path; note will not appear\), "Overview" \(id overview; no note\)\. .*"Upgrading from 2\.x" in CHANGELOG\.md and schemas\/README\.md\.$/m;

test('retiredViewsDiagnostics is silent without a non-empty meta.views', () => {
  assert.deepEqual(retiredViewsDiagnostics('architecture', {}), []);
  assert.deepEqual(retiredViewsDiagnostics('architecture', { views: [] }), []);
  assert.deepEqual(retiredViewsDiagnostics('architecture', undefined), []);
});

test('retiredViewsDiagnostics reports each chapter and whether its note is lost', () => {
  const [entry, ...rest] = retiredViewsDiagnostics('workflow', { views: VIEWS(['a']) });
  assert.equal(rest.length, 0);
  assert.equal(entry.code, 'meta/views-ignored');
  assert.equal(entry.severity, 'warning');
  assert.deepEqual(entry.subject, { diagramType: 'workflow', path: '/meta/views' });
  assert.equal(entry.evidence.chapters, 2);
  assert.equal(entry.evidence.chaptersWithNote, 1);
  assert.deepEqual(entry.evidence.views, [
    { id: 'main-path', label: 'Main path', hasNote: true, note: 'Generic chapter note.' },
    { id: 'overview', label: 'Overview', hasNote: false },
  ]);
  assert.match(entry.message, /^meta\.views is retired in Archify 3\.x and ignored: 2 chapters /);
  assert.match(entry.message, /node labels\/sublabels or cards/);
  assert.match(entry.message, /Route and Lens/);
  const [single] = retiredViewsDiagnostics('workflow', { views: [{ id: 'one', label: 'One', focus: ['a'], note: '   ' }] });
  assert.match(single.message, /: 1 chapter will not appear in the output \(0 with a note/);
  assert.match(single.message, /"One" \(id one; no note\)/);
});

for (const type of Object.keys(EXAMPLES)) {
  test(`${type}: render warns once on stderr and still succeeds when meta.views is present`, () => {
    const output = path.join(tmp, `${type}-render.html`);
    const result = run(['render', type, fixture(type, { views: true }), output]);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr.match(/meta\.views is retired/g)?.length, 1, result.stderr);
    assert.match(result.stderr, WARNING);
    assert.ok(fs.existsSync(output));
  });

  test(`${type}: validate --json carries the warning in diagnostics with unchanged exit code`, () => {
    const input = fixture(type, { views: true });
    const result = run(['validate', type, input, '--json']);
    assert.equal(result.status, 0, result.stderr);
    const receipt = JSON.parse(result.stdout);
    assert.equal(receipt.ok, true);
    assert.deepEqual(receipt.diagnostics.map((entry) => [entry.code, entry.severity]), [['meta/views-ignored', 'warning']]);
    assert.equal(receipt.diagnostics[0].evidence.chapters, 2);
    assert.equal(result.stderr, `archify: ${receipt.diagnostics[0].message}\n`, 'JSON mode discloses the warning once on stderr');

    const plain = run(['validate', type, fixture(type), '--json']);
    assert.equal(plain.status, 0, plain.stderr);
    assert.equal(JSON.parse(plain.stdout).diagnostics, undefined);
    assert.equal(plain.stderr, '');
  });
}

test('validate and deliver human output warn once and exit 0; documents without views stay silent', () => {
  const input = fixture('architecture', { views: true });
  const validate = run(['validate', 'architecture', input]);
  assert.equal(validate.status, 0, validate.stderr);
  assert.match(validate.stderr, WARNING);
  assert.equal(validate.stderr.match(/meta\.views is retired/g).length, 1);
  assert.match(validate.stdout, /^ok architecture /);

  const deliver = run(['deliver', 'architecture', input, path.join(tmp, 'deliver-human.html')]);
  assert.equal(deliver.status, 0, deliver.stderr);
  assert.match(deliver.stderr, WARNING);
  assert.equal(deliver.stderr.match(/meta\.views is retired/g).length, 1);

  const plain = fixture('architecture');
  for (const args of [['validate', 'architecture', plain], ['render', 'architecture', plain, path.join(tmp, 'plain.html')]]) {
    const result = run(args);
    assert.equal(result.status, 0, result.stderr);
    assert.doesNotMatch(result.stderr + result.stdout, /meta\.views/);
  }
});

test('deliver --json carries the warning in receipt diagnostics; without views there are none', () => {
  const result = run(['deliver', 'architecture', fixture('architecture', { views: true }), path.join(tmp, 'deliver-json.html'), '--json']);
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(result.stdout);
  assert.equal(receipt.ok, true);
  assert.deepEqual(receipt.diagnostics.map((entry) => entry.code), ['meta/views-ignored']);
  assert.equal(receipt.diagnostics[0].evidence.chaptersWithNote, 1);

  const plain = run(['deliver', 'architecture', fixture('architecture'), path.join(tmp, 'deliver-plain.html'), '--json']);
  assert.equal(plain.status, 0, plain.stderr);
  assert.equal(JSON.parse(plain.stdout).diagnostics, undefined);
});

test('meta.views warning does not displace locale warnings', () => {
  const document = JSON.parse(fs.readFileSync(fixture('architecture', { views: true }), 'utf8'));
  document.meta.locale = 'fr';
  const input = path.join(tmp, 'views-and-locale.json');
  fs.writeFileSync(input, JSON.stringify(document));
  const result = run(['validate', 'architecture', input, '--json']);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout).diagnostics.map((entry) => entry.code), ['i18n/locale-fallback', 'meta/views-ignored']);
});

test('finalize --json keeps the warning in a passing receipt (needs Chrome for the browser gate)', { skip: !process.env.ARCHIFY_CHROME }, () => {
  const result = run(['finalize', 'architecture', fixture('architecture', { views: true }), path.join(tmp, 'final.html'), '--quality', 'showcase', '--json']);
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const receipt = JSON.parse(result.stdout);
  assert.equal(receipt.ok, true);
  assert.deepEqual(receipt.diagnostics.map((entry) => [entry.code, entry.severity]), [['meta/views-ignored', 'warning']]);
});
