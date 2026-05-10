"""Литералы для pybabel extract (ngettext / pgettext)"""

from __future__ import annotations

from gettext import ngettext, pgettext


def _pybabel_extract_catalog_strings() -> None:
    """Не вызывается; нужен только чтобы extract находил контекстные строки"""
    ngettext("%(n)d hit point", "%(n)d hit points", 1)
    pgettext("weapon", "sword")
    pgettext("weapon", "axe")
    pgettext("weapon", "spear")
    pgettext("compass", "right")
    pgettext("compass", "left")
    pgettext("compass", "up")
    pgettext("compass", "down")
