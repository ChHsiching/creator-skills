#!/usr/bin/env node
/**
 * gen_image.mjs — 通用文生图调用（中性命名，不绑定任何第三方 skill）。
 *
 * 用法：
 *   node gen_image.mjs <prompt.md> <out.png> [--provider zai|openai] [--size 1280x720] [--quality hd|standard]
 *
 * 后端按优先级解析：
 *   1. --provider 显式指定
 *   2. 环境变量 IMAGE_PROVIDER
 *   3. 根据已设置的 API key 自动检测（ZAI_API_KEY/BIGMODEL_API_KEY → zai；OPENAI_API_KEY → openai）
 *
 * 支持的后端：
 *   - zai (智谱 GLM-Image)：endpoint 默认 https://open.bigmodel.cn/api/paas/v4，用 BIGMODEL_BASE_URL 覆盖。
 *     模型 glm-image，quality hd。请求体 {model,prompt,size,quality}，返回 data[0].url 后下载。
 *   - openai (gpt-image)：endpoint 用 OPENAI_BASE_URL 覆盖。模型由 OPENAI_IMAGE_MODEL 指定（默认 gpt-image-1）。
 *
 * 失败应对（区分两类）：
 *   - 限流（HTTP 429 / rate limit）：退避重试 3 次（30s / 60s / 90s）。配额按时间窗口恢复，等够就过。
 *   - 内容失败（empty url / HTTP 400 / 形状错误）：不重试——同一个 prompt 再发大概率还失败。
 *     报错后 agent 该简化 prompt（砍元素到 ≤4、合并隐喻、段落 ≤2 句）再来。
 * 批量生图串行间隔：每次调用前 sleep --delay <ms>（默认 0）。避免并发触发限流。
 * 每次调用都花钱，调用前 agent 应已获用户确认。
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const args = process.argv.slice(2);
function flag(name) {
  const i = args.indexOf(name);
  if (i === -1) return null;
  const v = args[i + 1];
  args.splice(i, 2);
  return v || null;
}
const [promptPath, outPath] = args;
const providerFlag = flag('--provider');
const sizeFlag = flag('--size');
const qualityFlag = flag('--quality');
const delayFlag = flag('--delay'); // 批量串行间隔，毫秒

if (!promptPath || !outPath) {
  console.error('Usage: node gen_image.mjs <prompt.md> <out.png> [--provider zai|openai] [--size WxH] [--quality hd|standard] [--delay <ms>]');
  process.exit(1);
}

function detectProvider() {
  if (providerFlag) return providerFlag;
  if (process.env.IMAGE_PROVIDER) return process.env.IMAGE_PROVIDER;
  if (process.env.ZAI_API_KEY || process.env.BIGMODEL_API_KEY) return 'zai';
  if (process.env.OPENAI_API_KEY) return 'openai';
  return null;
}

const prompt = readFileSync(promptPath, 'utf-8');
const provider = detectProvider();

async function generateZai(prompt, size, quality) {
  const key = process.env.ZAI_API_KEY || process.env.BIGMODEL_API_KEY;
  if (!key) throw new Error('ZAI_API_KEY (or BIGMODEL_API_KEY) not set');
  const base = process.env.ZAI_BASE_URL || process.env.BIGMODEL_BASE_URL || 'https://open.bigmodel.cn/api/paas/v4';
  const sz = size || '1280x720';
  const res = await fetch(`${base}/images/generations`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: 'glm-image', prompt, size: sz, quality: quality || 'hd' }),
  });
  if (!res.ok) throw new Error(`zai HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const j = await res.json();
  const url = j.data && j.data[0] && j.data[0].url;
  if (!url) throw new Error('zai: no image url in response');
  const img = await (await fetch(url)).arrayBuffer();
  return Buffer.from(img);
}

async function generateOpenai(prompt, size, quality) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('OPENAI_API_KEY not set');
  const base = process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1';
  const model = process.env.OPENAI_IMAGE_MODEL || 'gpt-image-1';
  const res = await fetch(`${base}/images/generations`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, prompt, size: size || '1536x1024', quality: quality || 'high' }),
  });
  if (!res.ok) throw new Error(`openai HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const j = await res.json();
  const item = j.data && j.data[0];
  if (!item) throw new Error('openai: no image in response');
  if (item.b64_json) return Buffer.from(item.b64_json, 'base64');
  if (item.url) return Buffer.from(await (await fetch(item.url)).arrayBuffer());
  throw new Error('openai: unrecognized response shape');
}

// 失败分类：限流类（HTTP 429 或「速率限制/limit」字样）vs 内容类（其他）。
// 两类应对不同——限流等一会再试同一个 prompt 就能过；内容失败重发同一个 prompt 多半还失败，
// agent 该简化 prompt 再来。不区分就会在限流上烧掉重试额度。
function isRateLimit(errMsg) {
  return /HTTP 429|rate.?limit|速率限制|限流|too many requests/i.test(errMsg);
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function run() {
  if (!provider) {
    console.error('No image provider: set --provider or an API key (ZAI_API_KEY/BIGMODEL_API_KEY or OPENAI_API_KEY).');
    process.exit(2);
  }
  const fn = provider === 'zai' ? generateZai : provider === 'openai' ? generateOpenai : null;
  if (!fn) { console.error(`Unknown provider: ${provider}`); process.exit(2); }

  // 批量串行间隔：避免并发触发限流。单次调用时 delayFlag 为 null，不睡。
  if (delayFlag) {
    const ms = parseInt(delayFlag, 10);
    if (ms > 0) { console.log(`delay ${ms}ms (serial batch spacing)...`); await sleep(ms); }
  }

  console.log(`generating [${provider}] -> ${outPath}`);

  // 限流：退避重试 3 次（30s / 60s / 90s）。限流配额按时间窗口恢复，等够就能过。
  // 内容失败：只试 1 次（同一个 prompt 再发大概率还失败），失败后明确告诉 agent 要简化 prompt。
  const RATE_LIMIT_ATTEMPTS = 3;
  const RATE_LIMIT_DELAYS = [30_000, 60_000, 90_000];
  let buf;
  let lastErr;
  for (let attempt = 0; attempt <= RATE_LIMIT_ATTEMPTS; attempt++) {
    try {
      buf = await fn(prompt, sizeFlag, qualityFlag);
      break;
    } catch (e) {
      lastErr = e;
      const msg = e.message || '';
      if (isRateLimit(msg) && attempt < RATE_LIMIT_ATTEMPTS) {
        const wait = RATE_LIMIT_DELAYS[attempt];
        console.error(`rate-limited (attempt ${attempt + 1}); sleeping ${wait / 1000}s then retrying...`);
        await sleep(wait);
        continue;
      }
      // 内容失败或限流重试用完：报错，让 agent 决定（简化 prompt / 换隐喻 / 换 provider）
      console.error(
        `generation failed: ${msg}\n` +
        (isRateLimit(msg)
          ? `rate limit retries exhausted. Wait a few minutes and rerun, or batch serially with --delay.`
          : `content/shape failure. Simplify the prompt (cut elements to ≤4, one metaphor, short paragraphs) and rerun.`)
      );
      process.exit(1);
    }
  }

  mkdirSync(dirname(resolve(outPath)), { recursive: true });
  writeFileSync(outPath, buf);
  console.log(`saved -> ${outPath} (${buf.length} bytes)`);
}

run().catch(e => { console.error(e.message); process.exit(1); });
