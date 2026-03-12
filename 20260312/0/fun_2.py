import cmd
import shlex
from calendar import TextCalendar, Month


class SizeCmd(cmd.Cmd):
    prompt = ">>"

    def do_prmonth(self, arg):
        """Print a month's calendar."""
        args = shlex.split(arg)
        try:
            if len(args) != 2:
                raise
            year, month = int(args[0]), int(args[1])
        except Exception:
            print("Required two integer arguments: theyear, themonth")

        try:
            print(TextCalendar().prmonth(theyear=year, themonth=month))
        except Exception as e:
            print(f"Error: {str(e)}")

    def complite_prmonth(self, text, line, begidx, endidx):
        print("meow")
        return [month.name for month in Month if text in month.name]

    def do_pryear(self, arg):
        """Print a year's calendar."""
        args = shlex.split(arg)
        try:
            if len(args) != 1:
                raise
            year = int(args[0])
        except Exception:
            print("Required one integer arguments: theyear")

        try:
            print(TextCalendar().pryear(theyear=year))
        except Exception as e:
            print(f"Error: {str(e)}")

    def do_EOF(self, arg):
        return 1


if __name__ == "__main__":
    SizeCmd().cmdloop()
