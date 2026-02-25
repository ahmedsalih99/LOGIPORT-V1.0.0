from typing import Optional, Dict, Any, List
from database.models import get_session_local, Client, ClientContact
from database.crud.base_crud_v5 import BaseCRUD_V5 as BaseCRUD
from sqlalchemy import select, func, cast, Integer

class ClientsCRUD(BaseCRUD):
    """CRUD for clients (no manual code; id is PK)."""

    def __init__(self):
        super().__init__(Client, get_session_local)

    def _SessionLocal(self):
        factory = self.session_factory
        return factory() if callable(factory) else factory

    @staticmethod
    def generate_next_client_code(session, prefix: str = "C") -> str:
        tail_max = session.execute(
            select(
                func.coalesce(
                    func.max(
                        cast(func.substr(Client.code, len(prefix) + 1), Integer)
                    ),
                    0
                )
            ).where(Client.code.like(prefix + "%"))
        ).scalar_one()
        return f"{prefix}{int(tail_max) + 1:04d}"

    def add_client(
            self, *,
            name_ar: str,
            name_en: Optional[str] = None,
            name_tr: Optional[str] = None,
            country_id: Optional[int] = None,
            city: Optional[str] = None,
            address_ar: Optional[str] = None,
            address_en: Optional[str] = None,
            address_tr: Optional[str] = None,
            address: Optional[str] = None,
            default_currency_id: Optional[int] = None,
            default_delivery_method_id: Optional[int] = None,
            default_packaging_type_id: Optional[int] = None,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            website: Optional[str] = None,
            tax_id: Optional[str] = None,
            notes: Optional[str] = None,
            code: Optional[str] = None,
            user_id: Optional[int] = None,
    ) -> Client:
        # توليد الكود عند الحاجة
        if not code or not str(code).strip():
            SessionLocal = get_session_local()
            with SessionLocal() as s:
                code = self.generate_next_client_code(s, prefix="C")

        # helper: upper for strings (except notes & email)
        def _U(x):
            if isinstance(x, str):
                x = x.strip()
                return x.upper() if x else None
            return x

        # طبّع الحقول
        name_ar = _U(name_ar)  # مطلوب
        name_en = _U(name_en)
        name_tr = _U(name_tr)
        city = _U(city)
        address_ar = _U(address_ar)
        address_en = _U(address_en)
        address_tr = _U(address_tr)
        address = _U(address)
        phone = _U(phone)
        website = _U(website)
        tax_id = _U(tax_id)

        # email دائمًا lowercase
        email = (email or "").strip().lower() or None

        obj = Client(
            code=code,
            name_ar=name_ar,
            name_en=name_en,
            name_tr=name_tr,
            country_id=country_id,
            city=city,
            address_ar=address_ar,
            address_en=address_en,
            address_tr=address_tr,
            address=address,
            default_currency_id=default_currency_id,
            default_delivery_method_id=default_delivery_method_id,
            default_packaging_type_id=default_packaging_type_id,
            phone=phone,
            email=email,
            website=website,
            tax_id=tax_id,
            notes=notes,  # notes تُترك كما هي
        )

        cols = set(getattr(Client, "__table__").c.keys())
        if user_id is not None:
            if "created_by_id" in cols and getattr(obj, "created_by_id", None) in (None, 0, ""):
                obj.created_by_id = user_id
            if "updated_by_id" in cols:
                obj.updated_by_id = user_id

        return self.add(obj, current_user={"id": user_id} if user_id is not None else None)

    def get_client(self, client_id: int) -> Optional[Client]:
        return self.get(client_id)

    def list_clients(self, *, order_by=None) -> List[Client]:
        if order_by is None:
            order_by = Client.id.asc()  # الأقدم أولاً
        return self.get_all(order_by=order_by)

    def update_client(self, client_id: int, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[Client]:
        payload = dict(data or {})

        # helper
        def _U(x):
            if isinstance(x, str):
                x = x.strip()
                return x.upper() if x else None
            return x

        # Upper لكل النصوص (ما عدا notes & email)
        for k in ("name_ar", "name_en", "name_tr", "city",
                  "address_ar", "address_en", "address_tr", "address",
                  "phone", "website", "tax_id"):
            if k in payload:
                payload[k] = _U(payload[k])

        # email دائمًا lowercase
        if "email" in payload and isinstance(payload["email"], str):
            payload["email"] = payload["email"].strip().lower() or None

        cols = set(getattr(Client, "__table__").c.keys())
        if user_id is not None and "updated_by_id" in cols:
            payload["updated_by_id"] = user_id

        return self.update(client_id, payload, current_user={"id": user_id} if user_id is not None else None)

    def delete_client(self, client_id: int, user_id: Optional[int] = None) -> bool:
        return self.delete(client_id, current_user={"id": user_id} if user_id is not None else None)


class ClientContactsCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(ClientContact, get_session_local)

    def _SessionLocal(self):
        """Returns callable that creates sessions."""
        factory = self.session_factory
        return factory() if callable(factory) else factory

    def add_contact(self, *, client_id: int, name: str, role_title: Optional[str] = None,
                    phone: Optional[str] = None, email: Optional[str] = None,
                    notes: Optional[str] = None, is_primary: bool = False) -> ClientContact:
        def _U(x):
            if isinstance(x, str):
                x = x.strip()
                return x.upper() if x else None
            return x

        name_val  = _U(name)
        role_val  = _U(role_title)
        phone_val = _U(phone)
        email_val = (email or "").strip().lower() or None

        with self.get_session() as s:
            # Clear existing primary in same session
            if is_primary:
                s.query(ClientContact).filter(
                    ClientContact.client_id == client_id,
                    ClientContact.is_primary == True,
                ).update({ClientContact.is_primary: False})
                s.flush()

            obj = ClientContact(
                client_id=client_id,
                name=name_val,
                role_title=role_val,
                phone=phone_val,
                email=email_val,
                notes=notes,
                is_primary=is_primary,
            )
            s.add(obj)
            s.flush()
            s.commit()
            s.refresh(obj)
            return obj


    def list_contacts(self, client_id: int) -> List[ClientContact]:
        """Return all contacts for a given client, primary first."""
        with self.get_session() as s:
            return (
                s.query(ClientContact)
                .filter(ClientContact.client_id == client_id)
                .order_by(ClientContact.is_primary.desc(), ClientContact.id)
                .all()
            )

    def update_contact(self, contact_id: int, *, name: Optional[str] = None,
                       role_title: Optional[str] = None, phone: Optional[str] = None,
                       email: Optional[str] = None, notes: Optional[str] = None,
                       is_primary: Optional[bool] = None) -> Optional[ClientContact]:
        def _U(x):
            if isinstance(x, str):
                x = x.strip()
                return x.upper() if x else None
            return x

        payload: Dict[str, Any] = {}
        if name is not None:        payload["name"]       = _U(name)
        if role_title is not None:  payload["role_title"] = _U(role_title)
        if phone is not None:       payload["phone"]      = _U(phone)
        if email is not None:       payload["email"]      = (email.strip().lower() or None)
        if notes is not None:       payload["notes"]      = notes
        if is_primary is not None:  payload["is_primary"] = is_primary

        # If setting as primary, clear existing primary first
        if is_primary:
            contact = self.get(contact_id)
            if contact:
                with self.get_session() as s:
                    s.query(ClientContact).filter(
                        ClientContact.client_id == contact.client_id,
                        ClientContact.is_primary == True,
                        ClientContact.id != contact_id,
                    ).update({ClientContact.is_primary: False})
                    s.flush()
                    s.commit()

        return self.update(contact_id, payload)

    def delete_contact(self, contact_id: int) -> bool:
        return self.delete(contact_id)