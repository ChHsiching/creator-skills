#!/usr/bin/env node
/**
 * lint_page.mjs — 渲染前/后给一张卡片做版面体检。
 *
 * 用法：
 *   node lint_page.mjs <template.html> <data.json> [--strict] [--quiet]
 *
 * 干嘛用的：render_page.mjs 只负责「渲染成 PNG」，不负责「渲染对了」。
 * 内容写多了、codeblock 太长、插图太大，body 会撑出 1080×1440 画布，
 * footer 被裁、text 和 footer 重叠——这些肉眼看 PNG 很难发现，得用 DOM 测量。
 *
 * 检查项（任一不过都算 problem）：
 *   - body 溢出：scrollHeight/scrollWidth 超过 1440/1080
 *   - 各主要块（header/illo/text/footer/codeblock/note）在视口内
 *   - text 底部和 footer 顶部不重叠（内容太长会顶上去）
 *   - codeblock 不过高（>700px 通常意味着把正文挤掉了）
 *   - 插图真的加载了（naturalWidth > 0，没加载 = 空白）
 *
 * 输出：
 *   默认：完整 JSON { problems: [...], rects: {...}, bodyH, bodyW }，调试用。
 *   --quiet：只打一行 `<data-name>: NONE | bodyH=1440`（有问题就把 problems 列出来），
 *            agent 批量 lint 时用，省掉解析 JSON 的 one-liner。
 *   --strict：有 problem 就 exit 1（给 agent 链路用）；默认 exit 0 只报告。
 *
 * 依赖：playwright（和 render_page.mjs 一样，从 cwd 解析）。
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const [,, templatePath, dataPath, ...rest] = process.argv;
const strict = rest.includes('--strict');
const quiet = rest.includes('--quiet');
if (!templatePath || !dataPath) {
  console.error('Usage: node lint_page.mjs <template.html> <data.json> [--strict] [--quiet]');
  process.exit(1);
}

const runRoot = resolve('.');
const tpl = readFileSync(templatePath, 'utf-8');
const data = JSON.parse(readFileSync(dataPath, 'utf-8'));

// 占位符替换（跟 render_page.mjs 保持一致）
let html = tpl.replace(/\{\{(\w+)\}\}/g, (m, k) => {
  if (data[k] === undefined) return m;
  let v = String(data[k]);
  if (k === 'ILLO' && v && !/^(https?:|file:)/.test(v)) {
    v = pathToFileURL(join(runRoot, v)).href;
  }
  return v;
});
html = html.replace(/\.\.\/assets\/fonts\/([\w.-]+)/g, (m, f) =>
  pathToFileURL(join(runRoot, 'assets', 'fonts', f)).href);

// FONT_BUMP：跟 render_page.mjs 同步——lint 必须按放大后的字号测量，否则漏报溢出。
if (data.FONT_BUMP !== undefined) {
  const bump = parseFloat(data.FONT_BUMP);
  if (Number.isFinite(bump) && bump > 0 && bump !== 1) {
    html = html.replace(/font-size:\s*([\d.]+)px/g, (m, px) =>
      `font-size:${Math.round(parseFloat(px) * bump)}px`);
  }
}

const tmpHtml = join(runRoot, '.lint_tmp.html');
writeFileSync(tmpHtml, html, 'utf-8');

const runRootRequire = createRequire(join(runRoot, 'package.json'));
let chromium;
try {
  ({ chromium } = runRootRequire('playwright'));
} catch (e) {
  console.error(
    `playwright not found from run directory: ${runRoot}\n` +
    `Fix: run "npm i playwright" in the run directory.\n` +
    `Original error: ${e.message}`
  );
  process.exit(1);
}

const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width: 1080, height: 1440 });
await page.goto(pathToFileURL(tmpHtml).href, { waitUntil: 'networkidle' });
await page.evaluate(async () => {
  const imgs = Array.from(document.images);
  await Promise.all(imgs.map(img =>
    (img.complete && img.naturalWidth > 0) ? Promise.resolve()
      : new Promise(res => { img.onload = img.onerror = res; })
  ));
});
await page.evaluate(() => document.fonts && document.fonts.ready);
await page.waitForTimeout(400);

const VW = 1080, VH = 1440;
const report = await page.evaluate((viewBox) => {
  const { VW, VH } = viewBox;
  const problems = [];
  const round = n => Math.round(n);

  const body = document.body;
  if (body.scrollHeight > VH + 2) problems.push(`BODY 溢出底部: scrollHeight=${body.scrollHeight} (canvas=${VH})`);
  if (body.scrollWidth > VW + 2) problems.push(`BODY 溢出右侧: scrollWidth=${body.scrollWidth} (canvas=${VW})`);

  const blocks = ['.header', '.illo', '.text', '.footer', '.text h2', '.codeblock', '.note', '.lead'];
  const rects = {};
  for (const sel of blocks) {
    const els = document.querySelectorAll(sel);
    els.forEach((el, i) => {
      const r = el.getBoundingClientRect();
      const key = els.length > 1 ? `${sel}[${i}]` : sel;
      rects[key] = { top: round(r.top), bottom: round(r.bottom), left: round(r.left), right: round(r.right), h: round(r.height) };
      if (r.bottom > VH + 2) problems.push(`${key} 底部超出画布: bottom=${round(r.bottom)}`);
      if (r.top < -2) problems.push(`${key} 顶部超出画布: top=${round(r.top)}`);
      if (r.right > VW + 2) problems.push(`${key} 右侧超出: right=${round(r.right)}`);
      if (r.left < -2) problems.push(`${key} 左侧超出: left=${round(r.left)}`);
    });
  }

  // text 和 footer 重叠：内容太长把 footer 顶出去了
  const text = document.querySelector('.text');
  const footer = document.querySelector('.footer');
  if (text && footer) {
    const tr = text.getBoundingClientRect();
    const fr = footer.getBoundingClientRect();
    if (tr.bottom > fr.top + 1) {
      problems.push(`.text 底部(${round(tr.bottom)}) 与 .footer 顶部(${round(fr.top)}) 重叠——正文太长`);
    }
  }

  // codeblock 过高（>700px 通常意味着正文被挤掉或本身内容太长）
  document.querySelectorAll('.codeblock').forEach((cb, i) => {
    const h = cb.getBoundingClientRect().height;
    if (h > 700) problems.push(`.codeblock[${i}] 过高: ${round(h)}px，可能挤掉正文`);
  });

  // 插图加载失败（naturalWidth=0）
  const illo = document.querySelector('.illo img');
  if (illo && illo.naturalWidth === 0) problems.push('.illo 图片未加载（naturalWidth=0）');

  return { problems, rects, bodyH: body.scrollHeight, bodyW: body.scrollWidth };
}, { VW, VH });

await browser.close();

if (quiet) {
  // 一行总结：`<data-name>: NONE | bodyH=1440` 或 `...: 2 problem(s) | <first> | <second> | bodyH=1440`
  const name = basename(dataPath, '.json');
  const head = `${name}: ${report.problems.length === 0 ? 'NONE' : report.problems.length + ' problem(s)'}`;
  const tail = `bodyH=${report.bodyH}`;
  console.log(report.problems.length === 0
    ? `${head} | ${tail}`
    : `${head} | ${report.problems.join(' | ')} | ${tail}`);
} else {
  console.log(JSON.stringify(report, null, 2));
}
if (strict && report.problems.length > 0) {
  console.error(`\n${report.problems.length} problem(s) found (strict mode).`);
  process.exit(1);
}
