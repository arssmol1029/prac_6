from pathlib import Path
import zlib
import sys

data = zlib.decompress(Path(sys.argv[1]).read_bytes())
print(data)

