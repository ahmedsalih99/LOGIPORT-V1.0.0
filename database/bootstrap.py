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
    (55, "delete_client",         "Delete client",                "حذف عميل",          "Delete Client",      "Müşteriyi Sil",              "CLIENTS"),
    (56, "add_company",           "Add new company",              "إضافة شركة",        "Add Company",        "Şirket Ekle",                "COMPANIES"),
    (57, "edit_company",          "Edit company",                 "تعديل شركة",        "Edit Company",       "Şirketi Düzenle",            "COMPANIES"),
    (58, "delete_company",        "Delete company",               "حذف شركة",          "Delete Company",     "Şirketi Sil",                "COMPANIES"),
    (59, "add_pricing",           "Add pricing record",           "إضافة تسعيرة",      "Add Pricing",        "Fiyatlandırma Ekle",         "PRICING"),
    (60, "edit_pricing",          "Edit pricing record",          "تعديل تسعيرة",      "Edit Pricing",       "Fiyatlandırmayı Düzenle",    "PRICING"),
    (61, "delete_pricing",        "Delete pricing record",        "حذف تسعيرة",        "Delete Pricing",     "Fiyatlandırmayı Sil",        "PRICING"),
    (62, "add_transaction",       "Create new transaction",       "إضافة معاملة",      "Add Transaction",    "İşlem Ekle",                 "TRANSACTIONS"),
    (63, "edit_transaction",      "Edit transaction",             "تعديل معاملة",      "Edit Transaction",   "İşlemi Düzenle",             "TRANSACTIONS"),
    (64, "delete_transaction",    "Delete transaction",           "حذف معاملة",        "Delete Transaction", "İşlemi Sil",                 "TRANSACTIONS"),
    (65, "close_transaction",     "Close/archive transaction",    "إغلاق معاملة",      "Close Transaction",  "İşlemi Kapat",               "TRANSACTIONS"),
    (66, "view_offices",          "View offices",                 "عرض المكاتب",       "View Offices",       "Ofisleri Görüntüle",         "OFFICES"),
    (67, "add_office",            "Add new office",               "إضافة مكتب",        "Add Office",         "Ofis Ekle",                  "OFFICES"),
    (68, "edit_office",           "Edit office",                  "تعديل مكتب",        "Edit Office",        "Ofisi Düzenle",              "OFFICES"),
    (69, "delete_office",         "Delete office",                "حذف مكتب",          "Delete Office",      "Ofisi Sil",                  "OFFICES"),
    # Container Tracking
    (70, "view_containers",          "View container tracking",      "عرض تتبع الحاويات", "View Containers",    "Konteynerleri Görüntüle",    "CONTAINERS"),
    (71, "add_container",            "Add container",                "إضافة حاوية",       "Add Container",      "Konteyner Ekle",             "CONTAINERS"),
    (72, "edit_container",           "Edit container",               "تعديل حاوية",       "Edit Container",     "Konteyneri Düzenle",         "CONTAINERS"),
    (73, "delete_container",         "Delete container",             "حذف حاوية",         "Delete Container",   "Konteyneri Sil",             "CONTAINERS"),
    (74, "export_container_report",  "Export container report",      "تصدير تقرير الحاويات","Export Container Report","Konteyner Raporu",       "CONTAINERS"),
    # ── Tasks (المرحلة 5) ──────────────────────────────────────────────────────
    (75, "view_tasks",    "View tasks list",    "عرض المهام",    "View Tasks",    "Görevleri Görüntüle", "TASKS"),
    (76, "add_task",      "Create new task",    "إضافة مهمة",    "Add Task",      "Görev Ekle",          "TASKS"),
    (77, "edit_task",     "Edit task",          "تعديل مهمة",    "Edit Task",     "Görevi Düzenle",      "TASKS"),
    (78, "delete_task",   "Delete task",        "حذف مهمة",      "Delete Task",   "Görevi Sil",          "TASKS"),
    (79, "close_task",    "Mark task as done",  "إغلاق مهمة",    "Close Task",    "Görevi Kapat",        "TASKS"),
]

