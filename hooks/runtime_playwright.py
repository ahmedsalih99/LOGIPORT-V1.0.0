import os
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
    browsers_path = base_path / ".local-browsers"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
