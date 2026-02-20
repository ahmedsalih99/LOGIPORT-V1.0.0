#!/usr/bin/env python3
"""
scripts/cleanup_output_paths.py
================================
يُصلح المجلدات العشوائية في documents/output/ الناتجة عن أرقام معاملات
تحتوي على / أو \\ (مثل "26/27" التي أنشأت مجلدَين متداخلَين).

الاستخدام:
    python scripts/cleanup_output_paths.py           # dry-run (يعرض ما سيتغير)
    python scripts/cleanup_output_paths.py --fix     # تطبيق التغييرات فعلياً

ما يفعله:
    1. يمشي على output/{YYYY}/{MM}/ ويبحث عن مجلدات تعرف أنها transaction IDs
       لكن مكسورة (رقم قصير جداً = جزء من slash مثل "26" أو "27")
    2. يدمج الملفات إلى المسار الصحيح (مثلاً 26-27)
    3. يحذف المجلدات القديمة الفارغة بعد النقل
"""

import shutil
import sys
import re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_ROOT = Path(__file__).parent.parent / "documents" / "output"
DRY_RUN = "--fix" not in sys.argv


def _safe_tx(tx: str) -> str:
    return re.sub(r"[/\\\s]+", "-", tx.strip()) or "UNKNOWN"


def _looks_like_slash_fragment(name: str) -> bool:
    """
    يكتشف مجلداً يبدو أنه جزء من transaction_no تحتوي /
    مثل "26" التي هي بداية "26/27".
    أسماء المعاملات الصحيحة عادةً: T0001, 260006, T0009 ...
    """
    # إذا كان الاسم رقماً قصيراً (2 خانات) — يُرجَّح أنه شظية
    if re.fullmatch(r"\d{1,3}", name):
        return True
    return False


def process():
    moved = 0
    errors = 0
    skipped = 0

    for year_dir in sorted(OUTPUT_ROOT.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue

            # بحث عن مجلدات تبدو كشظايا slash
            for tx_dir in sorted(month_dir.iterdir()):
                if not tx_dir.is_dir():
                    continue
                if not _looks_like_slash_fragment(tx_dir.name):
                    continue

                # هذا المجلد يحتوي مجلدات فرعية تكون هي الجزء الثاني
                for frag2 in sorted(tx_dir.iterdir()):
                    if not frag2.is_dir():
                        continue

                    # اجمع الجزأين: "26" + "27" → "26-27"
                    merged_name = f"{tx_dir.name}-{frag2.name}"
                    merged_dir = month_dir / merged_name

                    print(f"\n[FOUND] Broken path: {tx_dir.relative_to(OUTPUT_ROOT)}/{frag2.name}")
                    print(f"         → Should be: {merged_dir.relative_to(OUTPUT_ROOT)}")

                    if DRY_RUN:
                        print("         (dry-run — pass --fix to apply)")
                        skipped += 1
                        continue

                    # انقل كل ما بداخل frag2 إلى merged_dir
                    try:
                        merged_dir.mkdir(parents=True, exist_ok=True)
                        for child in frag2.iterdir():
                            dest = merged_dir / child.name
                            if dest.exists():
                                print(f"         ⚠️  Skipping existing: {dest.name}")
                                continue
                            shutil.move(str(child), str(dest))
                            print(f"         Moved: {child.name}")
                        # احذف المجلدات الفارغة
                        try:
                            frag2.rmdir()
                        except OSError:
                            pass
                        try:
                            tx_dir.rmdir()
                        except OSError:
                            pass
                        moved += 1
                        print(f"         ✅ Done → {merged_dir.name}")
                    except Exception as e:
                        print(f"         ❌ Error: {e}")
                        errors += 1

    print()
    if DRY_RUN:
        print(f"Dry-run complete. {skipped} path(s) would be fixed.")
        print("Run with --fix to apply changes.")
    else:
        print(f"Done. {moved} path(s) fixed, {errors} error(s).")


if __name__ == "__main__":
    print(f"Output root: {OUTPUT_ROOT}")
    print(f"Mode: {'DRY-RUN' if DRY_RUN else 'FIXING'}")
    print("─" * 60)
    process()
