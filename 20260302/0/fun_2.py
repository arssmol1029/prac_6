import shlex

while line := input():
    cmd, *args = shlex.split(line)
    print(cmd, len(args), args)
