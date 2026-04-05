import asyncio
import contextlib
import json
import sys
from dataclasses import dataclass

from cowsay import cowsay


def frame_text(text: str) -> bytes:
    data = text.encode("utf-8")
    return str(len(data)).encode("ascii") + b"\n" + data


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

    def move_player(self, username: str, dx: int, dy: int) -> list[tuple[str | None, str, str | None]]:
        player = self._players[username]
        x, y = player.move(dx=dx, dy=dy, size=self._size)
        out: list[tuple[str | None, str, str | None]] = [(username, f"Moved to ({x}, {y})", None)]
        ev = self[x, y]
        if isinstance(ev, Monster):
            art = cowsay(message=ev.hello, cow=ev.name)
            out.append((username, art, None))
        return out

    def attack_monster(
        self, username: str, monster_name: str, hit_damage: int, weapon_name: str
    ) -> list[tuple[str | None, str, str | None]]:
        pos = self._players[username].pos
        ev = self[pos]
        if not isinstance(ev, Monster) or ev.name != monster_name:
            return [(username, f"No {monster_name} here", None)]
        dealt = ev.take_damage(hit_damage)
        remaining = ev.hp
        if not ev.alive:
            self[pos] = EmptyEvent()
            msg = (
                f"{username} attacked {monster_name} with {weapon_name} for {dealt} damage "
                f"and killed the monster!"
            )
        else:
            msg = (
                f"{username} attacked {monster_name} with {weapon_name} for {dealt} damage; "
                f"{monster_name} has {remaining} HP left."
            )
        return [(None, msg, username)]

    def addmon(self, username: str, params: MonsterParams) -> list[tuple[str | None, str, str | None]]:
        x, y = params.pos
        replaced = bool(self[x, y])
        self[x, y] = Monster(params=params)
        suffix = " (replaced existing monster)" if replaced else ""
        msg = f"{username} placed monster {params.name} with {params.hp} HP at ({x}, {y}){suffix}."
        return [(None, msg, username)]


world = MultiMUDWorld()
clients: dict[str, asyncio.Queue[bytes]] = {}


async def deliver(messages: list[tuple[str | None, str, str | None]]) -> None:
    for target, text, _origin in messages:
        if target is None:
            for q in clients.values():
                await q.put(frame_text(text))
        elif target in clients:
            await clients[target].put(frame_text(text))


def handle_command(username: str, line: str) -> tuple[bool, list[tuple[str | None, str, str | None]]]:
    line = line.strip()
    if not line:
        return False, []
    if line == "quit":
        world.remove_player(username)
        return True, [(None, f"{username} left the MUD.", username)]

    try:
        parts = line.split()
        if not parts:
            return False, []
        cmd = parts[0]
        if cmd == "move":
            if len(parts) != 3:
                raise ValueError
            dx, dy = int(parts[1]), int(parts[2])
            return False, world.move_player(username, dx, dy)
        if cmd == "attack":
            if len(parts) != 4:
                raise ValueError
            monster_name = parts[1]
            hit_damage = int(parts[2])
            weapon_name = parts[3]
            return False, world.attack_monster(username, monster_name, hit_damage, weapon_name)
        if cmd == "addmon":
            payload = json.loads(line[len("addmon ") :])
            params = MonsterParams(
                name=payload["name"],
                pos=(int(payload["x"]), int(payload["y"])),
                hello=payload["hello"],
                hp=int(payload["hp"]),
            )
            return False, world.addmon(username, params)
        return False, [(username, f"Unknown command: {cmd}", None)]
    except (ValueError, json.JSONDecodeError, KeyError, TypeError):
        return False, [(username, "Invalid command or parameters.", None)]


async def reject_handshake(writer: asyncio.StreamWriter, message: str) -> None:
    try:
        writer.write(frame_text(message))
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def mud_session(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    first = await reader.readline()
    if not first:
        writer.close()
        await writer.wait_closed()
        return

    username = first.decode("utf-8").strip()
    if not username or any(c.isspace() for c in username):
        await reject_handshake(writer, "ERROR invalid username (non-empty, no spaces)")
        return
    if username in clients:
        await reject_handshake(writer, "ERROR username already connected")
        return

    queue: asyncio.Queue[bytes] = asyncio.Queue()
    clients[username] = queue
    world.add_player(username)

    send = asyncio.create_task(reader.readline())
    receive = asyncio.create_task(queue.get())
    user_initiated_quit = False

    try:
        for u, q in clients.items():
            if u != username:
                await q.put(frame_text(f"{username} joined the MUD."))
        await queue.put(frame_text(f"Welcome {username}, you are connected to Python-MUD."))

        running = True
        while running and not reader.at_eof():
            done, _pending = await asyncio.wait(
                {send, receive},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                if task is send:
                    data = task.result()
                    send = asyncio.create_task(reader.readline())
                    if not data:
                        running = False
                        break
                    line = data.decode("utf-8")
                    disconnect, msgs = handle_command(username, line.rstrip("\r\n"))
                    await deliver(msgs)
                    if disconnect:
                        user_initiated_quit = True
                        running = False
                        break
                elif task is receive:
                    blob = task.result()
                    receive = asyncio.create_task(queue.get())
                    writer.write(blob)
                    await writer.drain()
    finally:
        send.cancel()
        receive.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await send
        with contextlib.suppress(asyncio.CancelledError):
            await receive

        was_in_clients = username in clients
        if was_in_clients:
            del clients[username]
        world.remove_player(username)
        if was_in_clients and not user_initiated_quit:
            note = frame_text(f"{username} disconnected from the MUD.")
            for q in clients.values():
                await q.put(note)
        writer.close()
        await writer.wait_closed()


async def main(host: str, port: int) -> None:
    server = await asyncio.start_server(mud_session, host, port)
    print(f"MUD server listening on {host}:{port}", file=sys.stderr)
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
