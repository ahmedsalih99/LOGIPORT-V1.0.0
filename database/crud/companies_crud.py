from typing import Optional, Dict, Any, Iterable, List

from database.models import get_session_local
from database.crud.base_crud_v5 import BaseCRUD_V5 as BaseCRUD
from database.models.company import Company, CompanyRoleLink


_MINIMAL_FIELDS = {
    "name_ar", "name_en", "name_tr",
    "address_ar", "address_en", "address_tr",
    "bank_info",
    "default_currency_id",
    "country_id",  # << أضف هذا السطر
    "notes",
}


class CompaniesCRUD(BaseCRUD):
    """
    CRUD مبسّط لتبويب الشركات (٩ حقول فقط):

      - name_ar, name_en, name_tr
      - address_ar, address_en, address_tr
      - bank_info
      - default_currency_id
      - notes

    ملاحظات:
      - أي مفاتيح إضافية في data يتم تجاهلها تلقائيًا (يُفلتر على أعمدة Company الحقيقية).
      - دعم اختياري للأدوار عبر role_ids (إن رغبت باستخدامه لاحقًا).
      - لا يفرض وجود مالك/بلد… إلخ. إذا كانت قاعدة البيانات تشترط owner_client_id NOT NULL،
        يجب تعديل المخطط (migration) ليصبح Nullable قبل استخدام هذا الـCRUD المبسّط.
    """

    model = Company

    def __init__(self):
        super().__init__(Company, get_session_local)

    # ---------------- Helpers ----------------
    @staticmethod
    def _model_columns_set() -> set:
        return set(getattr(Company, "__table__").c.keys())

    @classmethod
    def _filter_payload(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """يُرجع فقط المفاتيح التي تطابق أعمدة الجدول، مع أولوية لحقول الحد الأدنى."""
        if not data:
            return {}
        cols = cls._model_columns_set()
        # إعطاء الأولوية لحقول الحد الأدنى؛ لكن لا نمنع الحقول القانونية الأخرى لو مرّت
        allowed = (cols & set(data.keys()))
        if not allowed:
            return {}
        payload = {k: data.get(k) for k in allowed}
        return payload

    # ---------------- Create ----------------
    def add_company(
            self,
            data: Dict[str, Any],
            *,
            owner_client_id: int,
            role_ids: Optional[Iterable[int]] = None,
            user_id: Optional[int] = None
    ) -> Company:

        if not owner_client_id:
            raise ValueError("owner_client_id is required")

        payload = dict(data or {})
        payload = self._filter_payload(payload)

        # ✅ تأكد من إضافة owner_client_id
        payload["owner_client_id"] = owner_client_id

        # ✅ UPPERCASE للأسماء والعناوين
        for k in ("name_ar", "name_en", "name_tr",
                  "address_ar", "address_en", "address_tr"):
            v = payload.get(k)
            if isinstance(v, str) and v:
                if k.endswith("_tr"):
                    v = v.replace("i", "İ").replace("ı", "I")
                payload[k] = v.upper()

        # ✅ تدقيق
        cols = self._model_columns_set()
        if user_id is not None:
            if "created_by_id" in cols:
                payload["created_by_id"] = user_id
            if "updated_by_id" in cols:
                payload["updated_by_id"] = user_id

        SessionLocal = get_session_local()

        with SessionLocal() as s:
            obj = Company(**payload)
            s.add(obj)
            s.flush()

            # روابط الأدوار
            if role_ids:
                self._persist_roles(s, obj.id, role_ids)

            s.commit()
            s.refresh(obj)
            return obj

    # ---------------- Read ----------------
    def get_company(self, company_id: int) -> Optional[Company]:
        return self.get(company_id)

    def list_companies(self, *, order_by=None) -> List[Company]:
        return self.get_all(order_by=order_by)

    # ---------------- Update ----------------
    def update_company(
            self,
            company_id: int,
            data: Dict[str, Any],
            *,
            role_ids: Optional[Iterable[int]] = None,
            user_id: Optional[int] = None
    ) -> Optional[Company]:
        """
        يحدّث شركة قائمة بالحقول التسعة. أي مفاتيح زائدة تُهمل.
        - role_ids اختياري: إن مرّرته سيتم تطبيقه بأسلوب hard reset للروابط.
        """
        payload = dict(data or {})
        payload = self._filter_payload(payload)

        # ✅ UPPERCASE للاسم/العنوان (مع معالجة خفيفة للتركي)
        for k in ("name_ar", "name_en", "name_tr", "address_ar", "address_en", "address_tr"):
            v = payload.get(k)
            if isinstance(v, str) and v:
                if k.endswith("_tr"):
                    v = v.replace("i", "İ").replace("ı", "I")
                payload[k] = v.upper()

        cols = self._model_columns_set()
        if user_id is not None and "updated_by_id" in cols:
            payload["updated_by_id"] = user_id

        # ✅ افتح Session من الـ sessionmaker
        SessionLocal = get_session_local()  # sessionmaker
        with SessionLocal() as s:
            obj = s.get(Company, company_id)
            if not obj:
                return None

            # تطبيق التعديلات
            for k, v in payload.items():
                setattr(obj, k, v)

            # روابط الأدوار (اختياري)
            if role_ids is not None:
                self._persist_roles(s, company_id, role_ids)

            s.commit()
            s.refresh(obj)
            return obj

    # ---------------- Delete ----------------
    def delete_company(self, company_id: int) -> bool:
        """
        يحذف الشركة وروابط الأدوار التابعة لها.
        """
        with get_session_local()() as s:
            obj = s.get(Company, company_id)
            if not obj:
                return False

            # نظّف الروابط (لو كان جدول الروابط مفعّل)
            try:
                s.query(CompanyRoleLink).filter(CompanyRoleLink.company_id == company_id).delete()
            except Exception:
                # لو ما في جدول روابط أو مختلف، نتجاهل بصمت
                pass

            s.delete(obj)
            s.commit()
            return True

    # ---------------- Role Links (optional) ----------------
    @staticmethod
    def _persist_roles(s, company_id: int, role_ids: Iterable[int]) -> None:
        """
        يطبّق روابط الأدوار بأسلوب hard reset:
          - حذف كل الروابط القديمة ثم إدخال الجديدة (unique).
        ملاحظة: هذه الدالة اختيارية ولن تعمل إلا إذا مرّرت role_ids إلى add/update.
        """
        if role_ids is None:
            return

        # احذف القديم
        s.query(CompanyRoleLink).filter(CompanyRoleLink.company_id == company_id).delete()

        # أدخل الجديد
        cleaned: List[int] = []
        for rid in role_ids:
            if rid is None:
                continue
            try:
                cleaned.append(int(rid))
            except Exception:
                continue

        unique_sorted = sorted(set(cleaned))
        if not unique_sorted:
            return

        rows = [CompanyRoleLink(company_id=company_id, role_id=r) for r in unique_sorted]
        s.bulk_save_objects(rows)


# ── CompanyBanksCRUD ──────────────────────────────────────────────────────────

from database.models.company import CompanyBank, CompanyPartnerLink
from database.models.client import Client


class CompanyBanksCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(CompanyBank, get_session_local)

    def list_banks(self, company_id: int) -> List["CompanyBank"]:
        """Return all banks for a company, primary first."""
        with self.get_session() as s:
            return (
                s.query(CompanyBank)
                .filter(CompanyBank.company_id == company_id)
                .order_by(CompanyBank.is_primary.desc(), CompanyBank.id)
                .all()
            )

    def add_bank(self, company_id: int, data: Dict[str, Any]) -> "CompanyBank":
        def _U(x): return x.strip().upper() if isinstance(x, str) and x.strip() else None

        with self.get_session() as s:
            if data.get("is_primary"):
                s.query(CompanyBank).filter(
                    CompanyBank.company_id == company_id,
                    CompanyBank.is_primary == True,
                ).update({CompanyBank.is_primary: False})
                s.flush()
                s.commit()

            obj = CompanyBank(
                company_id=company_id,
                bank_name=_U(data.get("bank_name")),
                branch=_U(data.get("branch")),
                beneficiary_name=_U(data.get("beneficiary_name")),
                iban=_U(data.get("iban")),
                swift_bic=_U(data.get("swift_bic")),
                account_number=_U(data.get("account_number")),
                bank_country_id=data.get("bank_country_id"),
                currency_id=data.get("currency_id"),
                is_primary=bool(data.get("is_primary", False)),
                notes=data.get("notes"),
            )
            s.add(obj)
            s.flush()
            s.commit()
            s.refresh(obj)
            return obj

    def update_bank(self, bank_id: int, data: Dict[str, Any]) -> Optional["CompanyBank"]:
        def _U(x): return x.strip().upper() if isinstance(x, str) and x.strip() else None

        payload = {}
        for k in ("bank_name", "branch", "beneficiary_name", "iban", "swift_bic", "account_number"):
            if k in data: payload[k] = _U(data[k])
        for k in ("bank_country_id", "currency_id", "notes"):
            if k in data: payload[k] = data[k]

        if "is_primary" in data:
            payload["is_primary"] = bool(data["is_primary"])
            if payload["is_primary"]:
                bank = self.get(bank_id)
                if bank:
                    with self.get_session() as s:
                        s.query(CompanyBank).filter(
                            CompanyBank.company_id == bank.company_id,
                            CompanyBank.is_primary == True,
                            CompanyBank.id != bank_id,
                        ).update({CompanyBank.is_primary: False})
                        s.flush()
                        s.commit()

        return self.update(bank_id, payload)

    def delete_bank(self, bank_id: int) -> bool:
        return self.delete(bank_id)


# ── CompanyPartnersCRUD ───────────────────────────────────────────────────────

class CompanyPartnersCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(CompanyPartnerLink, get_session_local)

    def list_partners(self, company_id: int) -> List["CompanyPartnerLink"]:
        """Return all partners for a company."""
        with self.get_session() as s:
            return (
                s.query(CompanyPartnerLink)
                .filter(CompanyPartnerLink.company_id == company_id,
                        CompanyPartnerLink.is_active == True)
                .order_by(CompanyPartnerLink.id)
                .all()
            )

    def add_partner(self, company_id: int, client_id: int, *,
                    partner_role: Optional[str] = None,
                    share_percent: Optional[float] = None,
                    notes: Optional[str] = None) -> "CompanyPartnerLink":
        with self.get_session() as s:
            obj = CompanyPartnerLink(
                company_id=company_id,
                client_id=client_id,
                partner_role=(partner_role or "").strip().upper() or None,
                share_percent=share_percent,
                is_active=True,
                notes=notes,
            )
            s.add(obj)
            s.flush()
            s.commit()
            s.refresh(obj)
            return obj

    def update_partner(self, link_id: int, data: Dict[str, Any]) -> Optional["CompanyPartnerLink"]:
        payload = {}
        if "partner_role" in data:
            r = (data["partner_role"] or "").strip().upper()
            payload["partner_role"] = r or None
        if "share_percent" in data: payload["share_percent"] = data["share_percent"]
        if "is_active" in data:     payload["is_active"]     = bool(data["is_active"])
        if "notes" in data:         payload["notes"]         = data["notes"]
        return self.update(link_id, payload)

    def delete_partner(self, link_id: int) -> bool:
        return self.delete(link_id)