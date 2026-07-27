import tomllib
from pathlib import Path
from typing import Self

from pydantic import BaseModel


class OneBotConfig(BaseModel):
    ws_url: str = "ws://127.0.0.1:6700"
    access_token: str = ""
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 10


class BotConfig(BaseModel):
    name: str = "LGS Tool Bot"


class Config(BaseModel):
    onebot: OneBotConfig = OneBotConfig()
    bot: BotConfig = BotConfig()

    @classmethod
    def load(cls, path: str | None = None) -> Self:
        paths = [path] if path else ["config.toml", "config.example.toml"]
        for p in paths:
            file = Path(p)
            if file.exists():
                with open(file, "rb") as f:
                    data = tomllib.load(f)
                return cls(**data)
        return cls()
