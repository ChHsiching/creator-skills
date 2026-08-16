#!/usr/bin/env node
/**
 * renumber.mjs — 加页 / 删页 / 改页码规则后，批量修 pages/*.json 的 NUM 和跨页引用。
 *
 * 为什么存在：手写脚本批量改 NUM 是踩过坑的（regex 留尾巴破坏 JSON）。页码一改，
 * 三件事必须同步：① JSON 文件名 ② 每个文件的 NUM 字段 ③ BODY/SUMMARY 里写死的「第 X 页」。
 * 这个脚本一次做完，并打印每一步的改动供你核对。
 *
 * 用法：
 *   node renumber.mjs <map> [--apply]
 *
 *   <map>  形如 00:01,01:02,...,08:09 —— 旧 NUM 到新 NUM 的映射
 *   --apply  默认 dry-run（只打印不写文件）；加 --apply 才真的改
 *
 * 例子（cover 从 00 改成 01，全部后移一位）：
 *   node renumber.mjs 00:01,01:02,02:03,03:04,04:05,05:06,06:07,07:08,08:09 --apply
 *
 * 做的事（按顺序）：
 *   1. 读 pages/NN-*.json，按映射重命名文件（00-cover.json → 01-cover.json）
 *   2. 改每个文件里的 "NUM" 字段（值同步映射）
 *   3. 改 TOTAL（如果你传了 --total NN；不改就不动）
 *   4. 改 BODY / SUMMARY 里所有「第 XX 页」引用（按映射同步；没在映射里的页码不动，方便你查）
 *   5. 打印每一项改动；dry-run 时文件不动
 *
 * 不做渲染。重命名 + 改完之后，自己重新 render + lint。
 */
import { readFileSync, writeFileSync, renameSync, readdirSync, existsSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

const [,, mapArg, ...rest] = process.argv;
const apply = rest.includes('--apply');
const totalIdx = rest.indexOf('--total');
const total = totalIdx !== -1 ? rest[totalIdx + 1] : null;

if (!mapArg) {
  console.error('Usage: node renumber.mjs <old:new,old:new,...> [--apply] [--total NN]');
  console.error('Example: node renumber.mjs 00:01,01:02,...,08:09 --apply');
  process.exit(1);
}

// 解析映射
const map = new Map();
for (const pair of mapArg.split(',')) {
  const [oldN, newN] = pair.split(':');
  if (!oldN || !newN) {
    console.error(`Bad pair "${pair}", expected old:new`);
    process.exit(1);
  }
  map.set(oldN, newN);
}

const pagesDir = join(process.cwd(), 'pages');
if (!existsSync(pagesDir)) {
  console.error(`No pages/ directory at ${pagesDir} (run this from the run root)`);
  process.exit(1);
}

// 收集要处理的文件（按当前文件名排序，让打印顺序稳定）
const files = readdirSync(pagesDir)
  .filter(f => /^\d{2}-.*\.json$/.test(f) && existsSync(join(pagesDir, f)))
  .sort();

const plan = []; // {oldFile, newFile, oldNum, newNum, bodyRefs: [{from,to,oldText,newText}]}
for (const f of files) {
  const m = f.match(/^(\d{2})-(.*)\.json$/);
  if (!m) continue;
  const oldNum = m[1];
  const slug = m[2];
  const newNum = map.get(oldNum);
  if (!newNum) continue; // 这个页码不在映射里——不动（可能你想保留某些页）

  const oldPath = join(pagesDir, f);
  const newPath = join(pagesDir, `${newNum}-${slug}.json`);
  const raw = readFileSync(oldPath, 'utf-8');
  const data = JSON.parse(raw);

  // 改 NUM
  const oldNumInFile = data.NUM;
  if (oldNumInFile !== oldNum) {
    console.warn(`warn: ${f} filename NUM="${oldNum}" but JSON NUM="${oldNumInFile}" — 用文件名`);
  }
  data.NUM = newNum;
  if (total) data.TOTAL = total;

  // 改跨页引用「第 XX 页」——按映射同步
  const bodyRefs = [];
  const patchStr = (s) => {
    if (typeof s !== 'string') return s;
    return s.replace(/第\s*(\d{1,3})\s*页/g, (m, n) => {
      const padded = n.padStart(2, '0');
      const mapped = map.get(padded) || map.get(n);
      if (!mapped) return m; // 没在映射里——不动（方便你事后查没覆盖到的引用）
      const newText = `第 ${mapped} 页`;
      bodyRefs.push({ from: n, to: mapped, oldText: m, newText });
      return newText;
    });
  };
  if (data.BODY) data.BODY = patchStr(data.BODY);
  if (data.SUMMARY) data.SUMMARY = patchStr(data.SUMMARY);
  if (data.LEAD) data.LEAD = patchStr(data.LEAD);
  if (data.NOTE) data.NOTE = patchStr(data.NOTE);

  plan.push({ oldFile: f, newFile: `${newNum}-${slug}.json`, oldNum, newNum, bodyRefs, newPath, newData: data });
}

// 打印计划
console.log(apply ? 'APPLYING:' : 'DRY RUN (add --apply to write):');
for (const p of plan) {
  console.log(`  ${p.oldFile} → ${p.newFile}  (NUM ${p.oldNum} → ${p.newNum})`);
  for (const r of p.bodyRefs) {
    console.log(`    ref: "${r.oldText}" → "${r.newText}"`);
  }
}

if (!apply) {
  console.log('\n(dry run, nothing written)');
  process.exit(0);
}

// 真写：先全部写新内容到旧路径，再统一重命名（避免文件名碰撞）
// 因为新文件名可能跟其他旧文件名冲突，分两步：先写到临时名，再 rename
// 简化做法：先把所有旧文件读到内存（plan 里已有 newData），然后删旧名写新名
// 这里直接：写新文件名（如果跟旧名不同），删旧文件
const tmpSuffix = '.renumber_tmp';
// 第一步：把所有文件重命名为 .renumber_tmp（避开冲突）
for (const p of plan) {
  if (p.oldFile === p.newFile) continue;
  renameSync(join(pagesDir, p.oldFile), join(pagesDir, p.oldFile + tmpSuffix));
}
// 第二步：写新内容到新文件名
for (const p of plan) {
  writeFileSync(p.newPath, JSON.stringify(p.newData, null, 2) + '\n', 'utf-8');
}
// 第三步：清理 .renumber_tmp（如果新旧名不同，旧的是 tmp；如果相同，原文件还在）
for (const p of plan) {
  if (p.oldFile === p.newFile) continue;
  const tmp = join(pagesDir, p.oldFile + tmpSuffix);
  if (existsSync(tmp)) {
    try { unlinkSync(tmp); } catch (e) { /* 忽略 */ }
  }
}

console.log(`\nDone: ${plan.length} file(s) renumbered. Now re-render and lint.`);
