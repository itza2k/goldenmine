from __future__ import annotations

from datetime import timedelta

import customtkinter as ctk

from goldmine.app_context import AppContext
from goldmine.exceptions import AppError
from goldmine.ui.dialogs import handle_error, owner_auth_dialog, prompt_text, show_info
from goldmine.ui.theme import NAVY, palette, ui_font
from goldmine.catalog import CLOSE_TYPES, CONDITIONS, JEWELLERY_TYPES, LOAN_FILTERS, NOTICE_STATUS, PAYMENT_KINDS, PAYMENT_METHODS, PURITIES
from goldmine.ui.widgets import (
    DataTable,
    GhostButton,
    GoldButton,
    LabeledDropdown,
    LabeledEntry,
    PageHeader,
    SectionLabel,
    StatusBadge,
)
from goldmine.util import format_date, money, now


def ticket_tag(loan: dict) -> str:
    if loan.get("status") == "closed":
        return "closed"
    today = now().date().isoformat()
    due = loan.get("due_date") or ""
    if due and due < today:
        return "overdue"
    soon = (now().date() + timedelta(days=7)).isoformat()
    if due and today <= due <= soon:
        return "soon"
    if loan.get("status") == "open" and not loan.get("is_locked"):
        return "edit"
    return "open"


class LoansPage(ctk.CTkFrame):
    def __init__(self, master, ctx: AppContext):
        super().__init__(master, fg_color="transparent")
        self.ctx = ctx
        self.current_id: int | None = None
        self.customer_id: int | None = None
        self._tick_job = None
        p = palette()

        PageHeader(self, "Tickets", "Issue, collect, and close pledges.", ("New ticket", self._new)).pack(fill="x")

        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.pack(fill="x", pady=(12, 10))
        self.search = ctk.CTkEntry(
            tools,
            placeholder_text="Search ticket, name, or phone",
            height=36,
            corner_radius=8,
            border_color=p["border"],
            font=ui_font(13),
        )
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.status = ctk.CTkOptionMenu(
            tools,
            values=LOAN_FILTERS,
            command=lambda _: self.refresh(),
            width=130,
            height=36,
            fg_color=NAVY,
            button_color="#2A2A2A",
            button_hover_color="#3A3A3A",
            text_color="#F5F5F3",
            dropdown_fg_color=NAVY,
            dropdown_text_color="#F5F5F3",
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
                ("loan_number", "Ticket", 110),
                ("customer_name", "Customer", 150),
                ("loan_amount", "Amount", 100),
                ("due", "Due", 90),
                ("status", "Status", 100),
            ],
            on_select=self._from_table,
        )
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        wrap = ctk.CTkFrame(split, fg_color="transparent")
        wrap.grid(row=0, column=1, sticky="nsew")
        self.tone_bar = ctk.CTkFrame(wrap, width=4, corner_radius=2, fg_color=p["border"])
        self.tone_bar.pack(side="left", fill="y", padx=(0, 8))
        self.tone_bar.pack_propagate(False)

        panel = ctk.CTkFrame(wrap, fg_color=p["card"], corner_radius=10, border_width=1, border_color=p["border"])
        panel.pack(side="left", fill="both", expand=True)
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
        self.lock_banner = ctk.CTkLabel(form, text="", wraplength=340, justify="left", text_color=p["muted"], font=ui_font(12))
        self.lock_banner.pack(anchor="w", padx=8, pady=(0, 6))

        SectionLabel(form, "Customer").pack(anchor="w", padx=8, pady=(4, 4))
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
        quick.pack_forget()
        GhostButton(form, text="New customer", height=34, command=self._customer_popup).pack(
            fill="x", padx=8, pady=(6, 8)
        )

        SectionLabel(form, "Ornament").pack(anchor="w", padx=8, pady=(6, 4))
        self.f_jtype = LabeledDropdown(form, "Jewellery type", JEWELLERY_TYPES)
        self.f_jtype.pack(fill="x", padx=8, pady=3)
        self.f_gold = LabeledEntry(form, "Description")
        self.f_gold.pack(fill="x", padx=8, pady=3)
        g2 = ctk.CTkFrame(form, fg_color="transparent")
        g2.pack(fill="x", padx=8)
        g2.grid_columnconfigure((0, 1), weight=1)
        self.f_weight = LabeledEntry(g2, "Gross weight (g)")
        self.f_weight.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        self.f_stone = LabeledEntry(g2, "Stone weight (g)")
        self.f_stone.grid(row=0, column=1, sticky="ew", pady=3)
        g2b = ctk.CTkFrame(form, fg_color="transparent")
        g2b.pack(fill="x", padx=8)
        g2b.grid_columnconfigure((0, 1), weight=1)
        self.f_purity = LabeledDropdown(g2b, "Purity", PURITIES)
        self.f_purity.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        self.f_cond = LabeledDropdown(g2b, "Condition", CONDITIONS)
        self.f_cond.grid(row=0, column=1, sticky="ew", pady=3)
        self.f_locker = LabeledEntry(form, "Locker / packet no.")
        self.f_locker.pack(fill="x", padx=8, pady=3)
        self.est_lbl = ctk.CTkLabel(form, text="", wraplength=340, justify="left", text_color=p["muted"], font=ui_font(12))
        self.est_lbl.pack(anchor="w", padx=8)
        GhostButton(form, text="Estimate value", height=34, command=self._estimate_popup).pack(
            fill="x", padx=8, pady=(4, 8)
        )

        SectionLabel(form, "Terms").pack(anchor="w", padx=8, pady=(10, 4))
        g3 = ctk.CTkFrame(form, fg_color="transparent")
        g3.pack(fill="x", padx=8)
        g3.grid_columnconfigure((0, 1), weight=1)
        self.f_amount = LabeledEntry(g3, "Amount")
        self.f_amount.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=3)
        rate_wrap = ctk.CTkFrame(g3, fg_color="transparent")
        rate_wrap.grid(row=0, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(rate_wrap, text="Interest rate", text_color=p["muted"], font=ui_font(11, "bold")).pack(anchor="w")
        self.rate_menu = ctk.CTkOptionMenu(rate_wrap, values=["—"], height=40, fg_color=NAVY, button_color="#3A3A3A")
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
        self.settle_lbl = ctk.CTkLabel(form, text="", wraplength=340, justify="left", text_color=p["text"], font=ui_font(12))
        self.settle_lbl.pack(anchor="w", padx=8)
        self.f_notice = LabeledDropdown(form, "Reminder", NOTICE_STATUS)
        self.f_notice.pack(fill="x", padx=8, pady=6)

        foot = ctk.CTkFrame(panel, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 14))
        self.save_btn = GoldButton(foot, text="Create loan", command=self._save)
        self.save_btn.pack(fill="x")
        row_b = ctk.CTkFrame(foot, fg_color="transparent")
        row_b.pack(fill="x", pady=(8, 0))
        self.print_btn = GhostButton(row_b, text="Print", command=self._print)
        self.print_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.pay_btn = GhostButton(row_b, text="Collect", command=self._pay, width=100)
        self.pay_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.close_btn = GhostButton(row_b, text="Close", command=self._close, width=100)
        self.close_btn.configure(text_color=p["stop"], border_color=p["stop"])
        self.reopen_btn = GhostButton(row_b, text="Reopen", command=self._reopen, width=100)
        self.more_btn = GhostButton(foot, text="More", command=self._more_popup)
        self.more_btn.pack(fill="x", pady=(8, 0))
        self.renew_btn = GhostButton(foot, text="Renew due date", command=self._renew)
        self.renew_btn.pack_forget()
        self._set_tone("draft")

    def _set_tone(self, tag: str):
        p = palette()
        colors = {
            "open": p["go"],
            "overdue": p["stop"],
            "soon": p["wait"],
            "closed": p["border"],
            "edit": p["text"],
            "draft": p["border"],
        }
        self.tone_bar.configure(fg_color=colors.get(tag, p["border"]))

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
            tag = ticket_tag(r)
            labels = {
                "open": "Open",
                "overdue": "Overdue",
                "soon": "Due soon",
                "closed": "Closed",
                "edit": "Open",
            }
            view.append(
                {
                    "id": r["id"],
                    "loan_number": r["loan_number"],
                    "customer_name": r["customer_name"],
                    "loan_amount": money(r["loan_amount"], symbol),
                    "due": format_date(r.get("due_date")) if r.get("due_date") else "—",
                    "status": labels.get(tag, tag.upper()),
                    "_tag": tag,
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
        self.f_stone.set("0")
        self.f_locker.set("")
        self.est_lbl.configure(text="")
        self.settle_lbl.configure(text="")
        self.f_amount.set("")
        self.f_start.set(today)
        self.f_due.set("")
        self.f_remarks.set("")
        self._set_fields_enabled(True)
        self.save_btn.configure(state="normal", text="Create ticket")
        self.close_btn.pack_forget()
        self.reopen_btn.pack_forget()
        self.renew_btn.pack_forget()
        self._load_rates()
        self._set_tone("draft")
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
            self.badge.set("Closed", "closed")
        else:
            tag = ticket_tag(loan)
            kind = {"overdue": "lock", "soon": "soon", "edit": "info", "open": "ok"}.get(tag, "ok")
            self.badge.set({"overdue": "Overdue", "soon": "Due soon", "edit": "Open", "open": "Open"}.get(tag, "Open"), kind)
        self._set_tone(ticket_tag(loan))
        self.sel_cust.configure(text=f"Using {loan['customer_name']}  ·  {loan['customer_phone']}")
        self.f_gold.set(loan["gold_description"])
        self.f_weight.set(loan["gold_weight"])
        self.f_purity.set(loan.get("gold_purity") or "22K / 916")
        self.f_locker.set(loan.get("locker_no") or "")
        items = loan.get("items") or []
        if items:
            first = items[0]
            self.f_jtype.set(first.get("jewellery_type") or JEWELLERY_TYPES[0])
            self.f_stone.set(first.get("stone_weight") or 0)
            self.f_cond.set(first.get("condition_label") or "Good")
            if first.get("purity"):
                self.f_purity.set(first["purity"])
        else:
            self.f_stone.set("0")
        self.f_notice.set(loan.get("notice_status") or "Not sent")
        try:
            st = self.ctx.shop.settlement(loan)
            symbol = self.ctx.settings.get("currency_symbol", "₹")
            self.settle_lbl.configure(
                text=(
                    f"{st['months']} month(s)  ·  Interest {money(st['interest_accrued'], symbol)}  ·  "
                    f"Paid {money(st['paid'], symbol)}  ·  Due {money(st['outstanding'], symbol)}"
                    + (f"  ·  Overdue {st['overdue_days']}d" if st["overdue_days"] else "")
                )
            )
        except Exception:
            self.settle_lbl.configure(text="")
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
        self.renew_btn.pack_forget()
        if owner and loan["status"] == "open":
            self.close_btn.pack(side="left", fill="x", expand=True)
            self.renew_btn.pack(fill="x", pady=(8, 0))
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
        for f in (
            self.f_gold,
            self.f_weight,
            self.f_stone,
            self.f_purity,
            self.f_jtype,
            self.f_cond,
            self.f_locker,
            self.f_amount,
            self.f_start,
            self.f_due,
            self.f_remarks,
        ):
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
        try:
            gross = float(self.f_weight.get() or 0)
            stone = float(self.f_stone.get() or 0)
        except ValueError:
            gross, stone = 0, 0
        net = max(gross - stone, 0)
        desc = (self.f_gold.get() or "").strip() or self.f_jtype.get()
        return {
            "customer_id": self.customer_id,
            "gold_description": desc,
            "gold_weight": net or self.f_weight.get(),
            "gold_purity": self.f_purity.get(),
            "loan_amount": self.f_amount.get(),
            "interest_rate": rate,
            "start_date": self.f_start.get().strip(),
            "due_date": self.f_due.get().strip(),
            "remarks": self.f_remarks.get(),
            "locker_no": self.f_locker.get(),
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
        lid = self.current_id
        if lid:
            try:
                self.ctx.shop.replace_items(self.ctx.user, lid, [self._item_payload()])
                self.ctx.shop.set_notice(self.ctx.user, lid, self.f_notice.get())
            except AppError as exc:
                handle_error(self, exc)
        self.refresh()

    def _item_payload(self) -> dict:
        try:
            gross = float(self.f_weight.get() or 0)
            stone = float(self.f_stone.get() or 0)
        except ValueError:
            gross, stone = 0.0, 0.0
        return {
            "jewellery_type": self.f_jtype.get(),
            "description": self.f_gold.get(),
            "purity": self.f_purity.get(),
            "gross_weight": gross,
            "stone_weight": stone,
            "condition_label": self.f_cond.get(),
        }

    def _customer_popup(self):
        p = palette()
        win = ctk.CTkToplevel(self)
        win.title("New customer")
        win.geometry("420x280")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(box, text="Add a customer", font=ui_font(18, "bold"), text_color=p["text"]).pack(
            padx=20, pady=(18, 8), anchor="w"
        )
        name = LabeledEntry(box, "Full name")
        name.pack(fill="x", padx=20, pady=4)
        phone = LabeledEntry(box, "Phone")
        phone.pack(fill="x", padx=20, pady=4)

        def go():
            self.quick_name.set(name.get())
            self.quick_phone.set(phone.get())
            self._quick_customer()
            win.destroy()

        GoldButton(box, text="Save customer", command=go).pack(padx=20, pady=16, fill="x")

    def _estimate_popup(self):
        try:
            gross = float(self.f_weight.get() or 0)
            stone = float(self.f_stone.get() or 0)
            est = self.ctx.shop.estimate(max(gross - stone, 0), self.f_purity.get())
        except (AppError, ValueError) as exc:
            handle_error(self, exc if isinstance(exc, AppError) else AppError("Enter a valid weight first."))
            return
        symbol = self.ctx.settings.get("currency_symbol", "₹")
        p = palette()
        win = ctk.CTkToplevel(self)
        win.title("Gold value")
        win.geometry("440x260")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(box, text="Today's valuation", font=ui_font(18, "bold"), text_color=p["text"]).pack(
            padx=20, pady=(18, 8), anchor="w"
        )
        msg = (
            f"Fine gold {est['fine_gold']} g\n"
            f"Value {money(est['estimated_value'], symbol)}\n"
            f"Maximum loan {money(est['max_loan'], symbol)} at {est['ltv']}% LTV"
        )
        ctk.CTkLabel(box, text=msg, justify="left", text_color=p["text"], font=ui_font(13)).pack(
            padx=20, anchor="w"
        )

        def use():
            self.est_lbl.configure(text=msg.replace("\n", "  ·  "))
            if not self.f_amount.get().strip():
                self.f_amount.set(est["max_loan"])
            win.destroy()

        GoldButton(box, text="Use this amount", command=use).pack(padx=20, pady=16, fill="x")

    def _more_popup(self):
        p = palette()
        win = ctk.CTkToplevel(self)
        win.title("Ticket actions")
        win.geometry("360x320")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(box, text="More actions", font=ui_font(18, "bold"), text_color=p["text"]).pack(
            padx=20, pady=(18, 10), anchor="w"
        )

        def run(fn):
            win.destroy()
            fn()

        GhostButton(box, text="Print receipt", command=lambda: run(self._print)).pack(fill="x", padx=20, pady=4)
        GhostButton(box, text="Collect payment", command=lambda: run(self._pay)).pack(fill="x", padx=20, pady=4)
        close_more = GhostButton(box, text="Close loan", command=lambda: run(self._close))
        close_more.pack(fill="x", padx=20, pady=4)
        close_more.configure(text_color=p["stop"], border_color=p["stop"])
        GhostButton(box, text="Renew due date", command=lambda: run(self._renew)).pack(fill="x", padx=20, pady=4)
        GhostButton(box, text="Reopen ticket", command=lambda: run(self._reopen)).pack(fill="x", padx=20, pady=4)

    def _estimate(self):
        self._estimate_popup()

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
        ctype = LabeledDropdown(box, "Close as", CLOSE_TYPES)
        ctype.pack(fill="x", padx=20, pady=4)
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
                    close_type=ctype.get(),
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

    def _pay(self):
        if not self.current_id:
            handle_error(self, AppError("Open a ticket first."))
            return
        win = ctk.CTkToplevel(self)
        win.title("Collect")
        win.geometry("420x360")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        p = palette()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        ctk.CTkLabel(box, text="Record a collection", font=ui_font(18, "bold"), text_color=p["text"]).pack(
            padx=20, pady=(16, 6), anchor="w"
        )
        amt = LabeledEntry(box, "Amount")
        amt.pack(fill="x", padx=20, pady=4)
        kind = LabeledDropdown(box, "Towards", PAYMENT_KINDS)
        kind.pack(fill="x", padx=20, pady=4)
        method = LabeledDropdown(box, "Received by", PAYMENT_METHODS)
        method.pack(fill="x", padx=20, pady=4)
        dt = LabeledEntry(box, "Date")
        dt.set(now().date().isoformat())
        dt.pack(fill="x", padx=20, pady=4)

        def go():
            try:
                self.ctx.shop.record_payment(
                    self.ctx.user,
                    self.current_id,
                    amount=amt.get(),
                    kind=kind.get(),
                    method=method.get(),
                    payment_date=dt.get().strip(),
                    remarks="",
                )
            except AppError as exc:
                handle_error(self, exc)
                return
            win.destroy()
            show_info(self, "Collection recorded.")
            self._load(self.current_id)

        GoldButton(box, text="Save collection", command=go).pack(padx=20, pady=14, fill="x")

    def _renew(self):
        if not self.current_id:
            return
        win = ctk.CTkToplevel(self)
        win.title("Renew")
        win.geometry("400x240")
        win.transient(self.winfo_toplevel())
        win.grab_set()
        p = palette()
        box = ctk.CTkFrame(win, fg_color=p["card"])
        box.pack(fill="both", expand=True)
        due = LabeledEntry(box, "New due date")
        due.pack(fill="x", padx=20, pady=(20, 4))
        reason = LabeledEntry(box, "Reason")
        reason.pack(fill="x", padx=20, pady=4)

        def go():
            try:
                self.ctx.shop.renew(self.ctx.user, self.current_id, due.get().strip(), reason.get())
            except AppError as exc:
                handle_error(self, exc)
                return
            win.destroy()
            self._load(self.current_id)
            self.refresh()

        GoldButton(box, text="Renew ticket", command=go).pack(padx=20, pady=16, fill="x")
