import sys
from os.path import dirname

BASE_DIR = dirname(dirname(dirname(dirname(__file__))))
print BASE_DIR
sys.path.append(BASE_DIR)
