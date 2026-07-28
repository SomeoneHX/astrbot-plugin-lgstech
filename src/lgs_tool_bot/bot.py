import logging
from collections.abc import Awaitable, Callable

from lgs_tool_bot.config import BotConfig, PermissionConfig
from lgs_tool_bot.onebot.client import OneBotClient
from lgs_tool_bot.onebot.models import OneBotEvent

logger = logging.getLogger(__name__)

Handler = Callable[["Bot", OneBotEvent], Awaitable[None]]


class Bot:
    def __init__(
        self,
        client: OneBotClient,
        config: BotConfig | None = None,
        perm_config: PermissionConfig | None = None,
    ):
        self.client = client
        self.config = config or BotConfig()
        self._perm_config = perm_config or PermissionConfig()
        self._handlers: list[Handler] = []
        self._running = False

    def get_user_level(self, user_id: int | None) -> int:
        if user_id is None:
            return self._perm_config.default_level
        return self._perm_config.users.get(str(user_id), self._perm_config.default_level)

    async def require_permission(self, event: OneBotEvent, level: int) -> bool:
        user_level = self.get_user_level(event.user_id)
        if user_level >= level:
            return True
        await self.send_msg(event, f"权限不足 (需要等级 {level}，你的等级 {user_level})")
        return False

    def register(self, handler: Handler):
        self._handlers.append(handler)

    async def _send(self, event: OneBotEvent, message: str):
        params = {"message": message}
        if event.is_private:
            params["user_id"] = event.user_id
            action = "send_private_msg"
        else:
            params["message_type"] = "group"
            params["group_id"] = event.group_id
            action = "send_group_msg"
        await self.client.call_api(action, **params)

    async def send_msg(self, event: OneBotEvent, message: str):
        await self._send(event, message)

    async def send_image(self, event: OneBotEvent, url: str):
        await self._send(event, f"[CQ:image,file={url}]")

    async def _dispatch(self, event: OneBotEvent):
        for handler in self._handlers:
            try:
                await handler(self, event)
            except Exception:
                logger.exception("Handler error")

    async def run(self):
        await self.client.connect()
        self._running = True
        logger.info("Bot %s is running", self.config.name)
        try:
            while self._running:
                raw = await self.client.recv()
                post_type = raw.get("post_type")
                if post_type == "meta_event":
                    logger.debug("Heartbeat: %s", raw.get("meta_event_type", "unknown"))
                    continue
                if post_type != "message":
                    continue
                event = OneBotEvent(**raw)
                if event.is_self:
                    logger.debug("Skipping self message")
                    continue
                logger.debug("Received: %s", event.plain_text)
                await self._dispatch(event)
        finally:
            await self.client.close()
