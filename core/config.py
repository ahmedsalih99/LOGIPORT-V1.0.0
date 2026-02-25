"""
Enhanced Configuration Manager with Environment Variables Support

Usage:
    from core.config import config

    db_url = config.get("DATABASE_URL")
    debug = config.get_bool("DEBUG")
"""
import os
import json
import logging
from core.singleton import SingletonMeta
from typing import Any, Optional, Dict
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


class Config(metaclass=SingletonMeta):
    """
    Unified configuration manager that supports:
    - Environment variables (.env)
    - JSON configuration files
    - Default values
    - Type conversion
    - Validation
    """

    def __init__(self):
        self._env_loaded = False
        self._config_cache: Dict[str, Any] = {}
        self._config_file_path = Path("config/settings.json")

        # Load environment variables
        self._load_env()

        # Load JSON config
        self._load_json_config()

    def _load_env(self):
        """Load environment variables from .env file"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            self._env_loaded = True
            logger.info("Environment variables loaded from .env")
        else:
            logger.warning(".env file not found, using system environment only")

    def _load_json_config(self):
        """Load configuration from JSON file"""
        if self._config_file_path.exists():
            try:
                with open(self._config_file_path, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
                logger.info(f"Configuration loaded from {self._config_file_path}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
                self._config_cache = {}
        else:
            logger.warning(f"Config file not found: {self._config_file_path}")
            self._config_cache = {}

    def get(
            self,
            key: str,
            default: Any = None,
            required: bool = False,
            from_env: bool = True
    ) -> Any:
        """
        Get configuration value.

        Priority order:
        1. Environment variable (if from_env=True)
        2. JSON config file
        3. Default value

        Args:
            key: Configuration key
            default: Default value if not found
            required: Raise error if not found and no default
            from_env: Check environment variables first

        Returns:
            Configuration value

        Raises:
            ConfigurationError: If required=True and key not found
        """
        # 1. Try environment variable
        if from_env:
            env_value = os.getenv(key)
            if env_value is not None:
                return env_value

        # 2. Try JSON config
        if key in self._config_cache:
            return self._config_cache[key]

        # 3. Use default
        if default is not None:
            return default

        # 4. Error if required
        if required:
            raise ConfigurationError(
                f"Required configuration '{key}' not found. "
                f"Set it in .env or {self._config_file_path}"
            )

        return None

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, default)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')

        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.get(key, default)

        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid int value for '{key}': {value}, using default")
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float configuration value"""
        value = self.get(key, default)

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for '{key}': {value}, using default")
            return default

    def get_list(self, key: str, default: list = None, separator: str = ',') -> list:
        """
        Get list configuration value.

        Supports:
        - JSON arrays: ["item1", "item2"]
        - Comma-separated strings: "item1,item2,item3"
        """
        if default is None:
            default = []

        value = self.get(key, default)

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            return [item.strip() for item in value.split(separator) if item.strip()]

        return default

    def get_path(self, key: str, default: str = None) -> Path:
        """Get Path configuration value"""
        value = self.get(key, default)
        return Path(value) if value else Path(default) if default else Path(".")

    def set(self, key: str, value: Any, persist: bool = False):
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            persist: Save to JSON config file
        """
        self._config_cache[key] = value

        if persist:
            self._save_json_config()

    def _save_json_config(self):
        """Save configuration to JSON file"""
        try:
            # Ensure directory exists
            self._config_file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_cache, f, indent=4, ensure_ascii=False)

            logger.info(f"Configuration saved to {self._config_file_path}")
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")

    def validate(self, schema: Dict[str, Dict[str, Any]]):
        """
        Validate configuration against schema.

        Example schema:
        {
            "DATABASE_URL": {
                "type": str,
                "required": True,
                "pattern": r"^(sqlite|postgresql)://.*"
            },
            "DEBUG": {
                "type": bool,
                "required": False,
                "default": False
            }
        }
        """
        errors = []

        for key, rules in schema.items():
            # Check required
            if rules.get("required", False):
                value = self.get(key)
                if value is None:
                    errors.append(f"Required config '{key}' is missing")
                    continue

            # Check type
            if "type" in rules:
                value = self.get(key)
                if value is not None and not isinstance(value, rules["type"]):
                    errors.append(
                        f"Config '{key}' must be {rules['type'].__name__}, "
                        f"got {type(value).__name__}"
                    )

            # Check pattern (for strings)
            if "pattern" in rules:
                import re
                value = self.get(key)
                if value and not re.match(rules["pattern"], str(value)):
                    errors.append(
                        f"Config '{key}' does not match pattern {rules['pattern']}"
                    )

        if errors:
            raise ConfigurationError(
                f"Configuration validation failed:\n" + "\n".join(f"- {e}" for e in errors)
            )

    def all(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        # Merge env vars and config cache
        result = dict(self._config_cache)

        # Add relevant environment variables
        for key, value in os.environ.items():
            if key.isupper() and key not in result:
                result[key] = value

        return result

    def reload(self):
        """Reload configuration from files"""
        self._load_env()
        self._load_json_config()
        logger.info("Configuration reloaded")


# Singleton instance
config = Config.get_instance()


# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return config.get(key, default)


def get_database_url() -> str:
    """Get database URL with validation"""
    db_url = config.get("DATABASE_URL", required=True)

    if not db_url:
        raise ConfigurationError(
            "DATABASE_URL is not set. "
            "Add it to .env file: DATABASE_URL=sqlite:///logiport.db"
        )

    return db_url


def is_debug_mode() -> bool:
    """Check if application is in debug mode"""
    return config.get_bool("DEBUG", default=False)


def get_log_level() -> str:
    """Get logging level"""
    return config.get("LOG_LEVEL", default="INFO").upper()


# Configuration schema for validation
CONFIG_SCHEMA = {
    "DATABASE_URL": {
        "type": str,
        "required": True,
        "pattern": r"^(sqlite|postgresql|mysql)://.*"
    },
    "SECRET_KEY": {
        "type": str,
        "required": True,
    },
    "DEBUG": {
        "type": bool,
        "required": False,
        "default": False
    },
    "LOG_LEVEL": {
        "type": str,
        "required": False,
        "default": "INFO"
    }
}


def validate_config():
    """Validate configuration on startup"""
    try:
        config.validate(CONFIG_SCHEMA)
        logger.info("Configuration validated successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise


if __name__ == "__main__":
    # Example usage
    print("Configuration loaded:")
    print(f"DATABASE_URL: {config.get('DATABASE_URL')}")
    print(f"DEBUG: {config.get_bool('DEBUG')}")
    print(f"LOG_LEVEL: {get_log_level()}")

    # Validate
    try:
        validate_config()
        print("\n✓ Configuration is valid")
    except ConfigurationError as e:
        print(f"\n✗ Configuration error: {e}")