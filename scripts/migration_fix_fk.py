#!/usr/bin/env python3
"""
migration_fix_fk.py
===================
يُصلح مشكلتين في logiport.db:

  1. transaction_items.FK  → كان يشير لـ transactions_OLD (غير موجود)
  2. transaction_entries.FK → نفس المشكلة
  → CASCADE لم يكن يعمل قط (خطأ من عملية migration قديمة)

  3. transaction_last_number → كان 260009 رغم أن أعلى رقم فعلي 260006
  → المعاملة التالية كانت ستكون 260010 بدل 260007

الاستخدام:
  python3 migration_fix_fk.py --db path/to/logiport.db
  python3 migration_fix_fk.py  # يستخدم logiport.db في نفس المجلد
"""

import sqlite3
import shutil
import sys
import re
from pathlib import Path
from datetime import datetime


def run_migration(db_path: str):
    path = Path(db_path)
    if not path.exists():
        print(f"❌ DB not found: {db_path}")
        sys.exit(1)

    # نسخة احتياطية تلقائية
    backup = path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy(path, backup)
    print(f"✅ Backup created: {backup.name}")

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    # ── 1. إصلاح FKs ──────────────────────────────────────────────
    print("\n[1/2] Fixing broken FK references (transactions_old → transactions)...")

    conn.executescript("""
PRAGMA foreign_keys = OFF;

-- Fix transaction_items
CREATE TABLE transaction_items_new (
    id                INTEGER       NOT NULL,
    transaction_id    INTEGER       NOT NULL,
    entry_id          INTEGER,
    entry_item_id     INTEGER,
    material_id       INTEGER       NOT NULL,
    packaging_type_id INTEGER,
    quantity          FLOAT         NOT NULL,
    gross_weight_kg   FLOAT,
    net_weight_kg     FLOAT,
    pricing_type_id   INTEGER,
    unit_price        NUMERIC(12,4) NOT NULL,
    currency_id       INTEGER,
    line_total        NUMERIC(12,4),
    origin_country_id INTEGER,
    source_type       VARCHAR(16),
    is_manual         BOOLEAN       NOT NULL,
    notes             TEXT,
    created_by_id     INTEGER,
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_id     INTEGER,
    updated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transport_ref     TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY (transaction_id)    REFERENCES transactions (id)    ON DELETE CASCADE,
    FOREIGN KEY (entry_id)          REFERENCES entries (id)         ON DELETE SET NULL,
    FOREIGN KEY (entry_item_id)     REFERENCES entry_items (id)     ON DELETE SET NULL,
    FOREIGN KEY (material_id)       REFERENCES materials (id)       ON DELETE RESTRICT,
    FOREIGN KEY (packaging_type_id) REFERENCES packaging_types (id) ON DELETE RESTRICT,
    FOREIGN KEY (pricing_type_id)   REFERENCES pricing_types (id)   ON DELETE RESTRICT,
    FOREIGN KEY (currency_id)       REFERENCES currencies (id)      ON DELETE RESTRICT,
    FOREIGN KEY (origin_country_id) REFERENCES countries (id)       ON DELETE RESTRICT,
    FOREIGN KEY (created_by_id)     REFERENCES users (id),
    FOREIGN KEY (updated_by_id)     REFERENCES users (id)
);
INSERT INTO transaction_items_new SELECT * FROM transaction_items;
DROP TABLE transaction_items;
ALTER TABLE transaction_items_new RENAME TO transaction_items;

-- Fix transaction_entries
CREATE TABLE transaction_entries_new (
    id             INTEGER NOT NULL,
    transaction_id INTEGER NOT NULL,
    entry_id       INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_transaction_entry UNIQUE (transaction_id, entry_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE,
    FOREIGN KEY (entry_id)       REFERENCES entries (id)      ON DELETE RESTRICT
);
INSERT INTO transaction_entries_new SELECT * FROM transaction_entries;
DROP TABLE transaction_entries;
ALTER TABLE transaction_entries_new RENAME TO transaction_entries;

PRAGMA foreign_keys = ON;
""")

    # التحقق
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transaction_items'")
    ddl = cur.fetchone()[0]
    if 'transactions_old' in ddl:
        print("   ❌ FAILED — still references transactions_old")
    else:
        print("   ✅ transaction_items FK fixed")

    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transaction_entries'")
    ddl2 = cur.fetchone()[0]
    if 'transactions_old' in ddl2:
        print("   ❌ FAILED — still references transactions_old")
    else:
        print("   ✅ transaction_entries FK fixed")

    # ── 2. مزامنة العداد ───────────────────────────────────────────
    print("\n[2/2] Syncing transaction_last_number with actual DB data...")

    cur.execute("SELECT transaction_no FROM transactions")
    rows = [r[0] for r in cur.fetchall()]

    max_num = 0
    for tx_no in rows:
        if not tx_no or any(c in str(tx_no) for c in ('/', '-', ' ')):
            continue
        digits = re.sub(r'\D', '', str(tx_no))
        if digits and len(digits) <= 9:
            try:
                n = int(digits)
                if n > max_num:
                    max_num = n
            except ValueError:
                pass

    cur.execute("SELECT value FROM app_settings WHERE key='transaction_last_number'")
    old_val = cur.fetchone()
    old_num = int(old_val[0]) if old_val else 0

    cur.execute("UPDATE app_settings SET value=? WHERE key='transaction_last_number'",
                (str(max_num),))
    conn.commit()

    print(f"   Old value: {old_num}")
    print(f"   New value: {max_num}  (max numeric found in DB)")
    print(f"   Next transaction will be: {max_num + 1}")
    if old_num > max_num:
        saved = old_num - max_num
        print(f"   ✅ Recovered {saved} 'lost' number(s)")

    conn.close()
    print(f"\n✅ Migration complete → {path.name}")
    print(f"   Backup at: {backup.name}")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "logiport.db"
    run_migration(db)