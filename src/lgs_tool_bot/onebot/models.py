from typing import Any

from pydantic import BaseModel


class Sender(BaseModel):
    user_id: int = 0
    nickname: str = ""
    sex: str = ""
    age: int = 0


class OneBotEvent(BaseModel):
    post_type: str = ""
    message_type: str | None = None
    sub_type: str | None = None
    self_id: int = 0
    user_id: int | None = None
    group_id: int | None = None
    message: str | list[Any] | None = None
    raw_message: str | None = None
    font: int | None = None
    sender: Sender | dict | None = None
    time: int = 0
    message_id: int | None = None

    @property
    def is_self(self) -> bool:
        return self.user_id is not None and self.user_id == self.self_id

    @property
    def is_private(self) -> bool:
        return self.message_type == "private"

    @property
    def is_group(self) -> bool:
        return self.message_type == "group"

    @property
    def plain_text(self) -> str:
        if self.raw_message:
            return self.raw_message
        if isinstance(self.message, str):
            return self.message
        return ""
