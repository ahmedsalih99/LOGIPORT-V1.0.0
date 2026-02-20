from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional
from sqlalchemy import text

logger = logging.getLogger(__name__)


# =============================================================================
# نفس بيانات scripts/seed_data.py — مصدر واحد للحقيقة
# =============================================================================

_ROLES = [
    (1, "Admin",       "Super Admin",          "مدير",          "Admin",           "Yönetici"),
    (3, "Manager",     None,                   "مدير قسم",      "Manager",         "Müdür"),
    (4, "User",        None,                   "مستخدم",        "User",            "Kullanıcı"),
    (5, "Accountant",  "إدارة العمليات المالية","محاسب",          "Accountant",      "Muhasebeci"),
    (6, "Operator",    "صلاحيات تنفيذية",      "موظف تشغيل",    "Operator",        "Operatör"),
    (7, "Viewer",      "عرض البيانات فقط",     "مشاهد فقط",     "Viewer",          "Sadece Görüntüleyici"),
    (8, "Client",      "مستخدم خارجي",         "عميل",          "Client",          "Müşteri"),
    (9, "Customs",     "إجراءات جمركية",       "موظف جمركي",    "Customs Officer", "Gümrük Görevlisi"),
]

_PERMISSIONS = [
    (1,  "view_dashboard",        "Allows access to dashboard",   "عرض لوحة التحكم",   "View Dashboard",     "Kontrol Panelini Görüntüle", "DASHBOARD"),
    (2,  "add_user",              "Add new user",                 "إضافة مستخدم",      "Add User",           "Kullanıcı Ekle",             "USERS"),
    (3,  "view_users",            "View users list",              "عرض المستخدمين",    "View Users",         "Kullanıcıları Görüntüle",    "USERS"),
    (4,  "edit_user",             "Edit user",                    "تعديل مستخدم",      "Edit User",          "Kullanıcıyı Düzenle",        "USERS"),
    (5,  "delete_user",           "Delete user",                  "حذف مستخدم",        "Delete User",        "Kullanıcıyı Sil",            "USERS"),
    (6,  "view_roles",            "View roles",                   "عرض الأدوار",       "View Roles",         "Rolleri Görüntüle",          "USERS"),
    (7,  "add_role",              "Add role",                     "إضافة دور",         "Add Role",           "Rol Ekle",                   "USERS"),
    (8,  "edit_role",             "Edit role",                    "تعديل دور",         "Edit Role",          "Rol Düzenle",                "USERS"),
    (9,  "delete_role",           "Delete role",                  "حذف دور",           "Delete Role",        "Rol Sil",                    "USERS"),
    (10, "view_permissions",      "View permissions",             "عرض الصلاحيات",     "View Permissions",   "Yetkileri Görüntüle",        "USERS"),
    (11, "add_permission",        "Add permission",               "إضافة صلاحية",      "Add Permission",     "Yetki Ekle",                 "USERS"),
    (12, "edit_permission",       "Edit permission",              "تعديل صلاحية",      "Edit Permission",    "Yetki Düzenle",              "USERS"),
    (13, "delete_permission",     "Delete permission",            "حذف صلاحية",        "Delete Permission",  "Yetki Sil",                  "USERS"),
    (14, "view_audit_log",        "View audit log",               "عرض سجل العمليات",  "View Audit Log",     "Kayıt Günlüğünü Görüntüle",  "AUDIT"),
    (15, "manage_settings",       "Manage settings",              "إدارة الإعدادات",   "Manage Settings",    "Ayarları Yönet",             "SETTINGS"),
    (16, "view_materials",        "View materials",               "عرض المواد",        "View Materials",     "Malzemeleri Görüntüle",      "MATERIALS"),
    (17, "add_material",          "Add material",                 "إضافة مادة",        "Add Material",       "Malzeme Ekle",               "MATERIALS"),
    (18, "edit_material",         "Edit material",                "تعديل مادة",        "Edit Material",      "Malzeme Düzenle",            "MATERIALS"),
    (19, "delete_material",       "Delete material",              "حذف مادة",          "Delete Material",    "Malzeme Sil",                "MATERIALS"),
    (20, "view_clients",          "View clients",                 "عرض العملاء",       "View Clients",       "Müşterileri Görüntüle",      "CLIENTS"),
    (21, "view_companies",        "View companies",               "عرض الشركات",       "View Companies",     "Şirketleri Görüntüle",       "COMPANIES"),
    (22, "view_countries",        "View countries",               "عرض الدول",         "View Countries",     "Ülkeleri Görüntüle",         "VALUES"),
    (23, "view_pricing",          "View pricing",                 "عرض التسعير",       "View Pricing",       "Fiyatlandırmayı Görüntüle",  "PRICING"),
    (24, "view_entries",          "View entries",                 "عرض الإدخالات",     "View Entries",       "Girişleri Görüntüle",        "ENTRIES"),
    (25, "view_transactions",     "View transactions",            "عرض المعاملات",     "View Transactions",  "İşlemleri Görüntüle",        "TRANSACTIONS"),
    (26, "view_documents",        "View documents",               "عرض المستندات",     "View Documents",     "Belgeleri Görüntüle",        "DOCUMENTS"),
    (27, "view_values",           "View values",                  "عرض القيم",         "View Values",        "Değerleri Görüntüle",        "VALUES"),
    (28, "view_users_roles",      "View users and roles",         "عرض المستخدمين والأدوار", "View Users & Roles", "Kullanıcıları ve Rolleri Görüntüle", "USERS"),
    (29, "view_audit_trail",      "View audit trail",             "عرض سجل التدقيق",   "View Audit Trail",   "Denetim İzini Görüntüle",    "AUDIT"),
    (30, "view_control_panel",    "View control panel",           "عرض لوحة الإدارة",  "View Control Panel", "Kontrol Panelini Görüntüle", "ADMIN"),
    (31, "add_country",           None,                           "إضافة دولة",        "Add Country",        "Ülke Ekle",                  "VALUES"),
    (32, "edit_country",          None,                           "تعديل دولة",        "Edit Country",       "Ülkeyi Düzenle",             "VALUES"),
    (33, "delete_country",        None,                           "حذف دولة",          "Delete Country",     "Ülkeyi Sil",                 "VALUES"),
    (34, "add_packaging_type",    None,                           "إضافة نوع تعبئة",   "Add Packaging Type", "Paketleme Türü Ekle",        "VALUES"),
    (35, "edit_packaging_type",   None,                           "تعديل نوع تعبئة",   "Edit Packaging Type","Paketleme Türünü Düzenle",   "VALUES"),
    (36, "delete_packaging_type", None,                           "حذف نوع تعبئة",     "Delete Packaging Type","Paketleme Türünü Sil",    "VALUES"),
    (37, "add_delivery_method",   None,                           "إضافة طريقة توصيل", "Add Delivery Method","Teslimat Yöntemi Ekle",      "VALUES"),
    (38, "edit_delivery_method",  None,                           "تعديل طريقة توصيل", "Edit Delivery Method","Teslimat Yöntemini Düzenle", "VALUES"),
    (39, "delete_delivery_method",None,                           "حذف طريقة توصيل",   "Delete Delivery Method","Teslimat Yöntemini Sil",  "VALUES"),
    (40, "add_currency",          None,                           "إضافة عملة",        "Add Currency",       "Para Birimi Ekle",           "VALUES"),
    (41, "edit_currency",         None,                           "تعديل عملة",        "Edit Currency",      "Para Birimini Düzenle",      "VALUES"),
    (42, "delete_currency",       None,                           "حذف عملة",          "Delete Currency",    "Para Birimini Sil",          "VALUES"),
    (43, "add_material_type",     None,                           "إضافة نوع مادة",    "Add Material Type",  "Malzeme Türü Ekle",          "MATERIALS"),
    (44, "edit_material_type",    None,                           "تعديل نوع مادة",    "Edit Material Type", "Malzeme Türünü Düzenle",     "MATERIALS"),
    (45, "delete_material_type",  None,                           "حذف نوع مادة",      "Delete Material Type","Malzeme Türünü Sil",        "MATERIALS"),
    (46, "view_packaging_types",  None,                           "عرض أنواع التغليف", "View Packaging Types","Ambalaj Türlerini Görüntüle","VALUES"),
    (47, "view_delivery_methods", None,                           "عرض طرق التسليم",   "View Delivery Methods","Teslimat Yöntemlerini Görüntüle","VALUES"),
    (48, "view_material_types",   None,                           "عرض أنواع المواد",  "View Material Types","Malzeme Türlerini Görüntüle", "MATERIALS"),
    (49, "view_currencies",       None,                           "عرض العملات",       "View Currencies",    "Para Birimlerini Görüntüle", "VALUES"),
    (50, "add_entry",             "Create new entry",             "إضافة إدخال",       "Add Entry",          "Giriş Ekle",                 "ENTRIES"),
    (51, "edit_entry",            "Edit existing entry",          "تعديل إدخال",       "Edit Entry",         "Girişi Düzenle",             "ENTRIES"),
    (52, "delete_entry",          "Delete entry",                 "حذف إدخال",         "Delete Entry",       "Girişi Sil",                 "ENTRIES"),
    (53, "add_client",            "Add new client",               "إضافة عميل",        "Add Client",         "Müşteri Ekle",               "CLIENTS"),
    (54, "edit_client",           "Edit client",                  "تعديل عميل",        "Edit Client",        "Müşteriyi Düzenle",          "CLIENTS"),
]

