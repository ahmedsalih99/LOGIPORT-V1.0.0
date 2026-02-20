"""
Enhanced Logging Configuration for LOGIPORT

Features:
- Rotating file handlers
- Separate error log file  
- Colored console output
- Configurable log levels
- Old logs cleanup
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        return super().format(record)


class LoggingConfig:
    """Centralized logging configuration"""

    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    DEFAULT_BACKUP_COUNT = 5

    @staticmethod
    def _default_log_dir() -> Path:
        """مجلد السجلات داخل AppData (مصدر الحقيقة الوحيد)."""
        try:
            from core.paths import logs_path
            return logs_path()
        except Exception:
            # fallback نادر أثناء التهيئة الأولى
            return Path("logs")

    @staticmethod
    def setup_logging(
            log_level: Optional[str] = None,
            log_dir: Optional[str] = None,
            enable_console: bool = True,
            enable_colors: bool = True,
    ) -> None:
        """Setup comprehensive logging system"""
        log_level = log_level or os.getenv("LOG_LEVEL", LoggingConfig.DEFAULT_LOG_LEVEL)

        if log_dir:
            log_path = Path(log_dir)
        else:
            log_path = LoggingConfig._default_log_dir()

        log_path.mkdir(exist_ok=True, parents=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        root_logger.handlers.clear()

        # Formatters
        detailed_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        if enable_console and sys.stdout is not None:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)

            is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

            if enable_colors and is_tty:
                console_handler.setFormatter(ColoredFormatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S'
                ))
            else:
                console_handler.setFormatter(detailed_format)

            root_logger.addHandler(console_handler)

        # File handler
        log_file = log_path / f"log_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LoggingConfig.DEFAULT_MAX_BYTES,
            backupCount=LoggingConfig.DEFAULT_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_format)
        root_logger.addHandler(file_handler)

        root_logger.info("Logging initialized.")

    @staticmethod
    def cleanup_old_logs(log_dir: Optional[str] = None, days_to_keep: int = 30) -> int:
        """Clean up old log files"""
        if log_dir:
            log_path = Path(log_dir)
        else:
            log_path = LoggingConfig._default_log_dir()

        if not log_path.exists():
            return 0

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0

        for log_file in log_path.glob("*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
            except Exception:
                pass

        return deleted_count