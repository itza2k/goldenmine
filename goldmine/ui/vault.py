from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.theme import palette, ui_font
from goldmine.ui.widgets import DataTable, PageHeader
from goldmine.util import money


class VaultPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        PageHeader(self, "Vault", "Every ornament still pledged in the shop.").pack(fill="x")
        self.note = ctk.CTkLabel(self, text="", text_color=palette()["muted"], font=ui_font(13))
        self.note.pack(anchor="w", pady=(8, 8))
        self.table = DataTable(
            self,
            [
                ("loan_number", "Ticket", 110),
                ("customer_name", "Customer", 140),
                ("jewellery_type", "Ornament", 120),
                ("purity", "Purity", 90),
                ("net_weight", "Net g", 70),
                ("locker_no", "Locker", 80),
                ("phone", "Phone", 110),
            ],
        )
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        rows = self.ctx.shop.vault()
        symbol = self.ctx.settings.get("currency_symbol", "₹")
        weight = sum(r.get("net_weight") or 0 for r in rows)
        self.note.configure(text=f"{len(rows)} pieces in vault  ·  {weight:.3f} g net")
        self.table.set_rows(rows, key="id")
        _ = symbol
