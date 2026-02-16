from pathlib import Path
import zlib
import sys

objects = sorted(Path(sys.argv[1]).glob('??/*'))
for object in objects:
    str_object = str(zlib.decompress(Path(object).read_bytes()))
    if "commit" in str_object:
        print(str_object)

