from __future__ import annotations

from goldmine.db.connection import Database, seed_needed
from goldmine.security.permissions import CurrentUser
from goldmine.services.audit import AuditService
from goldmine.services.auth import AuthService
from goldmine.services.backups import BackupService
from goldmine.services.customers import CustomerService
from goldmine.services.loans import LoanService
from goldmine.services.receipts import ReceiptService
from goldmine.services.reports import ReportService
from goldmine.services.settings import SettingsService
from goldmine.services.shop import ShopService
from goldmine.services.users import UserService


class AppContext:
    def __init__(self) -> None:
        self.db = Database()
        self.audit = AuditService(self.db)
        self.settings = SettingsService(self.db, self.audit)
        self.auth = AuthService(self.db, self.audit)
        self.users = UserService(self.db, self.audit)
        self.customers = CustomerService(self.db, self.audit)
        self.loans = LoanService(self.db, self.audit)
        self.shop = ShopService(self.db, self.audit, self.settings)
        self.reports = ReportService(self.db, self.audit, self.settings)
        self.backups = BackupService(self.db, self.audit, self.settings)
        self.receipts = ReceiptService(self.audit, self.settings)
        self.user: CurrentUser | None = None

    @property
    def needs_setup(self) -> bool:
        return seed_needed(self.db)

    def reopen_db(self) -> None:
        self.db = Database()
        self.audit = AuditService(self.db)
        self.settings = SettingsService(self.db, self.audit)
        self.auth = AuthService(self.db, self.audit)
        self.users = UserService(self.db, self.audit)
        self.customers = CustomerService(self.db, self.audit)
        self.loans = LoanService(self.db, self.audit)
        self.shop = ShopService(self.db, self.audit, self.settings)
        self.reports = ReportService(self.db, self.audit, self.settings)
        self.backups = BackupService(self.db, self.audit, self.settings)
        self.receipts = ReceiptService(self.audit, self.settings)
