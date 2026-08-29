"""LGS Tool Bot —— AstrBot 插件入口。

将原有的独立 OneBot 机器人 (lgs-tool-bot) 移植为 AstrBot Star 插件。
去掉了原项目中的基础机器人框架（自建 WS 连接、事件循环、/ping、/echo、/help、
/shot 等），仅保留洛谷保存站 (luogu.me) 与 CP OAuth 的查询/管理功能，
由 AstrBot 负责消息收发与平台适配。
"""

from __future__ import annotations

import base64
import os
import sys

# 确保插件自身目录在 sys.path 中，便于 import 同级 core 包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image
from astrbot.api.star import Context, Star, register

from core import ImageResult
from core.cpoauth import dispatch_cpoauth
from core.lgs import dispatch_lgs

DEFAULT_API_BASE = "https://api.luogu.me"
DEFAULT_CPOAUTH_API_BASE = "https://www.cpoauth.com/api/users"


@register(
    "astrbot_plugin_lgstech",
    "SomeoneHX",
    "洛谷保存站 (luogu.me) 查询与管理插件：用户/文章/剪贴板/任务/工作流查询与刷新派发，以及 CP OAuth 用户卡片。",
    "1.0.0",
    "https://github.com/SomeoneHX/astrbot-plugin-lgstech",
)
class LgsToolBotPlugin(Star):
    def __init__(self, context: Context, config: "AstrBotConfig | None" = None):
        super().__init__(context)
        # AstrBot 注入插件自身的 _conf_schema.json 配置；取不到时退回默认值。
        self.config = config if config is not None else {}
        self.api_base = self.config.get("api_base", DEFAULT_API_BASE)
        self.cpoauth_api_base = self.config.get("cpoauth_api_base", DEFAULT_CPOAUTH_API_BASE)
        self.admin_users = {str(u) for u in (self.config.get("admin_users") or [])}

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        return str(event.get_sender_id()) in self.admin_users

    def _to_result(self, event: AstrMessageEvent, item):
        if isinstance(item, ImageResult):
            b64 = base64.b64encode(item.data).decode()
            return event.chain_result([Image(file=f"base64://{b64}")])
        return event.plain_result(str(item))

    @filter.command("lgs")
    async def lgs_cmd(self, event: AstrMessageEvent):
        """洛谷保存站查询/刷新：/lgs query|update user|article|paste|task|workflow ..."""
        async for item in dispatch_lgs(event.message_str, self._is_admin(event), self.api_base):
            yield self._to_result(event, item)

    @filter.command("cpoauth")
    async def cpoauth_cmd(self, event: AstrMessageEvent):
        """CP OAuth 用户卡片：/cpoauth query <用户名>"""
        async for item in dispatch_cpoauth(event.message_str, self.cpoauth_api_base):
            yield self._to_result(event, item)
