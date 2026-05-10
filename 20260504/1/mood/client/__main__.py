import socket
import sys
import threading

from mood.client.cmdline import MUDClient, receiver_thread
from mood.common.constants import VERSION
from mood.common.framing import read_framed


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="MOOD MUD Client")
    parser.add_argument("username", help="Username for the game")
    parser.add_argument("host", nargs="?", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("port", nargs="?", type=int, default=1337, help="Server port (default: 1337)")
    parser.add_argument("--file", help="Read commands from file instead of interactive input")
    
    args = parser.parse_args()
    
    username = args.username
    host = args.host
    port = args.port
    file_path = args.file

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
            daemon=False,
        )
        recv_thr.start()

        if file_path:
            cli.set_file_mode(True)
            try:
                if not file_path.endswith('.mood'):
                    print(f"Warning: File extension should be '.mood', but got '{file_path}'", file=sys.stderr)
                
                with open(file_path, 'r') as f:
                    commands = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                
                import time
                for command in commands:
                    if command.lower() == 'quit':
                        break
                    cli.onecmd(command)
                    time.sleep(1)
                
                time.sleep(0.5)
                
            except FileNotFoundError:
                print(f"Error: File '{file_path}' not found", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"Error reading file: {e}", file=sys.stderr)
                sys.exit(1)
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
                sock.close()
        else:
            try:
                cli.cmdloop()
            except KeyboardInterrupt:
                print("\nGoodbye!")
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
