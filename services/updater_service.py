"""
services/updater_service.py — LOGIPORT
========================================
نظام التحديثات التلقائية عبر GitHub Releases.

الطريقة:
  1. يتحقق من آخر إصدار على GitHub API في الخلفية
  2. إذا وجد إصدار أحدث → يُرسل إشعار للمستخدم
  3. المستخدم يضغط "تحديث" → يُنزّل الـ installer ويشغّله
  4. الـ installer الجديد يُغلق البرنامج ويُثبّت التحديث

يعمل في thread منفصل — لا يُجمّد الواجهة أبداً.
"""

from __future__ import annotations
from core.singleton import SingletonMeta

import logging
import os
import sys
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional, Callable
from packaging.version import Version

logger = logging.getLogger(__name__)


def _current_version() -> str:
    try:
        from version import VERSION
        return VERSION
    except Exception:
        return "0.0.0"


def _github_repo() -> str:
    try:
        from version import GITHUB_REPO
        return GITHUB_REPO
    except Exception:
        return ""


def _download_url(version: str) -> str:
    try:
        from version import DOWNLOAD_URL_TEMPLATE
        return DOWNLOAD_URL_TEMPLATE.format(version=version)
    except Exception:
        repo = _github_repo()
        return f"https://github.com/{repo}/releases/download/v{version}/LOGIPORT_Setup_{version}.exe"


# ─────────────────────────────────────────────────────────────────────────────

class UpdateInfo:
    """معلومات الإصدار الجديد."""
    def __init__(self, version: str, url: str, notes: str = ""):
        self.version  = version
        self.url      = url
        self.notes    = notes

    def __repr__(self):
        return f"UpdateInfo(version={self.version})"


class UpdaterService(metaclass=SingletonMeta):
    """
    خدمة التحديثات — Singleton.

    الاستخدام:
        svc = UpdaterService.get_instance()
        svc.check_async(on_update_found=my_callback)
    """

    def __init__(self):
        self._checking = False
        self._last_info: Optional[UpdateInfo] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def check_async(
        self,
        on_update_found: Optional[Callable[[UpdateInfo], None]] = None,
        on_no_update:    Optional[Callable[[], None]] = None,
        on_error:        Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        يتحقق من التحديثات في الخلفية.
        on_update_found(info) تُستدعى إذا وجد إصدار أحدث.
        """
        if self._checking:
            logger.debug("Already checking for updates")
            return

        thread = threading.Thread(
            target=self._check_worker,
            args=(on_update_found, on_no_update, on_error),
            daemon=True,
            name="UpdateChecker",
        )
        thread.start()

    def download_and_install(
        self,
        info: UpdateInfo,
        on_progress: Optional[Callable[[int], None]] = None,
        on_done:     Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        """
        يُنزّل الـ installer ويشغّله في الخلفية.
        on_progress(percent) تُستدعى أثناء التنزيل.
        on_done(success, message) تُستدعى عند الانتهاء.
        """
        thread = threading.Thread(
            target=self._download_worker,
            args=(info, on_progress, on_done),
            daemon=True,
            name="UpdateDownloader",
        )
        thread.start()

    @property
    def last_update_info(self) -> Optional[UpdateInfo]:
        return self._last_info

    # ── Workers ───────────────────────────────────────────────────────────────

    def _check_worker(self, on_found, on_no_update, on_error):
        self._checking = True
        try:
            info = self._fetch_latest()
            if info:
                self._last_info = info
                logger.info(f"Update available: {info.version}")
                if on_found:
                    on_found(info)
            else:
                logger.info("No update available")
                if on_no_update:
                    on_no_update()
        except Exception as e:
            logger.warning(f"Update check failed: {e}")
            if on_error:
                on_error(str(e))
        finally:
            self._checking = False

    def _fetch_latest(self) -> Optional[UpdateInfo]:
        """يتحقق من GitHub API."""
        import urllib.request
        import json

        repo = _github_repo()
        if not repo or repo == "YOUR_GITHUB_USERNAME/LOGIPORT":
            logger.warning("GitHub repo not configured in version.py")
            return None

        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"LOGIPORT/{_current_version()}"}
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        tag = data.get("tag_name", "").lstrip("v")
        notes = data.get("body", "")

        if not tag:
            return None

        # مقارنة الإصدارات
        try:
            if Version(tag) <= Version(_current_version()):
                return None
        except Exception:
            if tag == _current_version():
                return None

        download_url = _download_url(tag)

        # نبحث عن الـ asset الصحيح في الـ release
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith(".exe") and "Setup" in name:
                download_url = asset["browser_download_url"]
                break

        return UpdateInfo(version=tag, url=download_url, notes=notes)

    def _download_worker(self, info: UpdateInfo, on_progress, on_done):
        try:
            import urllib.request

            # مجلد temp
            tmp_dir = Path(tempfile.gettempdir()) / "LOGIPORT_Update"
            tmp_dir.mkdir(exist_ok=True)
            installer_path = tmp_dir / f"LOGIPORT_Setup_{info.version}.exe"

            logger.info(f"Downloading update from: {info.url}")

            def _reporthook(count, block_size, total_size):
                if total_size > 0 and on_progress:
                    percent = min(100, int(count * block_size * 100 / total_size))
                    on_progress(percent)

            urllib.request.urlretrieve(info.url, str(installer_path), _reporthook)

            if on_progress:
                on_progress(100)

            logger.info(f"Downloaded to: {installer_path}")

            # شغّل الـ installer — /SILENT يثبّت بصمت، /CLOSEAPPLICATIONS يُغلق البرنامج
            subprocess.Popen(
                [str(installer_path), "/SILENT", "/CLOSEAPPLICATIONS"],
                creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
            )

            if on_done:
                on_done(True, str(installer_path))

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if on_done:
                on_done(False, str(e))