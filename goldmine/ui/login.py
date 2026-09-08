from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.theme import palette, ui_font
from goldmine.ui.widgets import GhostButton, GoldButton, LabeledEntry


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_success, *, username: str | None = None, on_profiles=None):
        p = palette()
        super().__init__(master, fg_color=p["bg"], corner_radius=0)
        self.ctx = ctx
        self.on_success = on_success
        self.on_profiles = on_profiles

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, fg_color=p["card"], corner_radius=16, border_width=1, border_color=p["border"])
        card.grid(row=0, column=0)
        inner = ctk.CTkFrame(card, fg_color=p["card"])
        inner.pack(padx=40, pady=32)

        shop = ctx.settings.get("shop_name", "Goldmine")
        ctk.CTkLabel(inner, text="Goldmine", text_color=p["muted"], font=ui_font(12, "bold")).pack(anchor="w")
        title = "Enter password" if username else "Sign in"
        ctk.CTkLabel(inner, text=title, text_color=p["text"], font=ui_font(28, "bold")).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(inner, text=shop, text_color=p["muted"], font=ui_font(13)).pack(anchor="w", pady=(0, 18))

        self.user = LabeledEntry(inner, "Username", "Enter username")
        self.user.pack(fill="x", pady=(0, 10))
        if username:
            self.user.set(username)
            self.user.configure_state("disabled")
        self.pw = LabeledEntry(inner, "Password", "Enter password", show="•")
        self.pw.pack(fill="x")
        self.err = ctk.CTkLabel(inner, text="", text_color=p["danger"], font=ui_font(12))
        self.err.pack(anchor="w", pady=(8, 0))
        GoldButton(inner, text="Continue", width=340, command=self._login).pack(pady=(10, 8))
        if on_profiles:
            GhostButton(inner, text="Back to profiles", width=340, command=self._back).pack()
        self.pw.entry.bind("<Return>", lambda e: self._login())
        self.user.entry.bind("<Return>", lambda e: self.pw.entry.focus())
        self.after(200, self.pw.entry.focus if username else self.user.entry.focus)

    def _back(self):
        self.ctx.settings.set_skip_profiles(False)
        if self.on_profiles:
            self.on_profiles()

    def _login(self):
        self.err.configure(text="")
        try:
            user = self.ctx.auth.login(self.user.get(), self.pw.get())
        except AppError as exc:
            self.err.configure(text=str(exc))
            return
        self.ctx.user = user
        self.on_success()
