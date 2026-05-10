#!/usr/bin/env python3
"""Цели сборки: i18n (шаги extract/update/compile), html, test."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

ROOT: Final = Path(__file__).resolve().parent
LOCALES_DIR = ROOT / "mood" / "server" / "locales"
DOMAIN = "mood"
LOCALE = "ru_RU.UTF8"
POT_PATH = LOCALES_DIR / f"{DOMAIN}.pot"
PO_PATH = LOCALES_DIR / LOCALE / "LC_MESSAGES" / f"{DOMAIN}.po"
MO_PATH = LOCALES_DIR / LOCALE / "LC_MESSAGES" / f"{DOMAIN}.mo"
DOC_SOURCE = ROOT / "doc" / "source"
DOC_BUILD = ROOT / "doc" / "build"
BABEL_CFG = ROOT / "babel.cfg"


def clean_targets(paths: tuple[Path | str, ...] | list[Path | str]) -> None:
    """Удалить файлы и каталоги из списка путей (игнорирует отсутствующие)."""
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def _build_i18n_extract() -> None:
    _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "extract",
            "--no-default-keywords",
            "-F",
            str(BABEL_CFG),
            "-o",
            str(POT_PATH),
            "-k",
            "gettext",
            "-k",
            "ngettext:1,2",
            "-k",
            "pgettext:1c,2",
            str(ROOT / "mood"),
        ]
    )


def _build_i18n_update() -> None:
    _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "update",
            "-i",
            str(POT_PATH),
            "-d",
            str(LOCALES_DIR),
            "-l",
            LOCALE,
            "-D",
            DOMAIN,
        ]
    )


def _build_i18n_compile() -> None:
    _run(
        [
            sys.executable,
            "-m",
            "babel.messages.frontend",
            "compile",
            "-d",
            str(LOCALES_DIR),
            "-l",
            LOCALE,
            "-D",
            DOMAIN,
        ]
    )


def _build_html() -> None:
    _run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-M",
            "html",
            str(DOC_SOURCE),
            str(DOC_BUILD),
        ]
    )


def _build_test() -> None:
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test*.py"
    )
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


@dataclass(frozen=True)
class Goal:
    """Цель: зависимости, действие, артефакты для clean."""

    name: str
    deps: tuple[str, ...] = ()
    clean: tuple[Path, ...] = ()
    build: Callable[[], None] | None = None


GOALS: dict[str, Goal] = {
    "i18n_extract": Goal(
        name="i18n_extract",
        clean=(POT_PATH,),
        build=_build_i18n_extract,
    ),
    "i18n_update": Goal(
        name="i18n_update",
        deps=("i18n_extract",),
        clean=(),
        build=_build_i18n_update,
    ),
    "i18n_compile": Goal(
        name="i18n_compile",
        deps=("i18n_update",),
        clean=(MO_PATH,),
        build=_build_i18n_compile,
    ),
    "i18n": Goal(
        name="i18n",
        deps=("i18n_compile",),
        clean=(POT_PATH, MO_PATH),
        build=None,
    ),
    "html": Goal(
        name="html",
        clean=(DOC_BUILD,),
        build=_build_html,
    ),
    "test": Goal(
        name="test",
        deps=("i18n",),
        clean=(),
        build=_build_test,
    ),
}


def _goal_order(goal_name: str) -> list[str]:
    """Топологический порядок: зависимости раньше цели."""
    seen: set[str] = set()
    out: list[str] = []

    def visit(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        g = GOALS[name]
        for d in g.deps:
            visit(d)
        out.append(name)

    visit(goal_name)
    return out


def run_goal(goal_name: str) -> None:
    for name in _goal_order(goal_name):
        g = GOALS[name]
        if g.build is not None:
            g.build()


def clean_goal(goal_name: str) -> None:
    g = GOALS[goal_name]
    clean_targets(g.clean)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Цели сборки MOOD (по умолчанию: html).")
    parser.add_argument(
        "parts",
        nargs="*",
        default=["html"],
        metavar="PART",
        help="цель или «clean ЦЕЛЬ» (по умолчанию: html)",
    )
    args = parser.parse_args(argv)
    parts: list[str] = args.parts or ["html"]

    if parts[0] == "clean":
        name = parts[1] if len(parts) > 1 else "html"
        if name not in GOALS:
            print(f"Неизвестная цель для clean: {name}", file=sys.stderr)
            raise SystemExit(2)
        clean_goal(name)
        return

    if len(parts) != 1:
        print("Укажите одну цель или «clean ЦЕЛЬ».", file=sys.stderr)
        raise SystemExit(2)

    goal_name = parts[0]
    if goal_name not in GOALS:
        print(f"Неизвестная цель: {goal_name}", file=sys.stderr)
        raise SystemExit(2)

    run_goal(goal_name)


if __name__ == "__main__":
    main()
