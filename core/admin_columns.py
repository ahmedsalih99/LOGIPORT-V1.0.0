"""
Admin Columns Utility - LOGIPORT

Utility for showing/hiding admin-only columns in Qt tables.
Enhanced with better error handling and flexibility.
"""
import logging
from typing import Iterable, Optional, Any, Union, List
from PySide6.QtWidgets import QTableWidget, QTableView, QHeaderView

from core.permissions import is_admin

logger = logging.getLogger(__name__)

# Type alias for table widgets
TableWidget = Union[QTableWidget, QTableView]


def apply_admin_columns_to_table(
        table: TableWidget,
        current_user: Any,
        admin_cols: Iterable[int],
        *,
        force_admin: Optional[bool] = None,
) -> bool:
    """
    Show/hide admin-only columns in a table.

    Args:
        table: QTableWidget or QTableView instance
        current_user: Current user object
        admin_cols: Column indices that should be admin-only
        force_admin: Force admin status (for testing)

    Returns:
        True if user is admin (columns shown), False otherwise

    Example:
        >>> apply_admin_columns_to_table(
        ...     table=users_table,
        ...     current_user=current_user,
        ...     admin_cols=[5, 6, 7]  # ID, Role, Actions columns
        ... )
        True  # User is admin, columns visible
    """
    if not table:
        logger.warning("No table provided to apply_admin_columns_to_table")
        return False

    # Determine if user is admin
    if force_admin is not None:
        admin = bool(force_admin)
        logger.debug(f"Using forced admin status: {admin}")
    else:
        admin = is_admin(current_user)

    # Convert to list for validation
    admin_col_list = list(admin_cols)

    if not admin_col_list:
        logger.debug("No admin columns specified")
        return admin

    # Get column count (if possible)
    try:
        if isinstance(table, QTableWidget):
            col_count = table.columnCount()
        else:
            # QTableView with model
            model = table.model()
            col_count = model.columnCount() if model else 0
    except Exception as e:
        logger.warning(f"Could not get column count: {e}")
        col_count = None

    # Apply column visibility
    hidden_count = 0
    shown_count = 0

    for col in admin_col_list:
        try:
            col_int = int(col)

            # Validate column index
            if col_count is not None and col_int >= col_count:
                logger.warning(f"Column {col_int} out of range (max: {col_count - 1})")
                continue

            # Set visibility
            table.setColumnHidden(col_int, not admin)

            if admin:
                shown_count += 1
            else:
                hidden_count += 1

        except ValueError:
            logger.error(f"Invalid column index: {col}")
        except Exception as e:
            logger.error(f"Error setting column {col} visibility: {e}")

    # Log result
    if admin:
        logger.debug(f"Admin user: shown {shown_count} admin columns")
    else:
        logger.debug(f"Non-admin user: hidden {hidden_count} admin columns")

    return admin


def get_admin_columns_indices(
        table: TableWidget,
        column_names: List[str]
) -> List[int]:
    """
    Get column indices by column names.

    Args:
        table: QTableWidget or QTableView instance
        column_names: List of column header names

    Returns:
        List of column indices

    Example:
        >>> indices = get_admin_columns_indices(
        ...     table=users_table,
        ...     column_names=['ID', 'Role', 'Actions']
        ... )
        [0, 5, 8]
    """
    indices = []

    try:
        if isinstance(table, QTableWidget):
            # QTableWidget
            col_count = table.columnCount()
            for col in range(col_count):
                header_item = table.horizontalHeaderItem(col)
                if header_item:
                    header_text = header_item.text()
                    if header_text in column_names:
                        indices.append(col)
        else:
            # QTableView with model
            model = table.model()
            if model:
                col_count = model.columnCount()
                for col in range(col_count):
                    header_text = model.headerData(col, 1)  # Qt.Horizontal = 1
                    if header_text in column_names:
                        indices.append(col)

    except Exception as e:
        logger.error(f"Error getting column indices: {e}")

    return indices


