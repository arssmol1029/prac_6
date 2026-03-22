import asyncio
import json
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MonsterParams:
    name: str = "default"
    pos: tuple[int, int] = (0, 0)
    hello: str = "Hello!"
    hp: int = 100
    damage: int = 10


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
        super().__init__(nothing=False, name=params.name, pos=params.pos, damage=params.damage, hp=params.hp, **kwargs)
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
        super().__init__(name=params.name, pos=params.pos, damage=params.damage, hp=params.hp, **kwargs)


class DungeonGame:
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

    def __getitem__(self, key: tuple[int, int]) -> Event:
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key
            return self._dungeon[x][y]
        raise KeyError

    def __setitem__(self, key: tuple[int, int], event: Event) -> None:
        if isinstance(key, tuple) and len(key) == 2:
            x, y = key
            self._dungeon[x][y] = event
        else:
            raise KeyError

    def addmon(self, *, params: MonsterParams) -> dict:
        x, y = params.pos
        is_replace = bool(self[x, y])
        self[x, y] = Monster(params=params)
        return {"kind": "addmon", "x": x, "y": y, "replaced": is_replace}

    def move_player(self, dx: int, dy: int) -> dict:
        x, y = self._player.move(dx=dx, dy=dy, size=self._size)
        ev = self[x, y]
        if isinstance(ev, Monster):
            return {
                "kind": "move",
                "x": x,
                "y": y,
                "monster": {"cow": ev.name, "hello": ev.hello},
            }
        return {"kind": "move", "x": x, "y": y, "monster": None}

    def attack_monster(self, name: str, hit_damage: int) -> dict:
        pos = self._player.pos
        ev = self[pos]
        if not isinstance(ev, Monster) or ev.name != name:
            return {"kind": "no_monster", "name": name}
        dealt = ev.take_damage(hit_damage)
        remaining = ev.hp
        if not ev.alive:
            self[pos] = EmptyEvent()
        return {"kind": "attack", "name": name, "dealt": dealt, "remaining": remaining}


def handle_line(game: DungeonGame, line: str) -> dict | None:
    line = line.strip()
    if not line:
        return {"kind": "error", "msg": "empty line"}
    if line == "quit":
        return None
    parts = line.split()
    cmd = parts[0]
    if cmd == "move":
        dx, dy = int(parts[1]), int(parts[2])
        return game.move_player(dx, dy)
    if cmd == "attack":
        name = parts[1]
        hit_damage = int(parts[2])
        return game.attack_monster(name, hit_damage)
    if cmd == "addmon":
        payload = json.loads(line[len("addmon ") :])
        params = MonsterParams(
            name=payload["name"],
            pos=(int(payload["x"]), int(payload["y"])),
            hello=payload["hello"],
            hp=int(payload["hp"]),
        )
        return game.addmon(params=params)
    return {"kind": "error", "msg": f"unknown command: {cmd}"}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    game = DungeonGame()
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            line = data.decode("utf-8")
            out = handle_line(game, line)
            if out is None:
                writer.write((json.dumps({"kind": "bye"}, ensure_ascii=False) + "\n").encode("utf-8"))
                await writer.drain()
                break
            writer.write((json.dumps(out, ensure_ascii=False) + "\n").encode("utf-8"))
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def main(host: str, port: int) -> None:
    server = await asyncio.start_server(handle_client, host, port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    h = "0.0.0.0"
    p = 1337
    if len(sys.argv) >= 2:
        h = sys.argv[1]
    if len(sys.argv) >= 3:
        p = int(sys.argv[2])
    asyncio.run(main(h, p))
