from pathlib import Path

DOC_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = DOC_DIR / "templates"   # ← داخل documents/
OUTPUT_DIR = DOC_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
