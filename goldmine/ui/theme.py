from __future__ import annotations

import customtkinter as ctk

NAVY = "#1A120C"
NAVY_DARK = "#120C08"
GOLD = "#D4AF37"
GOLD_HOVER = "#E3C25A"
CREAM = "#F3E4C4"
CREAM_CARD = "#FFF8E8"
MUTED = "#6B5344"
DANGER = "#B42318"
SUCCESS = "#087443"
SURFACE_DARK = "#16100C"
CARD_DARK = "#241C16"
SOFT = "#EAD9B4"


def ui_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Helvetica Neue", size=size, weight=weight)


def apply_theme(mode: str) -> None:
    if mode not in ("light", "dark", "system"):
        mode = "light"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("green")


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def palette() -> dict:
    dark = is_dark()
    return {
        "bg": SURFACE_DARK if dark else CREAM,
        "sidebar": NAVY_DARK if dark else NAVY,
        "card": CARD_DARK if dark else CREAM_CARD,
        "text": "#F7E7C3" if dark else "#2A1B12",
        "muted": "#B7A089" if dark else MUTED,
        "gold": GOLD,
        "danger": "#F97066" if dark else DANGER,
        "success": "#75E0A7" if dark else SUCCESS,
        "input": "#2B2118" if dark else "#FFFDF6",
        "border": "#3A2E22" if dark else "#E2C98A",
        "soft": "#2B2118" if dark else SOFT,
        "nav_hover": "#2A1D14",
        "nav_text": "#F7E7C3",
    }
