import asyncio
import contextlib
import json
import sys

from mood.common.framing import frame_text
from mood.common.models import MonsterParams
from mood.common.routing import RouterBatch
from mood.server.world import MultiMUDWorld


world = MultiMUDWorld()
clients: dict[str, asyncio.Queue[bytes]] = {}


async def deliver(messages: RouterBatch) -> None:
    for target, text, _origin in messages:
        if target is None:
            for q in clients.values():
                await q.put(frame_text(text))
        elif target in clients:
            await clients[target].put(frame_text(text))


def handle_command(username: str, line: str) -> tuple[bool, RouterBatch]:
    line = line.strip()
    if not line:
        return False, []
    if line == "quit":
        world.remove_player(username)
        return True, [(None, f"{username} left the MOOD.", username)]

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
            return False, world.attack_monster(
                username,
                monster_name,
                hit_damage,
                weapon_name,
            )
        if cmd == "addmon":
            payload = json.loads(line[len("addmon ") :])
            params = MonsterParams(
                name=payload["name"],
                pos=(int(payload["x"]), int(payload["y"])),
                hello=payload["hello"],
                hp=int(payload["hp"]),
            )
            return False, world.addmon(username, params)
        if cmd == "sayall":
            prefix = "sayall "
            if not line.startswith(prefix):
                raise ValueError
            rest = line[len(prefix) :]
            text = json.loads(rest)
            if not isinstance(text, str):
                raise ValueError
            return False, [(None, f"{username}: {text}", username)]
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


async def mud_session(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    first = await reader.readline()
    if not first:
        writer.close()
        await writer.wait_closed()
        return

    username = first.decode("utf-8").strip()
    if not username or any(c.isspace() for c in username):
        err = "ERROR invalid username (non-empty, no spaces)"
        await reject_handshake(writer, err)
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
                await q.put(frame_text(f"{username} joined the MOOD."))
        await queue.put(frame_text(f"Welcome {username}, you are connected to MOOD."))

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
            note = frame_text(f"{username} disconnected from the MOOD.")
            for q in clients.values():
                await q.put(note)
        writer.close()
        await writer.wait_closed()


async def main(host: str, port: int) -> None:
    server = await asyncio.start_server(mud_session, host, port)
    print(f"MOOD server listening on {host}:{port}", file=sys.stderr)
    async with server:
        await server.serve_forever()
