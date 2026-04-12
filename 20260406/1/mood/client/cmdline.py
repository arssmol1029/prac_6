import json
import readline
import shlex
import cmd
import socket
import sys
import threading

from mood.common.addmon import parse_addmon
from mood.common.constants import (
    ADDMON_PARAMS,
    MONSTERS_LIST,
    WEAPONS,
    WEAPON_NAMES,
)
from mood.common.framing import read_framed
from mood.common.models import InvalidCommand
from mood.common.sayall import parse_sayall


def emit_server_message(cmdline: "MUDClient", text: str, lock: threading.Lock) -> None:
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
                tail = readline.get_line_buffer()
                line = f"\n[connection closed]\n{cmdline.prompt}{tail}"
                sys.stdout.write(line)
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

    def do_sayall(self, arg: str) -> None:
        try:
            msg = parse_sayall(arg)
        except InvalidCommand:
            print("Invalid arguments")
            return
        self._send_line("sayall " + json.dumps(msg, ensure_ascii=False))

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
