import sys
import shlex

from dataclasses import dataclass
from cowsay import cowsay, list_cows


LIST_COWS = list_cows() + ["jgsbat"]

VERSION = 0.1


class InvalidCommand(RuntimeError):
    pass


class UnknownMonster(RuntimeError):
    pass


class Event:
    def __init__(self, *, nothing: bool = True):
        self._nothing = nothing

    def __bool__(self):
        return not self._nothing


@dataclass(frozen=True, slots=True)
class MonsterParams:
    name: str
    hello: str
    hp: int


class Monster(Event):
    def __init__(self, *, params: MonsterParams):
        super().__init__(nothing=False)
        self._params = params

    def say(self):
        print(cowsay(message=self._params.hello, cow=self._params.name))


class DungeonGame:
    def __init__(self, size: int = 10):
        self._size = size
        self.reset()

    @property
    def size(self) -> int:
        return self._size

    def reset(self) -> None:
        self._dungeon: list[list[Event]] = []
        for _ in range(self.size):
            row = []
            for _ in range(self.size):
                row.append(Event())
            self._dungeon.append(row)

    def start(self):
        print(f"<<< Welcome to Python-MUD {VERSION} >>>")
        self._user_pos: tuple[int, int] = (0, 0)

    def move(self, *, x: int = 0, y: int = 0) -> tuple[int, int]:
        _x, _y = self._user_pos
        _x = (_x + x) % self.size
        _y = (_y + y) % self.size
        self._user_pos = (_x, _y)
        return self.pos

    @property
    def pos(self) -> tuple[int, int]:
        return self._user_pos

    @property
    def x(self) -> int:
        return self._user_pos[0]

    @property
    def y(self) -> int:
        return self._user_pos[1]

    def go_right(self) -> tuple[int, int]:
        return self.move(x=1)

    def go_left(self) -> tuple[int, int]:
        return self.move(x=-1)

    def go_up(self) -> tuple[int, int]:
        return self.move(y=1)

    def go_down(self) -> tuple[int, int]:
        return self.move(y=-1)

    def __getitem__(self, key: tuple[int, int]) -> Event:
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key
            return self._dungeon[x][y]
        else:
            raise KeyError

    def __setitem__(self, key: tuple[int, int], event: Event):
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key
            self._dungeon[x][y] = event
        else:
            raise KeyError

    def addmon(self, x: int, y: int, *, params: MonsterParams) -> Event:
        if params.name not in list_cows():
            raise UnknownMonster

        self[x, y] = Monster(
            params=MonsterParams(name=params.name, hello=params.hello, hp=params.hp)
        )

        return self[x, y]

    def encounter(self, x: int, y: int) -> None:
        event = self[x, y]

        if isinstance(event, Monster):
            event.say()


def parse_addmon(args: list[str]) -> tuple[MonsterParams, int, int]:
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
        if key not in {"hello", "hp", "coords"}:
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
            except ValueError as e:
                raise InvalidCommand
            if hp <= 0:
                raise InvalidCommand
            i += 2

        else:
            need(2)
            try:
                x, y = int(args[i + 1]), int(args[i + 2])
            except ValueError as e:
                raise InvalidCommand
            i += 3

    missing = [p for p in ("hello", "hp", "coords") if p not in seen]
    if missing:
        raise InvalidCommand

    return MonsterParams(name=name, hello=hello, hp=hp), x, y


def main():
    game = DungeonGame()
    game.start()

    for line in sys.stdin:
        command, *args = shlex.split(line)
        try:
            if command in ["right", "left", "up", "down"] and len(args) == 0:
                if command == "right":
                    game.go_right()
                if command == "left":
                    game.go_left()
                if command == "up":
                    game.go_up()
                if command == "down":
                    game.go_down()

                x, y = game.pos
                print(f"Moved to ({x}, {y})")
                game.encounter(x, y)

            elif command == "addmon":
                params, x, y = parse_addmon(args)

                is_replace = bool(game[x, y])

                game.addmon(x, y, params=params)
                print(f"Added monster to ({x}, {y}) saying {params.hello}")

                if is_replace:
                    print("Replaced the old monster")
            else:
                raise InvalidCommand

        except UnknownMonster:
            print("Cannot add unknown monster")

        except Exception:
            print("Invalid command")


if __name__ == "__main__":
    main()
