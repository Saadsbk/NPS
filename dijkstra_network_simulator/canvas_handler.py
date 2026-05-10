"""Canvas interaction handler for the SDN Network Visualizer."""

import math
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable

from .models import LinkEdge, RouterNode, SDNNode
from .simulation_handler import PacketSimulationHandler
from .theme import (
    BTN_HOVER,
    CANVAS_BG,
    HEADER_BG,
    ROUTER_FILL,
    ROUTER_OUT,
    ROUTER_R,
    SDN_FILL,
    SDN_OUT,
    SDN_R,
    SELECT_CLR,
    TEXT_COLOR,
)


class CanvasHandler:
    """Manages the main canvas: drawing, dragging, panning, zooming, context menus."""

    def __init__(
        self,
        parent: tk.Frame,
        root: tk.Tk,
        *,
        get_routers: Callable[[], list[RouterNode]],
        get_sdn_node: Callable[[], SDNNode | None],
        get_links: Callable[[], list[LinkEdge]],
        get_mode: Callable[[], str],
        set_mode: Callable[[str], None],
        get_selected_node: Callable[[], RouterNode | None],
        set_selected_node: Callable[[RouterNode | None], None],
        on_place_router: Callable[[float, float], None],
        on_place_sdn: Callable[[float, float], None],
        on_create_link: Callable[[RouterNode, RouterNode], None],
        on_connect_sdn: Callable[[RouterNode], None],
        on_disconnect_sdn: Callable[[RouterNode], None],
        on_show_flow: Callable[[RouterNode], None],
        on_del_router: Callable[[RouterNode], None],
        on_del_sdn: Callable[[], None],
        on_run_dijkstra: Callable[[], None],
        on_close_weight_editor: Callable[[bool], None],
        on_open_weight_editor: Callable[[LinkEdge], None],
        on_deselect: Callable[[], None],
        on_silent_dijkstra: Callable[[], None],
        status: Callable[[str], None],
        get_simulator: Callable[[], PacketSimulationHandler | None],
        get_weight_editor: Callable[[], tk.Entry | None],
    ) -> None:
        self.root = root
        self._get_routers = get_routers
        self._get_sdn_node = get_sdn_node
        self._get_links = get_links
        self._get_mode = get_mode
        self._set_mode = set_mode
        self._get_selected_node = get_selected_node
        self._set_selected_node = set_selected_node
        self._on_place_router = on_place_router
        self._on_place_sdn = on_place_sdn
        self._on_create_link = on_create_link
        self._on_connect_sdn = on_connect_sdn
        self._on_disconnect_sdn = on_disconnect_sdn
        self._on_show_flow = on_show_flow
        self._on_del_router = on_del_router
        self._on_del_sdn = on_del_sdn
        self._on_run_dijkstra = on_run_dijkstra
        self._on_close_weight_editor = on_close_weight_editor
        self._on_open_weight_editor = on_open_weight_editor
        self._on_deselect = on_deselect
        self._on_silent_dijkstra = on_silent_dijkstra
        self._status = status
        self._get_simulator = get_simulator
        self._get_weight_editor = get_weight_editor

        self.drag_node: RouterNode | SDNNode | None = None
        self.ghost_id: int | None = None
        self.placing_type: str | None = None
        self.pan_anchor: tuple[float, float] | None = None

        cf = tk.Frame(parent, bg=CANVAS_BG)
        cf.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(cf, bg=CANVAS_BG, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self._bind_canvas()

    def _bind_canvas(self) -> None:
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_rclick)
        self.canvas.bind("<MouseWheel>", self._on_canvas_zoom)

    def _on_canvas_zoom(self, event: tk.Event) -> None:
        factor = 1.1 if event.delta > 0 else (1 / 1.1)
        if self._get_weight_editor() is not None:
            self._on_close_weight_editor(True)
        self.canvas.scale("all", event.x, event.y, factor, factor)
        cx, cy = float(event.x), float(event.y)
        for r in self._get_routers():
            r.x = cx + (r.x - cx) * factor
            r.y = cy + (r.y - cy) * factor
        sdn = self._get_sdn_node()
        if sdn is not None:
            sdn.x = cx + (sdn.x - cx) * factor
            sdn.y = cy + (sdn.y - cy) * factor

    def _link_at(self, x: float, y: float) -> LinkEdge | None:
        items = self.canvas.find_overlapping(x - 4, y - 4, x + 4, y + 4)
        for item in items:
            for lnk in self._get_links():
                if lnk.has_item(item):
                    return lnk
        return None

    def _node_at(self, x: float, y: float) -> RouterNode | SDNNode | None:
        items = self.canvas.find_overlapping(x - 3, y - 3, x + 3, y + 3)
        sdn = self._get_sdn_node()
        for item in items:
            tags = self.canvas.gettags(item)
            if "sdn_node" in tags and sdn:
                return sdn
            for r in self._get_routers():
                if f"R_{r.name}" in tags:
                    return r
        return None

    def _on_click(self, event: tk.Event) -> None:
        x, y = event.x, event.y
        mode = self._get_mode()

        if self._get_weight_editor() is not None:
            self._on_close_weight_editor(True)

        node = self._node_at(x, y)

        if mode == "idle":
            if node is None:
                clicked_link = self._link_at(x, y)
                if clicked_link is not None:
                    self._on_open_weight_editor(clicked_link)
                    return

            if isinstance(node, RouterNode):
                self._on_show_flow(node)
                self.drag_node = node
                self._set_mode("moving")
            elif isinstance(node, SDNNode):
                self.drag_node = node
                self._set_mode("moving")
            else:
                self._on_deselect()
                self._set_mode("panning")
                self.pan_anchor = (float(event.x), float(event.y))

        elif mode == "connecting":
            if isinstance(node, RouterNode):
                selected = self._get_selected_node()
                if selected is None:
                    self._set_selected_node(node)
                    node.set_selected(True)
                    self._status(f"Router {node.name} selected — click another router")
                elif selected is node:
                    self._on_deselect()
                    self._set_mode("connecting")
                else:
                    self._on_create_link(selected, node)
                    self._on_deselect()
                    self._set_mode("connecting")

        elif mode == "sdn_link":
            if isinstance(node, RouterNode):
                self._on_connect_sdn(node)

    def _on_drag(self, event: tk.Event) -> None:
        if self._get_weight_editor() is not None:
            self._on_close_weight_editor(True)
        mode = self._get_mode()
        if mode == "moving" and self.drag_node:
            self.drag_node.move_to(event.x, event.y)
            for lnk in self._get_links():
                if lnk.n1 is self.drag_node or lnk.n2 is self.drag_node:
                    lnk.refresh()
        elif mode == "panning" and self.pan_anchor is not None:
            dx = float(event.x) - self.pan_anchor[0]
            dy = float(event.y) - self.pan_anchor[1]
            if dx != 0 or dy != 0:
                self.canvas.move("all", dx, dy)
                for r in self._get_routers():
                    r.x += dx
                    r.y += dy
                sdn = self._get_sdn_node()
                if sdn is not None:
                    sdn.x += dx
                    sdn.y += dy
                self.pan_anchor = (float(event.x), float(event.y))

    def _on_release(self, event: tk.Event) -> None:
        _ = event
        mode = self._get_mode()
        if mode == "moving":
            self.drag_node = None
            self._set_mode("idle")
        elif mode == "panning":
            self.pan_anchor = None
            self._set_mode("idle")

    def _on_rclick(self, event: tk.Event) -> None:
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

    def _router_menu(self, event: tk.Event, r: RouterNode) -> None:
        m = self._make_menu()
        m.add_command(label=f"  Router {r.name}", state="disabled", font=("Consolas", 9, "bold"))
        m.add_separator()
        sdn = self._get_sdn_node()
        if sdn:
            if not r.connected_to_sdn:
                m.add_command(
                    label="  Connect to SDN Controller", command=lambda: self._on_connect_sdn(r)
                )
            else:
                m.add_command(
                    label="  Disconnect from SDN", command=lambda: self._on_disconnect_sdn(r)
                )
        m.add_command(label="  Show Flow Table", command=lambda: self._on_show_flow(r))
        m.add_separator()
        m.add_command(label="  Delete Router", command=lambda: self._on_del_router(r))
        m.tk_popup(event.x_root, event.y_root)

    def _sdn_menu(self, event: tk.Event) -> None:
        m = self._make_menu()
        m.add_command(label="  SDN Controller", state="disabled", font=("Consolas", 9, "bold"))
        m.add_separator()
        m.add_command(label="  Run Dijkstra", command=self._on_run_dijkstra)
        m.add_separator()
        m.add_command(label="  Delete SDN Controller", command=self._on_del_sdn)
        m.tk_popup(event.x_root, event.y_root)

    # ── Ghost (drag-to-place) ──

    def ghost_start(self, event: tk.Event, kind: str) -> None:
        self.placing_type = kind
        cx = self.canvas.winfo_rootx()
        cy = self.canvas.winfo_rooty()
        x = event.x_root - cx
        y = event.y_root - cy
        if kind == "router":
            r = ROUTER_R
            self.ghost_id = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=ROUTER_FILL, outline=ROUTER_OUT, width=2,
                stipple="gray50", tags=("ghost",),
            )
        else:
            pts = self._hex_pts(x, y, SDN_R)
            self.ghost_id = self.canvas.create_polygon(
                pts, fill=SDN_FILL, outline=SDN_OUT, width=2,
                stipple="gray50", tags=("ghost",),
            )

    def ghost_move(self, event: tk.Event) -> None:
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

    def ghost_drop(self, event: tk.Event) -> None:
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
                self._on_place_router(x, y)
            elif self.placing_type == "sdn":
                self._on_place_sdn(x, y)
        self.placing_type = None

    def draw_hints(self) -> None:
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
                20, y,
                text=f"•  {ln}",
                fill="#45475a",
                font=("Consolas", 10),
                anchor="w",
                tags=("hint",),
            )
            y += 24

    def clear_hints(self) -> None:
        self.canvas.delete("hint")

    @staticmethod
    def _hex_pts(x: float, y: float, r: float) -> list[float]:
        pts: list[float] = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts += [x + r * math.cos(a), y + r * math.sin(a)]
        return pts
