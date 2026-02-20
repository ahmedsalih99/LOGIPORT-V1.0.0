"""
Components Package
==================

All UI component styles for LOGIPORT theme system.
"""

from . import buttons
from . import forms
from . import tables
from . import dialogs
from . import tabs
from . import topbar
from . import sidebar
from . import cards
from . import misc
from . import transaction_styles
from . import details_view        # ← BaseDetailsView object names
from . import dashboard_profile   # ← Dashboard / UserProfile / Notifications

__all__ = [
    "buttons",
    "forms",
    "tables",
    "dialogs",
    "tabs",
    "topbar",
    "sidebar",
    "cards",
    "misc",
    "transaction_styles",
    "details_view",
    "dashboard_profile",
]