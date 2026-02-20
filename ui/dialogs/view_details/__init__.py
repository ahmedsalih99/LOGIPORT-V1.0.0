# -*- coding: utf-8 -*-
"""
view_details — حزمة dialogs عرض التفاصيل
"""
from .view_client_dialog          import ViewClientDialog
from .view_company_dialog         import ViewCompanyDialog
from .view_country_dialog         import ViewCountryDialog
from .view_currency_dialog        import ViewCurrencyDialog
from .view_delivery_method_dialog import ViewDeliveryMethodDialog
from .view_entry_dialog           import ViewEntryDialog
from .view_material_dialog        import ViewMaterialDialog
from .view_material_type_dialog   import ViewMaterialTypeDialog
from .view_packaging_type_dialog  import ViewPackagingTypeDialog
from .view_pricing_dialog         import ViewPricingDialog
from .view_role_dialog            import ViewRoleDialog
from .view_transaction_dialog     import ViewTransactionDialog
from .view_user_dialog            import ViewUserDialog

__all__ = [
    "ViewClientDialog",
    "ViewCompanyDialog",
    "ViewCountryDialog",
    "ViewCurrencyDialog",
    "ViewDeliveryMethodDialog",
    "ViewEntryDialog",
    "ViewMaterialDialog",
    "ViewMaterialTypeDialog",
    "ViewPackagingTypeDialog",
    "ViewPricingDialog",
    "ViewRoleDialog",
    "ViewTransactionDialog",
    "ViewUserDialog",
]
