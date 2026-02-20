"""
seed_data.py — LOGIPORT
========================
يُهيّئ جميع البيانات الأساسية اللازمة لعمل التطبيق على أي قاعدة بيانات جديدة.

الجداول المشمولة:
  - roles            : أدوار المستخدمين
  - permissions      : الصلاحيات
  - role_permissions : ربط الأدوار بالصلاحيات
  - company_roles    : أدوار الشركات (مورد، ناقل…)
  - document_types   : أنواع المستندات
  - pricing_types    : أنواع التسعير
  - app_settings     : إعدادات التطبيق الأولية

الاستخدام:
  python scripts/seed_data.py
  python scripts/seed_data.py --db /path/to/logiport.db
  python scripts/seed_data.py --dry-run       (عرض فقط بدون تطبيق)
  python scripts/seed_data.py --reset-perms   (إعادة تعيين صلاحيات الأدوار)
"""

import sqlite3
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# =============================================================================
# البيانات الأساسية
# =============================================================================

ROLES = [
    # (id, name, description, label_ar, label_en, label_tr)
    (1, "Admin",       "Super Admin",
     "مدير",          "Admin",           "Yönetici"),
    (3, "Manager",     None,
     "مدير قسم",       "Manager",         "Müdür"),
    (4, "User",        None,
     "مستخدم",         "User",            "Kullanıcı"),
    (5, "Accountant",  "إدارة العمليات المالية والفواتير",
     "محاسب",          "Accountant",      "Muhasebeci"),
    (6, "Operator",    "صلاحيات تنفيذية، مدخل بيانات",
     "موظف تشغيل",     "Operator",        "Operatör"),
    (7, "Viewer",      "عرض البيانات فقط بدون أي تعديل",
     "مشاهد فقط",      "Viewer",          "Sadece Görüntüleyici"),
    (8, "Client",      "مستخدم خارجي - تتبع عمليات فقط",
     "عميل",           "Client",          "Müşteri"),
    (9, "Customs",     "إدارة الإجراءات الجمركية والمعاملات المرتبطة",
     "موظف جمركي",     "Customs Officer", "Gümrük Görevlisi"),
]

