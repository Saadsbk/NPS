"""Right panel component for flow tables and path display."""

import tkinter as tk
from tkinter import ttk
from typing import Any, cast

from .theme import (
    ACCENT,
    BTN_HOVER,
    DIVIDER,
    FLOW_ROW_A,
    FLOW_ROW_B,
    MUTED_TEXT,
    PANEL_BG,
    ROUTER_CONN,
    ROUTER_FILL,
    SDN_FILL,
    SUBTLE_TEXT,
    UNREACHABLE,
)

# Column definitions: (header text, character width)
FLOW_COLS: tuple[tuple[str, int], ...] = (
    ("DST", 6),
    ("→", 2),
    ("NEXT HOP", 10),
    ("COST", 6),
)


class RightPanel:
    """Right side panel showing shortest & second-shortest path tables with full path display."""

    def __init__(self, parent: tk.Frame) -> None:
        self.fp_title: tk.Label
        self.fp_canvas_short: tk.Canvas
        self.fp_inner_short: tk.Frame
        self.fp_window_short: int
        self.fp_path_short: tk.Label
        self.fp_canvas_sec: tk.Canvas
        self.fp_inner_sec: tk.Frame
        self.fp_window_sec: int
        self.fp_path_sec: tk.Label
        self._build(parent)

    def _build(self, rp: tk.Frame) -> None:
        self.fp_title = tk.Label(
            rp,
            text="— select a router —",
            bg=PANEL_BG,
            fg=ACCENT,
            font=("Consolas", 12, "bold"),
        )
        self.fp_title.pack(padx=14, pady=(14, 2), anchor="w")

        pw = tk.PanedWindow(rp, orient="vertical", bg=DIVIDER, bd=0, sashwidth=4)
        pw.pack(fill="both", expand=True)

        # ── Top Pane: Shortest Paths ──
        top_pane = tk.Frame(pw, bg=PANEL_BG)
        pw.add(top_pane, minsize=120, stretch="always")

        tk.Label(
            top_pane,
            text="SHORTEST PATH TABLE",
            bg=PANEL_BG,
            fg=SUBTLE_TEXT,
            font=("Consolas", 8, "bold"),
        ).pack(pady=(10, 2), padx=14, anchor="w")

        tk.Frame(top_pane, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=4)

        hdr_top = tk.Frame(top_pane, bg=DIVIDER)
        hdr_top.pack(fill="x", padx=14, pady=(0, 4))
        for txt, w in FLOW_COLS:
            tk.Label(
                hdr_top,
                text=txt,
                bg=DIVIDER,
                fg=ACCENT,
                font=("Consolas", 8, "bold"),
                width=w,
                anchor="center",
                padx=2,
            ).pack(side="left", fill="x", expand=True)

        # Pack path label at bottom FIRST so it claims space and doesn't get squished
        self.fp_path_short = tk.Label(
            top_pane,
            text="",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 8),
            wraplength=0,  # will be set dynamically
            justify="left",
            anchor="nw",
            height=3,
        )
        self.fp_path_short.pack(side="bottom", padx=14, pady=(2, 4), fill="x")
        self.fp_path_short.bind(
            "<Configure>",
            lambda e: self.fp_path_short.configure(wraplength=max(e.width - 4, 50)),
        )
        tk.Frame(top_pane, bg=DIVIDER, height=1).pack(side="bottom", fill="x", padx=14, pady=(4, 0))

        outer_top = tk.Frame(top_pane, bg=PANEL_BG)
        outer_top.pack(side="top", fill="both", expand=True, padx=14)

        self.fp_canvas_short = tk.Canvas(outer_top, bg=PANEL_BG, highlightthickness=0)
        vsb_top = ttk.Scrollbar(outer_top, orient="vertical", command=self.fp_canvas_short.yview)
        self.fp_inner_short = tk.Frame(self.fp_canvas_short, bg=PANEL_BG)
        self.fp_inner_short.bind(
            "<Configure>",
            lambda e: self.fp_canvas_short.configure(scrollregion=self.fp_canvas_short.bbox("all")),
        )
        self.fp_window_short = self.fp_canvas_short.create_window(
            (0, 0), window=self.fp_inner_short, anchor="nw"
        )
        self.fp_canvas_short.bind(
            "<Configure>",
            lambda e: self.fp_canvas_short.itemconfigure(self.fp_window_short, width=e.width),
        )
        self.fp_canvas_short.configure(yscrollcommand=vsb_top.set)
        self.fp_canvas_short.pack(side="left", fill="both", expand=True)
        vsb_top.pack(side="right", fill="y")
        self.fp_canvas_short.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_short.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        self.fp_inner_short.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_short.yview_scroll(-1 * (e.delta // 120), "units"),
        )

        # ── Bottom Pane: Second Shortest Paths ──
        bottom_pane = tk.Frame(pw, bg=PANEL_BG)
        pw.add(bottom_pane, minsize=120, stretch="always")

        tk.Label(
            bottom_pane,
            text="SECOND SHORTEST PATH TABLE",
            bg=PANEL_BG,
            fg=SUBTLE_TEXT,
            font=("Consolas", 8, "bold"),
        ).pack(pady=(10, 2), padx=14, anchor="w")

        tk.Frame(bottom_pane, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=4)

        hdr_bottom = tk.Frame(bottom_pane, bg=DIVIDER)
        hdr_bottom.pack(fill="x", padx=14, pady=(0, 4))
        for txt, w in FLOW_COLS:
            tk.Label(
                hdr_bottom,
                text=txt,
                bg=DIVIDER,
                fg=ACCENT,
                font=("Consolas", 8, "bold"),
                width=w,
                anchor="center",
                padx=2,
            ).pack(side="left", fill="x", expand=True)

        # Pack path label at bottom FIRST so it claims space and doesn't get squished
        self.fp_path_sec = tk.Label(
            bottom_pane,
            text="",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 8),
            wraplength=0,  # will be set dynamically
            justify="left",
            anchor="nw",
            height=3,
        )
        self.fp_path_sec.pack(side="bottom", padx=14, pady=(2, 4), fill="x")
        self.fp_path_sec.bind(
            "<Configure>",
            lambda e: self.fp_path_sec.configure(wraplength=max(e.width - 4, 50)),
        )
        tk.Frame(bottom_pane, bg=DIVIDER, height=1).pack(side="bottom", fill="x", padx=14, pady=(4, 0))

        outer_bottom = tk.Frame(bottom_pane, bg=PANEL_BG)
        outer_bottom.pack(side="top", fill="both", expand=True, padx=14)

        self.fp_canvas_sec = tk.Canvas(outer_bottom, bg=PANEL_BG, highlightthickness=0)
        vsb_bottom = ttk.Scrollbar(outer_bottom, orient="vertical", command=self.fp_canvas_sec.yview)
        self.fp_inner_sec = tk.Frame(self.fp_canvas_sec, bg=PANEL_BG)
        self.fp_inner_sec.bind(
            "<Configure>",
            lambda e: self.fp_canvas_sec.configure(scrollregion=self.fp_canvas_sec.bbox("all")),
        )
        self.fp_window_sec = self.fp_canvas_sec.create_window(
            (0, 0), window=self.fp_inner_sec, anchor="nw"
        )
        self.fp_canvas_sec.bind(
            "<Configure>",
            lambda e: self.fp_canvas_sec.itemconfigure(self.fp_window_sec, width=e.width),
        )
        self.fp_canvas_sec.configure(yscrollcommand=vsb_bottom.set)
        self.fp_canvas_sec.pack(side="left", fill="both", expand=True)
        vsb_bottom.pack(side="right", fill="y")
        self.fp_canvas_sec.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_sec.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        self.fp_inner_sec.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_sec.yview_scroll(-1 * (e.delta // 120), "units"),
        )

    # ── Public API ──

    def set_title(self, text: str) -> None:
        self.fp_title.configure(text=text)

    def clear(self) -> None:
        """Reset panel to empty state."""
        self.fp_title.configure(text="— select a router —")
        for w in self.fp_inner_short.winfo_children():
            w.destroy()
        for w in self.fp_inner_sec.winfo_children():
            w.destroy()
        self.fp_path_short.configure(text="")
        self.fp_path_sec.configure(text="")

    def show_not_connected(self) -> None:
        """Show message that router is not connected to SDN."""
        msg1 = tk.Label(
            self.fp_inner_short,
            text="Not connected to SDN Controller.",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 9),
            padx=6,
            pady=6,
        )
        msg1.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_short.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        msg1.pack(anchor="w")

    def show_no_entries_short(self) -> None:
        msg = tk.Label(
            self.fp_inner_short,
            text="No other SDN-managed routers.\nAdd more routers and links.",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 9),
            padx=6,
            pady=6,
        )
        msg.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_short.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        msg.pack(anchor="w")

    def show_no_entries_sec(self) -> None:
        msg = tk.Label(
            self.fp_inner_sec,
            text="No other SDN-managed routers.",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 9),
            padx=6,
            pady=6,
        )
        msg.bind(
            "<MouseWheel>",
            lambda e: self.fp_canvas_sec.yview_scroll(-1 * (e.delta // 120), "units"),
        )
        msg.pack(anchor="w")

    def render_table(
        self, parent: tk.Frame, entries: list, canvas: tk.Canvas, path_label: tk.Label, prefix: str
    ) -> None:
        """Render flow table rows into the given parent frame.

        Args:
            parent: The inner frame to populate with rows.
            entries: List of flow entry dicts (dst, next_hop, cost, path).
            canvas: The scrollable canvas for mousewheel binding.
            path_label: The label widget where the full path text is displayed.
            prefix: Text prefix for the path display (e.g. "Shortest" or "2nd Shortest").
        """
        for i, e in enumerate(entries):
            row_bg = FLOW_ROW_A if i % 2 == 0 else FLOW_ROW_B
            row = tk.Frame(parent, bg=row_bg, cursor="hand2")
            row.pack(fill="x", pady=1)

            tk.Label(
                row,
                text=e["dst"],
                bg=row_bg,
                fg=ROUTER_FILL,
                font=("Consolas", 11, "bold"),
                width=FLOW_COLS[0][1],
                anchor="center",
                padx=4,
                pady=5,
            ).pack(side="left", fill="x", expand=True)
            tk.Label(
                row,
                text="→",
                bg=row_bg,
                fg=SUBTLE_TEXT,
                font=("Consolas", 9),
                width=FLOW_COLS[1][1],
                anchor="center",
            ).pack(side="left")
            nh_color = ROUTER_CONN if e["next_hop"] != "—" else UNREACHABLE
            tk.Label(
                row,
                text=str(e["next_hop"]),
                bg=row_bg,
                fg=nh_color,
                font=("Consolas", 10),
                width=FLOW_COLS[2][1],
                anchor="center",
            ).pack(side="left", fill="x", expand=True)
            tk.Label(
                row,
                text=str(e["cost"]),
                bg=row_bg,
                fg=SDN_FILL,
                font=("Consolas", 9, "bold"),
                width=FLOW_COLS[3][1],
                anchor="center",
                padx=2,
            ).pack(side="left", fill="x", expand=True)

            path = e["path"]

            def _hover_on(ev: tk.Event, f: tk.Frame = row) -> None:
                _ = ev
                for w in f.winfo_children():
                    cast(Any, w).configure(bg=BTN_HOVER)
                cast(Any, f).configure(bg=BTN_HOVER)

            def _hover_off(
                ev: tk.Event, f: tk.Frame = row, bg: str = row_bg
            ) -> None:
                _ = ev
                for w in f.winfo_children():
                    cast(Any, w).configure(bg=bg)
                cast(Any, f).configure(bg=bg)

            def _click(
                ev: tk.Event,
                p: str = path,
                lbl: tk.Label = path_label,
                pref: str = prefix,
            ) -> None:
                _ = ev
                lbl.configure(text=f"{pref} Path:\n{p}")

            for w in [cast(tk.Misc, row)] + [
                cast(tk.Misc, w_child) for w_child in row.winfo_children()
            ]:
                cast(Any, w).bind("<Enter>", _hover_on)
                cast(Any, w).bind("<Leave>", _hover_off)
                cast(Any, w).bind("<Button-1>", _click)
                cast(Any, w).bind(
                    "<MouseWheel>",
                    lambda ev, c=canvas: c.yview_scroll(-1 * (ev.delta // 120), "units"),
                )