_ROLE_PERMISSIONS = {
    1: list(range(1, 55)),  # Admin → كل الصلاحيات
    3: [1,2,3,4,6,7,8,10,11,12,14,16,17,18,19,22,27,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49],
    4: [16, 25, 49],
    5: [1, 3, 6, 10, 14, 16],
    6: [1, 16, 17, 18],
    7: [1, 6, 10, 16, 22, 27, 46, 47, 48, 49],
    8: [1, 16],
    9: [],
}

_COMPANY_ROLES = [
    (1,  "supplier",       "مورد",        "Supplier",      "Tedarikçi",  1, 10),
    (2,  "manufacturer",   "مصنّع",        "Manufacturer",  "Üretici",    1, 20),
    (9,  "exporter",       "مصدّر",        "Exporter",      "İhracatçı",  1, 20),
    (3,  "carrier",        "شركة نقل",    "Carrier",       "Taşıyıcı",   1, 30),
    (10, "importer",       "مستورد",      "Importer",      "İthalatçı",  1, 30),
    (4,  "forwarder",      "فورواردَر",    "Forwarder",     "Spedisyon",  1, 40),
    (11, "trader",         "تاجر",        "Trader",        "Tüccar",     1, 40),
    (5,  "customs_broker", "مخلّص جمركي", "Customs Broker","Gümrük",     1, 50),
    (6,  "warehouse",      "مستودع",      "Warehouse",     "Depo",       1, 60),
    (7,  "other",          "أخرى",        "Other",         "Diğer",      1, 100),
]

