import sys
from cowsay import cowsay

print(cowsay(sys.argv[2], cow=sys.argv[1]))
