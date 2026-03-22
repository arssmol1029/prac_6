import shlex
import cmd

from dataclasses import dataclass
from cowsay import cowsay, list_cows


VERSION = 0.1

MONSTERS_LIST = list_cows()

WEAPONS: dict[str, int] = {
    "sword": 10,
    "spear": 15,
    "axe": 20,
}
WEAPON_NAMES: tuple[str, ...] = tuple(WEAPONS.keys())

ADDMON_PARAMS = ("hello", "hp", "coords")


class InvalidCommand(RuntimeError):
    pass


class UnknownMonster(RuntimeError):
    pass


class Event:
    def __init__(self, *, nothing: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._nothing = nothing

    def __bool__(self):
        return not self._nothing


class EmptyEvent(Event):
    def __init__(self):
        super().__init__(nothing=True)


class Creature:
    def __init__(self, *, name: str, pos: tuple[int, int] = (0, 0), damage: int = 10, hp: int = 100, **kwargs):
        super().__init__(**kwargs)

        self.name = name
        self._pos = pos
        self._hp = hp
        self._damage = damage

        self._alive = True

    def take_damage(self, damage: int) -> int:
        start_hp = self._hp
        
        if damage > self._hp:
            self._hp = 0
            self.die()
        else:
            self._hp -= damage

        return start_hp - self._hp
    
    def attack(self, creature: "Creature") -> int:
        return creature.take_damage(self._damage)
    
    def die(self) -> None:
        self._alive = False

    @property
    def alive(self) -> bool:
        return self._alive
    
    @property
    def hp(self) -> int:
        return self._hp
    
    @property
    def damage(self) -> int:
        return self._damage
    
    @property
    def pos(self) -> tuple[int, int]:
        return self._pos

    @property
    def x(self) -> int:
        return self._pos[0]

    @property
    def y(self) -> int:
        return self._pos[1]
    
    # move commands
    def move(self, *, dx: int = 0, dy: int = 0, size: int = 10) -> tuple[int, int]:
        x, y = self._pos
        x = (x + dx) % size
        y = (y + dy) % size
        self._pos = (x, y)

        print(f"Moved to ({x}, {y})")
        
        return self.pos
    
    def go_right(self, size: int = 10) -> tuple[int, int]:
        return self.move(dx=1, size=size)

    def go_left(self, size: int = 10) -> tuple[int, int]:
        return self.move(dx=-1, size=size)

    def go_up(self, size: int = 10) -> tuple[int, int]:
        return self.move(dy=1, size=size)

    def go_down(self, size: int = 10) -> tuple[int, int]:
        return self.move(dy=-1, size=size)


@dataclass(frozen=True, slots=True)
class MonsterParams:
    name: str = "default"
    pos: tuple[int, int] = (0, 0)
    hello: str = "Hello!"
    hp: int = 100
    damage: int = 10


class Monster(Event, Creature):
    def __init__(self, *, params: MonsterParams, **kwargs):
        super().__init__(nothing=False, name=params.name, pos=params.pos, damage=params.damage, hp=params.hp, **kwargs)
        self.hello = params.hello

    def say(self) -> None:
        print(cowsay(message=self.hello, cow=self.name))

    def take_damage(self, damage) -> int:
        damage = super().take_damage(damage)
        if self.alive:
            print(f"{self.name} now has {self._hp} hp")
        return damage

    def die(self) -> None:
        super().die()
        print(f"{self.name} died")
        self._nothing = True


@dataclass(frozen=True, slots=True)
class PlayerParams:
    name: str = "player"
    pos: tuple[int, int] = (0, 0)
    hp: int = 100
    damage: int = 10


class Player(Creature):
    def __init__(self, *, params: PlayerParams, **kwargs):
        super().__init__(name=params.name, pos=params.pos, damage=params.damage, hp=params.hp, **kwargs)

    def attack(self, creature: Creature, *, hit_damage: int | None = None) -> int:
        if hit_damage is not None:
            damage = creature.take_damage(hit_damage)
        else:
            damage = super().attack(creature)
        print(f"Attacked {creature.name},  damage {damage} hp")
        return damage
    

class DungeonGame():
    def __init__(self, player_params: PlayerParams = PlayerParams(), size: int = 10):
        self._player = Player(params=player_params)
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
    def addmon(self, *, params: MonsterParams) -> Event:
        if params.name not in MONSTERS_LIST:
            raise UnknownMonster
        
        x, y = params.pos

        is_replace = bool(self[x, y])

        self[x, y] = Monster(
            params=params
        )

        print(f"Added monster to ({x}, {y}) saying {params.hello}")

        if is_replace:
            print("Replaced the old monster")

        return self[x, y]    

    def encounter(self, x: int, y: int) -> None:
        event = self[x, y]

        if isinstance(event, Monster):
            event.say()


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

    return MonsterParams(name=name, pos=(x, y), hello=hello, hp=hp)


class DungeonGameCmd(cmd.Cmd):
    def __init__(self, game: DungeonGame):
        super().__init__()
        self.prompt = "> "
        self._game = game

    def move(self, *, dx: int = 0, dy: int = 0, size: int = 10) -> tuple[int, int]:
        x, y = self._game._player.move(dx=dx, dy=dy, size=size)
        self._game.encounter(x, y)

    def do_right(self, arg: str) -> None:
        self.move(dx=1)

    def do_left(self, arg: str) -> None:
        self.move(dx=-1)

    def do_up(self, arg: str) -> None:
        self.move(dy=1)

    def do_down(self, arg: str) -> None:
        self.move(dy=-1)

    def do_addmon(self, arg: str) -> None:
        args = shlex.split(arg)
        try:
            params = parse_addmon(args)
        except InvalidCommand:
            print("Invalid arguments")
            return
        self._game.addmon(params=params)

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

    def complete_attack(self, text, line, begidx, endidx):
        tokens = self._split_for_complete(line[:begidx])
        if not tokens or tokens[0] != "attack":
            return []
        rest = tokens[1:]
        before = line[:begidx]

        if not rest:
            return [m for m in MONSTERS_LIST if m.startswith(text)]

        if len(rest) == 1:
            if text == "" and before.endswith(" "):
                return [w for w in ("with",) if w.startswith(text)]
            prefix = text if text else rest[0]
            return [m for m in MONSTERS_LIST if m.startswith(prefix)]

        if rest[1] != "with" and not "with".startswith(rest[1]):
            return []

        if len(rest) == 2:
            if rest[1] == "with":
                return [w for w in WEAPON_NAMES if w.startswith(text)]
            return [w for w in ("with",) if w.startswith(text)]

        if len(rest) == 3 and rest[1] == "with":
            return [w for w in WEAPON_NAMES if w.startswith(text)]

        return []

    def do_attack(self, arg: str) -> None:
        try:
            args = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return
        if not args:
            print("Invalid arguments")
            return

        pos = self._game._player.pos
        event = self._game[pos]

        if len(args) == 1:
            monster_name = args[0]
            if not isinstance(event, Monster) or event.name != monster_name:
                print(f"No {monster_name} here")
                return
            damage = WEAPONS["sword"]
            self._game._player.attack(event, hit_damage=damage)
        elif len(args) == 3 and args[1] == "with":
            monster_name = args[0]
            weapon_name = args[2]
            if weapon_name not in WEAPONS:
                print("Unknown weapon")
                return
            if not isinstance(event, Monster) or event.name != monster_name:
                print(f"No {monster_name} here")
                return
            damage = WEAPONS[weapon_name]
            self._game._player.attack(event, hit_damage=damage)
        else:
            print("Invalid arguments")
            return

        if not self._game[pos]:
            self._game[pos] = EmptyEvent()
    
    def emptyline(self) -> None:
        pass

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
