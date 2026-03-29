import json
import shlex
import cmd
import socket
import sys
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


class MUDClient(cmd.Cmd):
    def __init__(self, sock: socket.socket):
        super().__init__()
        self.prompt = "> "
        self._sock = sock
        self._r = sock.makefile("r", encoding="utf-8", newline="\n")
        self._w = sock.makefile("w", encoding="utf-8", newline="\n")

    def _send_recv(self, line: str) -> dict:
        self._w.write(line + "\n")
        self._w.flush()
        raw = self._r.readline()
        if not raw:
            raise ConnectionError("server closed connection")
        return json.loads(raw)

    def _do_move(self, dx: int, dy: int) -> None:
        data = self._send_recv(f"move {dx} {dy}")
        if data.get("kind") != "move":
            return
        x, y = data["x"], data["y"]
        print(f"Moved to ({x}, {y})")
        m = data.get("monster")
        if m:
            print(cowsay(message=m["hello"], cow=m["cow"]))

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
        line = "addmon " + json.dumps(payload, ensure_ascii=False)
        data = self._send_recv(line)
        if data.get("kind") != "addmon":
            return
        x, y = data["x"], data["y"]
        print(f"Added monster to ({x}, {y}) saying {params.hello}")
        if data.get("replaced"):
            print("Replaced the old monster")

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
            damage = WEAPONS["sword"]
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

        data = self._send_recv(f"attack {monster_name} {damage}")
        if data.get("kind") == "no_monster":
            print(f"No {data['name']} here")
            return
        if data.get("kind") != "attack":
            return
        name = data["name"]
        dealt = data["dealt"]
        remaining = data["remaining"]
        print(f"Attacked {name},  damage {dealt} hp")
        if remaining > 0:
            print(f"{name} now has {remaining} hp")
        else:
            print(f"{name} died")

    def emptyline(self) -> None:
        pass

    def do_EOF(self, arg: str) -> bool:
        return True

    def do_exit(self, arg: str) -> bool:
        return True


def main():
    host = "localhost" if len(sys.argv) < 2 else sys.argv[1]
    port = 1337 if len(sys.argv) < 3 else int(sys.argv[2])

    print(f"<<< Welcome to Python-MUD {VERSION} >>>")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        cli = MUDClient(s)
        try:
            cli.cmdloop()
        finally:
            try:
                cli._w.write("quit\n")
                cli._w.flush()
                cli._r.readline()
            except OSError:
                pass


if __name__ == "__main__":
    main()
