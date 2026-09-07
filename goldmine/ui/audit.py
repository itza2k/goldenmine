from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.theme import palette, ui_font
from goldmine.ui.widgets import DataTable, GhostButton, PageHeader
from goldmine.util import format_dt


class AuditPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        p = palette()
        PageHeader(self, "Audit log", "Permanent history. Nothing here can be edited or deleted.").pack(fill="x")

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", pady=10)
        self.search = ctk.CTkEntry(tools, placeholder_text="Search user, action, or reason", height=38)
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.action = ctk.CTkOptionMenu(tools, values=["All actions"], command=lambda _: self.refresh())
        self.action.pack(side="left", padx=8)
        GhostButton(tools, text="Refresh", width=100, command=self.refresh).pack(side="left")

        self.table = DataTable(
            self,
            [
                ("created_at", "When", 150),
                ("username", "User", 110),
                ("action", "Action", 150),
                ("entity_id", "Record", 120),
                ("reason", "Reason", 180),
                ("previous_value", "Previous", 180),
                ("new_value", "New", 180),
            ],
        )
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        actions = ["All actions"] + self.ctx.audit.distinct_actions()
        current = self.action.get()
        self.action.configure(values=actions)
        if current in actions:
            self.action.set(current)
        else:
            self.action.set("All actions")
        action = "" if self.action.get() == "All actions" else self.action.get()
        rows = self.ctx.audit.list(search=self.search.get(), action=action)
        for r in rows:
            r["created_at"] = format_dt(r.get("created_at"))
            for key in ("previous_value", "new_value"):
                val = r.get(key) or ""
                r[key] = val[:80] + ("…" if len(val) > 80 else "")
        self.table.set_rows(rows)
