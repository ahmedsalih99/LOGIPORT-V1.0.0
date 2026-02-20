"""
LOGIPORT Constants - Single Source of Truth
============================================

This file contains all constants used across the application.
Using constants instead of magic strings prevents typos and makes refactoring easier.

Created: 2025-01-29
"""

class DatabaseFields:
    """
    Database field names - SINGLE SOURCE OF TRUTH

    Usage:
        from constants import DatabaseFields as DB
        transaction_no = data.get(DB.TRANSACTION_NO)
    """

    # ==================== Common Fields ====================
    ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CREATED_BY_ID = "created_by_id"
    UPDATED_BY_ID = "updated_by_id"
    NOTES = "notes"

    # ==================== Transaction Fields ====================
    TRANSACTION_NO = "transaction_no"
    TRANSACTION_DATE = "transaction_date"
    TRANSACTION_TYPE = "transaction_type"
    CLIENT_ID = "client_id"
    EXPORTER_COMPANY_ID = "exporter_company_id"  # ✅ CORRECT
    IMPORTER_COMPANY_ID = "importer_company_id"  # ✅ CORRECT
    RELATIONSHIP_TYPE = "relationship_type"
    BROKER_COMPANY_ID = "broker_company_id"
    ORIGIN_COUNTRY_ID = "origin_country_id"
    DEST_COUNTRY_ID = "dest_country_id"
    CURRENCY_ID = "currency_id"
    PRICING_TYPE_ID = "pricing_type_id"
    DELIVERY_METHOD_ID = "delivery_method_id"
    TRANSPORT_TYPE = "transport_type"
    TRANSPORT_REF = "transport_ref"

    # Transaction totals
    TOTALS_COUNT = "totals_count"
    TOTALS_GROSS_KG = "totals_gross_kg"
    TOTALS_NET_KG = "totals_net_kg"
    TOTALS_VALUE = "totals_value"

    # ==================== Entry Fields ====================
    ENTRY_NO = "entry_no"
    ENTRY_DATE = "entry_date"
    TRANSPORT_UNIT_TYPE = "transport_unit_type"
    SEAL_NO = "seal_no"
    OWNER_CLIENT_ID = "owner_client_id"

    # ==================== Item Fields ====================
    MATERIAL_ID = "material_id"
    PACKAGING_TYPE_ID = "packaging_type_id"
    QUANTITY = "quantity"
    COUNT = "count"
    GROSS_WEIGHT_KG = "gross_weight_kg"
    NET_WEIGHT_KG = "net_weight_kg"
    UNIT_PRICE = "unit_price"
    LINE_TOTAL = "line_total"

    # ==================== Entity Name Fields ====================
    NAME_AR = "name_ar"
    NAME_EN = "name_en"
    NAME_TR = "name_tr"
    CODE = "code"

    # ==================== User Fields ====================
    USERNAME = "username"
    EMAIL = "email"
    FULL_NAME = "full_name"
    ROLE_ID = "role_id"


class UserRoles:
    """User role IDs and names — يجب أن تتطابق مع قيم database/bootstrap.py"""
    ADMIN       = 1
    MANAGER     = 3   # ← تغيّر من 2 إلى 3 ليتطابق مع DB
    USER        = 4   # ← تغيّر من 3 إلى 4 ليتطابق مع DB
    ACCOUNTANT  = 5
    OPERATOR    = 6
    VIEWER      = 7
    CLIENT      = 8
    CUSTOMS     = 9

    NAMES = {
        ADMIN:      "Admin",
        MANAGER:    "Manager",
        USER:       "User",
        ACCOUNTANT: "Accountant",
        OPERATOR:   "Operator",
        VIEWER:     "Viewer",
        CLIENT:     "Client",
        CUSTOMS:    "Customs",
    }

    @classmethod
    def get_name(cls, role_id: int) -> str:
        """Get role name by ID"""
        return cls.NAMES.get(role_id, "Unknown")

    @classmethod
    def is_admin(cls, role_id: int) -> bool:
        """Check if role is admin"""
        return role_id == cls.ADMIN


