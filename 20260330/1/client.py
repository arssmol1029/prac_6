import json
import readline
import shlex
import cmd
import socket
import sys
import threading
from dataclasses import dataclass

from cowsay import list_cows


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


@dataclass(frozen=True, slots=True)
class MonsterParams:
    name: str = "default"
    pos: tuple[int, int] = (0, 0)
    hello: str = "Hello!"
    hp: int = 100
    damage: int = 10


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


def read_framed(sock: socket.socket, buf: bytearray) -> str | None:
    while True:
        nl = buf.find(b"\n")
        if nl < 0:
            chunk = sock.recv(65536)
            if not chunk:
                return None
            buf += chunk
            continue
        try:
            n = int(bytes(buf[:nl]).decode("ascii"))
        except ValueError:
            return None
        if n < 0:
            return None
        del buf[: nl + 1]
        while len(buf) < n:
            chunk = sock.recv(max(8192, n - len(buf)))
            if not chunk:
                return None
            buf += chunk
        body = bytes(buf[:n])
        del buf[:n]
        return body.decode("utf-8")


def emit_server_message(cmdline: "MUDClient", text: str, lock: threading.Lock) -> None:
    """Вывод сообщения сервера и приглашения.

    Если предыдущая строка команды была пустой (только Enter) либо на сервер ушла
    строка, оканчивающаяся на \\n (любая _send_line), показываем пустой хвост
    после '> ' до тех пор, пока буфер readline пуст или совпадает с только что
    отправленной строкой; иначе показываем то, что введено (get_line_buffer).
    """
    body = text.strip("\n")
    prompt = cmdline.prompt
    with lock:
        raw = readline.get_line_buffer()
        if cmdline._use_empty_line_after_prompt:
            if raw == "" or (
                cmdline._last_user_line is not None and raw != cmdline._last_user_line
            ):
                buf = raw
                cmdline._use_empty_line_after_prompt = False
            else:
                buf = ""
        else:
            buf = raw
        if body:
            sys.stdout.write(f"\n{body}\n{prompt}{buf}")
        else:
            sys.stdout.write(f"\n{prompt}{buf}")
        sys.stdout.flush()


def receiver_thread(
    cmdline: "MUDClient", sock: socket.socket, buf: bytearray, lock: threading.Lock
) -> None:
    while True:
        text = read_framed(sock, buf)
        if text is None:
            with lock:
                sys.stdout.write(
                    f"\n[connection closed]\n{cmdline.prompt}{readline.get_line_buffer()}"
                )
                sys.stdout.flush()
            return
        emit_server_message(cmdline, text, lock)


class MUDClient(cmd.Cmd):
    def __init__(self, sock: socket.socket, lock: threading.Lock):
        super().__init__()
        self.prompt = "> "
        self._sock = sock
        self._lock = lock
        self._use_empty_line_after_prompt = False
        self._last_user_line: str | None = None

    def precmd(self, line: str) -> str:
        s = line.strip()
        if not s:
            self._use_empty_line_after_prompt = True
        else:
            self._last_user_line = s
        return line

    def _send_line(self, line: str) -> None:
        data = (line + "\n").encode("utf-8")
        with self._lock:
            self._sock.sendall(data)
            self._use_empty_line_after_prompt = True

    def _do_move(self, dx: int, dy: int) -> None:
        self._send_line(f"move {dx} {dy}")

    def do_right(self, arg: str) -> None:
        self._do_move(1, 0)

    def do_left(self, arg: str) -> None:
        self._do_move(-1, 0)

    def do_up(self, arg: str) -> None:
        self._do_move(0, 1)

    def do_down(self, arg: str) -> None:
        self._do_move(0, -1)

    def do_addmon(self, arg: str) -> None:
        args = shlex.split(arg)
        try:
            params = parse_addmon(args)
        except InvalidCommand:
            print("Invalid arguments")
            return
        if params.name not in MONSTERS_LIST:
            print("Unknown monster")
            return
        payload = {
            "name": params.name,
            "hello": params.hello,
            "hp": params.hp,
            "x": params.pos[0],
            "y": params.pos[1],
        }
        self._send_line("addmon " + json.dumps(payload, ensure_ascii=False))

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

        if len(args) == 1:
            monster_name = args[0]
            weapon_name = "sword"
            damage = WEAPONS[weapon_name]
        elif len(args) == 3 and args[1] == "with":
            monster_name = args[0]
            weapon_name = args[2]
            if weapon_name not in WEAPONS:
                print("Unknown weapon")
                return
            damage = WEAPONS[weapon_name]
        else:
            print("Invalid arguments")
            return

        self._send_line(f"attack {monster_name} {damage} {weapon_name}")

    def emptyline(self) -> None:
        pass

    def do_EOF(self, arg: str) -> bool:
        return True

    def do_exit(self, arg: str) -> bool:
        return True


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python client.py <username> [host] [port]", file=sys.stderr)
        sys.exit(1)

    username = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 1337

    if not username or any(c.isspace() for c in username):
        print("username must be non-empty and contain no spaces", file=sys.stderr)
        sys.exit(1)

    print(f"<<< Welcome to Python-MUD {VERSION} >>>")

    buf = bytearray()
    lock = threading.Lock()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall((username + "\n").encode("utf-8"))

        first = read_framed(sock, buf)
        if first is None:
            print("Server closed connection during login")
            sys.exit(1)
        welcome_text = first
        if welcome_text.startswith("ERROR"):
            print(welcome_text)
            sys.exit(1)

        print(welcome_text.strip("\n"))

        cli = MUDClient(sock, lock)
        recv_thr = threading.Thread(
            target=receiver_thread,
            args=(cli, sock, buf, lock),
            daemon=True,
        )
        recv_thr.start()

        try:
            cli.cmdloop()
        finally:
            try:
                with lock:
                    sock.sendall(b"quit\n")
            except OSError:
                pass
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


if __name__ == "__main__":
    main()
