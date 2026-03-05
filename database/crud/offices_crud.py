"""
database/crud/offices_crud.py
==============================
CRUD عمليات المكاتب.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any

from database.models import get_session_local, Office
from database.crud.base_crud import BaseCRUD
from core.translator import TranslationManager


class OfficesCRUD(BaseCRUD):

    def __init__(self):
        super().__init__(Office, get_session_local)

    # ── Reads ────────────────────────────────────────────────────────────────

    def get_all(self, active_only: bool = False,
                language: Optional[str] = None) -> List[Dict[str, Any]]:
        lang = language or TranslationManager.get_instance().get_current_language()
        with self.get_session() as session:
            q = session.query(Office).order_by(Office.sort_order, Office.id)
            if active_only:
                q = q.filter(Office.is_active == True)
            return [self._to_dict(o, lang) for o in q.all()]

    def get_by_id(self, office_id: int) -> Optional[Office]:
        with self.get_session() as session:
            return session.query(Office).filter(Office.id == office_id).first()

    def get_by_code(self, code: str) -> Optional[Office]:
        with self.get_session() as session:
            return session.query(Office).filter(Office.code == code).first()

    # ── Writes ───────────────────────────────────────────────────────────────

    def add(self, code: str, name_ar: str, name_en: str = "", name_tr: str = "",
            country: str = "", city: str = "", notes: str = "",
            sort_order: int = 0, user_id: int = None) -> Optional[Office]:
        with self.get_session() as session:
            office = Office(
                code=code.strip().upper(),
                name_ar=name_ar.strip(),
                name_en=name_en.strip() or None,
                name_tr=name_tr.strip() or None,
                country=country.strip().upper() or None,
                city=city.strip() or None,
                notes=notes.strip() or None,
                sort_order=sort_order,
                is_active=True,
            )
            session.add(office)
            session.flush()
            self._log(session, "create", office.id, None, self._snap(office), user_id)
            session.commit()
            return office

    def update(self, office_id: int, data: Dict[str, Any],
               user_id: int = None) -> Optional[Office]:
        with self.get_session() as session:
            office = session.query(Office).filter(Office.id == office_id).first()
            if not office:
                return None
            before = self._snap(office)
            allowed = {"code", "name_ar", "name_en", "name_tr",
                       "country", "city", "notes", "sort_order", "is_active"}
            for k, v in data.items():
                if k in allowed:
                    if k == "code" and isinstance(v, str):
                        v = v.strip().upper()
                    setattr(office, k, v)
            self._log(session, "update", office_id, before, self._snap(office), user_id)
            session.commit()
            return office

    def delete(self, office_id: int, user_id: int = None) -> bool:
        with self.get_session() as session:
            office = session.query(Office).filter(Office.id == office_id).first()
            if not office:
                return False
            before = self._snap(office)
            session.delete(office)
            self._log(session, "delete", office_id, before, None, user_id)
            session.commit()
            return True

    def toggle_active(self, office_id: int, user_id: int = None) -> Optional[Office]:
        with self.get_session() as session:
            office = session.query(Office).filter(Office.id == office_id).first()
            if not office:
                return None
            before = self._snap(office)
            office.is_active = not office.is_active
            self._log(session, "update", office_id, before, self._snap(office), user_id)
            session.commit()
            return office

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _snap(self, o: Office) -> dict:
        return {
            "id": o.id, "code": o.code, "name_ar": o.name_ar,
            "name_en": o.name_en, "country": o.country,
            "city": o.city, "is_active": o.is_active,
        }

    def _to_dict(self, o: Office, lang: str) -> Dict[str, Any]:
        return {
            "id":        o.id,
            "code":      o.code,
            "name":      o.get_name(lang),
            "name_ar":   o.name_ar,
            "name_en":   o.name_en,
            "name_tr":   o.name_tr,
            "country":   o.country,
            "city":      o.city,
            "is_active": o.is_active,
            "sort_order":o.sort_order,
            "notes":     o.notes,
        }

    def _log(self, session, action, record_id, before, after, user_id):
        try:
            import json
            from database.models.audit_log import AuditLog
            from database.db_utils import utc_now
            session.add(AuditLog(
                user_id=user_id,
                action=action,
                table_name="offices",
                record_id=record_id,
                before_data=json.dumps(before, ensure_ascii=False) if before else None,
                after_data=json.dumps(after, ensure_ascii=False) if after else None,
                timestamp=utc_now(),
            ))
        except Exception:
            pass