_DOCUMENT_TYPES = [
    (1,  "INV_EXT",              "فاتورة خارجية",              "External Invoice",         "Dış Fatura",                 1, None,              None,                                  0),
    (2,  "INV_SY",               "فاتورة سورية",               "Syrian Invoice",            "Suriye Faturası",            1, None,              None,                                  0),
    (3,  "INV_INDIRECT",         "فاتورة بالواسطة",             "Intermediary Invoice",      "Aracı Fatura",               1, None,              None,                                  0),
    (4,  "PACKING",              "قائمة تعبئة",                "Packing List",              "Çeki Listesi",               1, None,              None,                                  0),
    (9,  "INV_PRO",              "بروفورما إنفويس",             "Proforma Invoice",          "Proforma Fatura",            1, "invoice.proforma","invoices/proforma",                   10),
    (10, "invoice.syrian.entry", "فاتورة سورية إدخال",          "Syrian Entry Invoice",      "Suriye Giriş Faturası",      1, "invoice.syrian",  "invoices/syrian/entry",               0),
    (11, "INV_SYR_TRANS",        None,                          None,                        None,                         1, None,              "invoices/syrian/transit/{lang}.html", 0),
    (12, "INV_SYR_INTERM",       None,                          None,                        None,                         1, None,              "invoices/syrian/intermediary/{lang}.html", 0),
    (13, "PL_EXPORT_SIMPLE",     "قائمة تعبئة – بدون تواريخ", "Packing List – Simple",     "Ambalaj Listesi – Basit",    1, None,              None,                                  0),
    (14, "PL_EXPORT_WITH_DATES", "قائمة تعبئة – مع تواريخ",   "Packing List – With Dates", "Ambalaj Listesi – Tarihli",  1, None,              None,                                  0),
    (15, "INV_PROFORMA",         "بروفورما إنفويس",             "Proforma Invoice",          "Proforma Fatura",            1, "INVPL",            None,                                 0),
    (16, "INV_NORMAL",           "فاتورة عادية",               "Normal Invoice",            "Normal Fatura",              1, None,              None,                                  0),
    (17, "PL_EXPORT_WITH_LINE_ID","قائمة تعبئة مع رقم السطر",  "Packing List with Line ID", "Hat No'lu Paketleme Listesi",1, None,             None,                                  0),
]

