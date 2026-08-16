#!/usr/bin/env node
/**
 * render_page.mjs — 把模板 + 数据 JSON 渲染成一个 HTML 页面（替换占位符），再用无头浏览器截图成 PNG。
 *
 * 用法：
 *   node render_page.mjs <template.html> <data.json> <out.png>
 *
 * data.json 字段对应模板里的 {{...}} 占位符，例如：
 *   {
 *     "BG":"#FBF7EE","INK":"#2a2a2a","ACCENT":"#d9534f",
 *     "FONT_CN":"LXGW WenKai Lite","FONT_FILE":"LXGWWenKaiLite-Regular.ttf",
 *     "FONT_MONO":"LXGW WenKai Mono Lite","MONO_FILE":"LXGWWenKaiMonoLite-Regular.ttf",
 *     "NUM":"02","TOTAL":"08","CHAPTER":"安装","SERIES":"...",
 *     "ILLO":"illustrations/01.png","TITLE":"...","BODY":"<p>...</p>",
 *     "FOOTER_L":"...",
 *     "FONT_BUMP":"1.15"   // 可选：按比例放大本页字号（默认无）。逃生口，非必要不用。
 *   }
 *
 * 依赖：playwright（npm i playwright）。脚本不绑定任何特定生图后端。
 *
 * 路径处理：脚本可以在任意目录被调用。临时 HTML 写到 cwd（运行根目录），
 * 这样 data.json 里的相对路径（如 ILLO: "illustrations/01.png"）就以 cwd 为基准解析。
 * 字体的相对路径（模板里的 ../assets/fonts/）和 ILLO 都会被改写成绝对 file URL，
 * 不受临时 HTML 实际位置影响。
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const [,, templatePath, dataPath, outPng] = process.argv;
if (!templatePath || !dataPath || !outPng) {
  console.error('Usage: node render_page.mjs <template.html> <data.json> <out.png>');
  process.exit(1);
}

const runRoot = resolve('.'); // cwd = 运行根目录，所有相对路径的基准
const tpl = readFileSync(templatePath, 'utf-8');
const data = JSON.parse(readFileSync(dataPath, 'utf-8'));

// 占位符替换：{{KEY}} -> data[KEY]（未提供则保留原样，方便排查）
// 例外：ILLO_H 默认 600（插图高度），未提供时不能留 {{ILLO_H}} 进 CSS（无效）
let html = tpl.replace(/\{\{(\w+)\}\}/g, (m, k) => {
  if (k === 'ILLO_H' && data[k] === undefined) return '600';
  if (data[k] === undefined) return m;
  let v = String(data[k]);
  // ILLO 是图片相对路径，相对 cwd 解析成 file URL，避免受临时 html 位置影响
  if (k === 'ILLO' && v && !/^(https?:|file:)/.test(v)) {
    v = pathToFileURL(join(runRoot, v)).href;
  }
  return v;
});

// 字体相对路径（../assets/fonts/xxx.ttf）→ 绝对 file URL（<runRoot>/assets/fonts/xxx.ttf）
// 这样无论临时 HTML 放在哪个目录，字体都能加载
html = html.replace(/\.\.\/assets\/fonts\/([\w.-]+)/g, (m, f) =>
  pathToFileURL(join(runRoot, 'assets', 'fonts', f)).href);

// FONT_BUMP：可选字段（如 "1.15"），按比例放大字号。用来让某页字号比默认大一档，
// 不用复制一套「big 模板」。直接在模板 HTML 里改写每条 font-size 声明的值——
// 模板里写死的字号是 single source of truth，这里只读不改不复制。
// 注：FONT_BUMP 是逃生口，不到必要时不用——默认字号已经平衡过信息密度和留白。
if (data.FONT_BUMP !== undefined) {
  const bump = parseFloat(data.FONT_BUMP);
  if (Number.isFinite(bump) && bump > 0 && bump !== 1) {
    html = html.replace(/font-size:\s*([\d.]+)px/g, (m, px) => {
      const scaled = Math.round(parseFloat(px) * bump);
      return `font-size:${scaled}px`;
    });
  }
}

// 写到一个临时 html（放在 cwd 运行根，使 illustrations/ 相对路径直接可用）
const tmpHtml = join(runRoot, '.render_tmp.html');
writeFileSync(tmpHtml, html, 'utf-8');

// playwright 解析：ESM 裸导入（await import）从「脚本所在目录」找 node_modules，
// 但 skill 脚本目录通常没装 playwright（装在 run 目录）。
// 用 createRequire 从 cwd（run 根目录）解析，这样从 run 目录调用就能找到。
// 解析失败时给出可操作的错误，而不是含糊的 MODULE_NOT_FOUND。
const runRootRequire = createRequire(join(resolve('.'), 'package.json'));
let chromium;
try {
  ({ chromium } = runRootRequire('playwright'));
} catch (e) {
  console.error(
    `playwright not found from run directory: ${resolve('.')}\n` +
    `Fix: run "npm i playwright" in the run directory (where the page JSONs live).\n` +
    `Original error: ${e.message}`
  );
  process.exit(1);
}
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width: 1080, height: 1440 });
await page.goto(pathToFileURL(tmpHtml).href, { waitUntil: 'networkidle' });

// 显式等待所有图片加载完成（file:// 图片有时不触发 networkidle 计数）
// 不等的话会截到空白插图——这是踩过的坑
await page.evaluate(async () => {
  const imgs = Array.from(document.images);
  await Promise.all(imgs.map(img =>
    (img.complete && img.naturalWidth > 0)
      ? Promise.resolve()
      : new Promise(res => { img.onload = img.onerror = res; })
  ));
});
// 等字体加载完，避免首屏字体回退
await page.evaluate(() => document.fonts && document.fonts.ready);
await page.waitForTimeout(500);

mkdirSync(dirname(resolve(outPng)), { recursive: true });
await page.screenshot({ path: outPng });
await browser.close();

console.log('rendered ->', outPng);
