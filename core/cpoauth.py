"""CP OAuth 用户卡片查询，移植自原 ``lgs_tool_bot.plugins.cpoauth``。

抓取 SVG 卡片并转换为 PNG 后作为 :class:`~core.ImageResult` 返回。
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Union

import cairosvg
import httpx

from . import ImageResult

logger = logging.getLogger(__name__)

API_BASE = "https://www.cpoauth.com/api/users"

Result = Union[str, ImageResult]


async def dispatch_cpoauth(raw_text: str, api_base: str = API_BASE) -> AsyncGenerator[Result, None]:
    text = raw_text.strip()
    if not text:
        return
    body = text[1:] if text.startswith("/") else text
    parts = body.split(maxsplit=2)
    if len(parts) < 2 or parts[0].lower() != "cpoauth":
        return

    subcmd = parts[1].lower()
    username = parts[2] if len(parts) > 2 else ""

    if subcmd != "query":
        yield "用法: /cpoauth query <用户名>"
        return

    if not username:
        yield "用法: /cpoauth query <用户名>"
        return

    image_url = f"{api_base}/{username}/card.svg?lang=zh"
    logger.info("CPOAuth query: %s", username)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url, headers={"User-Agent": "lgs-tool-bot/0.1.0"})
            resp.raise_for_status()
            svg_data = resp.content
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            yield f"用户 {username} 不存在"
        else:
            yield f"请求失败: HTTP {e.response.status_code}"
        return
    except httpx.RequestError as e:
        logger.error("CPOAuth network error for %s: %s", username, e)
        yield f"网络错误: {e}"
        return

    logger.info("CPOAuth card fetched for %s (%d bytes SVG)", username, len(svg_data))

    # Inject CJK font fallback so Chinese text renders correctly
    svg_text = svg_data.decode("utf-8")
    cjk_fonts = (
        '"PingFang SC","Heiti SC","Microsoft YaHei",'
        '"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif'
    )
    style = f"<style>text,tspan{{font-family:{cjk_fonts}!important}}</style>"
    svg_text = svg_text.replace(">", f">\n{style}", 1)
    svg_data = svg_text.encode("utf-8")

    png_data = await asyncio.to_thread(cairosvg.svg2png, bytestring=svg_data)
    logger.info("Converted to PNG (%d bytes) for %s", len(png_data), username)
    yield ImageResult(png_data)
