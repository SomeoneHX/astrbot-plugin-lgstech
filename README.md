# LGS Tool Bot

基于 Python 3.12 的 OneBot v11 协议机器人，通过反向 WebSocket 连接 Napcat 等 OneBot 实现。

## 功能

| 命令 | 说明 | 权限 |
|------|------|------|
| `/ping` | 连通性测试 | 0 |
| `/echo <文本>` | 复读文本 | 1 |
| `/help` | 显示帮助 | 0 |
| `/cpoauth query <用户名>` | 查询 CP OAuth 用户卡片 | 0 |
| `/lgs query user <ID>` | 查询洛谷用户资料 | 0 |
| `/lgs update user <ID>` | 派发用户资料刷新任务 | 0 |
| `/lgs query article <ID> [--page N] [--full]` | 查询文章（支持分页/全文） | 0 / 1 (`--full`) |
| `/lgs update article <ID>` | 派发文章保存工作流 | 0 |
| `/lgs query paste <ID> [--page N] [--full]` | 查询剪贴板（支持分页/全文） | 0 / 1 (`--full`) |
| `/lgs update paste <ID>` | 派发剪贴板保存工作流 | 0 |
| `/lgs query task <ID>` | 查询任务状态 | 0 |
| `/lgs query workflow <ID>` | 查询工作流及子任务状态 | 0 |

## 快速开始

```bash
# 克隆后进入项目目录
cd lgs-tool-bot

# 安装依赖
uv sync

# 复制配置并修改
cp config.example.toml config.toml

# 启动
uv run lgs-tool-bot
```

## 配置

```toml
[onebot]
ws_url = "ws://127.0.0.1:6700"     # OneBot 服务端反向 WS 地址
access_token = ""                    # 访问令牌
heartbeat_interval = 30              # WebSocket ping 间隔（秒）
heartbeat_timeout = 10               # WebSocket ping 超时（秒）

[bot]
name = "LGS Tool Bot"                # 机器人名称

[permissions]
default_level = 0                     # 未指定用户的默认等级

[permissions.users]
# "QQ号" = 等级
```

## 权限系统

- **0**: 所有人可用
- **1+**: 需在 `permissions.users` 中配置

在插件中检查权限：

```python
if not await bot.require_permission(event, level=1):
    return
```

内置方法：

```python
bot.get_user_level(user_id)           # 获取用户等级
bot.require_permission(event, level)  # 检查并自动回复
```

## 项目结构

```
src/lgs_tool_bot/
├── __init__.py        # 版本号
├── __main__.py        # 入口
├── config.py          # TOML 配置加载
├── bot.py             # Bot 核心（事件循环 + 插件调度 + 消息发送）
├── onebot/
│   ├── models.py      # OneBot v11 事件模型
│   └── client.py      # 反向 WebSocket 客户端
└── plugins/
    ├── basic.py       # /ping /echo /help
    ├── cpoauth.py     # /cpoauth query（SVG → PNG 卡片）
    └── lgs.py         # 洛谷保存站 API 集成
```

## 扩展插件

1. 在 `plugins/` 下新建文件
2. 实现 `async def handler(bot, event)` 和 `def register(bot)`
3. 在 `__main__.py` 中注册

Bot 提供的方法：

```python
bot.send_msg(event, "文本")         # 发送消息
bot.send_image(event, "url")        # 发送图片（CQ 码）
bot.client.call_api("action", **params)  # 调用任意 OneBot API
```

事件对象常用属性：

```python
event.plain_text    # 纯文本消息
event.user_id       # 发送者 QQ
event.group_id      # 群号
event.is_private    # 是否私聊
event.is_group      # 是否群聊
event.is_self       # 是否机器人自己发出
event.self_id       # 机器人自身 QQ
```

## 许可

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
