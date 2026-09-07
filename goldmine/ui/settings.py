from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.dialogs import confirm, handle_error, prompt_text, show_info
from goldmine.ui.theme import apply_theme, palette, ui_font
from goldmine.ui.widgets import DataTable, GhostButton, GoldButton, LabeledEntry, PageHeader
from goldmine.util import format_dt


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_theme_change=None, on_logout=None):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.on_theme_change = on_theme_change
        self.on_logout = on_logout
        p = palette()
        PageHeader(self, "Settings", "Shop, rates, people, and backups.").pack(fill="x")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, pady=10)
        for name in ("Shop", "Gold rate", "Interest rates", "Users", "Backup", "My password"):
            self.tabs.add(name)

        shop = self.tabs.tab("Shop")
        self.s_name = LabeledEntry(shop, "Shop name")
        self.s_name.pack(fill="x", pady=4)
        self.s_addr = LabeledEntry(shop, "Shop address")
        self.s_addr.pack(fill="x", pady=4)
        self.s_phone = LabeledEntry(shop, "Shop phone")
        self.s_phone.pack(fill="x", pady=4)
        self.s_cur = LabeledEntry(shop, "Currency symbol")
        self.s_cur.pack(fill="x", pady=4)
        self.s_due = LabeledEntry(shop, "Due-soon warning (days)")
        self.s_due.pack(fill="x", pady=4)
        self.s_keep = LabeledEntry(shop, "Automatic backups to keep")
        self.s_keep.pack(fill="x", pady=4)
        self.s_foot = LabeledEntry(shop, "Receipt footer")
        self.s_foot.pack(fill="x", pady=4)
        ctk.CTkLabel(shop, text="Appearance", text_color=p["muted"], font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w", pady=(10, 4)
        )
        self.appearance = ctk.CTkSegmentedButton(shop, values=["light", "dark", "system"], command=self._theme)
        self.appearance.pack(anchor="w")
        GoldButton(shop, text="Save shop settings", command=self._save_shop).pack(anchor="w", pady=16)

        gold = self.tabs.tab("Gold rate")
        ctk.CTkLabel(
            gold,
            text="Today's bullion rate is used to value ornaments and suggest a maximum loan.",
            wraplength=640,
            justify="left",
            text_color=p["muted"],
        ).pack(anchor="w", pady=(4, 8))
        self.s_22 = LabeledEntry(gold, "22K rate per gram")
        self.s_22.pack(fill="x", pady=4)
        self.s_24 = LabeledEntry(gold, "24K rate per gram")
        self.s_24.pack(fill="x", pady=4)
        self.s_ltv = LabeledEntry(gold, "Default loan-to-value %")
        self.s_ltv.pack(fill="x", pady=4)
        self.s_mindays = LabeledEntry(gold, "Minimum interest days")
        self.s_mindays.pack(fill="x", pady=4)
        GoldButton(gold, text="Post today's gold rate", command=self._save_gold).pack(anchor="w", pady=12)

        rates = self.tabs.tab("Interest rates")
        self.rate_table = DataTable(rates, [("rate", "Rate %", 80), ("label", "Label", 200), ("is_active", "Active", 80)])
        self.rate_table.pack(fill="both", expand=True, pady=(0, 8))
        row = ctk.CTkFrame(rates, fg_color="transparent")
        row.pack(fill="x")
        self.new_rate = LabeledEntry(row, "New rate")
        self.new_rate.pack(side="left", fill="x", expand=True)
        self.new_label = LabeledEntry(row, "Label (optional)")
        self.new_label.pack(side="left", fill="x", expand=True, padx=8)
        GoldButton(row, text="Add", width=80, command=self._add_rate).pack(side="left", pady=(18, 0))
        GhostButton(rates, text="Activate / deactivate selected", command=self._toggle_rate).pack(anchor="w", pady=8)

        users = self.tabs.tab("Users")
        self.user_table = DataTable(
            users,
            [("username", "Username", 120), ("full_name", "Name", 160), ("role", "Role", 90), ("is_active", "Active", 80)],
        )
        self.user_table.pack(fill="both", expand=True)
        urow = ctk.CTkFrame(users, fg_color="transparent")
        urow.pack(fill="x", pady=8)
        self.u_user = LabeledEntry(urow, "New username")
        self.u_user.pack(side="left", fill="x", expand=True)
        self.u_name = LabeledEntry(urow, "Full name")
        self.u_name.pack(side="left", fill="x", expand=True, padx=8)
        self.u_pw = LabeledEntry(urow, "Password", show="•")
        self.u_pw.pack(side="left", fill="x", expand=True)
        GoldButton(users, text="Create employee", command=self._create_user).pack(anchor="w")
        brow = ctk.CTkFrame(users, fg_color="transparent")
        brow.pack(fill="x", pady=8)
        GhostButton(brow, text="Deactivate / activate", command=self._toggle_user).pack(side="left")
        GhostButton(brow, text="Reset password", command=self._reset_pw).pack(side="left", padx=8)

        backup = self.tabs.tab("Backup")
        self.backup_table = DataTable(
            backup, [("name", "File", 260), ("modified", "Created", 160), ("size", "Size", 80)]
        )
        self.backup_table.pack(fill="both", expand=True)
        b2 = ctk.CTkFrame(backup, fg_color="transparent")
        b2.pack(fill="x", pady=8)
        GoldButton(b2, text="Backup now", command=self._backup).pack(side="left")
        GhostButton(b2, text="Restore selected", command=self._restore).pack(side="left", padx=8)
        ctk.CTkLabel(
            backup,
            text="Automatic daily backups run when the app starts. Restore closes and reloads the database.",
            text_color=p["muted"],
            wraplength=700,
            justify="left",
        ).pack(anchor="w")

        pw = self.tabs.tab("My password")
        self.cur_pw = LabeledEntry(pw, "Current password", show="•")
        self.cur_pw.pack(fill="x", pady=4)
        self.new_pw = LabeledEntry(pw, "New password", show="•")
        self.new_pw.pack(fill="x", pady=4)
        self.new_pw2 = LabeledEntry(pw, "Confirm new password", show="•")
        self.new_pw2.pack(fill="x", pady=4)
        GoldButton(pw, text="Change password", command=self._change_pw).pack(anchor="w", pady=12)

    def refresh(self):
        s = self.ctx.settings.all()
        self.s_name.set(s.get("shop_name", ""))
        self.s_addr.set(s.get("shop_address", ""))
        self.s_phone.set(s.get("shop_phone", ""))
        self.s_cur.set(s.get("currency_symbol", "₹"))
        self.s_due.set(s.get("due_soon_days", "7"))
        self.s_keep.set(s.get("backup_retain_count", "14"))
        self.s_foot.set(s.get("receipt_footer", ""))
        self.appearance.set(s.get("appearance_mode", "light"))
        rate = self.ctx.shop.gold_rate()
        self.s_22.set(rate.get("rate_22k") or "")
        self.s_24.set(rate.get("rate_24k") or "")
        self.s_ltv.set(s.get("default_ltv", "75"))
        self.s_mindays.set(s.get("min_interest_days", "15"))
        rates = self.ctx.settings.list_rates(self.ctx.user)
        for r in rates:
            r["is_active"] = "Yes" if r["is_active"] else "No"
        self.rate_table.set_rows(rates)
        users = self.ctx.users.list(self.ctx.user)
        for u in users:
            u["is_active"] = "Yes" if u["is_active"] else "No"
        self.user_table.set_rows(users)
        backups = self.ctx.backups.list_backups()
        for b in backups:
            b["id"] = b["path"]
            b["size"] = f"{b['size'] / 1024:.1f} KB"
            b["modified"] = format_dt(b["modified"])
        self.backup_table.set_rows(backups, key="id")

    def _theme(self, mode: str):
        apply_theme(mode)
        if self.on_theme_change:
            self.on_theme_change()

    def _save_shop(self):
        try:
            self.ctx.settings.update_many(
                self.ctx.user,
                {
                    "shop_name": self.s_name.get(),
                    "shop_address": self.s_addr.get(),
                    "shop_phone": self.s_phone.get(),
                    "currency_symbol": self.s_cur.get() or "₹",
                    "due_soon_days": self.s_due.get(),
                    "backup_retain_count": self.s_keep.get(),
                    "receipt_footer": self.s_foot.get(),
                    "appearance_mode": self.appearance.get(),
                },
            )
            show_info(self, "Settings saved.")
        except AppError as exc:
            handle_error(self, exc)

    def _save_gold(self):
        try:
            self.ctx.shop.set_gold_rate(self.ctx.user, self.s_22.get(), self.s_24.get())
            self.ctx.settings.update_many(
                self.ctx.user,
                {"default_ltv": self.s_ltv.get(), "min_interest_days": self.s_mindays.get()},
            )
            show_info(self, "Gold rate posted for today.")
        except AppError as exc:
            handle_error(self, exc)

    def _add_rate(self):
        try:
            self.ctx.settings.add_rate(self.ctx.user, self.new_rate.get(), self.new_label.get())
            self.new_rate.set("")
            self.new_label.set("")
            self.refresh()
        except AppError as exc:
            handle_error(self, exc)

    def _toggle_rate(self):
        row = self.rate_table.selected()
        if not row:
            return
        active = row["is_active"] != "Yes"
        try:
            self.ctx.settings.set_rate_active(self.ctx.user, int(row["id"]), active)
            self.refresh()
        except AppError as exc:
            handle_error(self, exc)

    def _create_user(self):
        try:
            self.ctx.users.create_employee(self.ctx.user, self.u_user.get(), self.u_pw.get(), self.u_name.get())
            self.u_user.set("")
            self.u_name.set("")
            self.u_pw.set("")
            self.refresh()
            show_info(self, "Employee account created.")
        except AppError as exc:
            handle_error(self, exc)

    def _toggle_user(self):
        row = self.user_table.selected()
        if not row:
            return
        try:
            self.ctx.users.set_active(self.ctx.user, int(row["id"]), row["is_active"] != "Yes")
            self.refresh()
        except AppError as exc:
            handle_error(self, exc)

    def _reset_pw(self):
        row = self.user_table.selected()
        if not row:
            return
        pw = prompt_text(self, "Reset password", "New password (min 8 characters)")
        if pw is None:
            return
        try:
            self.ctx.users.reset_password(self.ctx.user, int(row["id"]), pw)
            show_info(self, "Password updated.")
        except AppError as exc:
            handle_error(self, exc)

    def _backup(self):
        try:
            path = self.ctx.backups.create(self.ctx.user)
            show_info(self, f"Backup saved as {path.name}")
            self.refresh()
        except AppError as exc:
            handle_error(self, exc)

    def _restore(self):
        row = self.backup_table.selected()
        if not row:
            return
        if not confirm(self, "Restore backup", "This replaces the current database. A safety copy is made first. Continue?"):
            return
        try:
            meta = self.ctx.backups.restore(self.ctx.user, row["id"])
            self.ctx.reopen_db()
            self.ctx.audit.record(
                self.ctx.user,
                "backup.restore",
                entity_type="backup",
                previous={"safety_copy": meta["safety_copy"]},
                new={"restored": meta["restored"]},
                reason="Owner restored a backup",
            )
            still = self.ctx.db.fetchone("SELECT id FROM users WHERE id = ?", (self.ctx.user.id,))
            show_info(self, "Backup restored.")
            if not still and self.on_logout:
                self.on_logout()
                return
            self.refresh()
        except AppError as exc:
            handle_error(self, exc)

    def _change_pw(self):
        if self.new_pw.get() != self.new_pw2.get():
            handle_error(self, AppError("New passwords do not match."))
            return
        try:
            self.ctx.auth.change_password(self.ctx.user, self.cur_pw.get(), self.new_pw.get())
            self.cur_pw.set("")
            self.new_pw.set("")
            self.new_pw2.set("")
            show_info(self, "Password changed.")
        except AppError as exc:
            handle_error(self, exc)
