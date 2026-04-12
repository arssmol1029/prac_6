from cowsay import list_cows

VERSION = 0.1

MONSTERS_LIST = list_cows()

WEAPONS: dict[str, int] = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}
WEAPON_NAMES: tuple[str, ...] = tuple(WEAPONS.keys())

ADDMON_PARAMS = ("hello", "hp", "coords")
