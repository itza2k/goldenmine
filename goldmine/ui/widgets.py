from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from goldmine.ui.theme import GOLD, GOLD_HOVER, NAVY, palette, ui_font


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        p = palette()
        kwargs.setdefault("fg_color", p["card"])
        kwargs.setdefault("corner_radius", 16)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", p["border"])
        super().__init__(master, **kwargs)


class PageHeader(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str = "", action: tuple | None = None):
        super().__init__(master, fg_color="transparent")
        p = palette()
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left, text=title, font=ui_font(26, "bold"), text_color=p["text"]).pack(anchor="w")
        self.sub = ctk.CTkLabel(left, text=subtitle, font=ui_font(13), text_color=p["muted"])
        self.sub.pack(anchor="w", pady=(2, 0))
        if action:
            GoldButton(self, text=action[0], width=140, command=action[1]).pack(side="right")

    def set_subtitle(self, text: str) -> None:
        self.sub.configure(text=text)


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text: str):
        p = palette()
        super().__init__(
            master,
            text=text.upper(),
            font=ui_font(11, "bold"),
            text_color=GOLD,
            anchor="w",
        )


class StatusBadge(ctk.CTkLabel):
    def __init__(self, master, text: str = "Open", kind: str = "ok"):
        colors = {
            "ok": ("#E8F6EE", "#087443"),
            "warn": ("#F8EED8", "#8A6A12"),
            "lock": ("#F4E8E6", "#B42318"),
            "info": ("#E8EEF6", NAVY),
        }
        bg, fg = colors.get(kind, colors["info"])
        super().__init__(
            master,
            text=text,
            fg_color=bg,
            text_color=fg,
            corner_radius=8,
            font=ui_font(11, "bold"),
            height=24,
            padx=10,
        )

    def set(self, text: str, kind: str) -> None:
        colors = {
            "ok": ("#E8F6EE", "#087443"),
            "warn": ("#F8EED8", "#8A6A12"),
            "lock": ("#F4E8E6", "#B42318"),
            "info": ("#E8EEF6", NAVY),
        }
        bg, fg = colors.get(kind, colors["info"])
        self.configure(text=text, fg_color=bg, text_color=fg)


class StatCard(Card):
    def __init__(self, master, title: str, value: str, subtitle: str = ""):
        super().__init__(master)
        p = palette()
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        accent = ctk.CTkFrame(inner, fg_color=GOLD, width=3, height=46, corner_radius=2)
        accent.pack(side="left", fill="y", padx=(0, 12))
        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(body, text=title, text_color=p["muted"], font=ui_font(11, "bold")).pack(anchor="w")
        self.value_lbl = ctk.CTkLabel(body, text=value, text_color=p["text"], font=ui_font(24, "bold"))
        self.value_lbl.pack(anchor="w", pady=(2, 0))
        self.sub_lbl = ctk.CTkLabel(body, text=subtitle, text_color=GOLD, font=ui_font(12))
        self.sub_lbl.pack(anchor="w")

    def set(self, value: str, subtitle: str | None = None) -> None:
        self.value_lbl.configure(text=value)
        if subtitle is not None:
            self.sub_lbl.configure(text=subtitle)


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label: str, placeholder: str = "", show: str | None = None, **kwargs):
        p = palette()
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=p["muted"], font=ui_font(11, "bold")).pack(anchor="w")
        self.entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            height=40,
            corner_radius=8,
            border_width=1,
            border_color=p["border"],
            fg_color=p["input"],
            text_color=p["text"],
            font=ui_font(13),
            show=show or "",
            **kwargs,
        )
        self.entry.pack(fill="x", pady=(5, 0))

    def get(self) -> str:
        return self.entry.get()

    def set(self, value) -> None:
        self.entry.delete(0, "end")
        if value is not None:
            self.entry.insert(0, str(value))

    def configure_state(self, state: str) -> None:
        self.entry.configure(state=state)


