from __future__ import annotations

TITLES = ["Mr", "Mrs", "Ms", "M/s"]

ID_PROOF_TYPES = [
    "Aadhaar",
    "PAN",
    "Voter ID",
    "Driving licence",
    "Passport",
    "Ration card",
    "Other",
]

JEWELLERY_TYPES = [
    "Necklace",
    "Chain",
    "Ring",
    "Bangle",
    "Bracelet",
    "Earring",
    "Mangalsutra",
    "Coin",
    "Bar / biscuit",
    "Pendant",
    "Anklet",
    "Other jewellery",
]

PURITIES = ["24K / 999", "22K / 916", "21K", "20K", "18K", "14K"]

PURITY_FINE = {
    "24K / 999": 1.0,
    "22K / 916": 0.916,
    "21K": 0.875,
    "20K": 0.833,
    "18K": 0.750,
    "14K": 0.585,
}

CONDITIONS = ["Excellent", "Good", "Average", "Stone-set", "Damaged"]

PAYMENT_METHODS = ["Cash", "UPI", "Bank transfer", "Cheque", "Card"]

PAYMENT_KINDS = ["Interest", "Principal", "Mixed"]

CLOSE_TYPES = ["Redeemed", "Interest settled", "Auctioned", "Written off"]

LOAN_FILTERS = ["Open", "Overdue", "Due soon", "Closed", "All"]

NOTICE_STATUS = ["Not sent", "Reminder sent", "Final notice"]


def fine_factor(purity: str | None) -> float:
    if not purity:
        return 0.916
    return PURITY_FINE.get(purity, 0.916)
