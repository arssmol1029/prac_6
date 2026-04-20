import socket


def sqrootnet(coeffs: str, s: socket.socket) -> str:
    s.sendall((coeffs + "\n").encode())
    return s.recv(128).decode().strip()


if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("localhost", 1337))
        while inp := input("Enter coefficients: "):
            print(sqrootnet(inp, s))
