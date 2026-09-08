from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.audit import AuditPage
from goldmine.ui.customers import CustomersPage
from goldmine.ui.dashboard import DashboardPage
from goldmine.ui.loans import LoansPage
from goldmine.ui.vault import VaultPage
from goldmine.ui.reports import ReportsPage
from goldmine.ui.settings import SettingsPage
from goldmine.ui.theme import NAVY, palette, ui_font


class ShellFrame(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_logout):
        p = palette()
        super().__init__(master, fg_color=p["bg"])
        self.ctx = ctx
        self.on_logout = on_logout
        self.nav_btns: dict[str, ctk.CTkButton] = {}
        self.pages: dict[str, ctk.CTkFrame] = {}

        self.sidebar = ctk.CTkFrame(self, width=232, corner_radius=0, fg_color=p["sidebar"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 8))
        mark = ctk.CTkFrame(brand, width=36, height=36, corner_radius=10, fg_color="#F5F5F3")
        mark.pack(side="left")
        mark.pack_propagate(False)
        ctk.CTkLabel(mark, text="G", text_color=NAVY, font=ui_font(18, "bold")).pack(expand=True)
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left", padx=(10, 0), fill="x", expand=True)
        ctk.CTkLabel(names, text="Goldmine", text_color=p["on_ink"], font=ui_font(15, "bold"), anchor="w").pack(fill="x")
        self.shop_lbl = ctk.CTkLabel(names, text="", text_color="#A8A8A4", font=ui_font(11), anchor="w")
        self.shop_lbl.pack(fill="x")

        self.jump = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Jump to name or loan #",
            height=36,
            corner_radius=8,
            border_width=0,
            fg_color="#2A2A2A",
            text_color="#F5F5F3",
        )
        self.jump.pack(fill="x", padx=14, pady=(8, 14))
        self.jump.bind("<Return>", lambda e: self._jump())

        self.content = ctk.CTkFrame(self, fg_color=p["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=22, pady=16)

        owner = bool(ctx.user and ctx.user.is_owner)
        self._nav_group("Counter")
        self._nav_btn("dashboard", "Home")
        self._nav_btn("loans", "Tickets")
        self._nav_btn("vault", "Vault")
        self._nav_btn("customers", "Customers")
        if owner:
            self._nav_group("Owner")
            self._nav_btn("reports", "Reports")
            self._nav_btn("audit", "Audit log")
            self._nav_btn("settings", "Settings")

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(fill="both", expand=True)

        user = ctx.user
        foot = ctk.CTkFrame(self.sidebar, fg_color="#2A2A2A", corner_radius=12)
        foot.pack(fill="x", padx=12, pady=(0, 8))
        initial = (user.full_name[:1] if user else "?").upper()
        avatar = ctk.CTkFrame(foot, width=32, height=32, corner_radius=16, fg_color="#F5F5F3")
        avatar.pack(side="left", padx=10, pady=10)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initial, text_color=NAVY, font=ui_font(13, "bold")).pack(expand=True)
        meta = ctk.CTkFrame(foot, fg_color="transparent")
        meta.pack(side="left", fill="x", expand=True, pady=8)
        self.user_lbl = ctk.CTkLabel(meta, text=user.full_name if user else "", font=ui_font(12, "bold"), text_color="#F4EFE4", anchor="w")
        self.user_lbl.pack(fill="x")
        self.role_lbl = ctk.CTkLabel(
            meta,
            text=(user.role.title() if user else ""),
            font=ui_font(11),
            text_color="#A9B3C6",
            anchor="w",
        )
        self.role_lbl.pack(fill="x")
        ctk.CTkButton(
            self.sidebar,
            text="Log out",
            command=self._logout,
            fg_color="transparent",
            hover_color="#2A2A2A",
            border_width=1,
            border_color="#4A4A4A",
            text_color="#F5F5F3",
            font=ui_font(13),
            height=36,
            corner_radius=8,
        ).pack(fill="x", padx=12, pady=(0, 16))

        self.pages["dashboard"] = DashboardPage(self.content, ctx, on_open_loans=lambda: self.show("loans"))
        self.pages["loans"] = LoansPage(self.content, ctx)
        self.pages["vault"] = VaultPage(self.content, ctx)
        self.pages["customers"] = CustomersPage(self.content, ctx)
        if owner:
            self.pages["reports"] = ReportsPage(self.content, ctx)
            self.pages["audit"] = AuditPage(self.content, ctx)
            self.pages["settings"] = SettingsPage(
                self.content, ctx, on_theme_change=self._restyle, on_logout=self._logout
            )

        self.show("dashboard")
        self._refresh_header()

    def _nav_group(self, title: str):
        ctk.CTkLabel(
            self.sidebar,
            text=title.upper(),
            font=ui_font(10, "bold"),
            text_color="#8A8A86",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(8, 4))

    def _nav_btn(self, key: str, label: str):
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {label}",
            anchor="w",
            height=38,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#2A2A2A",
            text_color="#F5F5F3",
            font=ui_font(13),
            command=lambda k=key: self.show(k),
        )
        btn.pack(fill="x", padx=10, pady=1)
        self.nav_btns[key] = btn

    def _refresh_header(self):
        self.shop_lbl.configure(text=self.ctx.settings.get("shop_name", "Goldmine"))

    def _restyle(self):
        pass

    def _jump(self):
        q = self.jump.get().strip()
        if not q:
            return
        if q.upper().startswith("GL-"):
            self.show("loans")
            self.pages["loans"].search.delete(0, "end")
            self.pages["loans"].search.insert(0, q)
            self.pages["loans"].refresh()
            return
        self.show("customers")
        self.pages["customers"].search.delete(0, "end")
        self.pages["customers"].search.insert(0, q)
        self.pages["customers"].refresh()

    def show(self, key: str):
        for k, btn in self.nav_btns.items():
            active = k == key
            btn.configure(
                fg_color="#F5F5F3" if active else "transparent",
                text_color=NAVY if active else "#F5F5F3",
                font=ui_font(13, "bold" if active else "normal"),
            )
        for page in self.pages.values():
            page.pack_forget()
        page = self.pages[key]
        page.pack(fill="both", expand=True)
        if hasattr(page, "refresh"):
            page.refresh()

    def _logout(self):
        if self.ctx.user:
            self.ctx.auth.logout(self.ctx.user)
        self.ctx.user = None
        self.on_logout()
