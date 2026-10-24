import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { computed, nextTick } from 'vue';
import ts from 'typescript';
import { parse, compileScript } from '@vue/compiler-sfc';
import { baseParse } from '@vue/compiler-dom';
import { renderToString } from '@vue/server-renderer';
import { setup as setupSsr } from '@css-render/vue3-ssr';

const root = path.resolve(import.meta.dirname, '..');
const storage = new Map();
globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
globalThis.document = { documentElement: { lang: '' }, title: '' };
const output = await build({ entryPoints: [path.join(root, 'src/i18n/index.ts')], bundle: true, write: false, format: 'esm', platform: 'node', external: ['vue'] });
const source = output.outputFiles[0].text.replaceAll('from "vue"', `from ${JSON.stringify(import.meta.resolve('vue'))}`);
const i18n = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const keys = Object.keys(i18n.messages['zh-CN']).sort();
assert.ok(keys.length > 300, 'All major views must be covered, not just navigation');
for (const locale of ['en', 'ja']) {
  assert.deepEqual(Object.keys(i18n.messages[locale]).sort(), keys, `${locale} key coverage`);
  for (const key of keys) {
    assert.ok(i18n.messages[locale][key]?.trim(), `${locale}: ${key}`);
    assert.deepEqual([...i18n.messages[locale][key].matchAll(/\{(\w+)\}/g)].map(x => x[1]).sort(), [...i18n.messages['zh-CN'][key].matchAll(/\{(\w+)\}/g)].map(x => x[1]).sort(), `${locale} placeholders: ${key}`);
  }
}
assert.equal(i18n.locale.value, 'zh-CN');
const label = computed(() => i18n.t('新建单任务'));
const form = { video: '/keep/file.mp4', asr_language: 'ja' };
i18n.setLocale('en');
await nextTick();
assert.equal(label.value, 'New task');
assert.equal(document.documentElement.lang, 'en');
assert.match(document.title, /ASR Studio/);
assert.equal(storage.get(i18n.LOCALE_STORAGE_KEY), 'en');
i18n.setLocale('ja');
await nextTick();
assert.equal(label.value, '新規タスク');
assert.equal(form.asr_language, 'ja');
assert.equal(form.video, '/keep/file.mp4');
assert.equal(i18n.readStoredLocale(), 'ja');
storage.set(i18n.LOCALE_STORAGE_KEY, 'invalid');
assert.equal(i18n.readStoredLocale(), 'zh-CN');
for (const locale of ['zh-CN', 'en', 'ja']) {
  i18n.setLocale(locale);
  for (const status of ['pending', 'running', 'success', 'failed', 'partial', 'completed', 'active', 'done', 'transcribe', 'prepare-reference', 'reference', 'conversation', 'prepare-job', 'staggered-pipeline', 'ocr', 'pdf-ocr']) {
    assert.notEqual(i18n.labelFor(status), status, `${locale} missing state ${status}`);
  }
  assert.ok(i18n.formatDate('2026-01-02T03:04:00Z'));
}
console.log(`PASS: ${keys.length} keys × 3 locales; placeholders, reactive switching, persistence, document metadata, states and dates`);

const helperOutput = await build({ entryPoints: [path.join(root, 'src/composables/asrLanguage.ts')], bundle: true, write: false, format: 'esm', platform: 'node' });
const helpers = await import(`data:text/javascript;base64,${Buffer.from(helperOutput.outputFiles[0].text).toString('base64')}`);
const candidates = [{ id: 'primary', supported_languages: ['auto', 'zh', 'en', 'ja'] }, { id: 'secondary', supported_languages: ['zh'] }];
assert.equal(helpers.incompatibleCandidates(candidates, 'ja', 'primary', 'secondary')[0].id, 'secondary');
assert.deepEqual(helpers.incompatibleCandidates(candidates, 'ja', 'primary', ''), []);
assert.deepEqual(helpers.supportedLanguages({ id: 'legacy' }), ['zh']);
assert.deepEqual(helpers.languageOverride(null), {});
assert.deepEqual(helpers.languageOverride('ja'), { asr_language: 'ja' });
assert.equal(helpers.isAsrLanguage('fr'), false);
assert.equal(candidates[0].id, 'primary', 'Validation must not switch models');
console.log('PASS: primary/secondary compatibility, legacy Chinese capability and snapshot-preserving overrides');

const apiOutput = await build({ stdin: { contents: `export * from './src/api/client.ts'; export { setLocale } from './src/i18n/index.ts';`, resolveDir: root, loader: 'ts' }, bundle: true, write: false, format: 'esm', platform: 'node', external: ['vue'] });
const apiSource = apiOutput.outputFiles[0].text.replaceAll('from "vue"', `from ${JSON.stringify(import.meta.resolve('vue'))}`);
const api = await import(`data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`);
const originalFetch = globalThis.fetch;
const requests = [];
globalThis.fetch = async (url, init) => { requests.push({ url, body: JSON.parse(init.body) }); return { ok: true, json: async () => ({ job_id: 'fixture' }) }; };
await api.submitJob({ video: '/sample.mp4', output_dir: '/output', asr_language: 'ja' });
await api.submitBatchJob({ asr_language: 'auto' });
await api.submitStageRun('transcribe', { asr_language: 'en' });
await api.submitStageFileRun('transcribe', { input_files: { audio: '/sample.wav' }, result_name: 'sample', asr_language: 'ja' });
await api.saveFrontendSettings({ asr_language: 'en' });
await api.rerunJob('original', { start_stage: 'transcribe', ...helpers.languageOverride(null) });
await api.rerunBatchItem('batch', 'item', { start_stage: 'transcribe', ...helpers.languageOverride('ja') });
assert.deepEqual(requests.map(request => request.body.asr_language), ['ja', 'auto', 'en', 'ja', 'en', undefined, 'ja']);
assert.ok(!Object.hasOwn(requests[5].body, 'asr_language'), 'Rerun must omit inherited language override');
api.setLocale('en');
globalThis.fetch = async () => ({ ok: false, status: 400, text: async () => JSON.stringify({ detail: 'original server detail' }) });
await assert.rejects(api.getConfig(), /Request failed: original server detail/);
globalThis.fetch = originalFetch;
console.log('PASS: actual API serialization for settings, single/batch/stage/file-stage/reruns and localized error envelope');

