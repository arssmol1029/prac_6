from cowsay import list_cows

VERSION = 0.1

_base = list(list_cows())
if "mood_extra" not in _base:
    _base.append("mood_extra")
MONSTERS_LIST = tuple(_base)

WEAPONS: dict[str, int] = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}
WEAPON_NAMES: tuple[str, ...] = tuple(WEAPONS.keys())

ADDMON_PARAMS = ("hello", "hp", "coords")
