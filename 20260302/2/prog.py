import sys

from cowsay import cowsay, list_cows


LIST_COWS = list_cows() + ["jgsbat"]


class InvalidCommand(RuntimeError):
    pass


class UnknownMonster(RuntimeError):
    pass


class Event:
    def __init__(self, *, nothing: bool = True):
        self._nothing = nothing

    def __bool__(self):
        return not self._nothing


class Monster(Event):
    def __init__(self, *, message: str, name: str):
        super().__init__(nothing=False)
        self._message = message
        self._name = name

    def say(self):
        if self._message:
            print(cowsay(message=self._message, cow=self._name))


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

    def addmon(
        self, pos: tuple[int, int], *, message: str, name: str = "default"
    ) -> Event:
        x, y = pos
        self[x, y] = Monster(message=message, name=name)

        return self[x, y]

    def encounter(self, x: int, y: int) -> None:
        event = self[x, y]

        if isinstance(event, Monster):
            event.say()


def main():
    game = DungeonGame()
    game.start()

    for line in sys.stdin:
        command, *args = line.split()
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

            elif command == "addmon" and len(args) == 4:
                name, x, y, message = args

                if name not in list_cows():
                    raise UnknownMonster

                x, y = int(x), int(y)

                is_replace = bool(game[x, y])

                game.addmon((x, y), message=message, name=name)
                print(f"Added monster to ({x}, {y}) saying {message}")

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
