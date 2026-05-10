import sys

from mood.server.session import run_mood_server


if __name__ == "__main__":
    h = "0.0.0.0"
    p = 1337
    if len(sys.argv) >= 2:
        h = sys.argv[1]
    if len(sys.argv) >= 3:
        p = int(sys.argv[2])
    run_mood_server(h, p)
