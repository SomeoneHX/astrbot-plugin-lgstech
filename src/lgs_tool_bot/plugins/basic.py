import logging

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.onebot.models import OneBotEvent

logger = logging.getLogger(__name__)


async def handler(bot: Bot, event: OneBotEvent):
    text = event.plain_text.strip()
    if not text or not text.startswith("/"):
        return

    parts = text[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "ping":
        await bot.send_msg(event, "pong")
        logger.info("Ping from %s", event.user_id)
    elif cmd == "echo":
        if not await bot.require_permission(event, 1):
            return
        if not arg:
            await bot.send_msg(event, "用法: /echo <文本>")
        else:
            await bot.send_msg(event, arg)
        logger.info("Echo from %s: %s", event.user_id, arg or "(empty)")
    elif cmd == "help":
        help_text = "可用命令：\n/ping - 测试连通性\n/echo <文本> - 复读文本\n/help - 显示此帮助"
        await bot.send_msg(event, help_text)


def register(bot: Bot):
    bot.register(handler)
