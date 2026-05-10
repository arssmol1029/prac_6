import socket


def frame_text(text: str) -> bytes:
    data = text.encode("utf-8")
    return str(len(data)).encode("ascii") + b"\n" + data


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
