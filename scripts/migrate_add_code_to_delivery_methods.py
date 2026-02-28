from sqlalchemy import text
from database.models import get_session_local

def column_exists(session, table_name, column_name):
    result = session.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
    return any(r["name"] == column_name for r in result)

def main():
    SessionLocal = get_session_local()

    with SessionLocal() as s:
        print("🔍 Checking delivery_methods schema...")

        if not column_exists(s, "delivery_methods", "code"):
            print("➕ Adding column 'code'...")
            s.execute(text("ALTER TABLE delivery_methods ADD COLUMN code TEXT"))
            s.commit()
        else:
            print("✔ Column 'code' already exists.")

        # تعبئة code للقيم الحالية إذا كانت فارغة
        rows = s.execute(text("SELECT id, name_en FROM delivery_methods")).mappings().all()

        for r in rows:
            code = (r["name_en"] or f"DM{r['id']}").upper().replace(" ", "_")
            s.execute(
                text("UPDATE delivery_methods SET code=:code WHERE id=:id AND code IS NULL"),
                {"code": code, "id": r["id"]}
            )

        s.commit()

        print("🔒 Creating unique index if not exists...")
        s.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_delivery_methods_code
            ON delivery_methods(code)
        """))
        s.commit()

        print("✅ Migration completed successfully.")

if __name__ == "__main__":
    main()