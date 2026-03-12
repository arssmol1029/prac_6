import cmd
import shlex
from pathlib import Path


class SizeCmd(cmd.Cmd):
    prompt = ">>"

    def do_size(self, arg):
        args = shlex.split(arg)
        for name in args:
            print(f"{name}: {Path(name).stat().st_size}")

    def complete_size(self, text, line, begidx, endidx):
        return [str(p) for p in Path("").glob(f"{text}*")]

    def do_EOF(self, arg):
        return 1


if __name__ == "__main__":
    SizeCmd().cmdloop()
