import base64
import logging

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.browser import get_browser
from lgs_tool_bot.onebot.models import OneBotEvent

logger = logging.getLogger(__name__)


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    url = parts[1] if len(parts) > 1 else ""

    if cmd != "shot":
        return

    if not await bot.require_permission(event, 1):
        return

    if not url:
        await bot.send_msg(event, "用法: /shot <URL>")
        return

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    await bot.send_msg(event, "正在截图，请稍候...")
    logger.info("Shot: %s", url)

    try:
        browser = await get_browser()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(url, wait_until="networkidle", timeout=15000)
        png_bytes = await page.screenshot(full_page=False)
        await page.close()
    except Exception as e:
        logger.error("Shot error for %s: %s", url, e)
        await bot.send_msg(event, f"截图失败: {e}")
        return

    b64 = base64.b64encode(png_bytes).decode()
    await bot.send_image(event, f"base64://{b64}")
    logger.info("Shot done: %s (%d bytes)", url, len(png_bytes))


def register(bot: Bot):
    bot.register(handler)
