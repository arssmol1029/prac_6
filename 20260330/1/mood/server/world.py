from dataclasses import dataclass

from cowsay import cowsay

from mood.common.models import MonsterParams
from mood.common.routing import RouterBatch


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
    def __init__(
        self,
        *,
        name: str,
        pos: tuple[int, int] = (0, 0),
        damage: int = 10,
        hp: int = 100,
        **kwargs,
    ):
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

    def die(self) -> None:
        self._alive = False

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def hp(self) -> int:
        return self._hp

    @property
    def pos(self) -> tuple[int, int]:
        return self._pos

    def move(self, *, dx: int = 0, dy: int = 0, size: int = 10) -> tuple[int, int]:
        x, y = self._pos
        x = (x + dx) % size
        y = (y + dy) % size
        self._pos = (x, y)
        return self.pos


class Monster(Event, Creature):
    def __init__(self, *, params: MonsterParams, **kwargs):
        super().__init__(
            nothing=False,
            name=params.name,
            pos=params.pos,
            damage=params.damage,
            hp=params.hp,
            **kwargs,
        )
        self.hello = params.hello

    def take_damage(self, damage) -> int:
        return super().take_damage(damage)

    def die(self) -> None:
        super().die()
        self._nothing = True


@dataclass(frozen=True, slots=True)
class PlayerParams:
    name: str = "player"
    pos: tuple[int, int] = (0, 0)
    hp: int = 100
    damage: int = 10


class Player(Creature):
    def __init__(self, *, params: PlayerParams, **kwargs):
        super().__init__(
            name=params.name,
            pos=params.pos,
            damage=params.damage,
            hp=params.hp,
            **kwargs,
        )


class MultiMUDWorld:
    def __init__(self, size: int = 10):
        self._size = size
        self._players: dict[str, Player] = {}
        self._dungeon: list[list[Event]] = []
        self._reset_grid()

    def _reset_grid(self) -> None:
        self._dungeon = []
        for _ in range(self._size):
            self._dungeon.append([EmptyEvent() for _ in range(self._size)])

    @property
    def size(self) -> int:
        return self._size

    def __getitem__(self, key: tuple[int, int]) -> Event:
        x, y = key
        return self._dungeon[x][y]

    def __setitem__(self, key: tuple[int, int], event: Event) -> None:
        x, y = key
        self._dungeon[x][y] = event

    def add_player(self, username: str) -> None:
        self._players[username] = Player(params=PlayerParams(name=username))

    def remove_player(self, username: str) -> None:
        self._players.pop(username, None)

    def move_player(self, username: str, dx: int, dy: int) -> RouterBatch:
        player = self._players[username]
        x, y = player.move(dx=dx, dy=dy, size=self._size)
        out: RouterBatch = [(username, f"Moved to ({x}, {y})", None)]
        ev = self[x, y]
        if isinstance(ev, Monster):
            art = cowsay(message=ev.hello, cow=ev.name)
            out.append((username, art, None))
        return out

    def attack_monster(
        self,
        username: str,
        monster_name: str,
        hit_damage: int,
        weapon_name: str,
    ) -> RouterBatch:
        pos = self._players[username].pos
        ev = self[pos]
        if not isinstance(ev, Monster) or ev.name != monster_name:
            return [(username, f"No {monster_name} here", None)]
        dealt = ev.take_damage(hit_damage)
        remaining = ev.hp
        if not ev.alive:
            self[pos] = EmptyEvent()
            head = f"{username} attacked {monster_name} with {weapon_name}"
            msg = f"{head} for {dealt} damage and killed the monster!"
        else:
            head = f"{username} attacked {monster_name} with {weapon_name}"
            tail = f"{monster_name} has {remaining} HP left."
            msg = f"{head} for {dealt} damage; {tail}"
        return [(None, msg, username)]

    def addmon(self, username: str, params: MonsterParams) -> RouterBatch:
        x, y = params.pos
        replaced = bool(self[x, y])
        self[x, y] = Monster(params=params)
        suffix = " (replaced existing monster)" if replaced else ""
        who = f"{username} placed monster {params.name}"
        stats = f"with {params.hp} HP at ({x}, {y}){suffix}."
        msg = f"{who} {stats}"
        return [(None, msg, username)]
