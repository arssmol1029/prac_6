"""Отрисовка монстров через python-cowsay (в т.ч. кастомный cowfile)."""

from __future__ import annotations

from importlib.resources import files
from io import StringIO

from cowsay import cowsay, read_dot_cow

MOOD_EXTRA = "mood_extra"
_EXTRA_COW = files("mood") / "data" / "extra_monster.txt"


def render_monster_art(name: str, hello: str) -> str:
    if name == MOOD_EXTRA:
        raw = _EXTRA_COW.read_text(encoding="utf-8")
        cow_src = read_dot_cow(StringIO(raw))
        return cowsay(message=hello, cowfile=cow_src)
    return cowsay(message=hello, cow=name)
