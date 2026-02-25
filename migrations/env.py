"""
migrations/env.py — LOGIPORT
==============================
بيئة Alembic المخصصة للمشروع.

الميزات:
  - يقرأ مسار DB ديناميكياً من database.db_utils.get_db_path()
    (يحترم db_path المخصص في الإعدادات)
  - يستخدم Base.metadata من models لـ autogenerate
  - يدعم كلا الوضعين: offline و online
  - يُفعّل PRAGMA foreign_keys = ON في كل اتصال SQLite
  - يتجاهل جداول Alembic الداخلية في المقارنة
"""
from __future__ import annotations

import sys
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, event, text
from sqlalchemy.engine import Connection

from alembic import context

# ── إضافة مسار المشروع لـ sys.path ──────────────────────────────────────────
# هذا يضمن أن imports مثل `from database.models import Base` تعمل
# سواء شغّلنا alembic من مجلد المشروع أو من أي مكان آخر
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

# تفعيل logging من alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── استيراد Base و جميع Models ───────────────────────────────────────────────
# يجب استيراد كل الـ models هنا حتى يراها autogenerate
from database.models import Base  # noqa: F401 — registers all models
import database.models  # noqa: F401 — ensures all submodules are imported

target_metadata = Base.metadata


# ── DB URL الديناميكي ─────────────────────────────────────────────────────────

def get_database_url() -> str:
    """
    يبني SQLAlchemy URL من مسار DB الفعلي.
    يحترم db_path المخصص في settings.json إن وجد،
    وإلا يستخدم المسار الافتراضي (CWD/logiport.db).
    """
    try:
        from database.db_utils import get_db_path
        db_path = get_db_path()
    except Exception:
        # fallback آمن لو فشل استيراد المشروع
        db_path = Path.cwd() / "logiport.db"

    return f"sqlite:///{db_path}"


def _configure_sqlite_pragmas(connection, _branch_point):
    """يُفعّل PRAGMA foreign_keys في كل اتصال SQLite."""
    connection.execute(text("PRAGMA foreign_keys = ON"))


def include_object(obj, name, type_, reflected, compare_to):
    """
    يُخبر autogenerate بماذا يتجاهل.
    - يتجاهل جدول alembic_version الداخلي
    - يتجاهل أي جداول مؤقتة تبدأ بـ tmp_ أو _
    """
    if type_ == "table":
        if name in ("alembic_version",):
            return False
        if name.startswith("tmp_") or name.startswith("_"):
            return False
    return True


# ── Offline mode (بدون اتصال DB فعلي — يولّد SQL فقط) ───────────────────────

def run_migrations_offline() -> None:
    """
    يولّد ملفات SQL بدون اتصال DB.
    مفيد للـ review أو التطبيق اليدوي.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_as_batch=True,   # ← مطلوب لـ SQLite (لا يدعم ALTER TABLE مباشرة)
        compare_type=True,       # ← يكتشف تغييرات أنواع الأعمدة
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (اتصال DB حقيقي) ─────────────────────────────────────────────

def run_migrations_online() -> None:
    """
    يُطبّق الـ migrations مباشرة على DB.
    """
    url = get_database_url()

    # بنى engine مؤقت لـ alembic (مستقل عن engine التطبيق)
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # لا connection pooling — كل migration يفتح/يغلق
    )

    with connectable.connect() as connection:
        # تفعيل PRAGMA foreign_keys لكل اتصال SQLite
        event.listen(connectable, "connect", _configure_sqlite_pragmas)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,    # ← مطلوب لـ SQLite
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry Point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
