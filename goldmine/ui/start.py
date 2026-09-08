from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.ui.theme import palette, ui_font
from goldmine.ui.widgets import GhostButton, GoldButton


class StartFrame(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext, on_pick, on_skip):
        p = palette()
        super().__init__(master, fg_color=p["bg"], corner_radius=0)
        self.ctx = ctx
        self.on_pick = on_pick
        self.on_skip = on_skip

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.grid(row=0, column=0)

        shop = ctx.settings.get("shop_name", "Goldmine")
        ctk.CTkLabel(wrap, text="GOLDMINE", text_color=p["muted"], font=ui_font(12, "bold")).pack(anchor="w")
        ctk.CTkLabel(wrap, text=shop, text_color=p["text"], font=ui_font(28, "bold")).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            wrap,
            text="Choose who is opening the shop, or skip and type a username.",
            text_color=p["muted"],
            font=ui_font(13),
        ).pack(anchor="w", pady=(6, 18))

        profiles = ctx.auth.list_profiles()
        if not profiles:
            ctk.CTkLabel(wrap, text="No people on this computer yet.", text_color=p["muted"]).pack(anchor="w")
        for person in profiles:
            self._profile_row(wrap, person)

        self.always = ctk.CTkCheckBox(
            wrap,
            text="Skip this list next time I open Goldmine",
            font=ui_font(12),
            text_color=p["text"],
            fg_color=p["text"],
            hover_color=p["muted"],
            checkmark_color=p["card"],
        )
        self.always.pack(anchor="w", pady=(18, 10))

        GhostButton(wrap, text="Skip profiles — sign in with username", command=self._skip, width=360).pack(
            fill="x"
        )

    def _profile_row(self, parent, person: dict):
        p = palette()
        row = ctk.CTkFrame(parent, fg_color=p["card"], corner_radius=12, border_width=1, border_color=p["border"])
        row.pack(fill="x", pady=5)
        mark = ctk.CTkFrame(row, width=40, height=40, corner_radius=20, fg_color=p["soft"])
        mark.pack(side="left", padx=12, pady=12)
        mark.pack_propagate(False)
        initial = (person.get("full_name") or person["username"])[:1].upper()
        ctk.CTkLabel(mark, text=initial, text_color=p["text"], font=ui_font(14, "bold")).pack(expand=True)
        meta = ctk.CTkFrame(row, fg_color="transparent")
        meta.pack(side="left", fill="x", expand=True, pady=10)
        ctk.CTkLabel(meta, text=person["full_name"], font=ui_font(14, "bold"), text_color=p["text"], anchor="w").pack(
            fill="x"
        )
        role = "Owner" if person["role"] == "owner" else "Employee"
        ctk.CTkLabel(meta, text=f"{role}  ·  {person['username']}", font=ui_font(12), text_color=p["muted"], anchor="w").pack(
            fill="x"
        )
        GoldButton(row, text="Continue", width=110, command=lambda u=person["username"]: self._choose(u)).pack(
            side="right", padx=12
        )

    def _choose(self, username: str):
        if self.always.get():
            self.ctx.settings.set_skip_profiles(True)
        self.on_pick(username)

    def _skip(self):
        self.ctx.settings.set_skip_profiles(True)
        self.on_skip()
