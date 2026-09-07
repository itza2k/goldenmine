from __future__ import annotations

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.dialogs import handle_error, owner_auth_dialog, prompt_text, show_info
from goldmine.ui.theme import GOLD, NAVY, palette, ui_font
from goldmine.ui.widgets import (
    DataTable,
    GhostButton,
    GoldButton,
    LabeledEntry,
    PageHeader,
    SectionLabel,
    StatusBadge,
)
from goldmine.util import format_date, money, now


class LoansPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.current_id: int | None = None
        self.customer_id: int | None = None
        self._tick_job = None
        p = palette()

        PageHeader(self, "Loans", "Issue, correct (5 minutes), or look up a pledge.", ("New loan", self._new)).pack(
            fill="x"
        )

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", pady=(12, 10))
        self.search = ctk.CTkEntry(
            tools,
            placeholder_text="Loan number, customer, or phone",
            height=40,
            corner_radius=8,
            border_color=p["border"],
            font=ui_font(13),
        )
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.status = ctk.CTkSegmentedButton(
            tools, values=["Open", "Closed", "All"], command=lambda _: self.refresh(), height=36
        )
        self.status.set("Open")
        self.status.pack(side="left", padx=(10, 0))

        split = ctk.CTkFrame(self, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=5)
        split.grid_columnconfigure(1, weight=4)
        split.grid_rowconfigure(0, weight=1)

        self.table = DataTable(
            split,
            [
                ("loan_number", "Loan", 110),
                ("customer_name", "Customer", 140),
                ("loan_amount", "Amount", 90),
                ("status", "Status", 70),
                ("lock", "Edit", 70),
            ],
            on_select=self._from_table,
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        panel = ctk.CTkFrame(split, fg_color=p["card"], corner_radius=16, border_width=1, border_color=p["border"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.form_title = ctk.CTkLabel(head, text="New loan", font=ui_font(18, "bold"), text_color=p["text"])
        self.form_title.pack(side="left")
        self.badge = StatusBadge(head, "Draft", "info")
        self.badge.pack(side="right", padx=(6, 0))
        self.lock_badge = StatusBadge(head, "", "warn")
        self.lock_badge.pack(side="right")

        form = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        form.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.form = form
        self.lock_banner = ctk.CTkLabel(form, text="", wraplength=340, justify="left", text_color=GOLD, font=ui_font(12))
        self.lock_banner.pack(anchor="w", padx=8, pady=(0, 6))

        SectionLabel(form, "1  Customer").pack(anchor="w", padx=8, pady=(4, 4))
        self.cust_search = ctk.CTkEntry(form, placeholder_text="Search existing customer", height=36, corner_radius=8)
        self.cust_search.pack(fill="x", padx=8)
        self.cust_search.bind("<KeyRelease>", lambda e: self._search_customers())
        self.cust_results = ctk.CTkFrame(form, fg_color="transparent")
        self.cust_results.pack(fill="x", padx=8, pady=4)
        self.sel_cust = ctk.CTkLabel(form, text="No customer selected", text_color=p["muted"], font=ui_font(12))
        self.sel_cust.pack(anchor="w", padx=8)
        quick = ctk.CTkFrame(form, fg_color="transparent")
        quick.pack(fill="x", padx=8, pady=(6, 2))
        quick.grid_columnconfigure((0, 1), weight=1)
        self.quick_name = LabeledEntry(quick, "New name")
        self.quick_name.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.quick_phone = LabeledEntry(quick, "New phone")
        self.quick_phone.grid(row=0, column=1, sticky="ew")
        GhostButton(form, text="Add this customer", height=34, command=self._quick_customer).pack(
            fill="x", padx=8, pady=(6, 8)
        )

        SectionLabel(form, "2  Gold").pack(anchor="w", padx=8, pady=(6, 4))
        self.f_gold = LabeledEntry(form, "Jewellery type")
        self.f_gold.pack(fill="x", padx=8, pady=3)
        g2 = ctk.CTkFrame(form, fg_color="transparent")
        g2.pack(fill="x", padx=8)
        g2.grid_columnconfigure((0, 1), weight=1)
        self.f_weight = LabeledEntry(g2, "Weight (grams)")
        self.f_weight.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        self.f_purity = LabeledEntry(g2, "Purity", "22K")
        self.f_purity.grid(row=0, column=1, sticky="ew", pady=3)

        SectionLabel(form, "3  Loan").pack(anchor="w", padx=8, pady=(10, 4))
        g3 = ctk.CTkFrame(form, fg_color="transparent")
        g3.pack(fill="x", padx=8)
        g3.grid_columnconfigure((0, 1), weight=1)
        self.f_amount = LabeledEntry(g3, "Amount")
        self.f_amount.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        rate_wrap = ctk.CTkFrame(g3, fg_color="transparent")
        rate_wrap.grid(row=0, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(rate_wrap, text="Interest rate", text_color=p["muted"], font=ui_font(11, "bold")).pack(anchor="w")
        self.rate_menu = ctk.CTkOptionMenu(rate_wrap, values=["—"], height=40, fg_color=NAVY, button_color=GOLD)
        self.rate_menu.pack(fill="x", pady=(5, 0))
        g4 = ctk.CTkFrame(form, fg_color="transparent")
        g4.pack(fill="x", padx=8)
        g4.grid_columnconfigure((0, 1), weight=1)
        self.f_start = LabeledEntry(g4, "Start date")
        self.f_start.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        self.f_due = LabeledEntry(g4, "Due date (optional)")
        self.f_due.grid(row=0, column=1, sticky="ew", pady=3)
        self.f_remarks = LabeledEntry(form, "Remarks (optional)")
        self.f_remarks.pack(fill="x", padx=8, pady=3)
        self.closed_info = ctk.CTkLabel(form, text="", wraplength=340, justify="left", text_color=p["muted"], font=ui_font(12))
        self.closed_info.pack(anchor="w", padx=8, pady=(8, 4))

        foot = ctk.CTkFrame(panel, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 14))
        self.save_btn = GoldButton(foot, text="Create loan", command=self._save)
        self.save_btn.pack(fill="x")
        row_b = ctk.CTkFrame(foot, fg_color="transparent")
        row_b.pack(fill="x", pady=(8, 0))
        self.print_btn = GhostButton(row_b, text="Print receipt", command=self._print)
        self.print_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.close_btn = GoldButton(row_b, text="Close", command=self._close, width=90)
        self.reopen_btn = GhostButton(row_b, text="Reopen", command=self._reopen, width=90)

    def _rate_map(self) -> dict[str, float]:
        rates = self.ctx.loans.active_rates()
        return {r["label"]: float(r["rate"]) for r in rates}

    def _load_rates(self, selected: float | None = None):
        mapping = self._rate_map()
        labels = list(mapping.keys()) or ["No rates configured"]
        self.rate_menu.configure(values=labels)
        if selected is not None:
            for label, rate in mapping.items():
                if abs(rate - float(selected)) < 1e-9:
                    self.rate_menu.set(label)
                    return
        if labels:
            self.rate_menu.set(labels[0])

    def refresh(self):
        status = self.status.get().lower()
        if status == "all":
            status = ""
        rows = self.ctx.loans.search(self.search.get(), status=status)
        symbol = self.ctx.settings.get("currency_symbol", "₹")
        view = []
        for r in rows:
            view.append(
                {
                    "id": r["id"],
                    "loan_number": r["loan_number"],
                    "customer_name": r["customer_name"],
                    "loan_amount": money(r["loan_amount"], symbol),
                    "status": r["status"].title(),
                    "lock": "5 min" if not r["is_locked"] and r["status"] == "open" else "Locked",
                }
            )
        self.table.set_rows(view)
        self._load_rates()

    def _search_customers(self):
        for w in self.cust_results.winfo_children():
            w.destroy()
        q = self.cust_search.get().strip()
        if len(q) < 2:
            return
        matches = self.ctx.customers.search(q)[:5]
        for m in matches:
            btn = GhostButton(
                self.cust_results,
                text=f"{m['name']}  ·  {m['phone']}",
                height=32,
                command=lambda c=m: self._pick_customer(c),
            )
            btn.pack(fill="x", pady=2)

    def _pick_customer(self, customer: dict):
        self.customer_id = customer["id"]
        self.sel_cust.configure(text=f"Using {customer['name']}  ·  {customer['phone']}")
        for w in self.cust_results.winfo_children():
            w.destroy()

    def _quick_customer(self):
        try:
            created = self.ctx.customers.create(
                self.ctx.user,
                {"name": self.quick_name.get(), "phone": self.quick_phone.get()},
            )
        except AppError as exc:
            handle_error(self, exc)
            return
        self._pick_customer(created)
        self.quick_name.set("")
        self.quick_phone.set("")

    def _new(self):
        self.current_id = None
        self.customer_id = None
        self.form_title.configure(text="New loan")
        self.badge.set("Draft", "info")
        self.lock_badge.set("Auto number", "warn")
        self.lock_banner.configure(text="Pick a customer, enter the gold, then create. You can fix typing for 5 minutes.")
        self.sel_cust.configure(text="No customer selected yet.")
        self.cust_search.configure(state="normal")
        self.quick_name.configure_state("normal")
        self.quick_phone.configure_state("normal")
        self.quick_name.set("")
        self.quick_phone.set("")
        self.closed_info.configure(text="")
        today = now().date().isoformat()
        self.f_gold.set("")
        self.f_weight.set("")
        self.f_purity.set("")
        self.f_amount.set("")
        self.f_start.set(today)
        self.f_due.set("")
        self.f_remarks.set("")
        self._set_fields_enabled(True)
        self.save_btn.configure(state="normal", text="Create loan")
        self.close_btn.pack_forget()
        self.reopen_btn.pack_forget()
        self._load_rates()
        self.cust_search.focus()

    def _from_table(self, row: dict):
        try:
            self._load(int(row["id"]))
        except (TypeError, ValueError):
            return

    def _load(self, loan_id: int):
        loan = self.ctx.loans.get(loan_id)
        self.current_id = loan["id"]
        self.customer_id = loan["customer_id"]
        self.form_title.configure(text=loan["loan_number"])
        if loan["status"] == "closed":
            self.badge.set("Closed", "lock")
        else:
            self.badge.set("Open", "ok")
        self.sel_cust.configure(text=f"Using {loan['customer_name']}  ·  {loan['customer_phone']}")
        self.f_gold.set(loan["gold_description"])
        self.f_weight.set(loan["gold_weight"])
        self.f_purity.set(loan.get("gold_purity") or "")
        self.f_amount.set(loan["loan_amount"])
        self.f_start.set(loan["start_date"])
        self.f_due.set(loan.get("due_date") or "")
        self.f_remarks.set(loan.get("remarks") or "")
        self._load_rates(loan["interest_rate"])
        symbol = self.ctx.settings.get("currency_symbol", "₹")
        if loan["status"] == "closed":
            self.closed_info.configure(
                text=(
                    f"Closed {format_date(loan.get('closing_date'))}  ·  "
                    f"Interest {money(loan.get('interest_collected'), symbol)}  ·  "
                    f"Received {money(loan.get('total_received'), symbol)}"
                )
            )
        else:
            self.closed_info.configure(text="")

        user = self.ctx.user
        employee_locked = bool(user and user.is_employee and loan["is_locked"])
        closed = loan["status"] == "closed"
        can_edit = not employee_locked and (not closed or (user and user.is_owner))
        if user and user.is_employee and closed:
            can_edit = False
        self._set_fields_enabled(can_edit and not (closed and user and user.is_employee))
        if user and user.is_employee:
            qstate = "disabled" if loan["is_locked"] else "normal"
            self.cust_search.configure(state=qstate)
            self.quick_name.configure_state(qstate)
            self.quick_phone.configure_state(qstate)
        else:
            self.cust_search.configure(state="normal")
            self.quick_name.configure_state("normal")
            self.quick_phone.configure_state("normal")

        if loan["is_locked"]:
            self.lock_badge.set("Locked", "lock")
            if user and user.is_owner:
                self.lock_banner.configure(text="Locked. Owner password is required to change it.")
            else:
                self.lock_banner.configure(text="Locked. This record cannot be changed at the counter.")
        else:
            mins = loan["seconds_remaining"] // 60
            secs = loan["seconds_remaining"] % 60
            self.lock_badge.set(f"{mins:02d}:{secs:02d}", "warn")
            self.lock_banner.configure(text="Correction window is open. Fix typing mistakes now.")
            self._schedule_tick(loan_id)

        self.save_btn.configure(state="normal" if (user and user.is_owner) or not loan["is_locked"] else "disabled")
        self.save_btn.configure(text="Save changes")
        owner = bool(user and user.is_owner)
        self.close_btn.pack_forget()
        self.reopen_btn.pack_forget()
        if owner and loan["status"] == "open":
            self.close_btn.pack(side="left", fill="x", expand=True)
        elif owner and loan["status"] == "closed":
            self.reopen_btn.pack(side="left", fill="x", expand=True)
        if not owner:
            self.save_btn.configure(state="disabled" if loan["is_locked"] or closed else "normal")

    def _schedule_tick(self, loan_id: int):
        if self._tick_job:
            self.after_cancel(self._tick_job)
        self._tick_job = self.after(1000, lambda: self._tick(loan_id))

    def _tick(self, loan_id: int):
        if self.current_id != loan_id:
            return
        try:
            loan = self.ctx.loans.get(loan_id)
        except AppError:
            return
        if loan["is_locked"]:
            self._load(loan_id)
            self.refresh()
            return
        mins = loan["seconds_remaining"] // 60
        secs = loan["seconds_remaining"] % 60
        self.lock_badge.set(f"{mins:02d}:{secs:02d}", "warn")
        self._schedule_tick(loan_id)

    def _set_fields_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for f in (self.f_gold, self.f_weight, self.f_purity, self.f_amount, self.f_start, self.f_due, self.f_remarks):
            f.configure_state(state)
        self.rate_menu.configure(state=state)

    def _payload(self) -> dict:
        mapping = self._rate_map()
        label = self.rate_menu.get()
        rate = mapping.get(label)
        if rate is None:
            try:
                rate = float(str(label).split("%")[0])
            except ValueError:
                rate = None
        return {
            "customer_id": self.customer_id,
            "gold_description": self.f_gold.get(),
            "gold_weight": self.f_weight.get(),
            "gold_purity": self.f_purity.get(),
            "loan_amount": self.f_amount.get(),
            "interest_rate": rate,
            "start_date": self.f_start.get().strip(),
            "due_date": self.f_due.get().strip(),
            "remarks": self.f_remarks.get(),
        }

    def _save(self):
        data = self._payload()
        try:
            if self.current_id is None:
                created = self.ctx.loans.create(self.ctx.user, data)
                show_info(self, f"Loan {created['loan_number']} created.")
                self._load(created["id"])
            else:
                loan = self.ctx.loans.get(self.current_id)
                password = reason = None
                if self.ctx.user.is_owner and (loan["is_locked"] or loan["status"] == "closed"):
                    pair = owner_auth_dialog(self, self.ctx.auth, self.ctx.user)
                    if not pair:
                        return
                    password, reason = pair
                updated = self.ctx.loans.update(
                    self.ctx.user,
                    self.current_id,
                    data,
                    owner_password=password,
                    reason=reason,
                    auth_service=self.ctx.auth,
                )
                show_info(self, f"Loan {updated['loan_number']} saved.")
                self._load(updated["id"])
        except AppError as exc:
            handle_error(self, exc)
            return
        self.refresh()

    def _print(self):
        if not self.current_id:
            handle_error(self, AppError("Open a loan first."))
            return
        try:
            loan = self.ctx.loans.get(self.current_id)
            path = self.ctx.receipts.generate(self.ctx.user, loan)
            self.ctx.receipts.open_file(path)
        except AppError as exc:
            handle_error(self, exc)

    def _close(self):
        if not self.current_id:
            return
        win = ctk.CTkToplevel(self)
        win.title("Close loan")
        win.geometry("420x380")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        p = palette()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(box, text="Close this loan", font=ui_font(18, "bold"), text_color=p["text"]).pack(
            padx=20, pady=(18, 4), anchor="w"
        )
        ctk.CTkLabel(box, text="Enter what the customer paid today.", text_color=p["muted"], font=ui_font(12)).pack(
            padx=20, anchor="w"
        )
        d = LabeledEntry(box, "Closing date (YYYY-MM-DD)")
        d.set(now().date().isoformat())
        d.pack(fill="x", padx=20, pady=4)
        i = LabeledEntry(box, "Interest collected")
        i.pack(fill="x", padx=20, pady=4)
        t = LabeledEntry(box, "Total received")
        t.pack(fill="x", padx=20, pady=4)
        r = LabeledEntry(box, "Remarks")
        r.pack(fill="x", padx=20, pady=4)

        def go():
            try:
                self.ctx.loans.close(
                    self.ctx.user,
                    self.current_id,
                    closing_date=d.get().strip(),
                    interest_collected=i.get(),
                    total_received=t.get(),
                    remarks=r.get(),
                )
            except (AppError, ValueError) as exc:
                handle_error(self, exc if isinstance(exc, AppError) else AppError(str(exc)))
                return
            win.destroy()
            show_info(self, "Loan closed.")
            self.refresh()
            self._load(self.current_id)

        GoldButton(box, text="Close loan", command=go).pack(padx=20, pady=16, fill="x")

    def _reopen(self):
        if not self.current_id:
            return
        reason = prompt_text(self, "Reopen loan", "Reason for reopening")
        if reason is None:
            return
        try:
            self.ctx.loans.reopen(self.ctx.user, self.current_id, reason)
        except AppError as exc:
            handle_error(self, exc)
            return
        self.refresh()
        self._load(self.current_id)
