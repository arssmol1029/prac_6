import shlex

while line := input():
    print(shlex.join(shlex.split(line)))
