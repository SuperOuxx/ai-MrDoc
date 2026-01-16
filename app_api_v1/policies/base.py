from enum import Enum
from typing import Any

from django.contrib.auth import get_user_model


User = get_user_model()


class Action(Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"


class BasePolicy:
    """Base class for permission policies."""

    @staticmethod
    def is_superuser(user: Any) -> bool:
        return bool(user and getattr(user, "is_authenticated", False) and getattr(user, "is_superuser", False))

    @staticmethod
    def is_authenticated(user: Any) -> bool:
        return bool(user and getattr(user, "is_authenticated", False))

    @staticmethod
    def is_creator(user: Any, obj: Any) -> bool:
        if not (user and getattr(user, "is_authenticated", False)):
            return False
        return getattr(obj, "create_user", None) == user
