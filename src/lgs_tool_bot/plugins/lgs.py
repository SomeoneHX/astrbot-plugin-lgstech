import logging

import httpx

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.onebot.models import OneBotEvent

logger = logging.getLogger(__name__)

API_BASE = "https://api.luogu.me"

COLOR_MAP = {
    "Gray": "灰",
    "Blue": "蓝",
    "Green": "绿",
    "Orange": "橙",
    "Red": "红",
    "Purple": "紫",
    "Legend": "黑",
}


async def handle_user_query(bot: Bot, event: OneBotEvent, uid: str):
    if not uid.isdigit():
        await bot.send_msg(event, "用法: /lgs query user <数字ID>")
        return

    url = f"{API_BASE}/user/query/{uid}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Uptime-Kuma"},
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.RequestError as e:
        logger.error("LGS API error: %s", e)
        await bot.send_msg(event, f"网络错误: {e}")
        return
    except httpx.HTTPStatusError as e:
        await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
        return

    if body.get("code") != 200:
        await bot.send_msg(event, f"查询失败: {body.get('message', '未知错误')}")
        return

    data = body.get("data")
    if not data:
        await bot.send_msg(event, "用户不存在")
        return

    name = data.get("name", "?")
    color = COLOR_MAP.get(data.get("color", ""), data.get("color", "?"))
    ccf_level = data.get("ccfLevel", 0)
    xcpc_level = data.get("xcpcLevel", 0)
    slogan = data.get("slogan") or "(无签名)"

    lines = [
        f"用户: {name}",
        f"颜色: {color}",
        f"CCF 等级: {ccf_level}",
        f"XCPC 等级: {xcpc_level}",
        f"签名: {slogan}",
    ]
    await bot.send_msg(event, "\n".join(lines))
    logger.info("LGS user query: %s -> %s", uid, name)


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=4)
    if len(parts) < 1 or parts[0].lower() != "lgs":
        return

    sub = parts[1].lower() if len(parts) > 1 else ""
    action = parts[2].lower() if len(parts) > 2 else ""
    arg = parts[3] if len(parts) > 3 else ""

    if sub == "query" and action == "user":
        await handle_user_query(bot, event, arg)


def register(bot: Bot):
    bot.register(handler)
