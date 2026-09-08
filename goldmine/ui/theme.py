from __future__ import annotations

import customtkinter as ctk

# Quiet paper + ink. One muted metal accent, used sparingly.
NAVY = "#1A1A1A"
NAVY_DARK = "#111111"
GOLD = "#8E8568"
GOLD_HOVER = "#2A2A2A"
CREAM = "#F5F5F3"
CREAM_CARD = "#FFFFFF"
MUTED = "#6E6E6A"
DANGER = "#B42318"
SUCCESS = "#2F6F4E"
SURFACE_DARK = "#121212"
CARD_DARK = "#1E1E1E"
SOFT = "#EFEFEA"


def ui_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Helvetica Neue", size=size, weight=weight)


def apply_theme(mode: str) -> None:
    if mode not in ("light", "dark", "system"):
        mode = "light"
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def palette() -> dict:
    dark = is_dark()
    return {
        "bg": SURFACE_DARK if dark else CREAM,
        "sidebar": NAVY_DARK if dark else NAVY,
        "card": CARD_DARK if dark else CREAM_CARD,
        "text": "#F2F2F0" if dark else "#1A1A1A",
        "muted": "#A8A8A4" if dark else MUTED,
        "gold": GOLD,
        "danger": "#F97066" if dark else DANGER,
        "success": "#6FCF97" if dark else SUCCESS,
        "input": "#2A2A2A" if dark else "#FFFFFF",
        "border": "#333333" if dark else "#E4E4E0",
        "soft": "#2A2A2A" if dark else SOFT,
        "nav_hover": "#2A2A2A",
        "nav_text": "#F2F2F0",
        "on_ink": "#F5F5F3",
    }
