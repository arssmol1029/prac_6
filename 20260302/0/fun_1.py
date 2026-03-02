while line := input():
    args = line.split()
    print(args[0], len(args) - 1, args[1:])
