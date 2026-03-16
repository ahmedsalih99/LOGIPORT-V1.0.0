"""
ui/dialogs/mixins
==================
Mixins لـ AddTransactionWindow — كل mixin تضيف تبويباً أو قسماً.

الاستخدام:
    from ui.dialogs.mixins import (
        GeneralTabMixin,
        PartiesGeoTabMixin,
        ItemsTabMixin,
        DocumentsTabMixin,
        TransportTabMixin,
    )
"""
from .general_tab    import GeneralTabMixin
from .parties_geo_tab import PartiesGeoTabMixin
from .items_tab      import ItemsTabMixin
from .documents_tab  import DocumentsTabMixin
from .transport_tab  import TransportTabMixin

__all__ = [
    "GeneralTabMixin",
    "PartiesGeoTabMixin",
    "ItemsTabMixin",
    "DocumentsTabMixin",
    "TransportTabMixin",
]