_PRICING_TYPES = [
    (7,  "TON_NET",   "بالطن - حسب الصافي",   None, None, 1, 10, "NET",   "TON",  1000.0),
    (8,  "TON_GROSS", "بالطن - حسب القائم",   None, None, 1, 11, "GROSS", "TON",  1000.0),
    (9,  "KG_NET",    "بالكيلو - حسب الصافي", None, None, 1, 15, "NET",   "KG",   1.0),
    (10, "KG_GROSS",  "بالكيلو - حسب القائم", None, None, 1, 16, "GROSS", "KG",   1.0),
    (2,  "UNIT",      "حسب العدد",            "Per Unit", "Adet Başına", 1, 20, "QTY", "UNIT", 1.0),
]

_APP_SETTINGS = [
    ("transaction_last_number",        "0",    "numbering", "آخر رقم معاملة"),
    ("transaction_prefix",             "",     "numbering", "بادئة رقم المعاملة"),
    ("transaction_auto_increment",     "true", "numbering", "تفعيل الترقيم التلقائي"),
    ("document_naming_use_transaction","true", "numbering", "استخدام رقم المعاملة"),
    ("documents_output_path",          "",     "storage",   "مسار حفظ المستندات"),
]


# =============================================================================
# دالة التهيئة الرئيسية
# =============================================================================

def _run_migrations(conn) -> None:
    """
    تُشغَّل في كل بداية تشغيل — تُنشئ الجداول/الأعمدة الناقصة في الـ DB الموجودة.
    آمنة تماماً: تستخدم IF NOT EXISTS / IF NOT column.
    """
    # Migration 1: جدول app_settings (لم يكن موجوداً في الإصدارات الأولى)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT NOT NULL UNIQUE,
            value       TEXT,
            category    TEXT,
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Seed القيم الافتراضية إن لم تكن موجودة
    for key, value, category, description in _APP_SETTINGS:
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (key, value, category, description) VALUES (?,?,?,?)",
            (key, value, category, description)
        )
    conn.commit()
    logger.info("Bootstrap: migrations تمت بنجاح")


def run_bootstrap() -> bool:

    try:
        # ① إنشاء الجداول
        from database.models import init_db
        init_db()
        logger.info("Bootstrap: جداول قاعدة البيانات جاهزة")

        # ① ب) migrations للـ DB الموجودة (تعمل بأمان مع أي DB)
        from database.db_utils import get_db_path
        import sqlite3 as _sqlite3
        with _sqlite3.connect(get_db_path()) as _conn:
            _run_migrations(_conn)

        # ② إدراج البيانات الأساسية
        _seed_all()
        logger.info("Bootstrap: البيانات الأساسية جاهزة")

        # ③ هل يوجد مستخدمون؟
        needs_setup = _no_users_exist()
        if needs_setup:
            logger.warning("Bootstrap: لا يوجد أي مستخدم — يجب عرض SetupWizard")
        else:
            logger.info("Bootstrap: يوجد مستخدمون، التطبيق جاهز")

        return needs_setup

    except Exception as exc:
        logger.error(f"Bootstrap فشل: {exc}", exc_info=True)
        # في حالة الفشل الكامل، نظهر نافذة الدخول العادية بدل التعليق
        return False