PERMISSIONS = [
    # (id, code, description, label_ar, label_en, label_tr, category)
    # ── لوحة التحكم ──────────────────────────────────────────────────
    (1,  "view_dashboard",       "Allows access to dashboard and statistics",
     "عرض لوحة التحكم",         "View Dashboard",           "Kontrol Panelini Görüntüle", "DASHBOARD"),
    # ── المستخدمون ────────────────────────────────────────────────────
    (2,  "add_user",             "Add new user",
     "إضافة مستخدم",             "Add User",                 "Kullanıcı Ekle",             "USERS"),
    (3,  "view_users",           "View users list",
     "عرض المستخدمين",           "View Users",               "Kullanıcıları Görüntüle",    "USERS"),
    (4,  "edit_user",            "Edit user",
     "تعديل مستخدم",             "Edit User",                "Kullanıcıyı Düzenle",        "USERS"),
    (5,  "delete_user",          "Delete user",
     "حذف مستخدم",               "Delete User",              "Kullanıcıyı Sil",            "USERS"),
    # ── الأدوار ───────────────────────────────────────────────────────
    (6,  "view_roles",           "عرض جميع الأدوار",
     "عرض الأدوار",              "View Roles",               "Rolleri Görüntüle",          "USERS"),
    (7,  "add_role",             "إضافة دور جديد",
     "إضافة دور",                "Add Role",                 "Rol Ekle",                   "USERS"),
    (8,  "edit_role",            "تعديل بيانات دور",
     "تعديل دور",                "Edit Role",                "Rol Düzenle",                "USERS"),
    (9,  "delete_role",          "حذف دور",
     "حذف دور",                  "Delete Role",              "Rol Sil",                    "USERS"),
    # ── الصلاحيات ─────────────────────────────────────────────────────
    (10, "view_permissions",     "عرض جميع الصلاحيات",
     "عرض الصلاحيات",            "View Permissions",         "Yetkileri Görüntüle",        "USERS"),
    (11, "add_permission",       "إضافة صلاحية جديدة",
     "إضافة صلاحية",             "Add Permission",           "Yetki Ekle",                 "USERS"),
    (12, "edit_permission",      "تعديل بيانات صلاحية",
     "تعديل صلاحية",             "Edit Permission",          "Yetki Düzenle",              "USERS"),
    (13, "delete_permission",    "حذف صلاحية",
     "حذف صلاحية",               "Delete Permission",        "Yetki Sil",                  "USERS"),
    # ── سجل العمليات ──────────────────────────────────────────────────
    (14, "view_audit_log",       "عرض سجل جميع العمليات",
     "عرض سجل العمليات",         "View Audit Log",           "Kayıt Günlüğünü Görüntüle",  "AUDIT"),
    # ── الإعدادات ─────────────────────────────────────────────────────
    (15, "manage_settings",      "Manage system settings",
     "إدارة الإعدادات",          "Manage Settings",          "Ayarları Yönet",             "SETTINGS"),
    # ── المواد ────────────────────────────────────────────────────────
    (16, "view_materials",       "عرض قائمة المواد",
     "عرض المواد",               "View Materials",           "Malzemeleri Görüntüle",      "MATERIALS"),
    (17, "add_material",         "إضافة مادة جديدة",
     "إضافة مادة",               "Add Material",             "Malzeme Ekle",               "MATERIALS"),
    (18, "edit_material",        "تعديل بيانات مادة",
     "تعديل مادة",               "Edit Material",            "Malzeme Düzenle",            "MATERIALS"),
    (19, "delete_material",      "حذف مادة",
     "حذف مادة",                 "Delete Material",          "Malzeme Sil",                "MATERIALS"),
    # ── العملاء ───────────────────────────────────────────────────────
    (20, "view_clients",         "View clients",
     "عرض العملاء",              "View Clients",             "Müşterileri Görüntüle",      "CLIENTS"),
    (53, "add_client",           "Add new client",
     "إضافة عميل",               "Add Client",               "Müşteri Ekle",               "CLIENTS"),
    (54, "edit_client",          "Edit client",
     "تعديل عميل",               "Edit Client",              "Müşteriyi Düzenle",          "CLIENTS"),
    # ── عروض عامة (view_*) ────────────────────────────────────────────
    (21, "view_companies",       "عرض الشركات",
     "عرض الشركات",              "View Companies",           "Şirketleri Görüntüle",       "COMPANIES"),
    (22, "view_countries",       "عرض الدول",
     "عرض الدول",                "View Countries",           "Ülkeleri Görüntüle",         "VALUES"),
    (23, "view_pricing",         "عرض التسعير",
     "عرض التسعير",              "View Pricing",             "Fiyatlandırmayı Görüntüle",  "PRICING"),
    (24, "view_entries",         "View entries list and details",
     "عرض الإدخالات",            "View Entries",             "Girişleri Görüntüle",        "ENTRIES"),
    (25, "view_transactions",    "View transactions",
     "عرض المعاملات",            "View Transactions",        "İşlemleri Görüntüle",        "TRANSACTIONS"),
    (26, "view_documents",       "عرض المستندات",
     "عرض المستندات",            "View Documents",           "Belgeleri Görüntüle",        "DOCUMENTS"),
    (27, "view_values",          "عرض القيم المرجعية",
     "عرض القيم",                "View Values",              "Değerleri Görüntüle",        "VALUES"),
    (28, "view_users_roles",     "عرض المستخدمين والأدوار",
     "عرض المستخدمين والأدوار", "View Users & Roles",       "Kullanıcıları ve Rolleri Görüntüle", "USERS"),
    (29, "view_audit_trail",     "عرض سجل التدقيق",
     "عرض سجل التدقيق",         "View Audit Trail",         "Denetim İzini Görüntüle",    "AUDIT"),
    (30, "view_control_panel",   "عرض لوحة الإدارة",
     "عرض لوحة الإدارة",        "View Control Panel",       "Kontrol Panelini Görüntüle", "ADMIN"),
    # ── الدول ─────────────────────────────────────────────────────────
    (31, "add_country",          None,
     "إضافة دولة",               "Add Country",              "Ülke Ekle",                  "VALUES"),
    (32, "edit_country",         None,
     "تعديل دولة",               "Edit Country",             "Ülkeyi Düzenle",             "VALUES"),
    (33, "delete_country",       None,
     "حذف دولة",                 "Delete Country",           "Ülkeyi Sil",                 "VALUES"),
    # ── أنواع التعبئة ──────────────────────────────────────────────────
    (34, "add_packaging_type",   None,
     "إضافة نوع تعبئة",          "Add Packaging Type",       "Paketleme Türü Ekle",        "VALUES"),
    (35, "edit_packaging_type",  None,
     "تعديل نوع تعبئة",          "Edit Packaging Type",      "Paketleme Türünü Düzenle",   "VALUES"),
    (36, "delete_packaging_type", None,
     "حذف نوع تعبئة",            "Delete Packaging Type",    "Paketleme Türünü Sil",       "VALUES"),
    # ── طرق التسليم ────────────────────────────────────────────────────
    (37, "add_delivery_method",  None,
     "إضافة طريقة توصيل",        "Add Delivery Method",      "Teslimat Yöntemi Ekle",      "VALUES"),
    (38, "edit_delivery_method", None,
     "تعديل طريقة توصيل",        "Edit Delivery Method",     "Teslimat Yöntemini Düzenle", "VALUES"),
    (39, "delete_delivery_method", None,
     "حذف طريقة توصيل",          "Delete Delivery Method",   "Teslimat Yöntemini Sil",     "VALUES"),
    # ── العملات ───────────────────────────────────────────────────────
    (40, "add_currency",         None,
     "إضافة عملة",               "Add Currency",             "Para Birimi Ekle",           "VALUES"),
    (41, "edit_currency",        None,
     "تعديل عملة",               "Edit Currency",            "Para Birimini Düzenle",      "VALUES"),
    (42, "delete_currency",      None,
     "حذف عملة",                 "Delete Currency",          "Para Birimini Sil",          "VALUES"),
    # ── أنواع المواد ───────────────────────────────────────────────────
    (43, "add_material_type",    None,
     "إضافة نوع مادة",           "Add Material Type",        "Malzeme Türü Ekle",          "MATERIALS"),
    (44, "edit_material_type",   None,
     "تعديل نوع مادة",           "Edit Material Type",       "Malzeme Türünü Düzenle",     "MATERIALS"),
    (45, "delete_material_type", None,
     "حذف نوع مادة",             "Delete Material Type",     "Malzeme Türünü Sil",         "MATERIALS"),
    # ── عروض القيم الفرعية ─────────────────────────────────────────────
    (46, "view_packaging_types", None,
     "عرض أنواع التغليف",        "View Packaging Types",     "Ambalaj Türlerini Görüntüle", "VALUES"),
    (47, "view_delivery_methods", None,
     "عرض طرق التسليم",          "View Delivery Methods",    "Teslimat Yöntemlerini Görüntüle", "VALUES"),
    (48, "view_material_types",  None,
     "عرض أنواع المواد",          "View Material Types",      "Malzeme Türlerini Görüntüle", "MATERIALS"),
    (49, "view_currencies",      None,
     "عرض العملات",              "View Currencies",          "Para Birimlerini Görüntüle", "VALUES"),
    # ── الإدخالات ─────────────────────────────────────────────────────
    (50, "add_entry",            "Create new entry",
     "إضافة إدخال",              "Add Entry",                "Giriş Ekle",                 "ENTRIES"),
    (51, "edit_entry",           "Edit existing entry",
     "تعديل إدخال",              "Edit Entry",               "Girişi Düzenle",             "ENTRIES"),
    (52, "delete_entry",         "Delete entry",
     "حذف إدخال",                "Delete Entry",             "Girişi Sil",                 "ENTRIES"),
]

