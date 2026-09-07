from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.theme import GOLD, NAVY, palette
from goldmine.ui.widgets import GoldButton, LabeledEntry


class SetupFrame(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_done):
        super().__init__(master, fg_color=NAVY, corner_radius=0)
        self.ctx = ctx
        self.on_done = on_done
        p = palette()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, fg_color=p["card"], corner_radius=20)
        card.grid(row=0, column=0, padx=24, pady=24)
        ctk.CTkFrame(card, fg_color=GOLD, height=6, corner_radius=0).pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color=p["card"])
        inner.pack(padx=36, pady=28)

        ctk.CTkLabel(inner, text="FIRST-TIME SETUP", text_color=GOLD, font=ctk.CTkFont(size=12, weight="bold")).pack(
            anchor="w"
        )
        ctk.CTkLabel(inner, text="Create the owner account", font=ctk.CTkFont(size=24, weight="bold"), text_color=p["text"]).pack(
            anchor="w", pady=(4, 8)
        )
        ctk.CTkLabel(
            inner,
            text="This account has full control. Keep the password safe — employees cannot recover it.",
            wraplength=400,
            justify="left",
            text_color=p["muted"],
        ).pack(anchor="w", pady=(0, 14))

        self.shop = LabeledEntry(inner, "Shop name", "e.g. Sri Lakshmi Jewellers")
        self.shop.pack(fill="x", pady=4)
        self.name = LabeledEntry(inner, "Owner full name")
        self.name.pack(fill="x", pady=4)
        self.user = LabeledEntry(inner, "Username", "owner")
        self.user.pack(fill="x", pady=4)
        self.pw = LabeledEntry(inner, "Password (min 8 characters)", show="•")
        self.pw.pack(fill="x", pady=4)
        self.pw2 = LabeledEntry(inner, "Confirm password", show="•")
        self.pw2.pack(fill="x", pady=4)
        self.err = ctk.CTkLabel(inner, text="", text_color="#B42318")
        self.err.pack(anchor="w")
        GoldButton(inner, text="Create owner account", width=408, command=self._create).pack(pady=(8, 0))

    def _create(self):
        self.err.configure(text="")
        if self.pw.get() != self.pw2.get():
            self.err.configure(text="Passwords do not match.")
            return
        try:
            user = self.ctx.auth.create_owner(self.user.get(), self.pw.get(), self.name.get(), self.shop.get())
        except AppError as exc:
            self.err.configure(text=str(exc))
            return
        self.ctx.user = user
        self.on_done()
