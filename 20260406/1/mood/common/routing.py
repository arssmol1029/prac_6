from typing import TypeAlias

RouterMsg: TypeAlias = tuple[str | None, str, str | None]
RouterBatch: TypeAlias = list[RouterMsg]