# صلاحيات كل دور: {role_id: [permission_ids]}
ROLE_PERMISSIONS = {
    # Admin → كل الصلاحيات
    1: list(range(1, 55)),
    # Manager → كل شيء عدا حذف الأدوار/الصلاحيات الحساسة
    3: [1,2,3,4,6,7,8,10,11,12,14,16,17,18,19,22,27,
        31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49],
    # User → عرض المواد والمعاملات والعملات فقط
    4: [16, 25, 49],
    # Accountant → لوحة التحكم، المستخدمين (عرض)، الأدوار (عرض)، الصلاحيات (عرض)، سجل العمليات، المواد
    5: [1, 3, 6, 10, 14, 16],
    # Operator → لوحة التحكم، المواد (إضافة/تعديل)
    6: [1, 16, 17, 18],
    # Viewer → لوحة التحكم، الأدوار، الصلاحيات، المواد، الدول، القيم، التغليف، التسليم، أنواع المواد، العملات
    7: [1, 6, 10, 16, 22, 27, 46, 47, 48, 49],
    # Client → لوحة التحكم، المواد فقط
    8: [1, 16],
    # Customs → لا شيء (يُحدَّد لاحقاً)
    9: [],
}

COMPANY_ROLES = [
    # (id, code, name_ar, name_en, name_tr, is_active, sort_order)
    (1,  "supplier",       "مورد",          "Supplier",       "Tedarikçi",  1, 10),
    (2,  "manufacturer",   "مصنّع",          "Manufacturer",   "Üretici",    1, 20),
    (9,  "exporter",       "مصدّر",          "Exporter",       "İhracatçı",  1, 20),
    (3,  "carrier",        "شركة نقل",       "Carrier",        "Taşıyıcı",   1, 30),
    (10, "importer",       "مستورد",         "Importer",       "İthalatçı",  1, 30),
    (4,  "forwarder",      "فورواردَر",       "Forwarder",      "Spedisyon",  1, 40),
    (11, "trader",         "تاجر",           "Trader",         "Tüccar",     1, 40),
    (5,  "customs_broker", "مخلّص جمركي",    "Customs Broker", "Gümrük",     1, 50),
    (6,  "warehouse",      "مستودع",         "Warehouse",      "Depo",       1, 60),
    (7,  "other",          "أخرى",           "Other",          "Diğer",      1, 100),
]

