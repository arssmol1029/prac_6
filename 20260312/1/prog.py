import sys
import shlex
import cmd

from io import StringIO
from dataclasses import dataclass
from cowsay import cowsay, list_cows


VERSION = 0.1

MONSTERS_LIST = list_cows()

ADDMON_PARAMS = ("hello", "hp", "coords")


class InvalidCommand(RuntimeError):
    pass


class UnknownMonster(RuntimeError):
    pass


class Event:
    def __init__(self, *, nothing: bool = True):
        self._nothing = nothing

    def __bool__(self):
        return not self._nothing


class EmptyEvent(Event):
    def __init__(self):
        super().__init__(nothing=True)


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


class DungeonGame():
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
                row.append(EmptyEvent())
            self._dungeon.append(row)

    def start(self):
        print(f"<<< Welcome to Python-MUD {VERSION} >>>")
        self._user_pos: tuple[int, int] = (0, 0)

    @property
    def pos(self) -> tuple[int, int]:
        return self._user_pos

    @property
    def x(self) -> int:
        return self._user_pos[0]

    @property
    def y(self) -> int:
        return self._user_pos[1]

    # move commands
    def move(self, *, x: int = 0, y: int = 0) -> tuple[int, int]:
        _x, _y = self._user_pos
        _x = (_x + x) % self.size
        _y = (_y + y) % self.size
        self._user_pos = (_x, _y)

        print(f"Moved to ({_x}, {_y})")
        self.encounter(_x, _y)
        
        return self.pos
    
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


    # addmon command
    def addmon(self, x: int, y: int, *, params: MonsterParams) -> Event:
        if params.name not in MONSTERS_LIST:
            raise UnknownMonster

        is_replace = bool(self[x, y])

        self[x, y] = Monster(
            params=MonsterParams(name=params.name, hello=params.hello, hp=params.hp)
        )

        print(f"Added monster to ({x}, {y}) saying {params.hello}")

        if is_replace:
            print("Replaced the old monster")

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

    missing = [p for p in ADDMON_PARAMS if p not in seen]
    if missing:
        raise InvalidCommand

    return MonsterParams(name=name, hello=hello, hp=hp), x, y


class DungeonGameCmd(cmd.Cmd):
    def __init__(self, game: DungeonGame):
        super().__init__()
        self.game = game

    def do_right(self, arg: str) -> None:
        self.game.go_right()

    def do_left(self, arg: str) -> None:
        self.game.go_left()

    def do_up(self, arg: str) -> None:
        self.game.go_up()

    def do_down(self, arg: str) -> None:
        self.game.go_down()

    def do_addmon(self, arg: str) -> None:
        args = shlex.split(arg)
        params, x, y = parse_addmon(args)
        self.game.addmon(x, y, params=params)

    def _split_for_complete(self, s: str) -> list[str]:
        try:
            return shlex.split(s)
        except ValueError:
            for q in ('"', "'"):
                if s.count(q) % 2 == 1:
                    try:
                        return shlex.split(s + q)
                    except ValueError:
                        pass
            return s.split()

    def complete_addmon(self, text, line, begidx, endidx):
        before = line[:begidx]
        tokens = self._split_for_complete(before)

        if tokens and tokens[0] == "addmon":
            tokens = tokens[1:]
        else:
            return []

        used = set()
        monster_written = False
        waiting_value_for = None
        coords_values = 0

        for tok in tokens:
            if not monster_written:
                monster_written = True
                continue

            if waiting_value_for is None:
                if tok in ADDMON_PARAMS and tok not in used:
                    waiting_value_for = tok
                    coords_values = 0
                else:
                    return []
            else:
                if waiting_value_for == "coords":
                    coords_values += 1
                    if coords_values == 2:
                        used.add("coords")
                        waiting_value_for = None
                        coords_values = 0
                else:
                    used.add(waiting_value_for)
                    waiting_value_for = None

        if not monster_written:
            return [name for name in MONSTERS_LIST if name.startswith(text)]

        if waiting_value_for is not None:
            return []

        return [p for p in ADDMON_PARAMS if p.startswith(text) and p not in used]
    
    def do_EOF(self, arg: str) -> bool:
        return True
    
    def do_exit(self, arg: str) -> bool:
        return True


def main():
    game = DungeonGame()
    game.start()

    cmd = DungeonGameCmd(game)
    cmd.cmdloop()


if __name__ == "__main__":
    main()
