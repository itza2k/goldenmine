from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.theme import GOLD, NAVY, palette, ui_font
from goldmine.ui.widgets import GoldButton, LabeledEntry


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_success):
        super().__init__(master, fg_color=NAVY, corner_radius=0)
        self.ctx = ctx
        self.on_success = on_success
        p = palette()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, fg_color=p["card"], corner_radius=20, border_width=0)
        card.grid(row=0, column=0)
        stripe = ctk.CTkFrame(card, fg_color=GOLD, height=6, corner_radius=0)
        stripe.pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color=p["card"])
        inner.pack(padx=40, pady=32)

        ctk.CTkLabel(inner, text="GOLDMINE", text_color=GOLD, font=ui_font(12, "bold")).pack(anchor="w")
        ctk.CTkLabel(inner, text="Sign in", text_color=p["text"], font=ui_font(28, "bold")).pack(anchor="w", pady=(2, 0))
        shop = ctx.settings.get("shop_name", "Goldmine")
        ctk.CTkLabel(inner, text=shop, text_color=p["muted"], font=ui_font(13)).pack(anchor="w", pady=(0, 18))

        self.user = LabeledEntry(inner, "Username", "Enter username")
        self.user.pack(fill="x", pady=(0, 10))
        self.pw = LabeledEntry(inner, "Password", "Enter password", show="•")
        self.pw.pack(fill="x")
        self.err = ctk.CTkLabel(inner, text="", text_color="#B42318", font=ui_font(12))
        self.err.pack(anchor="w", pady=(8, 0))
        GoldButton(inner, text="Continue", width=340, command=self._login).pack(pady=(10, 0))
        self.pw.entry.bind("<Return>", lambda e: self._login())
        self.user.entry.bind("<Return>", lambda e: self.pw.entry.focus())
        self.after(200, self.user.entry.focus)

    def _login(self):
        self.err.configure(text="")
        try:
            user = self.ctx.auth.login(self.user.get(), self.pw.get())
        except AppError as exc:
            self.err.configure(text=str(exc))
            return
        self.ctx.user = user
        self.on_success()
