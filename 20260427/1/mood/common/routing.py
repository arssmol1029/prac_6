from collections.abc import Callable
from typing import TypeAlias

# Второй элемент: строка на английском или функция, получающая локаль клиента и возвращающая текст.
MessageBody: TypeAlias = str | Callable[[str], str]
RouterMsg: TypeAlias = tuple[str | None, MessageBody, str | None]
RouterBatch: TypeAlias = list[RouterMsg]