class TransactionStatus:
    """Transaction status values"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    CHOICES = [ACTIVE, CANCELLED, COMPLETED]

    LABELS = {
        ACTIVE: {"ar": "نشط", "en": "Active", "tr": "Aktif"},
        CANCELLED: {"ar": "ملغي", "en": "Cancelled", "tr": "İptal"},
        COMPLETED: {"ar": "مكتمل", "en": "Completed", "tr": "Tamamlandı"},
    }


class TransactionType:
    """Transaction type values"""
    EXPORT = "export"
    IMPORT = "import"
    TRANSIT = "transit"

    CHOICES = [EXPORT, IMPORT, TRANSIT]

    LABELS = {
        EXPORT: {"ar": "تصدير", "en": "Export", "tr": "İhracat"},
        IMPORT: {"ar": "استيراد", "en": "Import", "tr": "İthalat"},
        TRANSIT: {"ar": "ترانزيت", "en": "Transit", "tr": "Transit"},
    }


class RelationshipType:
    """Company relationship types"""
    DIRECT = "direct"
    INTERMEDIARY = "intermediary"
    BY_REQUEST = "by_request"
    ON_BEHALF = "on_behalf"

    CHOICES = [DIRECT, INTERMEDIARY, BY_REQUEST, ON_BEHALF]

    LABELS = {
        DIRECT: {"ar": "مباشر", "en": "Direct", "tr": "Doğrudan"},
        INTERMEDIARY: {"ar": "وسيط", "en": "Intermediary", "tr": "Aracı"},
        BY_REQUEST: {"ar": "بطلب", "en": "By Request", "tr": "Talep Üzerine"},
        ON_BEHALF: {"ar": "بالنيابة", "en": "On Behalf", "tr": "Adına"},
    }


class TransportType:
    """Transport type values"""
    ROAD = "road"
    SEA = "sea"
    AIR = "air"
    RAIL = "rail"

    CHOICES = [ROAD, SEA, AIR, RAIL]

    LABELS = {
        ROAD: {"ar": "بري", "en": "Road", "tr": "Kara"},
        SEA: {"ar": "بحري", "en": "Sea", "tr": "Deniz"},
        AIR: {"ar": "جوي", "en": "Air", "tr": "Hava"},
        RAIL: {"ar": "سكك حديدية", "en": "Rail", "tr": "Demiryolu"},
    }


class TransportUnitType:
    """Transport unit type values"""
    CONTAINER = "container"
    TRUCK = "truck"
    SHIP = "ship"
    PLANE = "plane"
    TRAIN = "train"

    CHOICES = [CONTAINER, TRUCK, SHIP, PLANE, TRAIN]


class PricingCode:
    """Pricing type codes"""
    UNIT = "UNIT"
    PCS = "PCS"
    PIECE = "PIECE"
    KG = "KG"
    KILO = "KILO"
    KG_NET = "KG_NET"
    KG_GROSS = "KG_GROSS"
    GROSS = "GROSS"
    BRUT = "BRUT"
    TON = "TON"
    TON_NET = "TON_NET"
    TON_GROSS = "TON_GROSS"
    T = "T"
    MT = "MT"


class ComputeBy:
    """How to compute pricing"""
    QTY = "QTY"
    NET = "NET"
    GROSS = "GROSS"


class PriceUnit:
    """Price unit"""
    UNIT = "UNIT"
    KG = "KG"
    TON = "TON"


class UIConstants:
    """UI-related constants"""
    DEFAULT_ROWS_PER_PAGE = 50
    MAX_ROWS_PER_PAGE = 200
    DEFAULT_TIMEOUT = 30  # seconds

    # Colors
    COLOR_SUCCESS = "#4CAF50"
    COLOR_ERROR = "#F44336"
    COLOR_WARNING = "#FF9800"
    COLOR_INFO = "#2196F3"
    COLOR_PRIMARY = "#2196F3"

    # Sizes
    MIN_WINDOW_WIDTH = 1024
    MIN_WINDOW_HEIGHT = 768


class AuditActions:
    """Audit log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
    BULK_INSERT = "bulk_insert"


# Helper function for getting localized labels
def get_label(enum_class, value: str, lang: str = "ar") -> str:
    """
    Get localized label for enum value

    Usage:
        label = get_label(TransactionType, "export", "ar")  # "تصدير"
    """
    if hasattr(enum_class, 'LABELS'):
        labels = getattr(enum_class, 'LABELS')
        if value in labels:
            return labels[value].get(lang, value)
    return value


if __name__ == "__main__":
    # Test constants
    print("✅ Constants loaded successfully")
    print(f"Admin role ID: {UserRoles.ADMIN}")
    print(f"Transaction types: {TransactionType.CHOICES}")
    print(f"Export label (AR): {get_label(TransactionType, TransactionType.EXPORT, 'ar')}")