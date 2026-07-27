import asyncio
import base64
import logging

import cairosvg
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
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    image_url,
                    headers={"User-Agent": "lgs-tool-bot/0.1.0"},
                )
                resp.raise_for_status()
                svg_data = resp.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await bot.send_msg(event, f"用户 {username} 不存在")
            else:
                await bot.send_msg(event, f"请求失败: HTTP {e.response.status_code}")
            return
        except httpx.RequestError as e:
            logger.error("CPOAuth network error for %s: %s", username, e)
            detail = str(e) or type(e).__name__
            await bot.send_msg(event, f"网络错误: {detail}")
            return

        logger.info("CPOAuth card fetched for %s (%d bytes SVG)", username, len(svg_data))
        png_data = await asyncio.to_thread(cairosvg.svg2png, bytestring=svg_data)
        b64 = base64.b64encode(png_data).decode()
        logger.info("Converted to PNG (%d bytes) for %s", len(png_data), username)
        await bot.send_image(event, f"base64://{b64}")


def register(bot: Bot):
    bot.register(handler)
