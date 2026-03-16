import sys
import socket

from cmd import Cmd


host = "localhost" if len(sys.argv) < 2 else sys.argv[1]
port = 1337 if len(sys.argv) < 3 else int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

    class ClientCmd(Cmd):
        def __init__(self):
            super().__init__()
            self.prompt = "> "

        def do_print(self, arg):
            s.sendall(("print " + arg + "\n").encode("utf-8"))
            print(s.recv(1024).rstrip().decode())

        def do_info(self, arg):
            s.sendall(("info " + arg + "\n").encode("utf-8"))
            print(s.recv(1024).rstrip().decode())

        def complete_info(self, text, line, begidx, endidx):
            args = []
            if "host".startswith(text):
                args.append("host")
            if "port".startswith(text):
                args.append("port")
            return args

        def do_EOF(self, arg):
            return 1

    s.connect((host, port))
    ClientCmd().cmdloop()
