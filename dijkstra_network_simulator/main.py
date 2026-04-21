
import math
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, cast

from .logic import FlowTables, SDNLogic
from .models import LinkEdge, RouterNode, SDNNode
from .simulation_handler import PacketSimulationHandler

from .theme import (
    ACCENT,
    BG,
    BTN_BG,
    BTN_HOVER,
    CANVAS_BG,
    DIVIDER,
    FLOW_ROW_A,
    FLOW_ROW_B,
    HEADER_BG,
    MUTED_TEXT,
    PANEL_BG,
    ROUTER_CONN,
    ROUTER_FILL,
    ROUTER_OUT,
    SDN_FILL,
    SDN_OUT,
    SDN_R,
    SELECT_CLR,
    SIDEBAR_BG,
    SUBTLE_TEXT,
    TEXT_COLOR,
    UNREACHABLE,
    ROUTER_R,
)


class App:
    FLOW_COLS: tuple[tuple[str, int], ...] = (
        ("DST", 6),
        ("→", 2),
        ("NEXT HOP", 19),
        ("COST", 6),
    )

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SDN Network Visualizer — Dijkstra's Algorithm Demo")
        self.root.configure(bg=BG)
        self.root.geometry("1280x760")
        self.root.minsize(960, 600)

        self.routers: list[RouterNode] = []
        self.sdn_node: SDNNode | None = None
        self.links: list[LinkEdge] = []
        self.flow_tables: FlowTables = {}
        self.logic = SDNLogic()
        self.simulator: PacketSimulationHandler | None = None
        self.auto_dijkstra = False

        self.mode: str = "idle"
        self.selected_node: RouterNode | None = None
        self.drag_node: RouterNode | SDNNode | None = None
        self.ghost_id: int | None = None
        self.placing_type: str | None = None
        self.info_router: RouterNode | None = None
        self.pan_anchor: tuple[float, float] | None = None
        self.editing_link: LinkEdge | None = None
        self.weight_editor: tk.Entry | None = None
        self.weight_editor_window: int | None = None

        self.sb_canvas: tk.Canvas
        self.sb_window: int
        self.sb: tk.Frame
        self.canvas: tk.Canvas
        self.status_lbl: tk.Label
        self.btn_connect: tk.Label
        self.btn_sdn: tk.Label
        self.btn_auto: tk.Label
        self.src_var: tk.StringVar
        self.dst_var: tk.StringVar
        self.fp_title: tk.Label
        self.fp_canvas: tk.Canvas
        self.fp_inner: tk.Frame
        self.fp_window: int
        self.fp_path: tk.Label

        self._build_ui()
        self._bind_canvas()

    def _build_ui(self) -> None:
        hdr = tk.Frame(self.root, bg=HEADER_BG, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr,
            text="◈  SDN Network Visualizer  —  Dijkstra Algorithm Demo",
            bg=HEADER_BG,
            fg=ACCENT,
            font=("Consolas", 13, "bold"),
        ).pack(side="left", padx=16, pady=14)
        self.status_lbl = tk.Label(
            hdr,
            text="Drag a Router onto the canvas to begin",
            bg=HEADER_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 9),
        )
        self.status_lbl.pack(side="right", padx=16)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        sb_outer = tk.Frame(body, bg=SIDEBAR_BG, width=235)
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
        self.sb_canvas.pack(side="left", fill="both", expand=True)
        sb_vsb.pack(side="right", fill="y")
        self.sb_canvas.bind("<MouseWheel>", self._on_sidebar_mousewheel)
        self._build_sidebar()

        cf = tk.Frame(body, bg=CANVAS_BG)
        cf.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(cf, bg=CANVAS_BG, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.simulator = PacketSimulationHandler(self.canvas)

        rp = tk.Frame(body, bg=PANEL_BG, width=290)
        rp.pack(side="right", fill="y")
        rp.pack_propagate(False)
        self._build_right_panel(rp)

    def _build_sidebar(self) -> None:
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
            press_cb=lambda e: self._ghost_start(e, "router"),
            motion_cb=self._ghost_move,
            release_cb=self._ghost_drop,
        )
        self._sb_item(
            draw=self._draw_mini_sdn,
            label="SDN Ctrl",
            press_cb=lambda e: self._ghost_start(e, "sdn"),
            motion_cb=self._ghost_move,
            release_cb=self._ghost_drop,
        )

        tk.Frame(self.sb, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=12)
        section("TOOLS")

        self.btn_connect = self._tool_btn("⟷  Connect Routers", self._toggle_connect_mode)
        self.btn_sdn = self._tool_btn("⬡  SDN Link Mode", self._toggle_sdn_mode)
        self.btn_auto = self._tool_btn("☐  Auto Dijkstra: OFF", self._toggle_auto_dijkstra)
        self._tool_btn("▶  Run Dijkstra", self._run_dijkstra)
        self._tool_btn("⭳  Load Topology", self._load_topology)
        self._tool_btn("⭱  Save Topology", self._save_topology)

        tk.Frame(self.sb, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=12)
        section("PACKET SIM")
        self.src_var = tk.StringVar(value="A")
        self.dst_var = tk.StringVar(value="B")

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

        self._tool_btn("✉  Start Packet", self._start_packet_sim)
        self._tool_btn("↺  Reset Counter", self._reset_names)
        self._tool_btn("🗑  Clear Canvas", self._clear_all)

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
            # Recolor the whole tile area so hover state has no visual gaps.
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
        c.create_oval(6, 6, 38, 38, fill=ROUTER_FILL, outline=ROUTER_OUT, width=2)
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

    def _build_right_panel(self, rp: tk.Frame) -> None:
        tk.Label(
            rp,
            text="FLOW TABLE",
            bg=PANEL_BG,
            fg=SUBTLE_TEXT,
            font=("Consolas", 8, "bold"),
        ).pack(pady=(14, 2), padx=14, anchor="w")
        self.fp_title = tk.Label(
            rp,
            text="— select a router —",
            bg=PANEL_BG,
            fg=ACCENT,
            font=("Consolas", 12, "bold"),
        )
        self.fp_title.pack(padx=14, anchor="w")

        tk.Frame(rp, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=8)

        hdr = tk.Frame(rp, bg=DIVIDER)
        hdr.pack(fill="x", padx=14, pady=(0, 4))
        for txt, w in self.FLOW_COLS:
            tk.Label(
                hdr,
                text=txt,
                bg=DIVIDER,
                fg=ACCENT,
                font=("Consolas", 8, "bold"),
                width=w,
                anchor="center",
                padx=2,
            ).pack(side="left")

        outer = tk.Frame(rp, bg=PANEL_BG)
        outer.pack(fill="both", expand=True, padx=14)

        self.fp_canvas = tk.Canvas(outer, bg=PANEL_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self.fp_canvas.yview)
        self.fp_inner = tk.Frame(self.fp_canvas, bg=PANEL_BG)
        self.fp_inner.bind(
            "<Configure>",
            lambda e: self.fp_canvas.configure(scrollregion=self.fp_canvas.bbox("all")),
        )
        self.fp_window = self.fp_canvas.create_window((0, 0), window=self.fp_inner, anchor="nw")
        self.fp_canvas.bind(
            "<Configure>",
            lambda e: self.fp_canvas.itemconfigure(self.fp_window, width=e.width),
        )
        self.fp_canvas.configure(yscrollcommand=vsb.set)
        self.fp_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.fp_canvas.bind(
            "<MouseWheel>",
            self._on_flow_mousewheel,
        )
        self.fp_inner.bind("<MouseWheel>", self._on_flow_mousewheel)

        tk.Frame(rp, bg=DIVIDER, height=1).pack(fill="x", padx=14, pady=6)
        self.fp_path = tk.Label(
            rp,
            text="",
            bg=PANEL_BG,
            fg=MUTED_TEXT,
            font=("Consolas", 8),
            wraplength=258,
            justify="left",
        )
        self.fp_path.bind("<MouseWheel>", self._on_flow_mousewheel)
        self.fp_path.pack(padx=14, pady=(0, 10), anchor="w")

    def _on_flow_mousewheel(self, event: tk.Event[tk.Widget]) -> None:
        self.fp_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_sidebar_mousewheel(self, event: tk.Event[tk.Widget]) -> None:
        self.sb_canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _draw_canvas_hint(self) -> None:
        lines = [
            "Drag  →  Router / SDN Ctrl from sidebar",
            "Connect mode  →  click router A, then router B",
            "SDN Link mode  →  click a router to connect to SDN Ctrl",
            "Click any router  →  view its flow table",
            "Right-click any node  →  context menu",
        ]
        y = 120
        for ln in lines:
            self.canvas.create_text(
                20,
                y,
                text=f"•  {ln}",
                fill="#45475a",
                font=("Consolas", 10),
                anchor="w",
                tags=("hint",),
            )
            y += 24

    def _clear_hints(self) -> None:
        self.canvas.delete("hint")

    def _ghost_start(self, event: tk.Event[tk.Widget], kind: str) -> None:
        self.placing_type = kind
        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        x = event.x_root - cx
        y = event.y_root - cy
        if kind == "router":
            r = ROUTER_R
            self.ghost_id = self.canvas.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=ROUTER_FILL,
                outline=ROUTER_OUT,
                width=2,
                stipple="gray50",
                tags=("ghost",),
            )
        else:
            pts = self._hex_pts(x, y, SDN_R)
            self.ghost_id = self.canvas.create_polygon(
                pts,
                fill=SDN_FILL,
                outline=SDN_OUT,
                width=2,
                stipple="gray50",
                tags=("ghost",),
            )

    def _ghost_move(self, event: tk.Event[tk.Widget]) -> None:
        if self.ghost_id is None:
            return
        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        x = event.x_root - cx
        y = event.y_root - cy
        bb = self.canvas.bbox(self.ghost_id)
        if bb:
            dx = x - (bb[0] + bb[2]) / 2
            dy = y - (bb[1] + bb[3]) / 2
            self.canvas.move(self.ghost_id, dx, dy)

    def _ghost_drop(self, event: tk.Event[tk.Widget]) -> None:
        if self.ghost_id:
            self.canvas.delete(self.ghost_id)
            self.ghost_id = None

        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = event.x_root - cx
        y = event.y_root - cy

        if 0 <= x <= cw and 0 <= y <= ch:
            if self.placing_type == "router":
                self._place_router(x, y)
            elif self.placing_type == "sdn":
                self._place_sdn(x, y)
        self.placing_type = None

    def _bind_canvas(self) -> None:
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_rclick)
        self.canvas.bind("<MouseWheel>", self._on_canvas_zoom)

    def _on_canvas_zoom(self, event: tk.Event[tk.Widget]) -> None:
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        if self.weight_editor is not None:
            self._close_weight_editor(commit=True)
        self.canvas.scale("all", event.x, event.y, factor, factor)
        cx, cy = float(event.x), float(event.y)
        for r in self.routers:
            r.x = cx + (r.x - cx) * factor
            r.y = cy + (r.y - cy) * factor
        if self.sdn_node is not None:
            self.sdn_node.x = cx + (self.sdn_node.x - cx) * factor
            self.sdn_node.y = cy + (self.sdn_node.y - cy) * factor

    def _link_at(self, x: float, y: float) -> LinkEdge | None:
        items = self.canvas.find_overlapping(x - 4, y - 4, x + 4, y + 4)
        for item in items:
            for lnk in self.links:
                if lnk.has_item(item):
                    return lnk
        return None

    def _open_weight_editor(self, lnk: LinkEdge) -> None:
        self._close_weight_editor(commit=False)
        self.editing_link = lnk
        ex, ey = lnk.label_center()
        entry = tk.Entry(
            self.canvas,
            width=4,
            justify="center",
            font=("Consolas", 9, "bold"),
        )
        entry.insert(0, str(lnk.weight))
        entry.select_range(0, tk.END)
        self.weight_editor = entry
        self.weight_editor_window = self.canvas.create_window(ex, ey, window=entry)

        entry.bind("<Return>", lambda e: self._close_weight_editor(commit=True))
        entry.bind("<Escape>", lambda e: self._close_weight_editor(commit=False))
        entry.bind("<FocusOut>", lambda e: self._close_weight_editor(commit=True))
        entry.focus_set()

    def _close_weight_editor(self, commit: bool) -> None:
        if self.weight_editor is None:
            self.editing_link = None
            self.weight_editor_window = None
            return

        new_weight: int | None = None
        if commit:
            raw = self.weight_editor.get().strip()
            if raw.isdigit() and int(raw) >= 1:
                new_weight = int(raw)

        if (
            commit
            and new_weight is not None
            and self.editing_link is not None
            and new_weight != self.editing_link.weight
        ):
            self.editing_link.set_weight(new_weight)
            self.status(
                f"Updated link {self.editing_link.n1.name} ↔ {self.editing_link.n2.name} to cost {new_weight}"
            )
            self._silent_dijkstra()

        if self.weight_editor_window is not None:
            self.canvas.delete(self.weight_editor_window)
        self.weight_editor.destroy()
        self.weight_editor = None
        self.weight_editor_window = None
        self.editing_link = None

    def _router_by_name(self, name: str) -> RouterNode | None:
        for r in self.routers:
            if r.name == name:
                return r
        return None

    def _flow_entry(self, src: str, dst: str) -> dict[str, Any] | None:
        for entry in self.flow_tables.get(src, []):
            if entry.get("dst") == dst:
                return cast(dict[str, Any], entry)
        return None

    def _start_packet_sim(self) -> None:
        if self.simulator is None:
            return
        if self.weight_editor is not None:
            self._close_weight_editor(commit=True)

        src = self.src_var.get().strip().upper()
        dst = self.dst_var.get().strip().upper()

        if not src or not dst:
            self.status("Enter source and destination router names")
            return
        if src == dst:
            self.status("Source and destination must be different")
            return

        src_router = self._router_by_name(src)
        dst_router = self._router_by_name(dst)
        if src_router is None or dst_router is None:
            self.status("Invalid SRC/DST router name")
            return

        self._compute_flows()
        flow_entry = self._flow_entry(src, dst)

        if flow_entry is None:
            drop_pt = PacketSimulationHandler.halfway_point(
                (src_router.x, src_router.y), (dst_router.x, dst_router.y)
            )
            self.status(f"Packet dropped: no flow entry from {src} to {dst}")
            self.simulator.animate(
                [(src_router.x, src_router.y), drop_pt],
                dropped=True,
                on_complete=lambda: self.status(f"Packet dropped before reaching {dst}"),
            )
            return

        path_text = str(flow_entry.get("path", "unreachable"))
        if path_text == "unreachable":
            drop_pt = PacketSimulationHandler.halfway_point(
                (src_router.x, src_router.y), (dst_router.x, dst_router.y)
            )
            self.status(f"Packet dropped: destination {dst} unreachable")
            self.simulator.animate(
                [(src_router.x, src_router.y), drop_pt],
                dropped=True,
                on_complete=lambda: self.status(f"Packet dropped before reaching {dst}"),
            )
            return

        path_nodes = [name.strip() for name in path_text.split("→")]
        points: list[tuple[float, float]] = []
        for name in path_nodes:
            rtr = self._router_by_name(name)
            if rtr is None:
                self.status("Packet dropped: path has missing router")
                return
            points.append((rtr.x, rtr.y))

        self.status(f"Packet started: {src} -> {dst}")
        self.simulator.animate(
            points,
            dropped=False,
            on_complete=lambda: self.status(f"Packet delivered to {dst}"),
        )

    def _node_at(self, x: float, y: float) -> RouterNode | SDNNode | None:
        items = self.canvas.find_overlapping(x - 3, y - 3, x + 3, y + 3)
        for item in items:
            tags = self.canvas.gettags(item)
            if "sdn_node" in tags and self.sdn_node:
                return self.sdn_node
            for r in self.routers:
                if f"R_{r.name}" in tags:
                    return r
        return None

    def _on_click(self, event: tk.Event[tk.Widget]) -> None:
        x, y = event.x, event.y

        if self.weight_editor is not None:
            self._close_weight_editor(commit=True)

        if self.mode == "idle":
            clicked_link = self._link_at(x, y)
            if clicked_link is not None:
                self._open_weight_editor(clicked_link)
                return

        node = self._node_at(x, y)

        if self.mode == "idle":
            if isinstance(node, RouterNode):
                self._show_flow(node)
                self.drag_node = node
                self.mode = "moving"
            elif isinstance(node, SDNNode):
                self.drag_node = node
                self.mode = "moving"
            else:
                self._deselect()
                self.mode = "panning"
                self.pan_anchor = (float(event.x), float(event.y))

        elif self.mode == "connecting":
            if isinstance(node, RouterNode):
                if self.selected_node is None:
                    self.selected_node = node
                    node.set_selected(True)
                    self.status(f"Router {node.name} selected — click another router")
                elif self.selected_node is node:
                    self._deselect()
                    self.mode = "connecting"
                else:
                    self._create_link(self.selected_node, node)
                    self._deselect()
                    self.mode = "connecting"

        elif self.mode == "sdn_link":
            if isinstance(node, RouterNode):
                self._connect_sdn(node)

    def _on_drag(self, event: tk.Event[tk.Widget]) -> None:
        if self.weight_editor is not None:
            self._close_weight_editor(commit=True)
        if self.mode == "moving" and self.drag_node:
            self.drag_node.move_to(event.x, event.y)
            for lnk in self.links:
                if lnk.n1 is self.drag_node or lnk.n2 is self.drag_node:
                    lnk.refresh()
        elif self.mode == "panning" and self.pan_anchor is not None:
            dx = float(event.x) - self.pan_anchor[0]
            dy = float(event.y) - self.pan_anchor[1]
            if dx != 0 or dy != 0:
                self.canvas.move("all", dx, dy)
                for r in self.routers:
                    r.x += dx
                    r.y += dy
                if self.sdn_node is not None:
                    self.sdn_node.x += dx
                    self.sdn_node.y += dy
                self.pan_anchor = (float(event.x), float(event.y))

    def _on_release(self, event: tk.Event[tk.Widget]) -> None:
        _ = event
        if self.mode == "moving":
            self.drag_node = None
            self.mode = "idle"
        elif self.mode == "panning":
            self.pan_anchor = None
            self.mode = "idle"

    def _on_rclick(self, event: tk.Event[tk.Widget]) -> None:
        node = self._node_at(event.x, event.y)
        if isinstance(node, RouterNode):
            self._router_menu(event, node)
        elif isinstance(node, SDNNode):
            self._sdn_menu(event)

    def _make_menu(self) -> tk.Menu:
        return tk.Menu(
            self.root,
            tearoff=0,
            bg=HEADER_BG,
            fg=TEXT_COLOR,
            activebackground=BTN_HOVER,
            activeforeground=TEXT_COLOR,
            font=("Consolas", 9),
        )

    def _router_menu(self, event: tk.Event[tk.Widget], r: RouterNode) -> None:
        m = self._make_menu()
        m.add_command(label=f"  Router {r.name}", state="disabled", font=("Consolas", 9, "bold"))
        m.add_separator()
        if self.sdn_node:
            if not r.connected_to_sdn:
                m.add_command(
                    label="  Connect to SDN Controller", command=lambda: self._connect_sdn(r)
                )
            else:
                m.add_command(label="  Disconnect from SDN", command=lambda: self._disconnect_sdn(r))
        m.add_command(label="  Show Flow Table", command=lambda: self._show_flow(r))
        m.add_separator()
        m.add_command(label="  Delete Router", command=lambda: self._del_router(r))
        m.tk_popup(event.x_root, event.y_root)

    def _sdn_menu(self, event: tk.Event[tk.Widget]) -> None:
        m = self._make_menu()
        m.add_command(label="  SDN Controller", state="disabled", font=("Consolas", 9, "bold"))
        m.add_separator()
        m.add_command(label="  Run Dijkstra", command=self._run_dijkstra)
        m.add_separator()
        m.add_command(label="  Delete SDN Controller", command=self._del_sdn)
        m.tk_popup(event.x_root, event.y_root)

    def _place_router(self, x: float, y: float) -> None:
        self._clear_hints()
        r = RouterNode(self.canvas, x, y)
        self.routers.append(r)
        self.status(f"Router {r.name} added  —  right-click to connect to SDN")
        self._silent_dijkstra()

    def _place_sdn(self, x: float, y: float) -> None:
        if self.sdn_node:
            messagebox.showinfo("SDN Controller", "Only one SDN Controller is allowed on the canvas.")
            return
        self._clear_hints()
        self.sdn_node = SDNNode(self.canvas, x, y)
        self.status("SDN Controller placed  —  use 'SDN Link' mode to connect routers")

    def _create_link(self, n1: RouterNode, n2: RouterNode) -> None:
        for lnk in self.links:
            if {lnk.n1, lnk.n2} == {n1, n2}:
                messagebox.showinfo(
                    "Already Connected", f"Routers {n1.name} and {n2.name} are already linked."
                )
                return
        w = 1
        lnk = LinkEdge(self.canvas, n1, n2, w)
        self.links.append(lnk)
        self.status(f"Link {n1.name} ↔ {n2.name}  (weight {w})")
        self._silent_dijkstra()

    def _connect_sdn(self, r: RouterNode) -> None:
        if not self.sdn_node:
            messagebox.showwarning(
                "No SDN Controller", "Place an SDN Controller on the canvas first."
            )
            return
        r.set_sdn(True)
        self.status(f"Router {r.name} → SDN Controller  (color changed to green)")
        self._silent_dijkstra()
        if self.info_router is r:
            self._show_flow(r)

    def _disconnect_sdn(self, r: RouterNode) -> None:
        r.set_sdn(False)
        self.status(f"Router {r.name} disconnected from SDN")
        self._silent_dijkstra()
        if self.info_router is r:
            self._show_flow(r)

    def _del_router(self, r: RouterNode) -> None:
        if self.simulator is not None:
            self.simulator.cancel()
        for lnk in [l for l in self.links if l.n1 is r or l.n2 is r]:
            lnk.delete()
            self.links.remove(lnk)
        for cid in r.ids():
            self.canvas.delete(cid)
        self.routers.remove(r)
        if self.info_router is r:
            self.info_router = None
            self._clear_flow()
        self.status(f"Router {r.name} deleted")
        self._silent_dijkstra()

    def _del_sdn(self) -> None:
        if not self.sdn_node:
            return
        if self.simulator is not None:
            self.simulator.cancel()
        for cid in self.sdn_node.ids():
            self.canvas.delete(cid)
        self.sdn_node = None
        for r in self.routers:
            r.set_sdn(False)
        self.flow_tables = {}
        self._clear_flow()
        self.status("SDN Controller removed — all router connections cleared")

    def _toggle_connect_mode(self) -> None:
        if self.mode == "connecting":
            self._deselect()
            self.btn_connect.configure(fg=TEXT_COLOR)
            self.status("")
        else:
            self.mode = "connecting"
            self.selected_node = None
            self.btn_connect.configure(fg=SELECT_CLR)
            self.btn_sdn.configure(fg=TEXT_COLOR)
            self.status("Connect mode  —  click Router A, then Router B")

    def _toggle_sdn_mode(self) -> None:
        if self.mode == "sdn_link":
            self.mode = "idle"
            self.btn_sdn.configure(fg=TEXT_COLOR)
            self.status("")
        else:
            if not self.sdn_node:
                messagebox.showwarning(
                    "No SDN Controller", "Place an SDN Controller on the canvas first."
                )
                return
            self.mode = "sdn_link"
            self.btn_sdn.configure(fg=SELECT_CLR)
            self.btn_connect.configure(fg=TEXT_COLOR)
            self.status("SDN Link mode  —  click a router to connect it to SDN Ctrl")

    def _toggle_auto_dijkstra(self) -> None:
        self.auto_dijkstra = not self.auto_dijkstra
        if self.auto_dijkstra:
            self.btn_auto.configure(text="☑  Auto Dijkstra: ON", fg=ACCENT)
            self.status("Auto Dijkstra enabled")
            self._silent_dijkstra()
        else:
            self.btn_auto.configure(text="☐  Auto Dijkstra: OFF", fg=TEXT_COLOR)
            self.status("Auto Dijkstra disabled")

    def _serialize_topology(self) -> dict[str, Any]:
        routers = [
            {
                "name": r.name,
                "x": round(r.x, 2),
                "y": round(r.y, 2),
                "connected_to_sdn": bool(r.connected_to_sdn),
            }
            for r in self.routers
        ]
        routers.sort(key=lambda item: str(item["name"]))
        links = [
            {"n1": l.n1.name, "n2": l.n2.name, "weight": int(l.weight)}
            for l in self.links
        ]
        links.sort(key=lambda item: (str(item["n1"]), str(item["n2"])))

        sdn: dict[str, float] | None = None
        if self.sdn_node is not None:
            sdn = {"x": round(self.sdn_node.x, 2), "y": round(self.sdn_node.y, 2)}

        return {"sdn": sdn, "routers": routers, "links": links}

    def _apply_topology(self, topo: dict[str, Any]) -> None:
        self._clear_all(confirm=False)

        sdn_data = topo.get("sdn")
        if isinstance(sdn_data, dict):
            sx = float(sdn_data.get("x", 500.0))
            sy = float(sdn_data.get("y", 100.0))
            self.sdn_node = SDNNode(self.canvas, sx, sy)

        RouterNode.reset()
        router_map: dict[str, RouterNode] = {}
        for item in topo.get("routers", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().upper()
            if not name:
                continue
            rx = float(item.get("x", 0.0))
            ry = float(item.get("y", 0.0))
            r = RouterNode(self.canvas, rx, ry)
            if r.name != name:
                old_name = r.name
                r.name = name
                if r._tid is not None:
                    self.canvas.itemconfig(r._tid, text=name)
                for cid in r.ids():
                    tags = list(self.canvas.gettags(cid))
                    tags = [f"R_{name}" if t == f"R_{old_name}" else t for t in tags]
                    self.canvas.itemconfig(cid, tags=tuple(tags))
            self.routers.append(r)
            router_map[name] = r

        for item in topo.get("routers", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().upper()
            if name in router_map:
                connect = bool(item.get("connected_to_sdn", False))
                router_map[name].set_sdn(connect and self.sdn_node is not None)

        for item in topo.get("links", []):
            if not isinstance(item, dict):
                continue
            n1 = str(item.get("n1", "")).strip().upper()
            n2 = str(item.get("n2", "")).strip().upper()
            if n1 not in router_map or n2 not in router_map or n1 == n2:
                continue
            weight = int(item.get("weight", 1)) if str(item.get("weight", "1")).isdigit() else 1
            self.links.append(LinkEdge(self.canvas, router_map[n1], router_map[n2], max(1, weight)))

        self.flow_tables = {}
        self._compute_flows()
        self.status(f"Topology loaded: {len(self.routers)} routers, {len(self.links)} links")

    def _load_topology(self) -> None:
        initial_dir = os.path.dirname(__file__)
        path = filedialog.askopenfilename(
            title="Load Topology JSON",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                topo = json.load(f)
            if not isinstance(topo, dict):
                raise ValueError("Invalid topology format")
            self._apply_topology(topo)
        except Exception as exc:
            messagebox.showerror("Load Topology Failed", str(exc))

    def _save_topology(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Topology JSON",
            defaultextension=".json",
            initialfile="saved_topology.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            topo = self._serialize_topology()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(topo, f, indent=2)
            self.status(f"Topology saved: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Save Topology Failed", str(exc))

    def _deselect(self) -> None:
        if isinstance(self.selected_node, RouterNode):
            self.selected_node.set_selected(False)
        self.selected_node = None
        self.mode = "idle"
        self.btn_connect.configure(fg=TEXT_COLOR)
        self.btn_sdn.configure(fg=TEXT_COLOR)

    def _run_dijkstra(self) -> None:
        if not self.routers:
            messagebox.showinfo("Empty Network", "Add some routers to the canvas first.")
            return
        conn = [r for r in self.routers if r.connected_to_sdn]
        if not conn:
            messagebox.showwarning(
                "No SDN Connections",
                "No routers are connected to the SDN Controller.\n"
                "Right-click a router → 'Connect to SDN Controller'",
            )
            return
        self._compute_flows()
        messagebox.showinfo(
            "Dijkstra Complete ✓",
            f"Flow tables computed for {len(self.flow_tables)} SDN-managed router(s).\n\n"
            "Click any green router to view its routing table.",
        )

    def _silent_dijkstra(self) -> None:
        if not self.auto_dijkstra:
            return
        conn = [r for r in self.routers if r.connected_to_sdn]
        if conn:
            self._compute_flows()

    def _compute_flows(self) -> None:
        conn = [r for r in self.routers if r.connected_to_sdn]
        links = [
            (l.n1.name, l.n2.name, l.weight)
            for l in self.links
            if l.n1.connected_to_sdn and l.n2.connected_to_sdn
        ]
        self.logic.rebuild([r.name for r in conn], links)
        self.flow_tables = self.logic.compute()
        if self.info_router:
            self._show_flow(self.info_router)

    def _show_flow(self, r: RouterNode) -> None:
        self.info_router = r
        self.fp_title.configure(text=f"Router  {r.name}")
        self.fp_path.configure(text="")
        for w in self.fp_inner.winfo_children():
            w.destroy()

        if not r.connected_to_sdn:
            msg1 = tk.Label(
                self.fp_inner,
                text="Not connected to SDN Controller.",
                bg=PANEL_BG,
                fg=MUTED_TEXT,
                font=("Consolas", 9),
                padx=6,
                pady=6,
            )
            msg1.bind("<MouseWheel>", self._on_flow_mousewheel)
            msg1.pack(anchor="w")
            msg2 = tk.Label(
                self.fp_inner,
                text="Right-click router →\n'Connect to SDN Controller'",
                bg=PANEL_BG,
                fg=SUBTLE_TEXT,
                font=("Consolas", 8),
                padx=6,
            )
            msg2.bind("<MouseWheel>", self._on_flow_mousewheel)
            msg2.pack(anchor="w")
            return

        entries = self.flow_tables.get(r.name, [])
        if not entries:
            msg = tk.Label(
                self.fp_inner,
                text="No other SDN-managed routers.\nAdd more routers and links.",
                bg=PANEL_BG,
                fg=MUTED_TEXT,
                font=("Consolas", 9),
                padx=6,
                pady=6,
            )
            msg.bind("<MouseWheel>", self._on_flow_mousewheel)
            msg.pack(anchor="w")
            return

        for i, e in enumerate(entries):
            row_bg = FLOW_ROW_A if i % 2 == 0 else FLOW_ROW_B
            row = tk.Frame(self.fp_inner, bg=row_bg, cursor="hand2")
            row.pack(fill="x", pady=1)

            tk.Label(
                row,
                text=e["dst"],
                bg=row_bg,
                fg=ROUTER_FILL,
                font=("Consolas", 11, "bold"),
                width=self.FLOW_COLS[0][1],
                anchor="center",
                padx=4,
                pady=5,
            ).pack(side="left")
            tk.Label(
                row,
                text="→",
                bg=row_bg,
                fg=SUBTLE_TEXT,
                font=("Consolas", 9),
                width=self.FLOW_COLS[1][1],
                anchor="center",
            ).pack(side="left")
            nh_color = ROUTER_CONN if e["next_hop"] != "—" else UNREACHABLE
            tk.Label(
                row,
                text=str(e["next_hop"]),
                bg=row_bg,
                fg=nh_color,
                font=("Consolas", 10),
                width=self.FLOW_COLS[2][1],
                anchor="center",
            ).pack(side="left")
            tk.Label(
                row,
                text=str(e["cost"]),
                bg=row_bg,
                fg=SDN_FILL,
                font=("Consolas", 9, "bold"),
                width=self.FLOW_COLS[3][1],
                anchor="center",
                padx=2,
            ).pack(side="left")

            path = e["path"]

            def _hover_on(ev: tk.Event[tk.Widget], f: tk.Frame = row) -> None:
                _ = ev
                for w in f.winfo_children():
                    cast(Any, w).configure(bg=BTN_HOVER)
                cast(Any, f).configure(bg=BTN_HOVER)

            def _hover_off(
                ev: tk.Event[tk.Widget], f: tk.Frame = row, bg: str = row_bg
            ) -> None:
                _ = ev
                for w in f.winfo_children():
                    cast(Any, w).configure(bg=bg)
                cast(Any, f).configure(bg=bg)

            def _click(ev: tk.Event[tk.Widget], p: str = path) -> None:
                _ = ev
                self.fp_path.configure(text=f"Full path:\n{p}")

            for w in [cast(tk.Misc, row)] + [cast(tk.Misc, c) for c in row.winfo_children()]:
                cast(Any, w).bind("<Enter>", _hover_on)
                cast(Any, w).bind("<Leave>", _hover_off)
                cast(Any, w).bind("<Button-1>", _click)
                cast(Any, w).bind("<MouseWheel>", self._on_flow_mousewheel)

    def _clear_flow(self) -> None:
        self.fp_title.configure(text="— select a router —")
        for w in self.fp_inner.winfo_children():
            w.destroy()
        self.fp_path.configure(text="")

    def _reset_names(self) -> None:
        RouterNode.reset()
        for r in self.routers:
            RouterNode._counter += 1
            new_name = chr(64 + RouterNode._counter)
            r.name = new_name
            if r._tid is not None:
                self.canvas.itemconfig(r._tid, text=new_name)
        self.flow_tables = {}
        self._silent_dijkstra()
        self.status("Router names reset")

    def _clear_all(self, confirm: bool = True) -> None:
        if confirm and (not messagebox.askyesno("Clear Canvas", "Remove all nodes and links?")):
            return
        if self.simulator is not None:
            self.simulator.cancel()
        self.canvas.delete("all")
        self.routers.clear()
        self.links.clear()
        self.sdn_node = None
        self.flow_tables = {}
        self.info_router = None
        self.selected_node = None
        self.drag_node = None
        self.mode = "idle"
        RouterNode.reset()
        self._clear_flow()
        self.status("Canvas cleared")

    def status(self, msg: str) -> None:
        self.status_lbl.configure(text=msg)

    @staticmethod
    def _hex_pts(x: float, y: float, r: float) -> list[float]:
        pts: list[float] = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts += [x + r * math.cos(a), y + r * math.sin(a)]
        return pts
