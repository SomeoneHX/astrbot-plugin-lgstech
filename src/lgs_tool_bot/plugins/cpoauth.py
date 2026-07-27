import logging

import httpx

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.onebot.models import OneBotEvent

logger = logging.getLogger(__name__)

API_BASE = "https://www.cpoauth.com/api/users"


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=2)
    if len(parts) < 2 or parts[0].lower() != "cpoauth":
        return

    subcmd = parts[1].lower()
    username = parts[2] if len(parts) > 2 else ""

    if subcmd == "query":
        if not username:
            await bot.send_msg(event, "用法: /cpoauth query <用户名>")
            return

        image_url = f"{API_BASE}/{username}/card.svg?lang=zh"
        logger.info("CPOAuth query: %s", username)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await bot.send_msg(event, f"用户 {username} 不存在")
            else:
                await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
            return
        except httpx.RequestError as e:
            await bot.send_msg(event, f"网络错误: {e}")
            return

        await bot.send_image(event, image_url)
        logger.info("CPOAuth card sent for %s", username)


def register(bot: Bot):
    bot.register(handler)
