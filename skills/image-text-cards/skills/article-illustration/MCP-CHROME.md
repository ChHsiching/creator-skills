# MCP-CHROME.md — mcp-chrome 检测与安装

SKILL.md 的 Step 1（抓源内容）遇到**登录墙/反爬页面**时读这一份。

[mcp-chrome](https://github.com/hangwin/mcp-chrome)（12k+ stars，MIT，第三方——不是 Google 官方）是一个 Chrome 扩展 + MCP server，把用户**日常用的那个 Chrome**（带登录态）暴露给 agent。登录墙、bot 检测、需要 cookie 的页面，它都能过。

**它不是硬依赖**——skill 没有 mcp-chrome 也能跑完整流程（用 web fetch / playwright 兜底）。它只是让登录墙页面变简单。用户拒绝装就跳过，别阻塞。

---

## 检测：已装就直接用

看当前工具清单里有没有以 `mcp__mcp-chrome__`（或 `chrome_`）开头的 MCP 工具。有 → 直接用（它能看到用户已登录的标签页）。

---

## 没装：问用户，要装就自动跑大部分步骤

用 AskUserQuestion 问：「这个源可能需要登录或过验证，要不要装 mcp-chrome？我帮你装大部分，你只需在 Chrome 点两下。」选项 要 / 不要。

### 用户选「要」→ agent 自动跑下面 3 步，只把第 4 步留给用户

**第 1 步（agent 自动）**：装桥接
```bash
npm install -g mcp-chrome-bridge
```

**第 2 步（agent 自动）**：找当前 coding 环境的 MCP 配置，加 `mcp-chrome` 条目。环境不同配置文件不同，先检测再改对的那个：

| 环境 | 配置文件 | 加的键 |
|---|---|---|
| ZCode | `~/.zcode/cli/config.json` | `mcp.servers.mcp-chrome = { "command": "mcp-chrome-stdio", "args": [] }` |
| Cursor | `~/.cursor/mcp.json` | `mcpServers.mcp-chrome = { "command": "mcp-chrome-stdio", "args": [] }` |
| Claude Desktop | 它的 config.json | `mcpServers.mcp-chrome = { "command": "mcp-chrome-stdio", "args": [] }` |
| 通用 | workspace 根的 `.mcp.json` | 同上 |

**改配置前先备份**；只加这一个键，别动别的。

**第 3 步（agent 自动）**：下扩展 + 解压到固定路径。最新 release：`https://github.com/hangwin/mcp-chrome/releases/latest`。下载 `chrome-mcp-server-*.zip` 资产，解压到 `~/Downloads/mcp-chrome-extension/`（或临时目录）。确认 `manifest.json` 在那个目录的根。

**第 4 步（用户手动——只有这步不能自动化）**：明确告诉用户：

> 打开 Chrome，地址栏输入 `chrome://extensions/`
> 右上角打开「开发者模式」开关
> 点「加载已解压的扩展程序」，选 `<那个解压目录>`
> 点扩展图标 → 点 **connect**
> **重启 coding 环境**（MCP server 是启动时加载的）
> 重启后回来继续，agent 会重新检测到 mcp-chrome 已就绪。

加载未打包扩展没有 CLI——这步真没法自动化，别假装能。

### 用户选「不要」→ 跳过

落回 playwright / 让用户贴内容。别阻塞，别反复劝。
