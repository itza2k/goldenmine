from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.paths import EDIT_WINDOW_SECONDS
from goldmine.ui.dialogs import handle_error, show_info
from goldmine.ui.theme import palette, ui_font
from goldmine.catalog import ID_PROOF_TYPES, TITLES
from goldmine.ui.widgets import DataTable, GoldButton, LabeledDropdown, LabeledEntry, PageHeader
from goldmine.util import format_dt


class CustomersPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.current_id: int | None = None
        p = palette()

        PageHeader(self, "Customers", "Find a person, then issue a loan.", ("New customer", self._new)).pack(fill="x")

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", pady=(12, 10))
        self.search = ctk.CTkEntry(
            search_row,
            placeholder_text="Type a name or phone number",
            height=40,
            corner_radius=8,
            border_color=p["border"],
            font=ui_font(13),
        )
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self.table = DataTable(
            body,
            [
                ("name", "Name", 180),
                ("phone", "Phone", 130),
                ("address", "Address", 180),
                ("created_at", "Added", 140),
            ],
            on_select=self._from_table,
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        form = ctk.CTkFrame(body, fg_color=p["card"], corner_radius=16, border_width=1, border_color=p["border"])
        form.grid(row=0, column=1, sticky="nsew")
        inner = ctk.CTkFrame(form, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=18)
        self.form_title = ctk.CTkLabel(inner, text="Customer", font=ui_font(18, "bold"), text_color=p["text"])
        self.form_title.pack(anchor="w")
        ctk.CTkLabel(
            inner,
            text="Phone numbers must be unique so you never create a duplicate.",
            wraplength=280,
            justify="left",
            text_color=p["muted"],
            font=ui_font(12),
        ).pack(anchor="w", pady=(2, 12))
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=5)
        row.grid_columnconfigure((0, 1), weight=1)
        self.f_title = LabeledDropdown(row, "Title", TITLES)
        self.f_title.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.f_idtype = LabeledDropdown(row, "ID proof", ID_PROOF_TYPES)
        self.f_idtype.grid(row=0, column=1, sticky="ew")
        self.f_name = LabeledEntry(inner, "Full name")
        self.f_name.pack(fill="x", pady=5)
        self.f_phone = LabeledEntry(inner, "Phone")
        self.f_phone.pack(fill="x", pady=5)
        self.f_addr = LabeledEntry(inner, "Address (optional)")
        self.f_addr.pack(fill="x", pady=5)
        self.f_gov = LabeledEntry(inner, "ID number (optional)")
        self.f_gov.pack(fill="x", pady=5)
        self.f_nom = LabeledEntry(inner, "Nominee (optional)")
        self.f_nom.pack(fill="x", pady=5)
        self.lock_note = ctk.CTkLabel(inner, text="", wraplength=280, justify="left", text_color=p["muted"], font=ui_font(12))
        self.lock_note.pack(anchor="w", pady=(10, 0))
        self.save_btn = GoldButton(inner, text="Save customer", command=self._save)
        self.save_btn.pack(fill="x", pady=(16, 0))

    def refresh(self):
        rows = self.ctx.customers.search(self.search.get())
        for r in rows:
            r["created_at"] = format_dt(r.get("created_at"))
        self.table.set_rows(rows)

    def _new(self):
        self.current_id = None
        self.form_title.configure(text="New customer")
        for f in (self.f_name, self.f_phone, self.f_addr, self.f_gov, self.f_nom):
            f.set("")
            f.configure_state("normal")
        self.f_title.configure_state("normal")
        self.f_idtype.configure_state("normal")
        self.lock_note.configure(text="")
        self.save_btn.configure(state="normal")
        self.f_name.entry.focus()

    def _from_table(self, row: dict):
        try:
            self._load(int(row["id"]))
        except (TypeError, ValueError):
            return

    def _load(self, cid: int):
        data = self.ctx.customers.get(cid)
        self.current_id = cid
        self.form_title.configure(text=data["name"])
        self.f_name.set(data["name"])
        self.f_phone.set(data["phone"])
        self.f_addr.set(data.get("address") or "")
        self.f_gov.set(data.get("government_id") or "")
        self.f_nom.set(data.get("nominee_name") or "")
        self.f_title.set(data.get("title") or "Mr")
        self.f_idtype.set(data.get("id_proof_type") or "Aadhaar")
        locked = self.ctx.user and self.ctx.user.is_employee and self.ctx.customers.has_locked_loans(
            cid, EDIT_WINDOW_SECONDS
        )
        state = "disabled" if locked else "normal"
        for f in (self.f_name, self.f_phone, self.f_addr, self.f_gov, self.f_nom, self.f_title, self.f_idtype):
            f.configure_state(state)
        self.save_btn.configure(state=state)
        self.lock_note.configure(
            text="Locked loan on file — employees cannot change this profile." if locked else ""
        )

    def _save(self):
        payload = {
            "name": self.f_name.get(),
            "phone": self.f_phone.get(),
            "address": self.f_addr.get(),
            "government_id": self.f_gov.get(),
            "title": self.f_title.get(),
            "id_proof_type": self.f_idtype.get(),
            "nominee_name": self.f_nom.get(),
        }
        try:
            if self.current_id is None:
                created = self.ctx.customers.create(self.ctx.user, payload)
                show_info(self, f"{created['name']} was added.")
                self.current_id = created["id"]
            else:
                self.ctx.customers.update(
                    self.ctx.user, self.current_id, payload, edit_window_seconds=EDIT_WINDOW_SECONDS
                )
                show_info(self, "Customer details saved.")
        except AppError as exc:
            handle_error(self, exc)
            return
        self.refresh()
        if self.current_id:
            self._load(self.current_id)
