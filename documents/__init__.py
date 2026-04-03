from pathlib import Path
import os

DOC_DIR       = Path(__file__).resolve().parent
TEMPLATES_DIR = DOC_DIR / "templates"

# OUTPUT_DIR — نحاول داخل مجلد التطبيق أولاً
# إذا فشل (read-only عند التثبيت) → نستخدم AppData
_default_output = DOC_DIR / "output"
try:
    _default_output.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR = _default_output
except OSError:
    try:
        import sys
        if sys.platform == "win32":
            _appdata = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            _fallback = Path(_appdata) / "LOGIPORT" / "documents" / "generated"
        else:
            _fallback = Path.home() / ".local" / "share" / "LOGIPORT" / "documents" / "generated"
        _fallback.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR = _fallback
    except Exception:
        OUTPUT_DIR = _default_output   # آخر fallback