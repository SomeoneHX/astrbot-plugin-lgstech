import asyncio
import logging
import sys

from lgs_tool_bot.bot import Bot
from lgs_tool_bot.config import Config
from lgs_tool_bot.onebot.client import OneBotClient
from lgs_tool_bot.plugins import basic


def setup_logging(level: int = logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    setup_logging()
    config = Config.load()

    client = OneBotClient(
        ws_url=config.onebot.ws_url,
        access_token=config.onebot.access_token,
        heartbeat_interval=config.onebot.heartbeat_interval,
        heartbeat_timeout=config.onebot.heartbeat_timeout,
    )
    bot = Bot(client=client, config=config.bot)

    basic.register(bot)

    try:
        asyncio.run(bot.run())
    except ConnectionError as e:
        logger = logging.getLogger(__name__)
        logger.error(e)
        logger.error("请确认 OneBot 服务端（如 go-cqhttp / Lagrange）已启动，且 config.toml 中 ws_url 地址正确")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user")


if __name__ == "__main__":
    main()
