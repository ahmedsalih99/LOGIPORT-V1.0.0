"""
database/crud/base_crud_v5.py
==============================
.. deprecated::
    هذا الملف shim للتوافق مع الكود القديم فقط.
    BaseCRUD_V5 دُمج في base_crud.BaseCRUD.
    لا تستخدم هذا الملف في كود جديد — استخدم:
        from database.crud.base_crud import BaseCRUD
"""
import warnings
warnings.simplefilter("once", DeprecationWarning)  # اعرض مرة واحدة فقط

from database.crud.base_crud import BaseCRUD

# تحذير هاديء — يظهر فقط مرة واحدة لكل process
warnings.warn(
    "base_crud_v5 is deprecated. Use: from database.crud.base_crud import BaseCRUD",
    DeprecationWarning,
    stacklevel=2,
)

# Alias للتوافق مع الكود القديم
BaseCRUD_V5 = BaseCRUD

__all__ = ["BaseCRUD_V5", "BaseCRUD"]