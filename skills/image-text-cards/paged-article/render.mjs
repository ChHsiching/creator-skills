#!/usr/bin/env node
/**
 * render.mjs — 把 3:4 的 HTML 页面截图成 PNG（1080×1440 CSS → 3240×4320 PNG）。
 *
 * 用法：node render.mjs <input.html> <output.png>
 *
 * 3x 高清：deviceScaleFactor=3 让 Playwright 以 3 倍像素密度截图。
 * CSS 画布尺寸不变（1080×1440 的布局），导出的 PNG 是 3240×4320，
 * 衬线细笔画有足够像素描边，在手机缩略图下不发虚。
 *
 * 依赖：playwright（从 cwd 的 node_modules 解析）。
 * 如果运行目录没装，先 npm i playwright。
 */
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';

const [, , inputHtml, outputPng] = process.argv;
if (!inputHtml || !outputPng) {
  console.error('Usage: node render.mjs <input.html> <output.png>');
  process.exit(1);
}

const req = createRequire(resolve('package.json'));
let chromium;
try {
  ({ chromium } = req('playwright'));
} catch (e) {
  console.error(
    `playwright not found from: ${resolve('.')}\n` +
    `Fix: run "npm i playwright" in this directory.\n` +
    `Original error: ${e.message}`
  );
  process.exit(1);
}

const browser = await chromium.launch();
// 3x 高清：deviceScaleFactor=3，衬线笔画锐利清晰。
const page = await browser.newPage({ deviceScaleFactor: 3 });
await page.setViewportSize({ width: 1080, height: 1440 });
await page.goto(pathToFileURL(resolve(inputHtml)).href, { waitUntil: 'networkidle' });

// 等所有图片 + 字体加载完
await page.evaluate(async () => {
  await Promise.all(Array.from(document.images).map(img =>
    (img.complete && img.naturalWidth > 0) ? Promise.resolve()
      : new Promise(r => { img.onload = img.onerror = r; })
  ));
  if (document.fonts) await document.fonts.ready;
});
await page.waitForTimeout(400);

await page.screenshot({ path: outputPng });
await browser.close();
console.log('rendered ->', outputPng);