def hide_columns(table: TableWidget, columns: Iterable[int]) -> int:
    """
    Hide specific columns.

    Args:
        table: QTableWidget or QTableView instance
        columns: Column indices to hide

    Returns:
        Number of columns hidden
    """
    hidden = 0

    for col in columns:
        try:
            table.setColumnHidden(int(col), True)
            hidden += 1
        except Exception as e:
            logger.error(f"Error hiding column {col}: {e}")

    logger.debug(f"Hidden {hidden} columns")
    return hidden


def show_columns(table: TableWidget, columns: Iterable[int]) -> int:
    """
    Show specific columns.

    Args:
        table: QTableWidget or QTableView instance
        columns: Column indices to show

    Returns:
        Number of columns shown
    """
    shown = 0

    for col in columns:
        try:
            table.setColumnHidden(int(col), False)
            shown += 1
        except Exception as e:
            logger.error(f"Error showing column {col}: {e}")

    logger.debug(f"Shown {shown} columns")
    return shown


def toggle_columns(table: TableWidget, columns: Iterable[int]) -> int:
    """
    Toggle visibility of specific columns.

    Args:
        table: QTableWidget or QTableView instance
        columns: Column indices to toggle

    Returns:
        Number of columns toggled
    """
    toggled = 0

    for col in columns:
        try:
            col_int = int(col)
            is_hidden = table.isColumnHidden(col_int)
            table.setColumnHidden(col_int, not is_hidden)
            toggled += 1
        except Exception as e:
            logger.error(f"Error toggling column {col}: {e}")

    logger.debug(f"Toggled {toggled} columns")
    return toggled


def auto_resize_columns(
        table: TableWidget,
        mode: str = "stretch_last"
):
    try:
        header = table.horizontalHeader()

        # 🔥 مهم جداً
        table.setMinimumWidth(0)
        table.setSizePolicy(
            table.sizePolicy().Expanding,
            table.sizePolicy().Expanding
        )

        if mode == "content":
            # 🚫 لا تستخدم هذا في نوافذ رئيسية
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.resizeSections(QHeaderView.ResizeToContents)

        elif mode == "stretch":
            header.setSectionResizeMode(QHeaderView.Stretch)

        elif mode == "stretch_last":
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setStretchLastSection(True)

        elif mode == "interactive":
            header.setSectionResizeMode(QHeaderView.Interactive)

    except Exception as e:
        logger.error(f"Error setting column resize mode: {e}")



def apply_permission_based_columns(
        table: TableWidget,
        current_user: Any,
        column_permissions: dict
) -> None:
    """
    Apply column visibility based on permissions.

    Args:
        table: QTableWidget or QTableView instance
        current_user: Current user object
        column_permissions: Dict mapping column index to permission code
            Example: {5: 'view_user_id', 6: 'view_role', 7: 'manage_users'}
    """
    from core.permissions import has_perm

    for col, permission in column_permissions.items():
        try:
            col_int = int(col)
            has_permission = has_perm(current_user, permission)
            table.setColumnHidden(col_int, not has_permission)

            logger.debug(
                f"Column {col_int}: "
                f"{'visible' if has_permission else 'hidden'} "
                f"(requires: {permission})"
            )

        except Exception as e:
            logger.error(
                f"Error applying permission for column {col}: {e}"
            )


# Example usage
if __name__ == "__main__":
    """
    Example usage of admin columns utilities.
    """
    from PySide6.QtWidgets import QApplication, QTableWidget
    import sys

    # Create application
    app = QApplication(sys.argv)

    # Create table
    table = QTableWidget(10, 8)
    table.setHorizontalHeaderLabels([
        "Name", "Email", "Phone", "Address",
        "ID", "Role", "Created", "Actions"
    ])


    # Mock user
    class User:
        role_id = 1  # Admin


    user = User()

    # Apply admin columns (hide columns 4, 5, 6, 7 for non-admin)
    is_admin_user = apply_admin_columns_to_table(
        table=table,
        current_user=user,
        admin_cols=[4, 5, 6, 7]
    )

    print(f"User is admin: {is_admin_user}")

    # Show table
    table.show()

    sys.exit(app.exec())