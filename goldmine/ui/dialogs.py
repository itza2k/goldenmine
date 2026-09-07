from __future__ import annotations

import customtkinter as ctk

from goldmine.exceptions import AppError
from goldmine.ui.theme import GOLD, NAVY, palette
from goldmine.ui.widgets import GhostButton, GoldButton, LabeledEntry


def show_error(master, message: str, title: str = "Cannot continue") -> None:
    _toast(master, title, message, kind="error")


def show_info(master, message: str, title: str = "Done") -> None:
    _toast(master, title, message, kind="ok")


def _toast(master, title: str, message: str, kind: str) -> None:
    p = palette()
    win = ctk.CTkToplevel(master)
    win.title(title)
    win.geometry("420x180")
    win.resizable(False, False)
    win.transient(master.winfo_toplevel())
    win.grab_set()
    frame = ctk.CTkFrame(win, fg_color=p["card"], corner_radius=0)
    frame.pack(fill="both", expand=True)
    ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=p["text"]).pack(
        padx=24, pady=(22, 8), anchor="w"
    )
    ctk.CTkLabel(frame, text=message, wraplength=360, justify="left", text_color=p["muted"]).pack(
        padx=24, anchor="w"
    )
    GoldButton(frame, text="OK", width=100, command=win.destroy).pack(pady=18, padx=24, anchor="e")
    win.bind("<Return>", lambda e: win.destroy())
    win.focus()


def confirm(master, title: str, message: str) -> bool:
    p = palette()
    win = ctk.CTkToplevel(master)
    win.title(title)
    win.geometry("440x200")
    win.resizable(False, False)
    win.transient(master.winfo_toplevel())
    win.grab_set()
    result = {"ok": False}
    frame = ctk.CTkFrame(win, fg_color=p["card"], corner_radius=0)
    frame.pack(fill="both", expand=True)
    ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=p["text"]).pack(
        padx=24, pady=(22, 8), anchor="w"
    )
    ctk.CTkLabel(frame, text=message, wraplength=380, justify="left", text_color=p["muted"]).pack(padx=24, anchor="w")
    row = ctk.CTkFrame(frame, fg_color="transparent")
    row.pack(fill="x", padx=24, pady=18)

    def yes():
        result["ok"] = True
        win.destroy()

    GhostButton(row, text="Cancel", width=110, command=win.destroy).pack(side="right")
    GoldButton(row, text="Confirm", width=110, command=yes).pack(side="right", padx=(0, 8))
    win.wait_window()
    return result["ok"]


def prompt_text(master, title: str, label: str, placeholder: str = "") -> str | None:
    p = palette()
    win = ctk.CTkToplevel(master)
    win.title(title)
    win.geometry("440x220")
    win.resizable(False, False)
    win.transient(master.winfo_toplevel())
    win.grab_set()
    result = {"value": None}
    frame = ctk.CTkFrame(win, fg_color=p["card"], corner_radius=0)
    frame.pack(fill="both", expand=True)
    ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=p["text"]).pack(
        padx=24, pady=(22, 8), anchor="w"
    )
    field = LabeledEntry(frame, label, placeholder)
    field.pack(fill="x", padx=24)
    row = ctk.CTkFrame(frame, fg_color="transparent")
    row.pack(fill="x", padx=24, pady=18)

    def ok():
        result["value"] = field.get()
        win.destroy()

    GhostButton(row, text="Cancel", width=110, command=win.destroy).pack(side="right")
    GoldButton(row, text="Save", width=110, command=ok).pack(side="right", padx=(0, 8))
    win.bind("<Return>", lambda e: ok())
    field.entry.focus()
    win.wait_window()
    return result["value"]


def owner_auth_dialog(master, auth, user) -> tuple[str, str] | None:
    """Return (password, reason) or None."""
    p = palette()
    win = ctk.CTkToplevel(master)
    win.title("Owner confirmation")
    win.geometry("460x320")
    win.resizable(False, False)
    win.transient(master.winfo_toplevel())
    win.grab_set()
    result = {"pair": None}
    frame = ctk.CTkFrame(win, fg_color=p["card"], corner_radius=0)
    frame.pack(fill="both", expand=True)
    ctk.CTkLabel(
        frame,
        text="Owner password required",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=p["text"],
    ).pack(padx=24, pady=(22, 4), anchor="w")
    ctk.CTkLabel(
        frame,
        text="This loan is locked. Confirm your password and give a reason before changing it.",
        wraplength=400,
        justify="left",
        text_color=p["muted"],
    ).pack(padx=24, anchor="w")
    pw = LabeledEntry(frame, "Owner password", show="•")
    pw.pack(fill="x", padx=24, pady=(12, 0))
    reason = LabeledEntry(frame, "Reason for change")
    reason.pack(fill="x", padx=24, pady=(10, 0))
    err = ctk.CTkLabel(frame, text="", text_color="#B42318")
    err.pack(anchor="w", padx=24, pady=(6, 0))
    row = ctk.CTkFrame(frame, fg_color="transparent")
    row.pack(fill="x", padx=24, pady=12)

    def ok():
        password = pw.get()
        why = reason.get().strip()
        if not password or not why:
            err.configure(text="Password and reason are required.")
            return
        try:
            auth.verify_owner_password(user, password)
        except AppError as exc:
            err.configure(text=str(exc))
            return
        result["pair"] = (password, why)
        win.destroy()

    GhostButton(row, text="Cancel", width=110, command=win.destroy).pack(side="right")
    GoldButton(row, text="Confirm", width=110, command=ok).pack(side="right", padx=(0, 8))
    pw.entry.focus()
    win.wait_window()
    return result["pair"]


def handle_error(master, exc: Exception) -> None:
    if isinstance(exc, AppError):
        show_error(master, str(exc))
    else:
        show_error(master, "Something went wrong. The action was not saved.")
