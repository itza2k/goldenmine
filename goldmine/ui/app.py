from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.login import LoginFrame
from goldmine.ui.setup import SetupFrame
from goldmine.ui.shell import ShellFrame
from goldmine.ui.theme import apply_theme, palette


class GoldmineApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.ctx = AppContext()
        apply_theme(self.ctx.settings.get("appearance_mode", "light"))
        self.configure(fg_color=palette()["bg"])
        self.title("Goldmine")
        self.geometry("1280x800")
        self.minsize(1024, 680)
        try:
            self.ctx.backups.maybe_daily_backup()
        except Exception:
            pass
        self.current = None
        self._show_start()

    def _clear(self) -> None:
        if self.current is not None:
            self.current.destroy()
            self.current = None

    def _show_start(self) -> None:
        self._clear()
        if self.ctx.needs_setup:
            self.current = SetupFrame(self, self.ctx, on_done=self._enter_app)
        else:
            self.current = LoginFrame(self, self.ctx, on_success=self._enter_app)
        self.current.pack(fill="both", expand=True)
        self.configure(fg_color=palette()["bg"])

    def _enter_app(self) -> None:
        apply_theme(self.ctx.settings.get("appearance_mode", "light"))
        self._clear()
        self.configure(fg_color=palette()["bg"])
        self.current = ShellFrame(self, self.ctx, on_logout=self._show_start)
        self.current.pack(fill="both", expand=True)
        shop = self.ctx.settings.get("shop_name", "Goldmine")
        self.title(f"Goldmine — {shop}")
