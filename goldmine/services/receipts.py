from __future__ import annotations

import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from goldmine.paths import receipts_dir
from goldmine.security.permissions import CurrentUser, require_user
from goldmine.services.audit import AuditService
from goldmine.util import format_date, money, now


class ReceiptService:
    def __init__(self, audit: AuditService, settings) -> None:
        self.audit = audit
        self.settings = settings

    def generate(self, user: CurrentUser, loan: dict) -> Path:
        require_user(user)
        symbol = self.settings.get("currency_symbol", "₹")
        path = receipts_dir() / f"{loan['loan_number']}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        y = height - 20 * mm
        c.setFillColorRGB(0.11, 0.16, 0.29)
        c.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0.79, 0.64, 0.15)
        c.setFont("Times-Bold", 22)
        c.drawString(18 * mm, height - 16 * mm, self.settings.get("shop_name", "Goldmine"))
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 18 * mm, height - 14 * mm, "PLEDGE TICKET")
        c.setFillColorRGB(0.1, 0.1, 0.1)
        y = height - 40 * mm
        c.setFont("Helvetica", 9)
        addr = self.settings.get("shop_address", "")
        phone = self.settings.get("shop_phone", "")
        if addr:
            c.drawString(18 * mm, y, addr)
            y -= 5 * mm
        if phone:
            c.drawString(18 * mm, y, f"Phone: {phone}")
            y -= 8 * mm
        else:
            y -= 4 * mm

        def line(label, value):
            nonlocal y
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.35, 0.35, 0.35)
            c.drawString(18 * mm, y, label)
            c.setFillColorRGB(0.1, 0.1, 0.1)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(70 * mm, y, str(value or "—"))
            y -= 7 * mm

        line("Loan number", loan["loan_number"])
        line("Status", (loan.get("status") or "").title())
        line("Customer", loan.get("customer_name"))
        line("Phone", loan.get("customer_phone"))
        line("Gold", loan.get("gold_description"))
        line("Weight", f"{loan.get('gold_weight')} g")
        line("Purity", loan.get("gold_purity") or "—")
        line("Locker", loan.get("locker_no") or "—")
        for item in loan.get("items") or []:
            line("Ornament", f"{item.get('jewellery_type')}  {item.get('net_weight')} g")
        line("Loan amount", money(loan.get("loan_amount"), symbol))
        line("Interest rate", f"{loan.get('interest_rate')}% per month")
        line("Start date", format_date(loan.get("start_date")))
        line("Due date", format_date(loan.get("due_date")))
        if loan.get("status") == "closed":
            line("Closed on", format_date(loan.get("closing_date")))
            line("Interest collected", money(loan.get("interest_collected"), symbol))
            line("Total received", money(loan.get("total_received"), symbol))
        y -= 6 * mm
        c.setStrokeColorRGB(0.79, 0.64, 0.15)
        c.line(18 * mm, y, width - 18 * mm, y)
        y -= 10 * mm
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(18 * mm, y, self.settings.get("receipt_footer", "Thank you for your business."))
        c.drawString(18 * mm, 15 * mm, f"Printed {now().strftime('%d %b %Y %H:%M')} by {user.username}")
        c.showPage()
        c.save()
        self.audit.record(user, "loan.print", entity_type="loan", entity_id=loan["loan_number"], new={"path": path.name})
        return path

    def open_file(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
