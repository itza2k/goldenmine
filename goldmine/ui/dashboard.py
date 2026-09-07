from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.theme import GOLD, palette, ui_font
from goldmine.ui.widgets import Card, PageHeader, StatCard
from goldmine.util import format_date, money


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_open_loans=None):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.on_open_loans = on_open_loans
        self.header = PageHeader(self, "Pledge desk", "Today at the counter")
        self.header.pack(fill="x", pady=(0, 14))

        self.stats = ctk.CTkFrame(self, fg_color="transparent")
        self.stats.pack(fill="x")
        self.stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")

        self.cards: dict[str, StatCard] = {}
        specs = [
            ("active", "Active loans", "0", "Currently open"),
            ("today", "Issued today", "0", "New this morning"),
            ("closed", "Closed today", "0", "Repaid today"),
            ("collect", "Collections", "—", "Received today"),
        ]
        for i, (key, title, val, sub) in enumerate(specs):
            card = StatCard(self.stats, title, val, sub)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            self.cards[key] = card

        extra = ctk.CTkFrame(self, fg_color="transparent")
        extra.pack(fill="x", pady=(10, 0))
        extra.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi2")
        self.out_card = StatCard(extra, "Outstanding", "—", "Principal still out")
        self.out_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.due_card = StatCard(extra, "Due soon", "0", "Needs follow-up")
        self.due_card.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.over_card = StatCard(extra, "Overdue", "0", "Past due date")
        self.over_card.grid(row=0, column=2, sticky="nsew")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=(14, 0))
        body.grid_columnconfigure((0, 1), weight=1, uniform="lists")
        body.grid_rowconfigure(0, weight=1)

        self.due_box = Card(body)
        self.due_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(self.due_box, text="Due soon", font=ui_font(16, "bold"), text_color=palette()["text"]).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        self.due_list = ctk.CTkScrollableFrame(self.due_box, fg_color="transparent")
        self.due_list.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.cust_box = Card(body)
        self.cust_box.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(self.cust_box, text="New customers", font=ui_font(16, "bold"), text_color=palette()["text"]).pack(
            anchor="w", padx=18, pady=(16, 4)
        )
        self.cust_list = ctk.CTkScrollableFrame(self.cust_box, fg_color="transparent")
        self.cust_list.pack(fill="both", expand=True, padx=8, pady=(0, 10))

    def _row(self, parent, left: str, middle: str, right: str, gold_left: bool = False):
        p = palette()
        line = ctk.CTkFrame(parent, fg_color=p["soft"], corner_radius=10)
        line.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(
            line,
            text=left,
            text_color=GOLD if gold_left else p["text"],
            font=ui_font(12, "bold"),
        ).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(line, text=middle, text_color=p["text"], font=ui_font(12)).pack(side="left")
        ctk.CTkLabel(line, text=right, text_color=p["muted"], font=ui_font(12)).pack(side="right", padx=12)

    def refresh(self):
        p = palette()
        data = self.ctx.reports.dashboard()
        symbol = self.ctx.settings.get("currency_symbol", "₹")
        name = self.ctx.user.full_name.split()[0] if self.ctx.user else ""
        self.header.set_subtitle(f"Good to see you, {name}. Here is the shop today.")
        self.cards["active"].set(str(data["active_loans"]))
        self.cards["today"].set(str(data["issued_today"]))
        self.cards["closed"].set(str(data["closed_today"]))
        self.cards["collect"].set(money(data["collections_today"], symbol))
        self.out_card.set(money(data["outstanding"], symbol))
        self.due_card.set(str(len(data["due_soon"])), f"Next {data['due_soon_days']} days")
        self.over_card.set(str(data.get("overdue_count", 0)), f"{data.get('vault_items', 0)} pieces in vault")

        for w in self.due_list.winfo_children():
            w.destroy()
        if not data["due_soon"]:
            ctk.CTkLabel(self.due_list, text="Nothing due in this window.", text_color=p["muted"], font=ui_font(13)).pack(
                anchor="w", padx=12, pady=8
            )
        for row in data["due_soon"]:
            self._row(self.due_list, row["loan_number"], row["customer_name"], format_date(row["due_date"]), True)

        for w in self.cust_list.winfo_children():
            w.destroy()
        if not data["recent_customers"]:
            ctk.CTkLabel(self.cust_list, text="No customers yet. Add one from Customers.", text_color=p["muted"], font=ui_font(13)).pack(
                anchor="w", padx=12, pady=8
            )
        for row in data["recent_customers"]:
            self._row(self.cust_list, row["name"], "", row["phone"])
