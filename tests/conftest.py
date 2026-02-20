"""
tests/conftest.py
=================
Shared pytest fixtures — in-memory SQLite, no production DB touched.
"""
import pytest
from datetime import date
from unittest.mock import patch
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session


# ─── Engine (session-scoped) ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    from database.models import Base
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    # Enable FK enforcement
    @event.listens_for(engine, "connect")
    def set_fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    # Seed a default user so audit FK (created_by_id=1) never fails
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO users (id, username, password, is_active, created_at, updated_at)
            VALUES (1, 'test_user', 'hash', 1,
                    datetime('now'), datetime('now'))
        """))
        # app_settings is not an ORM model — create it manually
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key         TEXT NOT NULL UNIQUE,
                value       TEXT,
                category    TEXT,
                description TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # Seed numbering defaults
        conn.execute(text("""
            INSERT OR IGNORE INTO app_settings (key, value, category)
            VALUES
                ('transaction_last_number', '0',  'numbering'),
                ('transaction_prefix',      'T',  'numbering')
        """))
        # Seed a second user (id=2) for tests that use user_id=2
        conn.execute(text("""
            INSERT OR IGNORE INTO users (id, username, password, is_active, created_at, updated_at)
            VALUES (2, 'test_user2', 'hash2', 1,
                    datetime('now'), datetime('now'))
        """))

    return engine


# ─── Per-test session (rolled back) ──────────────────────────────────────────

@pytest.fixture
def db_session(db_engine):
    """Each test gets its own transaction that is rolled back on teardown."""
    connection = db_engine.connect()
    # Use savepoint so we can rollback without losing the seeded user
    nested = connection.begin_nested()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Restart the savepoint after any commit inside CRUD
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            connection.execute(text("SAVEPOINT test_savepoint"))

    yield session

    session.close()
    nested.rollback()
    connection.close()


# ─── session_factory for CRUD patching ───────────────────────────────────────

@pytest.fixture
def session_factory(db_session):
    """
    Returns lambda → db_session so CRUD calls hit the in-memory DB.

    Replaces session.commit() with session.flush() so savepoints stay alive
    and objects remain attached after CRUD operations (avoids DetachedInstanceError).
    """
    original_commit = db_session.commit
    db_session.commit = db_session.flush
    # Mark this session as shared (so BaseCRUD_V5 doesn't close it)
    db_session._is_shared_test_session = True
    yield lambda: db_session
    db_session._is_shared_test_session = False
    db_session.commit = original_commit


# ─── Model factories ─────────────────────────────────────────────────────────

@pytest.fixture
def make_client(db_session):
    from database.models.client import Client
    _n = [0]
    def _f(name_ar="عميل", name_en="Client", **kw):
        _n[0] += 1
        if "code" not in kw:
            kw["code"] = f"C{_n[0]:04d}"
        c = Client(name_ar=f"{name_ar} {_n[0]}", name_en=f"{name_en} {_n[0]}", **kw)
        db_session.add(c)
        db_session.flush()
        return c
    return _f


@pytest.fixture
def make_company(db_session):
    from database.models.company import Company
    from database.models.client import Client
    _n = [0]
    _owner = [None]  # lazy-created shared owner client for companies

    def _get_owner():
        if _owner[0] is None:
            _n[0] += 1
            c = Client(name_ar="مالك الشركة", name_en="Company Owner",
                       code=f"OWN{_n[0]:04d}")
            db_session.add(c)
            db_session.flush()
            _owner[0] = c
        return _owner[0]

    def _f(name_ar="شركة", name_en="Company", owner_client_id=None, **kw):
        _n[0] += 1
        if owner_client_id is None:
            owner_client_id = _get_owner().id
        c = Company(
            name_ar=f"{name_ar} {_n[0]}",
            name_en=f"{name_en} {_n[0]}",
            owner_client_id=owner_client_id,
            **kw,
        )
        db_session.add(c)
        db_session.flush()
        return c
    return _f


@pytest.fixture
def make_material(db_session):
    from database.models.material import Material
    from database.models.material_type import MaterialType
    _n = [0]
    _mtype = [None]

    def _get_type():
        if _mtype[0] is None:
            mt = MaterialType(name_ar="نوع", name_en="Type", name_tr="Tür")
            db_session.add(mt)
            db_session.flush()
            _mtype[0] = mt
        return _mtype[0]

    def _f(name_ar="مادة", name_en="Material", **kw):
        _n[0] += 1
        if "code" not in kw:
            kw["code"] = f"MAT{_n[0]:04d}"
        if "material_type_id" not in kw:
            kw["material_type_id"] = _get_type().id
        m = Material(
            name_ar=f"{name_ar} {_n[0]}",
            name_en=f"{name_en} {_n[0]}",
            **kw,
        )
        db_session.add(m)
        db_session.flush()
        return m
    return _f


@pytest.fixture
def make_currency(db_session):
    from database.models.currency import Currency
    _n = [0]
    def _f(code="USD", name_ar="دولار", name_en="Dollar", name_tr="Dolar", **kw):
        _n[0] += 1
        c = Currency(
            code=f"{code}{_n[0]}",
            name_ar=f"{name_ar} {_n[0]}",
            name_en=f"{name_en} {_n[0]}",
            name_tr=f"{name_tr} {_n[0]}",
            **kw,
        )
        db_session.add(c)
        db_session.flush()
        return c
    return _f


@pytest.fixture
def make_transaction(db_session, make_client, make_company, make_currency):
    from database.models.transaction import Transaction
    _n = [0]
    def _f(**kw):
        _n[0] += 1
        client   = kw.pop("client",   None) or make_client()
        exporter = kw.pop("exporter", None) or make_company(name_en="Exporter")
        importer = kw.pop("importer", None) or make_company(name_en="Importer")
        currency = kw.pop("currency", None) or make_currency()
        t = Transaction(
            transaction_no=kw.pop("transaction_no", f"T{_n[0]:04d}"),
            transaction_date=kw.pop("transaction_date", date.today()),
            transaction_type=kw.pop("transaction_type", "export"),
            client_id=client.id,
            exporter_company_id=exporter.id,
            importer_company_id=importer.id,
            currency_id=currency.id,
            **kw,
        )
        db_session.add(t)
        db_session.flush()
        return t
    return _f


@pytest.fixture
def make_entry(db_session, make_client):
    from database.models.entry import Entry
    def _f(owner_client_id=None, entry_date=None, **kw):
        if owner_client_id is None:
            owner_client_id = make_client().id
        e = Entry(
            owner_client_id=owner_client_id,
            entry_date=entry_date or date.today(),
            **kw,
        )
        db_session.add(e)
        db_session.flush()
        return e
    return _f