class LabeledDropdown(ctk.CTkFrame):
    def __init__(self, master, label: str, values: list[str], **kwargs):
        p = palette()
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text=label, text_color=p["muted"], font=ui_font(11, "bold")).pack(anchor="w")
        vals = values or ["—"]
        self.menu = ctk.CTkOptionMenu(
            self,
            values=vals,
            height=40,
            corner_radius=8,
            fg_color=NAVY,
            button_color=GOLD,
            button_hover_color=GOLD_HOVER,
            text_color="#FFF6E4",
            font=ui_font(13),
            dropdown_fg_color=NAVY,
            dropdown_text_color="#FFF6E4",
            **kwargs,
        )
        self.menu.pack(fill="x", pady=(5, 0))
        self.menu.set(vals[0])

    def get(self) -> str:
        return self.menu.get()

    def set(self, value) -> None:
        if value in self.menu.cget("values"):
            self.menu.set(str(value))
        elif value:
            current = list(self.menu.cget("values"))
            if str(value) not in current:
                self.menu.configure(values=current + [str(value)])
            self.menu.set(str(value))

    def configure_state(self, state: str) -> None:
        self.menu.configure(state=state)


class GoldButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", GOLD)
        kwargs.setdefault("hover_color", GOLD_HOVER)
        kwargs.setdefault("text_color", NAVY)
        kwargs.setdefault("font", ui_font(13, "bold"))
        kwargs.setdefault("height", 40)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(master, **kwargs)


class GhostButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        p = palette()
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", p["border"])
        kwargs.setdefault("text_color", p["text"])
        kwargs.setdefault("hover_color", p["soft"])
        kwargs.setdefault("font", ui_font(13))
        kwargs.setdefault("height", 40)
        kwargs.setdefault("corner_radius", 8)
        super().__init__(master, **kwargs)


class QuietButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", "#1B2740")
        kwargs.setdefault("text_color", "#C9D0DC")
        kwargs.setdefault("font", ui_font(13))
        kwargs.setdefault("height", 36)
        kwargs.setdefault("anchor", "w")
        super().__init__(master, **kwargs)


def style_treeview(tree: ttk.Treeview) -> None:
    p = palette()
    style = ttk.Style(tree)
    style.theme_use("clam")
    style.configure(
        "Gold.Treeview",
        background=p["card"],
        fieldbackground=p["card"],
        foreground=p["text"],
        rowheight=34,
        borderwidth=0,
        font=("Helvetica Neue", 12),
    )
    style.configure(
        "Gold.Treeview.Heading",
        background=NAVY,
        foreground="#F4EFE4",
        relief="flat",
        font=("Helvetica Neue", 11, "bold"),
        padding=6,
    )
    style.map("Gold.Treeview", background=[("selected", GOLD)], foreground=[("selected", NAVY)])
    tree.configure(style="Gold.Treeview")


class DataTable(ctk.CTkFrame):
    def __init__(self, master, columns: list[tuple[str, str, int]], on_select=None):
        p = palette()
        super().__init__(master, fg_color=p["card"], corner_radius=16, border_width=1, border_color=p["border"])
        self.columns = columns
        self.on_select = on_select
        ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", selectmode="browse")
        for col_id, heading, width in columns:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, stretch=True, anchor="w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", pady=10, padx=(0, 10))
        style_treeview(self.tree)
        self.tree.bind("<<TreeviewSelect>>", self._selected)
        self.tree.bind("<Double-1>", self._selected)

    def _selected(self, _=None):
        if self.on_select:
            item = self.selected()
            if item:
                self.on_select(item)

    def set_rows(self, rows: list[dict], key: str = "id") -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            values = [row.get(c[0], "") for c in self.columns]
            iid = str(row.get(key, ""))
            try:
                self.tree.insert("", "end", iid=iid, values=values)
            except Exception:
                self.tree.insert("", "end", values=values)

    def selected_id(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def selected(self) -> dict | None:
        iid = self.selected_id()
        if not iid:
            return None
        item = self.tree.item(iid)
        data = {c[0]: v for c, v in zip(self.columns, item["values"])}
        data["id"] = iid
        return data