const vueFiles = ['App.vue', ...['views', 'components'].flatMap(dir => readdirSync(path.join(root, 'src', dir)).filter(file => file.endsWith('.vue')).map(file => `${dir}/${file}`))];
const han = /[㐀-鿿]/;
let checked = 0;
for (const file of vueFiles) {
  const { descriptor } = parse(readFileSync(path.join(root, 'src', file), 'utf8'));
  const ast = baseParse(descriptor.template.content);
  function checkExpression(text) {
    const source = ts.createSourceFile('check.ts', text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    function visit(node) {
      if (ts.isStringLiteral(node) && han.test(node.text)) {
        assert.ok(Object.hasOwn(i18n.messages['zh-CN'], node.text), `${file}: unknown key ${node.text}`);
        checked++;
      }
      if (ts.isTemplateExpression(node)) {
        assert.ok(!han.test(node.head.text + node.templateSpans.map(span => span.literal.text).join('')), `${file}: untranslated template literal`);
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
  function visit(node) {
    if (node.type === 2) assert.ok(!han.test(node.content), `${file}: untranslated template text ${node.content}`);
    if (node.type === 5) checkExpression(node.content.content);
    for (const prop of node.props ?? []) {
      if (prop.type === 6 && prop.value) assert.ok(!han.test(prop.value.content), `${file}: untranslated ${prop.name}`);
      if (prop.type === 7 && prop.exp) checkExpression(prop.exp.content);
    }
    for (const child of node.children ?? []) visit(child);
  }
  visit(ast);
  checkExpression(descriptor.scriptSetup.content);
}
console.log(`PASS: ${vueFiles.length} Vue files, ${checked} source-key references; no unlocalized template text or attributes`);

// Compile the real SFCs and render every main route without a browser, HTTP server or model calls.
delete globalThis.document;
const entry = `
import App from './src/App.vue';
import Single from './src/views/SingleJobView.vue';
import Batch from './src/views/BatchJobView.vue';
import Jobs from './src/views/JobListView.vue';
import Stage from './src/views/StageRunnerView.vue';
import Pdf from './src/views/PDFBookOCRView.vue';
import Settings from './src/views/SettingsView.vue';
export { setLocale } from './src/i18n/index.ts';
export { createSSRApp } from 'vue';
export { createRouter, createMemoryHistory } from 'vue-router';
export { App };
export const routes = [Single, Batch, Jobs, Stage, Pdf, Settings].map((component, index) => ({ path: ['single-job', 'batch-job', 'jobs', 'stage-runner', 'pdf-book-ocr', 'settings'].map(name => '/' + name)[index], component }));`;
const appOutput = await build({
  stdin: { contents: entry, resolveDir: root, loader: 'ts' }, bundle: true, write: false, format: 'esm', platform: 'node',
  external: ['vue', 'vue-router', 'naive-ui'],
  plugins: [{ name: 'vue-test-compiler', setup(builder) {
    builder.onLoad({ filter: /\.vue$/ }, args => {
      const { descriptor } = parse(readFileSync(args.path, 'utf8'), { filename: args.path });
      const result = compileScript(descriptor, { id: args.path, inlineTemplate: true });
      return { contents: result.content, loader: 'ts', resolveDir: path.dirname(args.path) };
    });
  } }],
});
let appSource = appOutput.outputFiles[0].text;
for (const pkg of ['vue', 'vue-router', 'naive-ui']) appSource = appSource.replaceAll(`from "${pkg}"`, `from ${JSON.stringify(import.meta.resolve(pkg))}`);
const appModule = await import(`data:text/javascript;base64,${Buffer.from(appSource).toString('base64')}`);
for (const locale of ['zh-CN', 'en', 'ja']) {
  appModule.setLocale(locale);
  for (const route of appModule.routes) {
    const router = appModule.createRouter({ history: appModule.createMemoryHistory(), routes: appModule.routes });
    await router.push(route.path);
    await router.isReady();
    const app = appModule.createSSRApp(appModule.App).use(router);
    setupSsr(app);
    const html = await renderToString(app);
    assert.ok(html.includes('locale-control'), `${locale} ${route.path}: language control`);
    if (locale === 'en') assert.ok(!han.test(html.replace(/<select\b[\s\S]*?<\/select>/g, '')), `${route.path}: Chinese leaked into English render`);
    if (route.path === '/single-job') {
      assert.ok(html.includes(locale === 'en' ? 'Reference proofreading' : locale === 'ja' ? '参考資料による校正' : '参考材料校对'));
      assert.ok(html.includes(locale === 'en' ? 'Upload local video' : locale === 'ja' ? 'ローカルの動画をアップロード' : '选择并上传本机视频'));
    }
  }
}
console.log('PASS: all 6 main routes render in all 3 locales; real radio options/upload labels and English copy coverage');
