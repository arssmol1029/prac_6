"""Отрисовка монстров через python-cowsay (в т.ч. кастомный cowfile)."""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

from cowsay import cowsay

MOOD_EXTRA = "mood_extra"
_EXTRA_COW = files("mood") / "data" / "extra_monster.txt"


def render_monster_art(name: str, hello: str) -> str:
    if name == MOOD_EXTRA:
        with as_file(_EXTRA_COW) as cow_path:
            return cowsay(message=hello, cowfile=str(Path(cow_path)))
    return cowsay(message=hello, cow=name)