def create_superadmin(username: str, password: str, full_name: str) -> bool:
    """
    ينشئ مستخدم SuperAdmin (role_id=1).
    """
    try:
        from database.crud.users_crud import UsersCRUD

        crud = UsersCRUD()

        # تحقق هل المستخدم موجود مسبقاً
        existing = crud.get_by_username(username)
        if existing:
            logger.warning(f"Bootstrap: المستخدم '{username}' موجود مسبقاً")
            return True

        user = crud.add_user(
            username=username,
            password=password,
            full_name=full_name,
            role_id=1,
            is_active=True,
            user_id=None,  # لا يوجد مستخدم حالي لأنه أول مستخدم
        )

        if user:
            logger.info(
                f"Bootstrap: تم إنشاء SuperAdmin '{username}' بنجاح (id={user.id})"
            )
            return True

        logger.error("Bootstrap: add_user أعاد None")
        return False

    except Exception as exc:
        logger.error(
            f"Bootstrap: خطأ أثناء إنشاء SuperAdmin: {exc}",
            exc_info=True
        )
        return False




# =============================================================================
# الدوال الداخلية
# =============================================================================

def _get_db_path() -> Path:
    """يحصل على مسار قاعدة البيانات من db_utils."""
    from database.db_utils import get_db_path
    return get_db_path()


def _no_users_exist() -> bool:
    try:
        from database.db_utils import get_session_local
        from database.models.user import User
        from sqlalchemy import func as sa_func

        SessionLocal = get_session_local()
        session = SessionLocal()
        try:
            count = session.query(sa_func.count(User.id)).scalar()
            return (count or 0) == 0
        finally:
            session.close()

    except Exception as exc:
        logger.error(f"Bootstrap._no_users_exist خطأ: {exc}")
        return False


def _seed_all() -> None:
    from database.db_utils import get_session_local

    SessionLocal = get_session_local()
    session = SessionLocal()

    try:
        conn = session.connection().connection  # raw sqlite connection
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()

        _seed_roles(cur)
        _seed_permissions(cur)
        _seed_role_permissions(cur)
        _seed_company_roles(cur)
        _seed_document_types(cur)
        _seed_pricing_types(cur)
        _seed_app_settings(cur)

        session.commit()
        logger.info("Bootstrap: seed_all تم بنجاح")

    except Exception as exc:
        session.rollback()
        logger.error(f"Bootstrap._seed_all خطأ: {exc}", exc_info=True)
        raise
    finally:
        session.close()



def _seed_roles(cur: sqlite3.Cursor) -> None:
    for rid, name, desc, label_ar, label_en, label_tr in _ROLES:
        exists = cur.execute("SELECT 1 FROM roles WHERE id=?", (rid,)).fetchone()
        if exists:
            cur.execute(
                "UPDATE roles SET name=?, description=?, label_ar=?, label_en=?, label_tr=? WHERE id=?",
                (name, desc, label_ar, label_en, label_tr, rid)
            )
        else:
            cur.execute(
                "INSERT INTO roles (id, name, description, label_ar, label_en, label_tr) VALUES (?,?,?,?,?,?)",
                (rid, name, desc, label_ar, label_en, label_tr)
            )


def _seed_permissions(cur: sqlite3.Cursor) -> None:
    # تحقق هل العمود category موجود
    cols = {row[1] for row in cur.execute("PRAGMA table_info(permissions)").fetchall()}
    has_category = "category" in cols

    for row in _PERMISSIONS:
        pid, code, desc, label_ar, label_en, label_tr, category = row
        exists = cur.execute("SELECT 1 FROM permissions WHERE id=?", (pid,)).fetchone()
        if exists:
            if has_category:
                cur.execute(
                    "UPDATE permissions SET code=?, description=?, label_ar=?, label_en=?, label_tr=?, category=? WHERE id=?",
                    (code, desc, label_ar, label_en, label_tr, category, pid)
                )
            else:
                cur.execute(
                    "UPDATE permissions SET code=?, description=?, label_ar=?, label_en=?, label_tr=? WHERE id=?",
                    (code, desc, label_ar, label_en, label_tr, pid)
                )
        else:
            if has_category:
                cur.execute(
                    "INSERT INTO permissions (id, code, description, label_ar, label_en, label_tr, category) VALUES (?,?,?,?,?,?,?)",
                    (pid, code, desc, label_ar, label_en, label_tr, category)
                )
            else:
                cur.execute(
                    "INSERT INTO permissions (id, code, description, label_ar, label_en, label_tr) VALUES (?,?,?,?,?,?)",
                    (pid, code, desc, label_ar, label_en, label_tr)
                )


