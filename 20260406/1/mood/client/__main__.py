import socket
import sys
import threading

from mood.client.cmdline import MUDClient, receiver_thread
from mood.common.constants import VERSION
from mood.common.framing import read_framed


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "usage: python3 -m mood.client <username> [host] [port]",
            file=sys.stderr,
        )
        sys.exit(1)

    username = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 1337

    if not username or any(c.isspace() for c in username):
        print("username must be non-empty and contain no spaces", file=sys.stderr)
        sys.exit(1)

    print(f"<<< Welcome to MOOD {VERSION} >>>")

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
