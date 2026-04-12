import asyncio
import contextlib
import json
import random
import sys

from cowsay import cowsay
from mood.common.framing import frame_text
from mood.common.models import MonsterParams
from mood.common.routing import RouterBatch
from mood.server.world import MultiMUDWorld


world = MultiMUDWorld()
clients: dict[str, asyncio.Queue[bytes]] = {}


async def deliver(messages: RouterBatch) -> None:
    """
    Отправить сообщения игрокам.
    
    Args:
        messages: Список сообщений для отправки
    """
    for target, text, _origin in messages:
        if target is None:
            for q in clients.values():
                await q.put(frame_text(text))
        elif target in clients:
            await clients[target].put(frame_text(text))


def handle_command(username: str, line: str) -> tuple[bool, RouterBatch]:
    """
    Обработать команду от пользователя.
    
    Args:
        username: Имя пользователя, отправившего команду
        line: Строка с командой
        
    Returns:
        Кортеж (disconnect, messages), где:
        - disconnect: True если пользователь хочет отключиться
        - messages: Список сообщений для отправки
        
    Raises:
        ValueError: При некорректных параметрах команды
    """
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
    """
    Отклонить рукопожатие и закрыть соединение.
    
    Args:
        writer: StreamWriter для отправки сообщения
        message: Сообщение об ошибке
    """
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
    """
    Обработать сессию подключения игрока.
    
    Args:
        reader: StreamReader для чтения данных от клиента
        writer: StreamWriter для отправки данных клиенту
    """
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


async def monster_wandering_task() -> None:
    """
    Фоновая задача для перемещения монстров каждые 30 секунд.
    
    Первый раз запускается через 30 секунд после старта сервера.
    """
    await asyncio.sleep(30)
    
    while True:
        monsters = world.get_all_monsters()
        
        if not monsters:
            await asyncio.sleep(30)
            continue
        
        success = False
        attempts = 0
        max_attempts = len(monsters) * 4
        
        while not success and attempts < max_attempts:
            old_pos, monster = random.choice(monsters)
            
            directions = ['right', 'left', 'up', 'down']
            direction = random.choice(directions)
            
            success, new_pos, direction_name = world.move_monster(old_pos, direction)
            attempts += 1
            
            if success:
                msg = f"{monster.name} moved one cell {direction_name}"
                await deliver([(None, msg, None)])
                
                players_at_pos = world.get_players_at(new_pos)
                for player_name in players_at_pos:
                    art = cowsay(message=monster.hello, cow=monster.name)
                    await deliver([(player_name, art, None)])
        
        await asyncio.sleep(30)


async def main(host: str, port: int) -> None:
    """
    Основная функция запуска сервера.
    
    Args:
        host: Хост для прослушивания
        port: Порт для прослушивания
    """
    server = await asyncio.start_server(mud_session, host, port)
    print(f"MOOD server listening on {host}:{port}", file=sys.stderr)
    
    wandering_task = asyncio.create_task(monster_wandering_task())
    
    async with server:
        try:
            await server.serve_forever()
        finally:
            wandering_task.cancel()
            try:
                await wandering_task
            except asyncio.CancelledError:
                pass