def _seed_role_permissions(cur: sqlite3.Cursor) -> None:
    for role_id, perm_ids in _ROLE_PERMISSIONS.items():
        for perm_id in perm_ids:
            exists = cur.execute(
                "SELECT 1 FROM role_permissions WHERE role_id=? AND permission_id=?",
                (role_id, perm_id)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                    (role_id, perm_id)
                )


def _seed_company_roles(cur: sqlite3.Cursor) -> None:
    # تحقق هل الجدول موجود
    exists_tbl = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='company_roles'"
    ).fetchone()
    if not exists_tbl:
        return

    for rid, code, name_ar, name_en, name_tr, is_active, sort_order in _COMPANY_ROLES:
        exists = cur.execute("SELECT 1 FROM company_roles WHERE id=?", (rid,)).fetchone()
        if exists:
            cur.execute(
                "UPDATE company_roles SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, sort_order=? WHERE id=?",
                (code, name_ar, name_en, name_tr, is_active, sort_order, rid)
            )
        else:
            cur.execute(
                "INSERT INTO company_roles (id, code, name_ar, name_en, name_tr, is_active, sort_order) VALUES (?,?,?,?,?,?,?)",
                (rid, code, name_ar, name_en, name_tr, is_active, sort_order)
            )


def _seed_document_types(cur: sqlite3.Cursor) -> None:
    exists_tbl = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='document_types'"
    ).fetchone()
    if not exists_tbl:
        return

    for did, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order in _DOCUMENT_TYPES:
        exists = cur.execute("SELECT 1 FROM document_types WHERE id=?", (did,)).fetchone()
        if exists:
            cur.execute(
                "UPDATE document_types SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, group_code=?, template_path=?, sort_order=? WHERE id=?",
                (code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order, did)
            )
        else:
            cur.execute(
                "INSERT INTO document_types (id, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
                (did, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order)
            )


def _seed_pricing_types(cur: sqlite3.Cursor) -> None:
    exists_tbl = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pricing_types'"
    ).fetchone()
    if not exists_tbl:
        return

    # تحقق هل الأعمدة الممتدة موجودة
    cols = {row[1] for row in cur.execute("PRAGMA table_info(pricing_types)").fetchall()}
    has_extended = "compute_by" in cols

    for pid, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor in _PRICING_TYPES:
        exists = cur.execute("SELECT 1 FROM pricing_types WHERE id=?", (pid,)).fetchone()
        if exists:
            if has_extended:
                cur.execute(
                    "UPDATE pricing_types SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, sort_order=?, compute_by=?, price_unit=?, divisor=? WHERE id=?",
                    (code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor, pid)
                )
            else:
                cur.execute(
                    "UPDATE pricing_types SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, sort_order=? WHERE id=?",
                    (code, name_ar, name_en, name_tr, is_active, sort_order, pid)
                )
        else:
            if has_extended:
                cur.execute(
                    "INSERT INTO pricing_types (id, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (pid, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor)
                )
            else:
                cur.execute(
                    "INSERT INTO pricing_types (id, code, name_ar, name_en, name_tr, is_active, sort_order) VALUES (?,?,?,?,?,?,?)",
                    (pid, code, name_ar, name_en, name_tr, is_active, sort_order)
                )


def _seed_app_settings(cur: sqlite3.Cursor) -> None:
    # أنشئ الجدول إذا لم يكن موجوداً (ليس ORM model)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT NOT NULL UNIQUE,
            value       TEXT,
            category    TEXT,
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for key, value, category, description in _APP_SETTINGS:
        exists = cur.execute("SELECT 1 FROM app_settings WHERE key=?", (key,)).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO app_settings (key, value, category, description) VALUES (?,?,?,?)",
                (key, value, category, description)
            )