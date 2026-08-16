#!/usr/bin/env node
/**
 * count_title.mjs — 数小红书标题的字符数，标出超 20 字的。
 *
 * 用法：
 *   node count_title.mjs "标题一" "标题二" "标题三"
 *   node count_title.mjs -f titles.txt      # 每行一个标题
 *   echo -e "标题一\n标题二" | node count_title.mjs   # 从 stdin
 *
 * 干嘛用的：小红书标题 ≤20 字符。agent（模型）估字符数经常错——尤其遇到
 * GPT-5.6 /Claude 3.5 这种混合 token（一个 GPT-5.6 就 7 个字符）。
 * 规则要求「数过字符数」，这个脚本是那个「数」的工具。
 *
 * 字符数规则（跟小红书一致）：每个 Unicode 码点算 1（中文 1 字 = 1，
 * 英文字母/数字/空格/标点各算 1）。emoji 通常算 2（代理对），但小红书标题少用 emoji。
 */
import { readFileSync } from 'node:fs';

let titles = [];
if (process.argv[2] === '-f') {
  titles = readFileSync(process.argv[3], 'utf-8').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
} else if (process.argv.length > 2) {
  titles = process.argv.slice(2);
} else {
  // stdin
  const stdin = readFileSync(0, 'utf-8');
  titles = stdin.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
}

if (titles.length === 0) {
  console.error('Usage: node count_title.mjs "标题一" "标题二"  或  -f file.txt  或  stdin');
  process.exit(1);
}

const LIMIT = 20;
let overCount = 0;
console.log(`标题字符数（上限 ${LIMIT}）:\n`);
for (const t of titles) {
  // 用 [...str] 按 Unicode 码点拆，正确处理中文和代理对
  const n = [...t].length;
  const flag = n <= LIMIT ? '✅' : '❌';
  if (n > LIMIT) overCount++;
  console.log(`  ${flag} [${String(n).padStart(2)}] ${t}`);
}
console.log(`\n${titles.length - overCount}/${titles.length} 通过，${overCount} 个超标。`);
if (overCount > 0) process.exit(1);
