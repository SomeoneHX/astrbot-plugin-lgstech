import json
import logging
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class OneBotClient:
    def __init__(
        self,
        ws_url: str,
        access_token: str = "",
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 10,
    ):
        self._ws_url = ws_url
        self._access_token = access_token
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def connect(self):
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        try:
            self._ws = await websockets.connect(
                self._ws_url,
                extra_headers=headers,
                ping_interval=self._heartbeat_interval,
                ping_timeout=self._heartbeat_timeout,
            )
        except (OSError, websockets.InvalidURI) as e:
            raise ConnectionError(
                f"无法连接到 OneBot 服务器 ({self._ws_url}): {e}"
            ) from e
        logger.info("Connected to %s", self._ws_url)

    async def close(self):
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def recv(self) -> dict[str, Any]:
        data = await self._ws.recv()
        return json.loads(data)

    async def call_api(self, action: str, **params) -> dict[str, Any]:
        payload = {"action": action, "params": params}
        logger.debug("API call: %s %s", action, params)
        await self._ws.send(json.dumps(payload))
        return {}
