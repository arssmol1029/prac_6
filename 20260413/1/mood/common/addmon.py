from mood.common.constants import ADDMON_PARAMS
from mood.common.models import InvalidCommand, MonsterParams


def parse_addmon(args: list[str]) -> MonsterParams:
    if len(args) < 1:
        raise InvalidCommand

    name = args[0]
    i = 1

    seen: set[str] = set()
    hello: str
    hp: int
    x: int
    y: int

    def need(n: int) -> None:
        if i + n >= len(args):
            raise InvalidCommand

    while i < len(args):
        key = args[i]
        if key not in ADDMON_PARAMS:
            raise InvalidCommand

        if key in seen:
            raise InvalidCommand
        seen.add(key)

        if key == "hello":
            need(1)
            hello = args[i + 1]
            i += 2

        elif key == "hp":
            need(1)
            try:
                hp = int(args[i + 1])
            except ValueError:
                raise InvalidCommand
            if hp <= 0:
                raise InvalidCommand
            i += 2

        else:
            need(2)
            try:
                x, y = int(args[i + 1]), int(args[i + 2])
            except ValueError:
                raise InvalidCommand
            i += 3

    missing = [p for p in ADDMON_PARAMS if p not in seen]
    if missing:
        raise InvalidCommand

    return MonsterParams(name=name, pos=(x, y), hello=hello, hp=hp)
