"""
Тесты клиента без сервера
"""

import json
import threading
import unittest
from unittest.mock import MagicMock, call, patch

from mood.client.cmdline import MUDClient
from mood.common.constants import MONSTERS_LIST


def _make_client(mock_sock: MagicMock) -> MUDClient:
    lock = threading.Lock()
    cli = MUDClient(mock_sock, lock)
    cli.use_rawinput = False
    cli.completekey = None
    cli.stdout = MagicMock()
    return cli


def _wire_lines(mock_sock: MagicMock) -> list[str]:
    """Все полезные нагрузки, переданные в sendall, как строки с \\n."""
    out: list[str] = []
    for c in mock_sock.sendall.call_args_list:
        (payload,) = c[0]
        out.append(payload.decode("utf-8"))
    return out


class TestMovementUserInputToProtocol(unittest.TestCase):
    """Пользователь: right / down. Протокол: ``move 1 0`` и ``move 0 -1`` (два направления)."""

    def setUp(self) -> None:
        self.mock_sock = MagicMock()
        self.cli = _make_client(self.mock_sock)
        self.stdin = MagicMock()
        self.cli.stdin = self.stdin

    def test_cmdloop_stdin_mock_sequence_two_directions(self) -> None:
        self.stdin.readline = MagicMock(
            side_effect=[
                "right\n",
                "down\n",
                "exit\n",
            ]
        )
        self.cli.cmdloop(intro="")
        self.assertEqual(
            _wire_lines(self.mock_sock),
            ["move 1 0\n", "move 0 -1\n"],
        )

    def test_onecmd_right_and_down_match_protocol(self) -> None:
        self.mock_sock.reset_mock()
        self.cli.onecmd("right")
        self.cli.onecmd("down")
        self.mock_sock.sendall.assert_has_calls(
            [call(b"move 1 0\n"), call(b"move 0 -1\n")],
        )


class TestAddmonUserInputToProtocol(unittest.TestCase):
    """Пользователь: addmon <shlex>. Протокол: ``addmon`` + JSON."""

    def setUp(self) -> None:
        self.m = MONSTERS_LIST[0]
        self.mock_sock = MagicMock()
        self.cli = _make_client(self.mock_sock)

    def test_addmon_two_parameter_sets(self) -> None:
        self.cli.onecmd(
            f'addmon {self.m} hello "alpha" hp 7 coords 1 0',
        )
        self.cli.onecmd(
            f"addmon {self.m} hello beta hp 22 coords 4 9",
        )
        lines = _wire_lines(self.mock_sock)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("addmon "))
        self.assertTrue(lines[1].startswith("addmon "))
        p0 = json.loads(lines[0].split(" ", 1)[1])
        p1 = json.loads(lines[1].split(" ", 1)[1])
        self.assertEqual(
            p0,
            {"name": self.m, "hello": "alpha", "hp": 7, "x": 1, "y": 0},
        )
        self.assertEqual(
            p1,
            {"name": self.m, "hello": "beta", "hp": 22, "x": 4, "y": 9},
        )

    def test_addmon_invalid_incomplete_no_send(self) -> None:
        with patch("builtins.print") as mock_print:
            self.cli.onecmd(f"addmon {self.m} hello only hp")
        self.mock_sock.sendall.assert_not_called()
        mock_print.assert_called()

    def test_addmon_unknown_monster_no_send(self) -> None:
        with patch("builtins.print") as mock_print:
            self.cli.onecmd(
                'addmon __not_a_real_cow__ hello x hp 1 coords 0 0',
            )
        self.mock_sock.sendall.assert_not_called()
        mock_print.assert_called()


class TestStdinToSendallChain(unittest.TestCase):
    """Одна цепочка: последовательные ``readline`` → ``cmdloop`` → несколько ``sendall``."""

    def test_movement_then_addmon_via_mocked_stdin(self) -> None:
        m = MONSTERS_LIST[0]
        mock_sock = MagicMock()
        cli = _make_client(mock_sock)
        stdin = MagicMock()
        stdin.readline = MagicMock(
            side_effect=[
                "left\n",
                "up\n",
                f'addmon {m} hello "chain" hp 3 coords 0 1\n',
                "exit\n",
            ]
        )
        cli.stdin = stdin
        cli.cmdloop(intro="")
        self.assertEqual(
            _wire_lines(mock_sock),
            [
                "move -1 0\n",
                "move 0 1\n",
                "addmon "
                + json.dumps(
                    {"name": m, "hello": "chain", "hp": 3, "x": 0, "y": 1},
                    ensure_ascii=False,
                )
                + "\n",
            ],
        )
