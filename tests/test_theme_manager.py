import sys
import pytest
from PySide6.QtWidgets import QApplication

from core.theme_manager import ThemeManager


@pytest.fixture(scope="session")
def app():
    return QApplication(sys.argv)


def test_apply_light_theme(app):
    tm = ThemeManager.get_instance()

    result = tm.apply_theme(
        theme_name="light",
        font_size=13,
        font_family="Tajawal"
    )

    assert result is True
    assert tm.get_current_theme() == "light"
    assert tm.get_current_font_size() == 13
    assert tm.get_current_font_family() == "Tajawal"

    stylesheet = app.styleSheet()
    assert len(stylesheet) > 0
    assert "qlineargradient" in stylesheet
    assert "rgba" in stylesheet
