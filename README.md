# LGS 工具箱（AstrBot 插件）

基于原 [lgs-tool-bot](https://github.com/SomeoneHX/astrbot-plugin-lgstech)（独立 OneBot v11 机器人）移植而来的 **AstrBot 插件**。

与原项目相比，本插件**去掉了独立机器人框架与基础指令**，改为由 AstrBot 统一负责消息收发与平台适配（OneBot v11 / QQ 等），仅保留洛谷保存站 (luogu.store) 与 CP OAuth 的查询/管理功能：

- ❌ 已移除：自建反向 WebSocket 连接、事件循环、`/ping`、`/echo`、`/help`、`/shot` 等基础机器人功能。
- ✅ 保留并移植：`/lgs`（洛谷保存站查询/刷新）、`/cpoauth`（CP OAuth 用户卡片）。

## 指令

| 指令 | 说明 | 权限 |
|------|------|------|
| `/lgs query user <ID>` | 查询洛谷用户资料 | 所有人 |
| `/lgs update user <ID>` | 派发用户资料刷新任务 | 所有人 |
| `/lgs query article <ID> [--page N] [--full]` | 查询文章（支持分页；`--full` 输出全文） | `--full` 需管理员 |
| `/lgs update article <ID>` | 派发文章保存工作流 | 所有人 |
| `/lgs query paste <ID> [--page N] [--full]` | 查询剪贴板（支持分页；`--full` 输出全文） | `--full` 需管理员 |
| `/lgs update paste <ID>` | 派发剪贴板保存工作流 | 所有人 |
| `/lgs query task <ID>` | 查询任务状态 | 所有人 |
| `/lgs query workflow <ID>` | 查询工作流及子任务状态 | 所有人 |
| `/cpoauth query <用户名>` | 查询 CP OAuth 用户卡片（SVG→PNG 图片） | 所有人 |

> 文章/剪贴板支持 `--html` 将渲染内容截图返回。HTML 由插件在内部由 markdown 拼接，CSS 为内置通用样式，**支持 LaTeX（KaTeX）公式渲染**（所有 KaTeX 资源已打包进 `core/katex/`，无需联网下载，渲染时也不需要外网）。

## 安装

将本仓库放入 AstrBot 的 `data/plugins/` 目录后，于 WebUI 插件管理重载即可。依赖由 `requirements.txt` 自动安装：

```
httpx
markdown
cairosvg
playwright   # 需要执行 playwright install chromium 以启用 --html 渲染
```

## 配置

在 WebUI 插件配置面板中可修改（对应 `_conf_schema.json`）：

| 配置项 | 说明 | 默认 |
|--------|------|------|
| `api_base` | 洛谷保存站 API 根地址 | `https://api.luogu.me` |
| `cpoauth_api_base` | CP OAuth 用户卡片 API 根地址 | `https://www.cpoauth.com/api/users` |
| `admin_users` | 允许使用 `--full` 等长输出指令的 QQ 号列表 | `[]` |

## 目录结构

```
.
├── metadata.yaml        # 插件元数据（AstrBot 必需）
├── _conf_schema.json     # 插件配置 schema
├── requirements.txt      # 第三方依赖
├── main.py              # 插件入口（Star + @command）
└── core/                # 与 AstrBot 解耦的业务逻辑
    ├── lgs.py           # 洛谷保存站 API 集成
    ├── cpoauth.py       # CP OAuth 卡片（SVG→PNG）
    ├── browser.py       # HTML→PNG 渲染（Playwright + KaTeX）
    └── katex/           # 本地 KaTeX 资源（CSS / JS / 字体），用于 LaTeX 渲染
```

## 许可与署名

- 原 `lgs-tool-bot` 采用 MIT 许可，本移植版本沿用，见 `LICENSE`。
- LaTeX 渲染由 [KaTeX](https://katex.org/) 提供，版本 0.16.11，相关 CSS/JS/字体随插件打包于 `core/katex/`，不依赖任何运行时网络资源。
