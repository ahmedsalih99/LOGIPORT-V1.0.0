"""
Singleton Pattern Implementation - LOGIPORT

Provides thread-safe singleton metaclass and decorator.
"""
import threading
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """
    Thread-safe singleton metaclass.

    Usage:
        class MyClass(metaclass=SingletonMeta):
            pass

        obj1 = MyClass()
        obj2 = MyClass()
        assert obj1 is obj2  # Same instance
    """

    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """
        Control instance creation.
        Thread-safe singleton pattern.
        """
        # Check if instance exists (fast path without lock)
        if cls not in cls._instances:
            # Acquire lock for thread safety
            with cls._lock:
                # Double-check after acquiring lock
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    logger.debug(f"Created singleton instance: {cls.__name__}")

        return cls._instances[cls]

    @classmethod
    def clear_instance(mcs, cls: type) -> None:
        """
        Clear singleton instance (useful for testing).

        Args:
            cls: Class to clear instance for
        """
        with mcs._lock:
            if cls in mcs._instances:
                del mcs._instances[cls]
                logger.debug(f"Cleared singleton instance: {cls.__name__}")

    @classmethod
    def clear_all_instances(mcs) -> None:
        """Clear all singleton instances (useful for testing)."""
        with mcs._lock:
            count = len(mcs._instances)
            mcs._instances.clear()
            logger.debug(f"Cleared {count} singleton instances")


def singleton(cls):
    """
    Singleton decorator (alternative to metaclass).

    Usage:
        @singleton
        class MyClass:
            pass

        obj1 = MyClass()
        obj2 = MyClass()
        assert obj1 is obj2  # Same instance

    Args:
        cls: Class to make singleton

    Returns:
        Wrapped class with singleton behavior
    """
    instances = {}
    lock = threading.Lock()

    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
                    logger.debug(f"Created singleton instance: {cls.__name__}")
        return instances[cls]

    # Add clear method
    def clear_instance():
        with lock:
            if cls in instances:
                del instances[cls]
                logger.debug(f"Cleared singleton instance: {cls.__name__}")

    get_instance.clear_instance = clear_instance
    get_instance.__name__ = cls.__name__
    get_instance.__doc__ = cls.__doc__

    return get_instance


class Singleton:
    """
    Singleton base class (inheritance approach).

    Usage:
        class MyClass(Singleton):
            pass

        obj1 = MyClass.get_instance()
        obj2 = MyClass.get_instance()
        assert obj1 is obj2  # Same instance
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Prevent direct instantiation."""
        raise TypeError(
            f"{cls.__name__} is a singleton. "
            f"Use {cls.__name__}.get_instance() instead."
        )

    @classmethod
    def get_instance(cls):
        """
        Get singleton instance.

        Returns:
            Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Bypass __new__ for singleton creation
                    instance = object.__new__(cls)
                    instance.__init__()
                    cls._instance = instance
                    logger.debug(f"Created singleton instance: {cls.__name__}")

        return cls._instance

    @classmethod
    def clear_instance(cls):
        """Clear singleton instance (useful for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance = None
                logger.debug(f"Cleared singleton instance: {cls.__name__}")


# Example usage and tests
if __name__ == "__main__":
    # Test 1: Metaclass approach
    class ConfigManager(metaclass=SingletonMeta):
        def __init__(self):
            self.config = {}


    config1 = ConfigManager()
    config2 = ConfigManager()
    print(f"Metaclass test: {config1 is config2}")  # True


    # Test 2: Decorator approach
    @singleton
    class Logger:
        def __init__(self):
            self.logs = []


    logger1 = Logger()
    logger2 = Logger()
    print(f"Decorator test: {logger1 is logger2}")  # True


    # Test 3: Base class approach
    class DatabaseConnection(Singleton):
        def __init__(self):
            self.connection = "Connected"


    db1 = DatabaseConnection.get_instance()
    db2 = DatabaseConnection.get_instance()
    print(f"Base class test: {db1 is db2}")  # True

    # Test 4: Thread safety
    import concurrent.futures

    instances = []


    def create_instance():
        return ConfigManager()


    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_instance) for _ in range(100)]
        instances = [f.result() for f in futures]

    # All instances should be the same
    print(f"Thread safety test: {all(inst is instances[0] for inst in instances)}")  # True