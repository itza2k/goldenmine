from __future__ import annotations

from dataclasses import dataclass

from goldmine.exceptions import PermissionDenied


ROLE_OWNER = "owner"
ROLE_EMPLOYEE = "employee"

EMPLOYEE_ALLOWED = {
    "login",
    "logout",
    "customer.create",
    "customer.view",
    "customer.search",
    "customer.update_unlocked",
    "loan.create",
    "loan.view",
    "loan.search",
    "loan.update_unlocked",
    "loan.print",
    "dashboard.view",
}

OWNER_ONLY = {
    "reports.view",
    "reports.export",
    "settings.view",
    "settings.update",
    "rates.manage",
    "users.manage",
    "backup.create",
    "backup.restore",
    "audit.view",
    "loan.close",
    "loan.reopen",
    "loan.update_locked",
    "customer.update_any",
}


@dataclass
class CurrentUser:
    id: int
    username: str
    full_name: str
    role: str

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_OWNER

    @property
    def is_employee(self) -> bool:
        return self.role == ROLE_EMPLOYEE


def require_user(user: CurrentUser | None) -> CurrentUser:
    if user is None:
        raise PermissionDenied("You must be signed in.")
    return user


def require_owner(user: CurrentUser | None) -> CurrentUser:
    user = require_user(user)
    if not user.is_owner:
        raise PermissionDenied("This action is available only to the owner.")
    return user


def can(user: CurrentUser | None, action: str) -> bool:
    if user is None:
        return False
    if user.is_owner:
        return True
    return action in EMPLOYEE_ALLOWED