DOCUMENT_TYPES = [
    # (id, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order)
    (1,  "INV_EXT",               "فاتورة خارجية",            "External Invoice",
     "Dış Fatura",                1, None,              None,                                  0),
    (2,  "INV_SY",                "فاتورة سورية",             "Syrian Invoice",
     "Suriye Faturası",           1, None,              None,                                  0),
    (3,  "INV_INDIRECT",          "فاتورة بالواسطة",          "Intermediary Invoice",
     "Aracı Fatura",              1, None,              None,                                  0),
    (4,  "PACKING",               "قائمة تعبئة",              "Packing List",
     "Çeki Listesi",              1, None,              None,                                  0),
    (9,  "INV_PRO",               "بروفورما إنفويْس",         "Proforma Invoice",
     "Proforma Fatura",           1, "invoice.proforma","invoices/proforma",                   10),
    (10, "invoice.syrian.entry",  "فاتورة سورية إدخال",       "Syrian Entry Invoice",
     "Suriye Giriş Faturası",     1, "invoice.syrian",  "invoices/syrian/entry",               0),
    (11, "INV_SYR_TRANS",         None,                       None,
     None,                        1, None,              "invoices/syrian/transit/{lang}.html", 0),
    (12, "INV_SYR_INTERM",        None,                       None,
     None,                        1, None,              "invoices/syrian/intermediary/{lang}.html", 0),
    (13, "PL_EXPORT_SIMPLE",      "قائمة تعبئة – بدون تواريخ","Packing List – Simple",
     "Ambalaj Listesi – Basit",   1, None,              None,                                  0),
    (14, "PL_EXPORT_WITH_DATES",  "قائمة تعبئة – مع تواريخ", "Packing List – With Dates",
     "Ambalaj Listesi – Tarihli", 1, None,              None,                                  0),
    (15, "INV_PROFORMA",          "بروفورما إنفويْس",         "Proforma Invoice",
     "Proforma Fatura",           1, "INVPL",            None,                                  0),
    (16, "INV_NORMAL",            "فاتورة عادية",             "Normal Invoice",
     "Normal Fatura",             1, None,              None,                                  0),
    (17, "PL_EXPORT_WITH_LINE_ID","قائمة تعبئة مع رقم السطر","Packing List with Line ID",
     "Hat No'lu Paketleme Listesi",1, None,             None,                                  0),
]

PRICING_TYPES = [
    # (id, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor)
    (7,  "TON_NET",   "بالطن - حسب الصافي",   None,        None,          1, 10, "NET",   "TON",  1000.0),
    (8,  "TON_GROSS", "بالطن - حسب القائم",   None,        None,          1, 11, "GROSS", "TON",  1000.0),
    (9,  "KG_NET",    "بالكيلو - حسب الصافي", None,        None,          1, 15, "NET",   "KG",   1.0),
    (10, "KG_GROSS",  "بالكيلو - حسب القائم", None,        None,          1, 16, "GROSS", "KG",   1.0),
    (2,  "UNIT",      "حسب العدد",             "Per Unit",  "Adet Başına", 1, 20, "QTY",  "UNIT", 1.0),
]

