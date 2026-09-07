from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.dialogs import handle_error, show_info
from goldmine.ui.theme import palette, ui_font
from goldmine.ui.widgets import DataTable, GhostButton, GoldButton, LabeledEntry, PageHeader
from goldmine.util import now


class ReportsPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.report = None
        p = palette()
        PageHeader(self, "Reports", "Owner only — generate, print, or export.").pack(fill="x")

        bar = ctk.CTkFrame(self, fg_color=p["card"], corner_radius=16, border_width=1, border_color=p["border"])
        bar.pack(fill="x", pady=(12, 10))
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        kinds = [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
            ("open", "Open loans"),
            ("closed", "Closed loans"),
            ("interest", "Interest earned"),
            ("activity", "Employee activity"),
            ("overdue", "Overdue pledges"),
            ("vault", "Vault inventory"),
            ("collections", "Collections"),
        ]
        self._kind_map = {v: k for k, v in kinds}
        self.kind = ctk.CTkOptionMenu(inner, values=[k[1] for k in kinds], width=180, height=36)
        self.kind.set("Daily")
        self.kind.pack(side="left")
        today = now().date().isoformat()
        self.date_from = LabeledEntry(inner, "From")
        self.date_from.set(today)
        self.date_from.pack(side="left", padx=8)
        self.date_to = LabeledEntry(inner, "To")
        self.date_to.set(today)
        self.date_to.pack(side="left")
        GoldButton(inner, text="Generate", width=110, command=self._run).pack(side="left", padx=10)
        GhostButton(inner, text="Excel", width=80, command=self._excel).pack(side="left")
        GhostButton(inner, text="PDF", width=80, command=self._pdf).pack(side="left", padx=6)
        self.summary = ctk.CTkLabel(self, text="Choose a report and press Generate.", text_color=p["muted"], font=ui_font(13))
        self.summary.pack(anchor="w", pady=(0, 8))
        self.table = DataTable(self, [("placeholder", "No rows yet", 400)])
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        pass

    def _run(self):
        kind = self._kind_map[self.kind.get()]
        try:
            self.report = self.ctx.reports.generate(
                self.ctx.user, kind, self.date_from.get().strip(), self.date_to.get().strip()
            )
        except AppError as exc:
            handle_error(self, exc)
            return
        cols = list(zip(self.report["columns"], self.report["headers"], [120] * len(self.report["columns"])))
        self.table.destroy()
        self.table = DataTable(self, cols)
        self.table.pack(fill="both", expand=True)
        rows = []
        for i, r in enumerate(self.report["rows"]):
            item = dict(r)
            item["id"] = i
            rows.append(item)
        self.table.set_rows(rows, key="id")
        bits = [f"{k}: {v}" for k, v in self.report["summary"].items()]
        self.summary.configure(text=self.report["title"] + "  ·  " + "  ·  ".join(bits))

    def _excel(self):
        if not self.report:
            handle_error(self, AppError("Generate a report first."))
            return
        try:
            path = self.ctx.reports.export_excel(self.ctx.user, self.report)
            show_info(self, f"Saved to {path}")
            self.ctx.receipts.open_file(path)
        except AppError as exc:
            handle_error(self, exc)

    def _pdf(self):
        if not self.report:
            handle_error(self, AppError("Generate a report first."))
            return
        try:
            path = self.ctx.reports.export_pdf(self.ctx.user, self.report)
            show_info(self, f"Saved to {path}")
            self.ctx.receipts.open_file(path)
        except AppError as exc:
            handle_error(self, exc)
