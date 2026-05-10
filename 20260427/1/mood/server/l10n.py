"""Серверная локализация сообщений"""

from __future__ import annotations

from gettext import NullTranslations
from pathlib import Path

from babel.support import Translations

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DOMAIN = "mood"

_ru_catalog: Translations | NullTranslations | None = None


def uses_russian_catalog(locale: str) -> bool:
    """True, если для локали нужно подставить каталог ru"""
    if not locale or not locale.strip():
        return False
    s = locale.strip().lower().replace("utf8", "utf-8")
    return s == "ru_ru.utf-8" or s.startswith("ru_ru.")


def _russian_translations() -> Translations | NullTranslations:
    """Читаем .mo из каталога ru_RU.UTF8"""
    global _ru_catalog
    if _ru_catalog is None:
        mo = LOCALES_DIR / "ru_RU.UTF8" / "LC_MESSAGES" / f"{DOMAIN}.mo"
        try:
            with mo.open("rb") as fp:
                _ru_catalog = Translations(fp=fp, domain=DOMAIN)
        except OSError:
            _ru_catalog = NullTranslations()
    return _ru_catalog


class LocaleContext:
    """Контекст gettext для одной строки локали"""

    __slots__ = ("_t",)

    def __init__(self, locale: str) -> None:
        if uses_russian_catalog(locale):
            self._t = _russian_translations()
        else:
            self._t = NullTranslations()

    def gettext(self, message: str) -> str:
        return self._t.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return self._t.ngettext(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str:
        return self._t.pgettext(context, message)

    def hp_phrase(self, n: int) -> str:
        return self.ngettext("%(n)d hit point", "%(n)d hit points", n) % {"n": n}

    def weapon_label(self, weapon_name: str) -> str:
        return self.pgettext("weapon", weapon_name)

    def compass(self, direction: str) -> str:
        return self.pgettext("compass", direction)