_ROLE_PERMISSIONS = {
    1: list(range(1, 80)),  # Admin → كل الصلاحيات (1-79)
    3: [  # Manager
        1,2,3,4,6,7,8,10,11,12,14,
        16,17,18,19,          # materials
        20,53,54,55,          # clients (view+add+edit+delete)
        21,56,57,             # companies (view+add+edit) بدون delete
        22,27,                # countries + values
        23,59,60,             # pricing (view+add+edit) بدون delete
        24,50,51,52,          # entries full
        25,62,63,             # transactions (view+add+edit) بدون delete/close
        26,                   # view documents
        28,                   # view users_roles (تاب users_permissions)
        31,32,33,             # countries crud
        34,35,36,             # packaging types crud
        37,38,39,             # delivery methods crud
        40,41,42,             # currencies crud
        43,44,45,             # material types crud
        46,47,48,49,          # view lookups
        66,                   # view offices
        70, 71, 72,           # containers (view+add+edit) بدون delete/export
        75, 76, 77, 79,       # tasks (view+add+edit+close) بدون delete
    ],
    4: [16, 25, 49, 66, 75, 76, 77, 79],  # User: + view/add/edit/close tasks
    5: [],                   # Accountant — محذوف (غير مستخدم)
    6: [1, 16, 17, 18, 75, 76, 77, 79],   # Operator: + tasks
    7: [1, 6, 10, 16, 22, 27, 46, 47, 48, 49, 66, 70, 75],  # Viewer: view tasks only
    8: [1, 16],              # Client
    9: [1, 25, 26],          # Customs: dashboard + view transactions + view documents
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
    (10, "invoice.syrian.entry", "فاتورة سورية إدخال",          "Syrian Entry Invoice",      "Suriye Giriş Faturası",      1, "invoice.syrian",  "invoices/syrian/entry",               0),
    (11, "INV_SYR_TRANS",        "فاتورة سورية – عبور",         "Syrian Invoice – Transit",  "Suriye Faturası – Transit",  1, "invoice.syrian.transit",       "invoices/syrian/transit",     5),
    (12, "INV_SYR_INTERM",       "فاتورة سورية – وسيط",        "Syrian Invoice – Intermediary","Suriye Faturası – Aracı",  1, "invoice.syrian.intermediary",  "invoices/syrian/intermediary",6),
    (20, "INV_SYR_ENTRY",        "فاتورة سورية – إدخال",       "Syrian Invoice – Entry",    "Suriye Faturası – Giriş",    1, "invoice.syrian.entry",         "invoices/syrian/entry",       4),
    (13, "PL_EXPORT_SIMPLE",     "قائمة تعبئة – بدون تواريخ", "Packing List – Simple",     "Ambalaj Listesi – Basit",    1, None,              None,                                  0),
    (14, "PL_EXPORT_WITH_DATES", "قائمة تعبئة – مع تواريخ",   "Packing List – With Dates", "Ambalaj Listesi – Tarihli",  1, None,              None,                                  0),
    (15, "INV_PROFORMA",         "بروفورما إنفويس",             "Proforma Invoice",          "Proforma Fatura",            1, "invoice.proforma", "invoices/proforma",                   10),
    (16, "INV_NORMAL",           "فاتورة عادية",               "Normal Invoice",            "Normal Fatura",              1, None,              None,                                  0),
    (17, "PL_EXPORT_WITH_LINE_ID","قائمة تعبئة مع رقم السطر",  "Packing List with Line ID", "Hat No'lu Paketleme Listesi",1, None,             None,                                  0),
    (18, "cmr.copy1.sender",      "CMR – نسخة المرسِل (أحمر)",   "CMR – Copy 1: Sender",      "CMR – 1. Kopya: Gönderici",  1, "cmr",  "cmr/copy1_sender.html",   20),
    (21, "cmr.copy2.consignee",   "CMR – نسخة المستلِم (أزرق)",  "CMR – Copy 2: Consignee",   "CMR – 2. Kopya: Alıcı",      1, "cmr",  "cmr/copy2_consignee.html", 21),
    (22, "cmr.copy3.carrier",     "CMR – نسخة الناقل (أخضر)",   "CMR – Copy 3: Carrier",     "CMR – 3. Kopya: Taşıyıcı",   1, "cmr",  "cmr/copy3_carrier.html",  22),
    (23, "cmr.copy4.archive",     "CMR – نسخة الأرشيف (أسود)",  "CMR – Copy 4: Archive",     "CMR – 4. Kopya: Arşiv",      1, "cmr",  "cmr/copy4_archive.html",  23),
    (19, "form_a",                "شهادة المنشأ نموذج أ",       "Form A Certificate of Origin","Form A Menşe Şahadetnamesi", 1, "form_a",         "form_a",                              21),
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
    # Migration: bank_info column for companies
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()]
        if "bank_info" not in cols:
            conn.execute("ALTER TABLE companies ADD COLUMN bank_info TEXT")
            conn.commit()
            logger.info("Bootstrap: added bank_info to companies")
    except Exception as _e:
        logger.warning("Bootstrap: bank_info migration skipped: %s", _e)

    # Migration: avatar_path column for users
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "avatar_path" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500)")
            conn.commit()
            logger.info("Bootstrap: added avatar_path to users")
    except Exception as _e:
        logger.warning("Bootstrap: avatar_path migration skipped: %s", _e)

    # Migration: category column for permissions
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(permissions)").fetchall()]
        if "category" not in cols:
            conn.execute("ALTER TABLE permissions ADD COLUMN category VARCHAR(50)")
            conn.commit()
            logger.info("Bootstrap: added category to permissions")
    except Exception as _e:
        logger.warning("Bootstrap: category (permissions) migration skipped: %s", _e)

    # Migration: office_id column for users
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "office_id" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN office_id INTEGER REFERENCES offices(id)")
            conn.commit()
            logger.info("Bootstrap: added office_id to users")
    except Exception as _e:
        logger.warning("Bootstrap: office_id (users) migration skipped: %s", _e)

    # Migration: تعيين مكتب HQ للسوبرأدمن إذا كان office_id=NULL
    try:
        hq = conn.execute(
            "SELECT id FROM offices WHERE is_active=1 ORDER BY sort_order, id LIMIT 1"
        ).fetchone()
        if hq:
            conn.execute(
                "UPDATE users SET office_id=? WHERE role_id=1 AND (office_id IS NULL OR office_id=0)",
                (hq[0],)
            )
            conn.commit()
            logger.info("Bootstrap: assigned HQ office to superadmin users")
    except Exception as _e:
        logger.warning("Bootstrap: superadmin office assignment skipped: %s", _e)

    # Migration: office_id column for transactions
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(transactions)").fetchall()]
        if "office_id" not in cols:
            conn.execute("ALTER TABLE transactions ADD COLUMN office_id INTEGER REFERENCES offices(id)")
            conn.commit()
            logger.info("Bootstrap: added office_id to transactions")
    except Exception as _e:
        logger.warning("Bootstrap: office_id (transactions) migration skipped: %s", _e)

    # Migration: origin_country / dest_country / certificate_date في transport_details
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(transport_details)").fetchall()]
        for col, typedef in [
            ("cmr_no",           "VARCHAR(64)"),
            ("origin_country",   "VARCHAR(128)"),
            ("dest_country",     "VARCHAR(128)"),
            ("certificate_date", "DATE"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE transport_details ADD COLUMN {col} {typedef}")
                logger.info("Bootstrap: added %s to transport_details", col)
        conn.commit()
    except Exception as _e:
        logger.warning("Bootstrap: transport_details migration skipped: %s", _e)


    # Migration: performance indexes (safe — CREATE INDEX IF NOT EXISTS)
    _indexes = [
        # transactions
        ("idx_trx_date",       "CREATE INDEX IF NOT EXISTS idx_trx_date       ON transactions(transaction_date)"),
        ("idx_trx_client",     "CREATE INDEX IF NOT EXISTS idx_trx_client     ON transactions(client_id)"),
        ("idx_trx_office",     "CREATE INDEX IF NOT EXISTS idx_trx_office     ON transactions(office_id)"),
        ("idx_trx_type",       "CREATE INDEX IF NOT EXISTS idx_trx_type       ON transactions(transaction_type)"),
        # transaction_items
        ("idx_trxitem_trx",    "CREATE INDEX IF NOT EXISTS idx_trxitem_trx    ON transaction_items(transaction_id)"),
        ("idx_trxitem_mat",    "CREATE INDEX IF NOT EXISTS idx_trxitem_mat    ON transaction_items(material_id)"),
        # entries
        ("idx_entry_date",     "CREATE INDEX IF NOT EXISTS idx_entry_date     ON entries(entry_date)"),
        # audit_log
        ("idx_audit_user",     "CREATE INDEX IF NOT EXISTS idx_audit_user     ON audit_log(user_id)"),
        ("idx_audit_table",    "CREATE INDEX IF NOT EXISTS idx_audit_table    ON audit_log(table_name)"),
        ("idx_audit_ts",       "CREATE INDEX IF NOT EXISTS idx_audit_ts       ON audit_log(timestamp)"),
        # op_log (sync)
        ("idx_oplog_status",   "CREATE INDEX IF NOT EXISTS idx_oplog_status   ON op_log(status)"),
        ("idx_oplog_entity",   "CREATE INDEX IF NOT EXISTS idx_oplog_entity   ON op_log(entity_name)"),
        # entry_items (defined as Index() in model — need migration for existing DBs)
        ("idx_entry_items_entry",   "CREATE INDEX IF NOT EXISTS idx_entry_items_entry   ON entry_items(entry_id)"),
        ("idx_entry_items_mat",     "CREATE INDEX IF NOT EXISTS idx_entry_items_mat     ON entry_items(material_id)"),
        ("idx_entry_items_origin",  "CREATE INDEX IF NOT EXISTS idx_entry_items_origin  ON entry_items(origin_country_id)"),
        # client contacts
        ("idx_contacts_primary",    "CREATE INDEX IF NOT EXISTS idx_contacts_primary    ON client_contacts(is_primary)"),
    ]
    for idx_name, idx_sql in _indexes:
        try:
            conn.execute(idx_sql)
        except Exception as _ie:
            logger.warning("Bootstrap: index %s skipped: %s", idx_name, _ie)
    conn.commit()
    logger.info("Bootstrap: performance indexes checked/created")

    # Migration: جدول container_tracking + container_entry_links
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS container_tracking (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id    INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                client_id         INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                container_no      VARCHAR(32),
                bl_number         VARCHAR(64),
                booking_no        VARCHAR(64),
                shipping_line     VARCHAR(128),
                vessel_name       VARCHAR(128),
                voyage_no         VARCHAR(32),
                port_of_loading   VARCHAR(128),
                port_of_discharge VARCHAR(128),
                final_destination VARCHAR(128),
                etd               DATE,
                eta               DATE,
                atd               DATE,
                ata               DATE,
                customs_date      DATE,
                delivery_date     DATE,
                status            VARCHAR(32) NOT NULL DEFAULT 'booked',
                notes             TEXT,
                created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_transaction_id ON container_tracking(transaction_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_client_id      ON container_tracking(client_id)")
        # Migration: office_id for multi-office filtering
        try:
            conn.execute("ALTER TABLE container_tracking ADD COLUMN office_id INTEGER REFERENCES offices(id) ON DELETE SET NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_office_id ON container_tracking(office_id)")
            conn.commit()
        except Exception:
            pass  # Column already exists
        # Migration: حذف جدول ربط الإدخالات (تم إلغاؤه في v1.1)
        try:
            conn.execute("DROP TABLE IF EXISTS container_entry_links")
            conn.commit()
        except Exception:
            pass
        conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_container_no   ON container_tracking(container_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_status         ON container_tracking(status)")
        conn.commit()
        logger.info("Bootstrap: container_tracking جاهز")
    except Exception as _e:
        logger.warning("Bootstrap: container_tracking migration skipped: %s", _e)

    # Migration: client_id على container_tracking (للـ DBs القديمة التي أُنشئت بدونه)
    try:
        _ct_cols = [r[1] for r in conn.execute("PRAGMA table_info(container_tracking)").fetchall()]
        if _ct_cols and "client_id" not in _ct_cols:
            conn.execute("ALTER TABLE container_tracking ADD COLUMN client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_ct_client_id ON container_tracking(client_id)")
            conn.commit()
            logger.info("Bootstrap: added client_id to container_tracking")
    except Exception as _e:
        logger.warning("Bootstrap: container_tracking client_id migration skipped: %s", _e)

    # Migration v2: أعمدة جديدة لـ container_tracking
    try:
        _ct_cols = [r[1] for r in conn.execute("PRAGMA table_info(container_tracking)").fetchall()]
        _ct_new = {
            "cargo_type":         "VARCHAR(128)",
            "quantity":           "VARCHAR(64)",
            "origin_country":     "VARCHAR(128)",
            "containers_count":   "INTEGER",
            "docs_delivered":     "INTEGER NOT NULL DEFAULT 0",
            "cargo_tracking":     "TEXT",
            "docs_received_date": "DATE",
            "bl_status":          "VARCHAR(64)",
        }
        for col, coldef in _ct_new.items():
            if col not in _ct_cols:
                conn.execute(f"ALTER TABLE container_tracking ADD COLUMN {col} {coldef}")
                logger.info("Bootstrap: added %s to container_tracking", col)
        # إعادة تسمية: bl_number كان nullable=True، نتحقق فقط
        conn.commit()
    except Exception as _e:
        logger.warning("Bootstrap: container_tracking v2 migration skipped: %s", _e)

    # Migration: جدول shipment_containers (كونتينرات البوليصة)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipment_containers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id  INTEGER NOT NULL REFERENCES container_tracking(id) ON DELETE CASCADE,
                container_no VARCHAR(32),
                seal_no      VARCHAR(32),
                recipient    VARCHAR(128),
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_sc_shipment_id ON shipment_containers(shipment_id)")
        conn.commit()
        logger.info("Bootstrap: shipment_containers جاهز")
    except Exception as _e:
        logger.warning("Bootstrap: shipment_containers migration skipped: %s", _e)

    # Migration: add ForeignKey constraints to client default fields
    try:
        _cl_cols = [r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if _cl_cols:
            # SQLite لا يدعم ALTER COLUMN مباشرة — نتحقق فقط من وجود العمود
            # القيد (ForeignKey) موجود في الـ model الجديد وسيُطبَّق على DBs الجديدة
            # للـ DBs القديمة: نتأكد أن العمودين موجودان
            if "default_delivery_method_id" not in _cl_cols:
                conn.execute("ALTER TABLE clients ADD COLUMN default_delivery_method_id INTEGER REFERENCES delivery_methods(id) ON DELETE SET NULL")
                conn.commit()
                logger.info("Bootstrap: added default_delivery_method_id to clients")
            if "default_packaging_type_id" not in _cl_cols:
                conn.execute("ALTER TABLE clients ADD COLUMN default_packaging_type_id INTEGER REFERENCES packaging_types(id) ON DELETE SET NULL")
                conn.commit()
                logger.info("Bootstrap: added default_packaging_type_id to clients")
    except Exception as _e:
        logger.warning("Bootstrap: clients default FK migration skipped: %s", _e)

    # Migration: حذف triggers العنوان الإجباري من companies (العنوان اختياري)
    try:
        conn.execute("DROP TRIGGER IF EXISTS trg_companies_require_any_address")
        conn.execute("DROP TRIGGER IF EXISTS trg_companies_require_any_address_update")
        conn.commit()
        logger.info("Bootstrap: dropped address triggers from companies (address is optional)")
    except Exception as _e:
        logger.warning("Bootstrap: address trigger drop skipped: %s", _e)

    # Migration: جدول المهام (tasks) — المرحلة 5
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title           VARCHAR(255) NOT NULL,
                description     TEXT,
                priority        VARCHAR(16)  NOT NULL DEFAULT 'medium',
                status          VARCHAR(16)  NOT NULL DEFAULT 'pending',
                due_date        DATE,
                created_at      DATETIME     NOT NULL DEFAULT (datetime('now')),
                updated_at      DATETIME,
                completed_at    DATETIME,
                assigned_to_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_by_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                updated_by_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                transaction_id  INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                container_id    INTEGER REFERENCES container_tracking(id) ON DELETE SET NULL,
                client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL
            )
        """)
        # Migration: add updated_by_id if missing (existing DBs)
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
            conn.commit()
        except Exception:
            pass  # Column already exists
        conn.execute("CREATE INDEX IF NOT EXISTS ix_tasks_status     ON tasks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_tasks_due_date   ON tasks(due_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_tasks_assigned   ON tasks(assigned_to_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_tasks_status_due ON tasks(status, due_date)")
        conn.commit()
        logger.info("Bootstrap: tasks table created/verified")
    except Exception as _e:
        logger.warning("Bootstrap: tasks migration skipped: %s", _e)

    # Migration: إصلاح container_tracking.container_no NOT NULL في DBs القديمة
    # SQLite >= 3.35 يدعم DROP COLUMN، لكن ما يساعدنا هنا
    # الحل الأسلم: إذا العمود NOT NULL، نضع DEFAULT '' عليه عبر UPDATE
    # SQLite لا يدعم ALTER COLUMN — لكن يمكن تغيير الـ schema بطريقة آمنة:
    # نتحقق فقط، ونُسجّل تحذيراً — الـ CRUD سيتعامل بـ empty string بدل None
    try:
        cols = {c[1]: c[3] for c in conn.execute("PRAGMA table_info(container_tracking)").fetchall()}
        if cols.get("container_no") == 1:   # notnull=1
            logger.warning(
                "Bootstrap: container_tracking.container_no هو NOT NULL في هذه DB. "
                "سيتم استخدام string فارغ بدلاً من NULL."
            )
    except Exception as _e:
        logger.warning("Bootstrap: container_no check skipped: %s", _e)

    # =========================================================================
    # Migration SYNC-1: جدول local_sync_cursors
    # يحفظ آخر cursor لكل جدول في كل اتجاه (push/pull) لكل مكتب.
    # هذا الجدول محلي فقط — لا يُزامَن مع Supabase.
    # =========================================================================
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS local_sync_cursors (
                table_name  TEXT     NOT NULL,
                direction   TEXT     NOT NULL,
                last_cursor TEXT     NOT NULL DEFAULT '1970-01-01T00:00:00+00:00',
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (table_name, direction)
            )
        """)
        conn.commit()
        logger.info("Bootstrap: local_sync_cursors جاهز")
    except Exception as _e:
        logger.warning("Bootstrap: local_sync_cursors migration skipped: %s", _e)

    # =========================================================================
    # Migration SYNC-2: عمود server_id على كل الجداول القابلة للمزامنة
    # UUID نصي — يُولَّد في LOGIPORT ويُرسل لـ Supabase كمفتاح upsert.
    # =========================================================================
    _sync_tables_server_id = [
        # جداول البيانات الرئيسية
        "clients", "client_contacts", "companies", "company_banks",
        "company_role_links", "company_partner_links",
        "entries", "entry_items",
        "transactions", "transaction_items", "transaction_entries",
        "transport_details", "doc_groups", "documents",
        "audit_log", "users",
        "container_tracking", "shipment_containers", "tasks",
        # جداول مرجعية — يحتاج server_id للـ upsert في Supabase
        "offices", "countries", "currencies",
        "material_types", "materials",
        "packaging_types", "delivery_methods", "pricing_types",
        "document_types", "roles", "permissions",
        "role_permissions", "company_roles",
    ]
    for _tbl in _sync_tables_server_id:
        try:
            _existing = [r[1] for r in conn.execute(f"PRAGMA table_info({_tbl})").fetchall()]
            if not _existing:
                continue   # الجدول غير موجود بعد
            if "server_id" not in _existing:
                conn.execute(f"ALTER TABLE {_tbl} ADD COLUMN server_id TEXT")
                conn.execute(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{_tbl}_server_id"
                    f" ON {_tbl}(server_id) WHERE server_id IS NOT NULL"
                )
                logger.info("Bootstrap: added server_id to %s", _tbl)
        except Exception as _e:
            logger.warning("Bootstrap: server_id(%s) skipped: %s", _tbl, _e)
    try:
        conn.commit()
    except Exception:
        pass

    # =========================================================================
    # Migration SYNC-3: عمود updated_at على الجداول التي تفتقده
    # لازم للـ cursor-based sync — بدونه لا يمكن معرفة ما تغيّر.
    # =========================================================================
    # الجداول التي نضيف لها updated_at:
    # - يجب أن يكون الجدول موجوداً في DB
    # - company_banks / company_role_links / client_contacts ليس فيهم created_at
    #   نضيف updated_at فارغ ونملأه بـ datetime('now')
    # - transaction_entries: جدول ربط بسيط — لا نضيفه
    _sync_tables_updated_at = [
        # جداول البيانات — بدون updated_at أصلاً
        "transaction_items",
        "entry_items",
        "company_banks",
        "company_role_links",
        "company_partner_links",
        "client_contacts",
        "shipment_containers",
        # جداول مرجعية — بدون updated_at في DBs القديمة
        "pricing_types",
        "document_types",
        "roles",
        "permissions",
        "role_permissions",
        "company_roles",
    ]
    for _tbl in _sync_tables_updated_at:
        try:
            _existing = [r[1] for r in conn.execute(f"PRAGMA table_info({_tbl})").fetchall()]
            if not _existing:
                continue
            if "updated_at" not in _existing:
                # [FIX] SQLite لا يقبل DEFAULT CURRENT_TIMESTAMP في ALTER TABLE
                # نضيف العمود بـ DEFAULT NULL ثم نملأه بـ UPDATE
                conn.execute(
                    f"ALTER TABLE {_tbl} ADD COLUMN updated_at DATETIME"
                )
                if "created_at" in _existing:
                    conn.execute(
                        f"UPDATE {_tbl} SET updated_at = created_at"
                        f" WHERE updated_at IS NULL"
                    )
                else:
                    conn.execute(
                        f"UPDATE {_tbl} SET updated_at = datetime('now')"
                        f" WHERE updated_at IS NULL"
                    )
                logger.info("Bootstrap: added updated_at to %s", _tbl)
        except Exception as _e:
            logger.warning("Bootstrap: updated_at(%s) skipped: %s", _tbl, _e)
    try:
        conn.commit()
        logger.info("Bootstrap: sync columns (server_id + updated_at) checked/created")
    except Exception:
        pass

    # =========================================================================
    # Migration SYNC-4: indexes على updated_at للجداول الرئيسية (أداء الـ push)
    # =========================================================================
    _sync_idx = [
        ("ix_clients_updated_at",            "CREATE INDEX IF NOT EXISTS ix_clients_updated_at            ON clients(updated_at)"),
        ("ix_transactions_updated_at",       "CREATE INDEX IF NOT EXISTS ix_transactions_updated_at       ON transactions(updated_at)"),
        ("ix_entries_updated_at",            "CREATE INDEX IF NOT EXISTS ix_entries_updated_at            ON entries(updated_at)"),
        ("ix_ct_updated_at",                 "CREATE INDEX IF NOT EXISTS ix_ct_updated_at                 ON container_tracking(updated_at)"),
        ("ix_tasks_updated_at",              "CREATE INDEX IF NOT EXISTS ix_tasks_updated_at              ON tasks(updated_at)"),
        ("ix_companies_updated_at",          "CREATE INDEX IF NOT EXISTS ix_companies_updated_at          ON companies(updated_at)"),
        ("ix_local_sync_cursors_table",      "CREATE INDEX IF NOT EXISTS ix_local_sync_cursors_table      ON local_sync_cursors(table_name)"),
    ]
    for _iname, _isql in _sync_idx:
        try:
            conn.execute(_isql)
        except Exception as _ie:
            logger.warning("Bootstrap: index %s skipped: %s", _iname, _ie)
    try:
        conn.commit()
        logger.info("Bootstrap: sync indexes checked/created")
    except Exception:
        pass

    conn.commit()
    logger.info("Bootstrap: migrations تمت بنجاح")


def run_bootstrap() -> bool:

    try:
        # ① إنشاء الجداول
        from database.models import init_db
        init_db()
        logger.info("Bootstrap: جداول قاعدة البيانات جاهزة")

        # ① ب) الـ migrations اليدوية (إضافة أعمدة ناقصة في DBs القديمة)
        from database.db_utils import get_db_path
        import sqlite3 as _sqlite3
        with _sqlite3.connect(get_db_path()) as _conn:
            _run_migrations(_conn)

        # إعادة تهيئة الـ engine بعد الـ migrations لمسح الـ metadata القديمة
        try:
            from database.models.base import get_engine
            get_engine().dispose()
        except Exception:
            pass

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

        # جلب أول مكتب نشط لتعيينه للسوبرأدمن
        hq_office_id = None
        try:
            from database.crud.offices_crud import OfficesCRUD
            offices = OfficesCRUD().get_all(active_only=True)
            if offices:
                hq_office_id = offices[0]["id"]
        except Exception:
            pass

        user = crud.add_user(
            username=username,
            password=password,
            full_name=full_name,
            role_id=1,
            is_active=True,
            office_id=hq_office_id,
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
        from database.models import get_session_local
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


# =============================================================================
# Reference Data — بيانات مرجعية افتراضية (تُزرع مرة واحدة عند أول تشغيل)
# =============================================================================

_COUNTRIES = [
    # (code, name_ar, name_en, name_tr)
    ("SY", "سوريا",          "Syria",               "Suriye"),
    ("TR", "تركيا",          "Turkey",              "Türkiye"),
    ("LB", "لبنان",          "Lebanon",             "Lübnan"),
    ("JO", "الأردن",         "Jordan",              "Ürdün"),
    ("IQ", "العراق",         "Iraq",                "Irak"),
    ("SA", "السعودية",       "Saudi Arabia",        "Suudi Arabistan"),
    ("AE", "الإمارات",       "UAE",                 "BAE"),
    ("EG", "مصر",            "Egypt",               "Mısır"),
    ("DE", "ألمانيا",        "Germany",             "Almanya"),
    ("FR", "فرنسا",          "France",              "Fransa"),
    ("IT", "إيطاليا",        "Italy",               "İtalya"),
    ("ES", "إسبانيا",        "Spain",               "İspanya"),
    ("NL", "هولندا",         "Netherlands",         "Hollanda"),
    ("BE", "بلجيكا",         "Belgium",             "Belçika"),
    ("PL", "بولندا",         "Poland",              "Polonya"),
    ("RO", "رومانيا",        "Romania",             "Romanya"),
    ("BG", "بلغاريا",        "Bulgaria",            "Bulgaristan"),
    ("GR", "اليونان",        "Greece",              "Yunanistan"),
    ("CN", "الصين",          "China",               "Çin"),
    ("IN", "الهند",          "India",               "Hindistan"),
    ("RU", "روسيا",          "Russia",              "Rusya"),
    ("UA", "أوكرانيا",       "Ukraine",             "Ukrayna"),
    ("GB", "المملكة المتحدة","United Kingdom",       "Birleşik Krallık"),
    ("US", "الولايات المتحدة","United States",       "Amerika Birleşik Devletleri"),
    ("IR", "إيران",          "Iran",                "İran"),
    ("KW", "الكويت",         "Kuwait",              "Kuveyt"),
    ("QA", "قطر",            "Qatar",               "Katar"),
    ("OM", "عُمان",          "Oman",                "Umman"),
    ("MA", "المغرب",         "Morocco",             "Fas"),
    ("TN", "تونس",           "Tunisia",             "Tunus"),
    ("DZ", "الجزائر",        "Algeria",             "Cezayir"),
    ("LY", "ليبيا",          "Libya",               "Libya"),
    ("PS", "فلسطين",         "Palestine",           "Filistin"),
    ("YE", "اليمن",          "Yemen",               "Yemen"),
    ("AT", "النمسا",         "Austria",             "Avusturya"),
    ("CH", "سويسرا",         "Switzerland",         "İsviçre"),
    ("CZ", "التشيك",         "Czech Republic",      "Çekya"),
    ("HU", "المجر",          "Hungary",             "Macaristan"),
    ("SK", "سلوفاكيا",       "Slovakia",            "Slovakya"),
    ("PK", "باكستان",        "Pakistan",            "Pakistan"),
    ("BD", "بنغلاديش",       "Bangladesh",          "Bangladeş"),
    ("KR", "كوريا الجنوبية", "South Korea",         "Güney Kore"),
    ("JP", "اليابان",        "Japan",               "Japonya"),
    ("TH", "تايلاند",        "Thailand",            "Tayland"),
    ("MY", "ماليزيا",        "Malaysia",            "Malezya"),
    ("ID", "إندونيسيا",      "Indonesia",           "Endonezya"),
    ("AZ", "أذربيجان",       "Azerbaijan",          "Azerbaycan"),
    ("GE", "جورجيا",         "Georgia",             "Gürcistan"),
    ("AM", "أرمينيا",        "Armenia",             "Ermenistan"),
]

_CURRENCIES = [
    # (code, symbol, name_ar, name_en, name_tr)
    ("USD", "$",   "دولار أمريكي",     "US Dollar",          "Amerikan Doları"),
    ("EUR", "€",   "يورو",             "Euro",               "Euro"),
    ("TRY", "₺",   "ليرة تركية",      "Turkish Lira",       "Türk Lirası"),
    ("SYP", "ل.س", "ليرة سورية",      "Syrian Pound",       "Suriye Lirası"),
    ("SAR", "﷼",   "ريال سعودي",      "Saudi Riyal",        "Suudi Riyali"),
    ("AED", "د.إ", "درهم إماراتي",    "UAE Dirham",         "BAE Dirhemi"),
    ("GBP", "£",   "جنيه إسترليني",   "British Pound",      "İngiliz Sterlini"),
    ("IQD", "ع.د", "دينار عراقي",     "Iraqi Dinar",        "Irak Dinarı"),
    ("JOD", "د.أ", "دينار أردني",     "Jordanian Dinar",    "Ürdün Dinarı"),
    ("LBP", "ل.ل", "ليرة لبنانية",    "Lebanese Pound",     "Lübnan Lirası"),
    ("CNY", "¥",   "يوان صيني",       "Chinese Yuan",       "Çin Yuanı"),
    ("RUB", "₽",   "روبل روسي",       "Russian Ruble",      "Rus Rublesi"),
    ("EGP", "ج.م", "جنيه مصري",      "Egyptian Pound",     "Mısır Sterlini"),
]

_PACKAGING_TYPES = [
    # (name_ar, name_en, name_tr)
    ("كرتون",        "Carton",        "Karton"),
    ("طرد",          "Package",       "Paket"),
    ("كيس",          "Bag",           "Çuval"),
    ("برميل",        "Barrel",        "Varil"),
    ("صندوق خشبي",   "Wooden Box",    "Ahşap Kutu"),
    ("إطار",         "Roll",          "Rulo"),
    ("بالة",         "Bale",          "Balya"),
    ("قارورة",       "Bottle",        "Şişe"),
    ("علبة",         "Can/Tin",       "Teneke"),
    ("جراكن",        "Jerry Can",     "Bidon"),
    ("حاوية",        "Container",     "Konteyner"),
    ("صينية",        "Tray",          "Tepsi"),
    ("قطعة",         "Piece",         "Parça"),
    ("طن",           "Ton",           "Ton"),
    ("كغ",           "KG",            "KG"),
]

_DELIVERY_METHODS = [
    # (name_ar, name_en, name_tr, sort_order)
    # Incoterms — شروط التسليم التجارية
    ("فوب",                     "FOB",   "FOB",   1),
    ("سيف",                     "CIF",   "CIF",   2),
    ("تكلفة وشحن",              "CFR",   "CFR",   3),
    ("تكلفة وشحن وتأمين",       "CIP",   "CIP",   4),
    ("تكلفة وشحن (CNF)",        "CNF",   "CNF",   5),
    ("تسليم في الميناء",        "DAP",   "DAP",   6),
    ("تسليم مدفوع الرسوم",      "DDP",   "DDP",   7),
    ("تكلفة وأجرة الشحن",       "CPT",   "CPT",   8),
    ("تسليم على ظهر السفينة",   "FAS",   "FAS",   9),
    ("حر للناقل",               "FCA",   "FCA",   10),
    ("تسليم المصنع",            "EXW",   "EXW",   11),
]

_MATERIAL_TYPES = [
    # (name_ar, name_en, name_tr)
    ("مواد غذائية",        "Food",               "Gıda"),
    ("مواد بناء",          "Construction",       "İnşaat"),
    ("كيماويات",           "Chemicals",          "Kimyasallar"),
    ("منسوجات وألبسة",     "Textiles",           "Tekstil"),
    ("إلكترونيات",         "Electronics",        "Elektronik"),
    ("آلات ومعدات",        "Machinery",          "Makine"),
    ("مواد طبية",          "Medical",            "Medikal"),
    ("أثاث",               "Furniture",          "Mobilya"),
    ("مواد زراعية",        "Agricultural",       "Tarım"),
    ("بلاستيك ومطاط",      "Plastics & Rubber",  "Plastik ve Kauçuk"),
    ("معادن",              "Metals",             "Metaller"),
    ("ورق وطباعة",         "Paper & Print",      "Kağıt ve Baskı"),
    ("مواد خام",           "Raw Materials",      "Ham Maddeler"),
    ("منتجات نفطية",       "Petroleum Products", "Petrol Ürünleri"),
    ("أخرى",               "Other",              "Diğer"),
]


def _tbl_exists(cur: sqlite3.Cursor, name: str) -> bool:
    return bool(cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def _seed_reference_data(cur: sqlite3.Cursor) -> None:
    """
    يزرع البيانات المرجعية الأساسية.
    يتحقق من كل سجل بشكل فردي بالاسم الإنجليزي → آمن تماماً على DBs موجودة.
    """
    # ── الدول ──────────────────────────────────────────────────────────────
    if _tbl_exists(cur, "countries"):
        added = 0
        for code, name_ar, name_en, name_tr in _COUNTRIES:
            exists = cur.execute(
                "SELECT 1 FROM countries WHERE name_en=? OR code=?", (name_en, code)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO countries (code, name_ar, name_en, name_tr) VALUES (?,?,?,?)",
                    (code, name_ar, name_en, name_tr)
                )
                added += 1
        if added:
            logger.info(f"Bootstrap: زُرع {added} دولة")

    # ── العملات ────────────────────────────────────────────────────────────
    if _tbl_exists(cur, "currencies"):
        added = 0
        for code, symbol, name_ar, name_en, name_tr in _CURRENCIES:
            exists = cur.execute(
                "SELECT 1 FROM currencies WHERE code=? OR name_en=?", (code, name_en)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO currencies (code, symbol, name_ar, name_en, name_tr) VALUES (?,?,?,?,?)",
                    (code, symbol, name_ar, name_en, name_tr)
                )
                added += 1
        if added:
            logger.info(f"Bootstrap: زُرع {added} عملة")

    # ── أنواع التغليف ───────────────────────────────────────────────────────
    if _tbl_exists(cur, "packaging_types"):
        added = 0
        for name_ar, name_en, name_tr in _PACKAGING_TYPES:
            exists = cur.execute(
                "SELECT 1 FROM packaging_types WHERE name_en=?", (name_en,)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO packaging_types (name_ar, name_en, name_tr) VALUES (?,?,?)",
                    (name_ar, name_en, name_tr)
                )
                added += 1
        if added:
            logger.info(f"Bootstrap: زُرع {added} نوع تغليف")

    # ── طرق التسليم ────────────────────────────────────────────────────────
    if _tbl_exists(cur, "delivery_methods"):
        added = 0
        for name_ar, name_en, name_tr, sort_order in _DELIVERY_METHODS:
            exists = cur.execute(
                "SELECT 1 FROM delivery_methods WHERE name_en=?", (name_en,)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO delivery_methods (name_ar, name_en, name_tr, is_active, sort_order) VALUES (?,?,?,1,?)",
                    (name_ar, name_en, name_tr, sort_order)
                )
                added += 1
        if added:
            logger.info(f"Bootstrap: زُرع {added} طريقة تسليم")

    # ── أنواع المواد ────────────────────────────────────────────────────────
    if _tbl_exists(cur, "material_types"):
        added = 0
        for name_ar, name_en, name_tr in _MATERIAL_TYPES:
            exists = cur.execute(
                "SELECT 1 FROM material_types WHERE name_en=?", (name_en,)
            ).fetchone()
            if not exists:
                cur.execute(
                    "INSERT INTO material_types (name_ar, name_en, name_tr) VALUES (?,?,?)",
                    (name_ar, name_en, name_tr)
                )
                added += 1
        if added:
            logger.info(f"Bootstrap: زُرع {added} نوع مادة")


def _seed_all() -> None:
    from database.models import get_session_local

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
        _seed_offices(cur)
        _seed_reference_data(cur)

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
    for pid, code, desc, label_ar, label_en, label_tr, category in _PERMISSIONS:
        exists = cur.execute("SELECT 1 FROM permissions WHERE id=?", (pid,)).fetchone()
        if exists:
            cur.execute(
                "UPDATE permissions SET code=?, description=?, label_ar=?, label_en=?, label_tr=?, category=? WHERE id=?",
                (code, desc, label_ar, label_en, label_tr, category, pid)
            )
        else:
            cur.execute(
                "INSERT INTO permissions (id, code, description, label_ar, label_en, label_tr, category) VALUES (?,?,?,?,?,?,?)",
                (pid, code, desc, label_ar, label_en, label_tr, category)
            )


def _seed_role_permissions(cur: sqlite3.Cursor) -> None:
    for role_id, perm_ids in _ROLE_PERMISSIONS.items():
        if not perm_ids:
            # الدور معرَّف بقائمة فارغة — امسح أي صلاحيات موجودة له (تنظيف بيانات قديمة)
            cur.execute("DELETE FROM role_permissions WHERE role_id=?", (role_id,))
            continue
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

    for pid, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor in _PRICING_TYPES:
        exists = cur.execute("SELECT 1 FROM pricing_types WHERE id=?", (pid,)).fetchone()
        if exists:
            cur.execute(
                "UPDATE pricing_types SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, sort_order=?, compute_by=?, price_unit=?, divisor=? WHERE id=?",
                (code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor, pid)
            )
        else:
            cur.execute(
                "INSERT INTO pricing_types (id, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (pid, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor)
            )



def _seed_offices(cur) -> None:
    """يُنشئ مكتباً افتراضياً إذا لم يكن الجدول فارغاً بالكامل."""
    # تحقق هل الجدول موجود
    tbl = cur.execute(
        "SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'offices\'"
    ).fetchone()
    if not tbl:
        return
    # لا تُضف إذا كان في مكاتب مسبقاً
    count = cur.execute("SELECT COUNT(*) FROM offices").fetchone()[0]
    if count > 0:
        return
    # مكتب افتراضي واحد — يُعدَّل لاحقاً من واجهة الإعدادات
    cur.execute(
        """INSERT INTO offices (code, name_ar, name_en, name_tr, country, is_active, sort_order)
           VALUES (?,?,?,?,?,?,?)""",
        ("HQ", "المكتب الرئيسي", "Headquarters", "Genel Merkez", None, 1, 0)
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