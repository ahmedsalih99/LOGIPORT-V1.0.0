# مثال اختياري تضعه في database/models/utils.py
from contextlib import contextmanager
from database.models import get_session_local

@contextmanager
def db_session():
    SessionLocal = get_session_local()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
