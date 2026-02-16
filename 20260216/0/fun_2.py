from pathlib import Path
import sys

objects = sorted(Path(sys.argv[1]).glob('**/*'))
for object in objects:
    print(object)

