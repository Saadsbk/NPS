"""Sidebar component for the SDN Network Visualizer."""

import math
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, cast

from .theme import (
    BTN_BG,
    BTN_HOVER,
    DIVIDER,
    MUTED_TEXT,
    ROUTER_CONN,
    ROUTER_FILL,
    SDN_FILL,
    SDN_OUT,
    SIDEBAR_BG,
    SUBTLE_TEXT,
    TEXT_COLOR,
)


class Sidebar:
    """Left sidebar with drag-to-canvas items, tool buttons, packet sim controls, and legend."""

    def __init__(
        self,
        parent: tk.Frame,
        *,
        on_ghost_start: Callable[[tk.Event, str], None],
        on_ghost_move: Callable[[tk.Event], None],
        on_ghost_drop: Callable[[tk.Event], None],
        on_toggle_connect: Callable[[], None],
        on_toggle_delete_link: Callable[[], None],
        on_toggle_sdn: Callable[[], None],
        on_toggle_auto: Callable[[], None],
        on_run_dijkstra: Callable[[], None],
        on_load_topology: Callable[[], None],
        on_save_topology: Callable[[], None],
        on_start_packet: Callable[[], None],
        on_clear_all: Callable[[], None],
    ) -> None:
        self.sb_canvas: tk.Canvas
        self.sb_window: int
        self.sb: tk.Frame
        self.btn_connect: tk.Label
        self.btn_del_link: tk.Label
        self.btn_sdn: tk.Label
        self.btn_auto: tk.Label
        self.src_var = tk.StringVar(value="A")
        self.dst_var = tk.StringVar(value="B")

        self._build(
            parent,
            on_ghost_start=on_ghost_start,
            on_ghost_move=on_ghost_move,
            on_ghost_drop=on_ghost_drop,
            on_toggle_connect=on_toggle_connect,
            on_toggle_delete_link=on_toggle_delete_link,
            on_toggle_sdn=on_toggle_sdn,
            on_toggle_auto=on_toggle_auto,
            on_run_dijkstra=on_run_dijkstra,
            on_load_topology=on_load_topology,
            on_save_topology=on_save_topology,
            on_start_packet=on_start_packet,
            on_clear_all=on_clear_all,
        )

    def _build(
        self,
        parent: tk.Frame,
        *,
        on_ghost_start: Callable[[tk.Event, str], None],
        on_ghost_move: Callable[[tk.Event], None],
        on_ghost_drop: Callable[[tk.Event], None],
        on_toggle_connect: Callable[[], None],
        on_toggle_delete_link: Callable[[], None],
        on_toggle_sdn: Callable[[], None],
        on_toggle_auto: Callable[[], None],
        on_run_dijkstra: Callable[[], None],
        on_load_topology: Callable[[], None],
        on_save_topology: Callable[[], None],
        on_start_packet: Callable[[], None],
        on_clear_all: Callable[[], None],
    ) -> None:
        sb_outer = tk.Frame(parent, bg=SIDEBAR_BG, width=235)
        sb_outer.pack(side="left", fill="y")
        sb_outer.pack_propagate(False)

        self.sb_canvas = tk.Canvas(sb_outer, bg=SIDEBAR_BG, highlightthickness=0, bd=0)
        sb_vsb = ttk.Scrollbar(sb_outer, orient="vertical", command=self.sb_canvas.yview)
        self.sb = tk.Frame(self.sb_canvas, bg=SIDEBAR_BG)
        self.sb.bind(
            "<Configure>",
            lambda e: self.sb_canvas.configure(scrollregion=self.sb_canvas.bbox("all")),
        )
        self.sb_window = self.sb_canvas.create_window((0, 0), window=self.sb, anchor="nw")
        self.sb_canvas.bind(
            "<Configure>",
            lambda e: self.sb_canvas.itemconfigure(self.sb_window, width=e.width),
        )
        self.sb_canvas.configure(yscrollcommand=sb_vsb.set)
        
        sb_vsb.pack(side="right", fill="y")
        self.sb_canvas.pack(side="left", fill="both", expand=True)
        self.sb_canvas.bind("<MouseWheel>", self._on_sidebar_mousewheel)

        self._build_contents(
            on_ghost_start=on_ghost_start,
            on_ghost_move=on_ghost_move,
            on_ghost_drop=on_ghost_drop,
            on_toggle_connect=on_toggle_connect,
            on_toggle_delete_link=on_toggle_delete_link,
            on_toggle_sdn=on_toggle_sdn,
            on_toggle_auto=on_toggle_auto,
            on_run_dijkstra=on_run_dijkstra,
            on_load_topology=on_load_topology,
            on_save_topology=on_save_topology,
            on_start_packet=on_start_packet,
            on_clear_all=on_clear_all,
        )

    def _build_contents(
        self,
        *,
        on_ghost_start: Callable[[tk.Event, str], None],
        on_ghost_move: Callable[[tk.Event], None],
        on_ghost_drop: Callable[[tk.Event], None],
        on_toggle_connect: Callable[[], None],
        on_toggle_delete_link: Callable[[], None],
        on_toggle_sdn: Callable[[], None],
        on_toggle_auto: Callable[[], None],
        on_run_dijkstra: Callable[[], None],
        on_load_topology: Callable[[], None],
        on_save_topology: Callable[[], None],
        on_start_packet: Callable[[], None],
        on_clear_all: Callable[[], None],
    ) -> None:
        def section(txt: str) -> None:
            tk.Label(
                self.sb,
                text=txt,
                bg=SIDEBAR_BG,
                fg=SUBTLE_TEXT,
                font=("Consolas", 7, "bold"),
            ).pack(pady=(14, 6), padx=14, anchor="w")

        section("DRAG TO CANVAS")
        self._sb_item(
            draw=self._draw_mini_router,
            label="Router",
            press_cb=lambda e: on_ghost_start(e, "router"),
            motion_cb=on_ghost_move,
            release_cb=on_ghost_drop,
        )
        self._sb_item(
            draw=self._draw_mini_sdn,
            label="SDN Ctrl",
            press_cb=lambda e: on_ghost_start(e, "sdn"),
            motion_cb=on_ghost_move,
            release_cb=on_ghost_drop,
        )

        tk.Frame(self.sb, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=12)
        section("TOOLS")

        self.btn_connect = self._tool_btn("⟷  Create Link", on_toggle_connect)
        self.btn_del_link = self._tool_btn("✖  Delete Link", on_toggle_delete_link)
        self.btn_sdn = self._tool_btn("⬡  SDN Link Mode", on_toggle_sdn)
        self.btn_auto = self._tool_btn("☐  Auto Dijkstra: OFF", on_toggle_auto)
        self._tool_btn("▶  Run Dijkstra", on_run_dijkstra)
        self._tool_btn("⭳  Load Topology", on_load_topology)
        self._tool_btn("⭱  Save Topology", on_save_topology)

        tk.Frame(self.sb, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=12)
        section("PACKET SIM")

        src_row = tk.Frame(self.sb, bg=SIDEBAR_BG)
        src_row.pack(fill="x", padx=12, pady=2)
        tk.Label(src_row, text="SRC", bg=SIDEBAR_BG, fg=MUTED_TEXT, font=("Consolas", 8), width=5).pack(side="left")
        tk.Entry(
            src_row,
            textvariable=self.src_var,
            width=10,
            justify="center",
            font=("Consolas", 9),
            bg=BTN_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief="flat",
        ).pack(side="left", fill="x", expand=True)

        dst_row = tk.Frame(self.sb, bg=SIDEBAR_BG)
        dst_row.pack(fill="x", padx=12, pady=2)
        tk.Label(dst_row, text="DST", bg=SIDEBAR_BG, fg=MUTED_TEXT, font=("Consolas", 8), width=5).pack(side="left")
        tk.Entry(
            dst_row,
            textvariable=self.dst_var,
            width=10,
            justify="center",
            font=("Consolas", 9),
            bg=BTN_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief="flat",
        ).pack(side="left", fill="x", expand=True)

        self._tool_btn("✉  Start Packet", on_start_packet)
        self._tool_btn("🗑  Clear Canvas", on_clear_all)

        tk.Frame(self.sb, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=12)
        section("LEGEND")
        for color, lbl in [
            (ROUTER_FILL, "Router (no SDN)"),
            (ROUTER_CONN, "Router (SDN linked)"),
            (SDN_FILL, "SDN Controller"),
        ]:
            row = tk.Frame(self.sb, bg=SIDEBAR_BG)
            row.pack(fill="x", padx=14, pady=2)
            c = tk.Canvas(row, width=14, height=14, bg=SIDEBAR_BG, highlightthickness=0)
            c.pack(side="left")
            c.create_oval(1, 1, 13, 13, fill=color, outline="")
            tk.Label(
                row,
                text=f"  {lbl}",
                bg=SIDEBAR_BG,
                fg=MUTED_TEXT,
                font=("Consolas", 8),
            ).pack(side="left")

    def _sb_item(
        self,
        draw: Callable[[tk.Canvas], None],
        label: str,
        press_cb: Callable[[Any], None],
        motion_cb: Callable[[Any], None],
        release_cb: Callable[[Any], None],
    ) -> None:
        frame = tk.Frame(self.sb, bg=BTN_BG, cursor="hand2")
        frame.pack(fill="x", padx=12, pady=3)

        ic = tk.Canvas(frame, width=44, height=44, bg=BTN_BG, highlightthickness=0)
        ic.pack(side="left", padx=6, pady=6)
        draw(ic)

        tk.Label(frame, text=label, bg=BTN_BG, fg=TEXT_COLOR, font=("Consolas", 10)).pack(
            side="left"
        )

        def _set_tile_bg(color: str) -> None:
            cast(Any, frame).configure(bg=color)
            for child in frame.winfo_children():
                try:
                    cast(Any, child).configure(bg=color)
                except tk.TclError:
                    pass

        def _bind_all(w: tk.Misc) -> None:
            cast(Any, w).bind("<ButtonPress-1>", press_cb)
            cast(Any, w).bind("<B1-Motion>", motion_cb)
            cast(Any, w).bind("<ButtonRelease-1>", release_cb)
            cast(Any, w).bind("<Enter>", lambda e: _set_tile_bg(BTN_HOVER))
            cast(Any, w).bind("<Leave>", lambda e: _set_tile_bg(BTN_BG))
            for child in w.winfo_children():
                _bind_all(cast(tk.Misc, child))

        _bind_all(frame)

    def _tool_btn(self, text: str, cmd: Callable[[], None]) -> tk.Label:
        btn = tk.Label(
            self.sb,
            text=text,
            bg=BTN_BG,
            fg=TEXT_COLOR,
            font=("Consolas", 9),
            padx=10,
            pady=7,
            cursor="hand2",
            anchor="w",
        )
        btn.pack(fill="x", padx=12, pady=2)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.configure(bg=BTN_HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=BTN_BG))
        return btn

    @staticmethod
    def _draw_mini_router(c: tk.Canvas) -> None:
        c.create_oval(6, 6, 38, 38, fill=ROUTER_FILL, outline="#5ea46a", width=2)
        c.create_text(22, 22, text="R", fill="#1e1e2e", font=("Consolas", 12, "bold"))

    @staticmethod
    def _draw_mini_sdn(c: tk.Canvas) -> None:
        pts: list[float] = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts += [22 + 16 * math.cos(a), 22 + 16 * math.sin(a)]
        c.create_polygon(pts, fill=SDN_FILL, outline=SDN_OUT, width=2)
        c.create_text(22, 20, text="S", fill="#1e1e2e", font=("Consolas", 9, "bold"))
        c.create_text(22, 30, text="D", fill="#1e1e2e", font=("Consolas", 7))

    def _on_sidebar_mousewheel(self, event: tk.Event) -> None:
        self.sb_canvas.yview_scroll(-1 * (event.delta // 120), "units")
