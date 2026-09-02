import sys
from pathlib import Path

UI_ROOT = Path(__file__).parents[1]
if str(UI_ROOT) not in sys.path:
    sys.path.insert(0, str(UI_ROOT))
