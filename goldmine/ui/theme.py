from __future__ import annotations

import customtkinter as ctk

NAVY = "#15233F"
NAVY_DARK = "#0E1728"
GOLD = "#C8A349"
GOLD_HOVER = "#D4B45C"
CREAM = "#F3EEE4"
CREAM_CARD = "#FFFCF7"
MUTED = "#6D7380"
DANGER = "#B42318"
SUCCESS = "#087443"
SURFACE_DARK = "#121826"
CARD_DARK = "#1C2434"
SOFT = "#EFE8D8"


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
        "text": "#F4EFE4" if dark else NAVY,
        "muted": "#9AA3B5" if dark else MUTED,
        "gold": GOLD,
        "danger": "#F97066" if dark else DANGER,
        "success": "#75E0A7" if dark else SUCCESS,
        "input": "#2A3246" if dark else "#FFFFFF",
        "border": "#343E52" if dark else "#E4D9C0",
        "soft": "#252E41" if dark else SOFT,
        "nav_hover": "#1B2740",
        "nav_text": "#F4EFE4",
    }