APP_SETTINGS = [
    # (key, value, category, description)
    ("transaction_last_number",       "0",    "numbering", "آخر رقم معاملة"),
    ("transaction_prefix",            "",     "numbering", "بادئة رقم المعاملة"),
    ("transaction_auto_increment",    "true", "numbering", "تفعيل الترقيم التلقائي"),
    ("document_naming_use_transaction","true","numbering", "استخدام رقم المعاملة"),
    ("documents_output_path",         "",     "storage",   "مسار حفظ المستندات"),
]


# =============================================================================
# دوال الإدراج
# =============================================================================

def _upsert_roles(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for row in ROLES:
        rid, name, desc, label_ar, label_en, label_tr = row
        exists = cur.execute("SELECT 1 FROM roles WHERE id=?", (rid,)).fetchone()
        if exists:
            if not dry_run:
                cur.execute(
                    "UPDATE roles SET name=?, description=?, label_ar=?, label_en=?, label_tr=? WHERE id=?",
                    (name, desc, label_ar, label_en, label_tr, rid)
                )
            print(f"  [UPDATE] roles id={rid}: {name}")
        else:
            if not dry_run:
                cur.execute(
                    "INSERT INTO roles (id, name, description, label_ar, label_en, label_tr) VALUES (?,?,?,?,?,?)",
                    (rid, name, desc, label_ar, label_en, label_tr)
                )
            print(f"  [INSERT] roles id={rid}: {name}")
        count += 1
    return count


def _upsert_permissions(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for row in PERMISSIONS:
        pid, code, desc, label_ar, label_en, label_tr, category = row
        exists = cur.execute("SELECT 1 FROM permissions WHERE id=?", (pid,)).fetchone()
        if exists:
            if not dry_run:
                cur.execute(
                    "UPDATE permissions SET code=?, description=?, label_ar=?, label_en=?, label_tr=?, category=? WHERE id=?",
                    (code, desc, label_ar, label_en, label_tr, category, pid)
                )
            print(f"  [UPDATE] permissions id={pid}: {code}")
        else:
            if not dry_run:
                cur.execute(
                    "INSERT INTO permissions (id, code, description, label_ar, label_en, label_tr, category) VALUES (?,?,?,?,?,?,?)",
                    (pid, code, desc, label_ar, label_en, label_tr, category)
                )
            print(f"  [INSERT] permissions id={pid}: {code}")
        count += 1
    return count


def _upsert_role_permissions(cur: sqlite3.Cursor, dry_run: bool, reset_first: bool) -> int:
    count = 0
    if reset_first:
        print("  [RESET] حذف جميع role_permissions الحالية وإعادة إدراجها…")
        if not dry_run:
            cur.execute("DELETE FROM role_permissions")

    for role_id, perm_ids in ROLE_PERMISSIONS.items():
        for perm_id in perm_ids:
            exists = cur.execute(
                "SELECT 1 FROM role_permissions WHERE role_id=? AND permission_id=?",
                (role_id, perm_id)
            ).fetchone()
            if not exists:
                if not dry_run:
                    cur.execute(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (?,?)",
                        (role_id, perm_id)
                    )
                count += 1
    print(f"  role_permissions: {count} ربط جديد أُضيف")
    return count


def _upsert_company_roles(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for row in COMPANY_ROLES:
        rid, code, name_ar, name_en, name_tr, is_active, sort_order = row
        exists = cur.execute("SELECT 1 FROM company_roles WHERE id=?", (rid,)).fetchone()
        if exists:
            if not dry_run:
                cur.execute(
                    "UPDATE company_roles SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, sort_order=? WHERE id=?",
                    (code, name_ar, name_en, name_tr, is_active, sort_order, rid)
                )
            print(f"  [UPDATE] company_roles id={rid}: {code}")
        else:
            if not dry_run:
                cur.execute(
                    "INSERT INTO company_roles (id, code, name_ar, name_en, name_tr, is_active, sort_order) VALUES (?,?,?,?,?,?,?)",
                    (rid, code, name_ar, name_en, name_tr, is_active, sort_order)
                )
            print(f"  [INSERT] company_roles id={rid}: {code}")
        count += 1
    return count


def _upsert_document_types(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for row in DOCUMENT_TYPES:
        did, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order = row
        exists = cur.execute("SELECT 1 FROM document_types WHERE id=?", (did,)).fetchone()
        if exists:
            if not dry_run:
                cur.execute(
                    "UPDATE document_types SET code=?, name_ar=?, name_en=?, name_tr=?, is_active=?, group_code=?, template_path=?, sort_order=? WHERE id=?",
                    (code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order, did)
                )
            print(f"  [UPDATE] document_types id={did}: {code}")
        else:
            if not dry_run:
                cur.execute(
                    "INSERT INTO document_types (id, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order) VALUES (?,?,?,?,?,?,?,?,?)",
                    (did, code, name_ar, name_en, name_tr, is_active, group_code, template_path, sort_order)
                )
            print(f"  [INSERT] document_types id={did}: {code}")
        count += 1
    return count


def _upsert_pricing_types(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for row in PRICING_TYPES:
        pid, code, name_ar, name_en, name_tr, is_active, sort_order, compute_by, price_unit, divisor = row
        # تحقق هل العمود compute_by موجود في الجدول
        try:
            cur.execute("SELECT compute_by FROM pricing_types LIMIT 1")
            has_extended = True
        except sqlite3.OperationalError:
            has_extended = False

        exists = cur.execute("SELECT 1 FROM pricing_types WHERE id=?", (pid,)).fetchone()
        if exists:
            if not dry_run:
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
            print(f"  [UPDATE] pricing_types id={pid}: {code}")
        else:
            if not dry_run:
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
            print(f"  [INSERT] pricing_types id={pid}: {code}")
        count += 1
    return count


def _upsert_app_settings(cur: sqlite3.Cursor, dry_run: bool) -> int:
    count = 0
    for key, value, category, description in APP_SETTINGS:
        exists = cur.execute("SELECT 1 FROM app_settings WHERE key=?", (key,)).fetchone()
        if not exists:
            if not dry_run:
                cur.execute(
                    "INSERT INTO app_settings (key, value, category, description) VALUES (?,?,?,?)",
                    (key, value, category, description)
                )
            print(f"  [INSERT] app_settings: {key} = {repr(value)}")
            count += 1
        else:
            print(f"  [SKIP]   app_settings: {key} (موجود مسبقاً)")
    return count


# =============================================================================
# نقطة الدخول
# =============================================================================

def main():
    ap = argparse.ArgumentParser(
        description="LOGIPORT — تهيئة البيانات الأساسية لقاعدة البيانات"
    )
    ap.add_argument("--db",          default="logiport.db",
                    help="مسار ملف قاعدة البيانات (افتراضي: logiport.db)")
    ap.add_argument("--dry-run",     action="store_true",
                    help="عرض ما سيتم فعله بدون تطبيق أي تغييرات")
    ap.add_argument("--reset-perms", action="store_true",
                    help="حذف جميع role_permissions وإعادة إدراجها من الصفر")
    ap.add_argument("--backup",      action="store_true",
                    help="إنشاء نسخة احتياطية قبل التطبيق")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ قاعدة البيانات غير موجودة: {db_path}")
        print("   شغّل التطبيق أولاً لإنشاء الجداول، ثم أعد تشغيل هذا السكريبت.")
        sys.exit(1)

    if args.dry_run:
        print("=" * 60)
        print("⚠️  وضع المعاينة (DRY RUN) — لن يتم حفظ أي تغييرات")
        print("=" * 60)

    if args.backup and not args.dry_run:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.stem}.seed-backup-{ts}.db")
        shutil.copy2(db_path, backup_path)
        print(f"✅ نسخة احتياطية: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    try:
        sections = [
            ("📋 الأدوار (roles)",                 _upsert_roles,           {}),
            ("🔐 الصلاحيات (permissions)",          _upsert_permissions,     {}),
            ("🔗 ربط الأدوار بالصلاحيات",           _upsert_role_permissions, {"reset_first": args.reset_perms}),
            ("🏢 أدوار الشركات (company_roles)",    _upsert_company_roles,   {}),
            ("📄 أنواع المستندات (document_types)", _upsert_document_types,  {}),
            ("💰 أنواع التسعير (pricing_types)",    _upsert_pricing_types,   {}),
            ("⚙️  إعدادات التطبيق (app_settings)", _upsert_app_settings,    {}),
        ]

        total = 0
        for title, fn, kwargs in sections:
            print(f"\n{title}")
            print("-" * 50)
            n = fn(cur, args.dry_run, **kwargs)
            total += n

        if not args.dry_run:
            conn.commit()
            print(f"\n✅ تم الحفظ بنجاح — {total} سجل عولج")
        else:
            print(f"\n⚠️  DRY RUN — {total} عملية ستُنفَّذ عند التشغيل الفعلي")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
