"""Интеграционные тесты: клиент отправляет строки протокола, проверяются ответы сервера."""

import json
import multiprocessing
import socket
import time
import unittest
from typing import Any

from mood.common.constants import MONSTERS_LIST, WEAPONS
from mood.common.framing import read_framed, frame_text
from mood.server.session import run_mood_server


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_tcp_accepting(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last_err: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return
        except OSError as e:
            last_err = e
            time.sleep(0.05)
    raise RuntimeError(f"server not accepting on {host}:{port}: {last_err!r}")


class TestMoodServerClientCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.host = "127.0.0.1"
        self.port = _pick_free_port()
        self.proc = multiprocessing.Process(
            target=run_mood_server,
            args=(self.host, self.port),
        )
        self.proc.start()
        _wait_tcp_accepting(self.host, self.port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.buf = bytearray()
        self.sock.sendall(b"integration_user\n")
        welcome = read_framed(self.sock, self.buf)
        self.assertIsNotNone(welcome)
        assert welcome is not None
        self.assertFalse(
            welcome.startswith("ERROR"),
            msg=f"login failed: {welcome!r}",
        )

    def tearDown(self) -> None:
        try:
            self.sock.sendall(b"quit\n")
        except OSError:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()

        self.proc.terminate()
        self.proc.join(timeout=10.0)
        if self.proc.is_alive():
            self.proc.kill()
            self.proc.join(timeout=5.0)

    def _send_line(self, line: str) -> None:
        self.sock.sendall((line + "\n").encode("utf-8"))

    def _read_frame(self) -> str:
        text = read_framed(self.sock, self.buf)
        self.assertIsNotNone(text, msg="unexpected EOF before framed message")
        assert text is not None
        return text

    def _addmon_payload(self, **overrides: Any) -> dict[str, Any]:
        name = MONSTERS_LIST[0]
        base: dict[str, Any] = {
            "name": name,
            "hello": "MUD test hello",
            "hp": 10,
            "x": 1,
            "y": 0,
        }
        base.update(overrides)
        return base

    def test_addmon_broadcast(self) -> None:
        payload = self._addmon_payload()
        self._send_line("addmon " + json.dumps(payload, ensure_ascii=False))
        msg = self._read_frame()
        self.assertIn("placed monster", msg)
        self.assertIn(payload["name"], msg)
        self.assertIn("(1, 0)", msg)

    def test_move_encounter_monster_greets(self) -> None:
        payload = self._addmon_payload()
        self._send_line("addmon " + json.dumps(payload, ensure_ascii=False))
        self._read_frame()

        self._send_line("move 1 0")
        moved = self._read_frame()
        self.assertIn("Moved to (1, 0)", moved)

        greeting = self._read_frame()
        self.assertIn(payload["hello"], greeting)
        self.assertIn("< ", greeting)
        self.assertIn(" >", greeting)

    def test_attack_monster(self) -> None:
        payload = self._addmon_payload(hp=10)
        monster = str(payload["name"])
        self._send_line("addmon " + json.dumps(payload, ensure_ascii=False))
        self._read_frame()

        self._send_line("move 1 0")
        self._read_frame()
        self._read_frame()

        dmg = WEAPONS["sword"]
        weapon = "sword"
        self._send_line(f"attack {monster} {dmg} {weapon}")
        outcome = self._read_frame()
        self.assertIn("attacked", outcome)
        self.assertIn(monster, outcome)
        self.assertIn("killed the monster", outcome)


class TestFramingRoundTrip(unittest.TestCase):
    def test_read_framed_matches_frame_text(self) -> None:
        a, b = socket.socketpair()
        try:
            body = "проверка\nкадра"
            b.sendall(frame_text(body))
            buf = bytearray()
            self.assertEqual(read_framed(a, buf), body)
        finally:
            a.close()
            b.close()


if __name__ == "__main__":
    unittest.main()
