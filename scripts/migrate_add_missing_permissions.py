"""
scripts/migrate_add_missing_permissions.py
==========================================
يضيف الصلاحيات الناقصة (55-65) إلى DB الموجودة.

الصلاحيات المضافة:
  55 - delete_client
  56 - add_company
  57 - edit_company
  58 - delete_company
  59 - add_pricing
  60 - edit_pricing
  61 - delete_pricing
  62 - add_transaction
  63 - edit_transaction
  64 - delete_transaction
  65 - close_transaction

آمن تماماً: يستخدم INSERT OR IGNORE — لا يمس البيانات الموجودة.
يُشغَّل مرة واحدة، وإذا شُغِّل مجدداً لا يفعل شيئاً.

الاستخدام:
    python scripts/migrate_add_missing_permissions.py
"""

import sys
import sqlite3
from pathlib import Path

# أضف جذر المشروع لمسار الاستيراد
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


NEW_PERMISSIONS = [
    (55, "delete_client",      "Delete client",             "حذف عميل",           "Delete Client",       "Müşteriyi Sil",              "CLIENTS"),
    (56, "add_company",        "Add new company",           "إضافة شركة",         "Add Company",         "Şirket Ekle",                "COMPANIES"),
    (57, "edit_company",       "Edit company",              "تعديل شركة",         "Edit Company",        "Şirketi Düzenle",            "COMPANIES"),
    (58, "delete_company",     "Delete company",            "حذف شركة",           "Delete Company",      "Şirketi Sil",                "COMPANIES"),
    (59, "add_pricing",        "Add pricing record",        "إضافة تسعيرة",       "Add Pricing",         "Fiyatlandırma Ekle",         "PRICING"),
    (60, "edit_pricing",       "Edit pricing record",       "تعديل تسعيرة",       "Edit Pricing",        "Fiyatlandırmayı Düzenle",    "PRICING"),
    (61, "delete_pricing",     "Delete pricing record",     "حذف تسعيرة",         "Delete Pricing",      "Fiyatlandırmayı Sil",        "PRICING"),
    (62, "add_transaction",    "Create new transaction",    "إضافة معاملة",       "Add Transaction",     "İşlem Ekle",                 "TRANSACTIONS"),
    (63, "edit_transaction",   "Edit transaction",          "تعديل معاملة",       "Edit Transaction",    "İşlemi Düzenle",             "TRANSACTIONS"),
    (64, "delete_transaction", "Delete transaction",        "حذف معاملة",         "Delete Transaction",  "İşlemi Sil",                 "TRANSACTIONS"),
    (65, "close_transaction",  "Close/archive transaction", "إغلاق معاملة",       "Close Transaction",   "İşlemi Kapat",               "TRANSACTIONS"),
]

# الصلاحيات الإضافية لـ Admin و Manager
ADMIN_ROLE_ID    = 1
MANAGER_ROLE_ID  = 3

# IDs التي يجب أن يحصل عليها Manager من الصلاحيات الجديدة
MANAGER_NEW_PERMS = [
    55,       # delete_client
    56, 57,   # add/edit company (بدون delete)
    59, 60,   # add/edit pricing (بدون delete)
    62, 63,   # add/edit transaction (بدون delete/close)
]


def get_db_path() -> Path:
    """يجد مسار DB من db_utils أو يستخدم المسار الافتراضي."""
    try:
        from database.db_utils import get_db_path as _get
        return Path(_get())
    except Exception:
        # fallback: APPDATA/LOGIPORT/logiport.db
        import os
        if sys.platform == "win32":
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".local" / "share"
        return base / "LOGIPORT" / "logiport.db"


def run_migration(db_path: Path) -> None:
    if not db_path.exists():
        print(f"❌ DB غير موجودة: {db_path}")
        sys.exit(1)

    print(f"📂 DB: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        # 1) تحقق من وجود عمود category
        cols = {row[1] for row in cur.execute("PRAGMA table_info(permissions)").fetchall()}
        has_category = "category" in cols

        # 2) أضف الصلاحيات الناقصة
        added = 0
        skipped = 0
        for pid, code, desc, label_ar, label_en, label_tr, category in NEW_PERMISSIONS:
            exists = cur.execute("SELECT 1 FROM permissions WHERE id=?", (pid,)).fetchone()
            if exists:
                skipped += 1
                print(f"  ⏭️  [{pid}] {code} — موجودة مسبقاً")
                continue

            if has_category:
                cur.execute(
                    "INSERT OR IGNORE INTO permissions "
                    "(id, code, description, label_ar, label_en, label_tr, category) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (pid, code, desc, label_ar, label_en, label_tr, category)
                )
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO permissions "
                    "(id, code, description, label_ar, label_en, label_tr) "
                    "VALUES (?,?,?,?,?,?)",
                    (pid, code, desc, label_ar, label_en, label_tr)
                )
            added += 1
            print(f"  ✅ [{pid}] {code} — أضيفت")

        # 3) امنح Admin كل الصلاحيات الجديدة
        admin_granted = 0
        for pid, code, *_ in NEW_PERMISSIONS:
            exists = cur.execute(
                "SELECT 1 FROM role_permissions WHERE role_id=? AND permission_id=?",
                (ADMIN_ROLE_ID, pid)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                    (ADMIN_ROLE_ID, pid)
                )
                admin_granted += 1

        # 4) امنح Manager الصلاحيات المناسبة
        manager_granted = 0
        for pid in MANAGER_NEW_PERMS:
            exists = cur.execute(
                "SELECT 1 FROM role_permissions WHERE role_id=? AND permission_id=?",
                (MANAGER_ROLE_ID, pid)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                    (MANAGER_ROLE_ID, pid)
                )
                manager_granted += 1

        conn.commit()

    print()
    print("=" * 50)
    print(f"✅ الصلاحيات المضافة:          {added}")
    print(f"⏭️  الصلاحيات الموجودة مسبقاً: {skipped}")
    print(f"👑 ممنوحة لـ Admin:             {admin_granted}")
    print(f"👔 ممنوحة لـ Manager:           {manager_granted}")
    print("=" * 50)
    print()
    print("✅ Migration اكتمل. أعد تشغيل التطبيق لتفعيل التغييرات.")


if __name__ == "__main__":
    db_path = get_db_path()
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    run_migration(db_path)
