"""Main App class – thin orchestrator that wires together all UI components."""

import tkinter as tk
from tkinter import messagebox
from typing import Any, cast

from .canvas_handler import CanvasHandler
from .logic import FlowTables, SDNLogic
from .models import LinkEdge, RouterNode, SDNNode
from .simulation_handler import PacketSimulationHandler
from .topology_manager import TopologyManager
from .ui_header import HeaderBar
from .ui_right_panel import RightPanel
from .ui_sidebar import Sidebar

from .theme import (
    ACCENT,
    BG,
    PANEL_BG,
    SELECT_CLR,
    TEXT_COLOR,
)


class App:
    """Application root – constructs UI components and connects them."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SDN Network Visualizer — Dijkstra's Algorithm Demo")
        self.root.configure(bg=BG)
        self.root.geometry("1280x760")
        self.root.minsize(960, 600)

        # ── State ──
        self.routers: list[RouterNode] = []
        self.sdn_node: SDNNode | None = None
        self.links: list[LinkEdge] = []
        self.flow_tables_short: FlowTables = {}
        self.flow_tables_sec: FlowTables = {}
        self.logic = SDNLogic()
        self.auto_dijkstra = False

        self.mode: str = "idle"
        self.selected_node: RouterNode | None = None
        self.info_router: RouterNode | None = None
        self.editing_link: LinkEdge | None = None
        self.weight_editor: tk.Entry | None = None
        self.weight_editor_window: int | None = None

        # ── Build UI ──
        self.header = HeaderBar(root)

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True)

        self.sidebar = Sidebar(
            body,
            on_ghost_start=self._ghost_start,
            on_ghost_move=self._ghost_move,
            on_ghost_drop=self._ghost_drop,
            on_toggle_connect=self._toggle_connect_mode,
            on_toggle_delete_link=self._toggle_delete_link,
            on_toggle_sdn=self._toggle_sdn_mode,
            on_toggle_auto=self._toggle_auto_dijkstra,
            on_run_dijkstra=self._run_dijkstra,
            on_load_topology=self._load_topology,
            on_save_topology=self._save_topology,
            on_start_packet=self._start_packet_sim,
            on_clear_all=self._clear_all,
        )

        self.canvas_handler = CanvasHandler(
            body,
            root,
            get_routers=lambda: self.routers,
            get_sdn_node=lambda: self.sdn_node,
            get_links=lambda: self.links,
            get_mode=lambda: self.mode,
            set_mode=self._set_mode,
            get_selected_node=lambda: self.selected_node,
            set_selected_node=self._set_selected_node,
            on_place_router=self._place_router,
            on_place_sdn=self._place_sdn,
            on_create_link=self._create_link,
            on_connect_sdn=self._connect_sdn,
            on_disconnect_sdn=self._disconnect_sdn,
            on_show_flow=self._show_flow,
            on_del_router=self._del_router,
            on_del_link=self._del_link,
            on_del_sdn=self._del_sdn,
            on_run_dijkstra=self._run_dijkstra,
            on_close_weight_editor=lambda commit: self._close_weight_editor(commit),
            on_open_weight_editor=self._open_weight_editor,
            on_deselect=self._deselect,
            on_silent_dijkstra=self._silent_dijkstra,
            status=self.status,
            get_simulator=lambda: self.simulator,
            get_weight_editor=lambda: self.weight_editor,
        )

        self.canvas = self.canvas_handler.canvas
        self.simulator = PacketSimulationHandler(self.canvas)

        rp_frame = tk.Frame(body, bg=PANEL_BG, width=290)
        rp_frame.pack(side="right", fill="y")
        rp_frame.pack_propagate(False)
        self.right_panel = RightPanel(rp_frame)

        self.topo_manager = TopologyManager(
            get_routers=lambda: self.routers,
            get_sdn_node=lambda: self.sdn_node,
            get_links=lambda: self.links,
            on_clear_all=lambda confirm: self._clear_all(confirm=confirm),
            on_set_sdn_node=self._set_sdn_node,
            get_canvas=lambda: self.canvas,
            add_router=lambda r: self.routers.append(r),
            add_link=lambda l: self.links.append(l),
            set_flow_tables=self._set_flow_tables,
            compute_flows=self._compute_flows,
            status=self.status,
        )

    # ── Ghost drag callbacks (forwarded to canvas handler) ──

    def _ghost_start(self, event: tk.Event, kind: str) -> None:
        self.canvas_handler.ghost_start(event, kind)

    def _ghost_move(self, event: tk.Event) -> None:
        self.canvas_handler.ghost_move(event)

    def _ghost_drop(self, event: tk.Event) -> None:
        self.canvas_handler.ghost_drop(event)

    # ── Mode helpers ──

    def _set_mode(self, mode: str) -> None:
        self.mode = mode

    def _set_selected_node(self, node: RouterNode | None) -> None:
        self.selected_node = node

    def _set_sdn_node(self, node: SDNNode) -> None:
        self.sdn_node = node

    def _set_flow_tables(self, short: FlowTables, sec: FlowTables) -> None:
        self.flow_tables_short = short
        self.flow_tables_sec = sec

    # ── Weight editor ──

    def _open_weight_editor(self, lnk: LinkEdge) -> None:
        self._close_weight_editor(commit=False)
        self.editing_link = lnk
        lnk.highlight(True)
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
            if self.editing_link is not None:
                self.editing_link.highlight(False)
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

        if self.editing_link is not None:
            self.editing_link.highlight(False)

        if self.weight_editor_window is not None:
            self.canvas.delete(self.weight_editor_window)
        self.weight_editor.destroy()
        self.weight_editor = None
        self.weight_editor_window = None
        self.editing_link = None

    # ── Node placement ──

    def _place_router(self, x: float, y: float) -> None:
        r = RouterNode(self.canvas, x, y)
        self.routers.append(r)
        self.status(f"Router {r.name} added  —  right-click to connect to SDN")
        self._silent_dijkstra()

    def _place_sdn(self, x: float, y: float) -> None:
        if self.sdn_node:
            messagebox.showinfo("SDN Controller", "Only one SDN Controller is allowed on the canvas.")
            return
        self.sdn_node = SDNNode(self.canvas, x, y)
        self.status("SDN Controller placed  —  use 'SDN Link' mode to connect routers")

    # ── Link creation ──

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

    # ── SDN connect/disconnect ──

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

    # ── Router/SDN deletion ──

    def _del_router(self, r: RouterNode) -> None:
        self.simulator.cancel()
        for lnk in [l for l in self.links if l.n1 is r or l.n2 is r]:
            lnk.delete()
            self.links.remove(lnk)
        for cid in r.ids():
            self.canvas.delete(cid)
        self.routers.remove(r)
        if self.info_router is r:
            self.info_router = None
            self.right_panel.clear()
        self.status(f"Router {r.name} deleted")
        self._silent_dijkstra()

    def _del_sdn(self) -> None:
        if not self.sdn_node:
            return
        self.simulator.cancel()
        for cid in self.sdn_node.ids():
            self.canvas.delete(cid)
        self.sdn_node = None
        for r in self.routers:
            r.set_sdn(False)
        self.flow_tables_short = {}
        self.flow_tables_sec = {}
        self.right_panel.clear()
        self.status("SDN Controller removed — all router connections cleared")

    # ── Tool mode toggles ──

    def _toggle_connect_mode(self) -> None:
        if self.mode == "connecting":
            self._deselect()
            self.sidebar.btn_connect.configure(fg=TEXT_COLOR)
            self.status("")
        else:
            self.mode = "connecting"
            self.selected_node = None
            self.sidebar.btn_connect.configure(fg=SELECT_CLR)
            self.sidebar.btn_sdn.configure(fg=TEXT_COLOR)
            self.sidebar.btn_del_link.configure(fg=TEXT_COLOR)
            self.status("Connect mode  —  click Router A, then Router B")

    def _toggle_delete_link(self) -> None:
        if self.mode == "deleting_link":
            self._deselect()
            self.sidebar.btn_del_link.configure(fg=TEXT_COLOR)
            self.status("")
        else:
            self.mode = "deleting_link"
            self.selected_node = None
            self.sidebar.btn_connect.configure(fg=TEXT_COLOR)
            self.sidebar.btn_sdn.configure(fg=TEXT_COLOR)
            self.sidebar.btn_del_link.configure(fg=SELECT_CLR)
            self.status("Delete link mode  —  click a link to delete it")

    def _del_link(self, lnk: LinkEdge) -> None:
        if self.editing_link is lnk:
            self._close_weight_editor(commit=False)
        lnk.delete()
        self.links.remove(lnk)
        self.status("Link deleted")
        self._silent_dijkstra()

    def _toggle_sdn_mode(self) -> None:
        if self.mode == "sdn_link":
            self.mode = "idle"
            self.sidebar.btn_sdn.configure(fg=TEXT_COLOR)
            self.status("")
        else:
            if not self.sdn_node:
                messagebox.showwarning(
                    "No SDN Controller", "Place an SDN Controller on the canvas first."
                )
                return
            self.mode = "sdn_link"
            self.sidebar.btn_sdn.configure(fg=SELECT_CLR)
            self.sidebar.btn_connect.configure(fg=TEXT_COLOR)
            self.sidebar.btn_del_link.configure(fg=TEXT_COLOR)
            self.status("SDN Link mode  —  click a router to connect it to SDN Ctrl")

    def _toggle_auto_dijkstra(self) -> None:
        self.auto_dijkstra = not self.auto_dijkstra
        if self.auto_dijkstra:
            self.sidebar.btn_auto.configure(text="☑  Auto Dijkstra: ON", fg=ACCENT)
            self.status("Auto Dijkstra enabled")
            self._silent_dijkstra()
        else:
            self.sidebar.btn_auto.configure(text="☐  Auto Dijkstra: OFF", fg=TEXT_COLOR)
            self.status("Auto Dijkstra disabled")

    # ── Dijkstra ──

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
            f"Flow tables computed for {len(self.flow_tables_short)} SDN-managed router(s).\n\n"
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
        self.flow_tables_short, self.flow_tables_sec = self.logic.compute()
        if self.info_router:
            self._show_flow(self.info_router)

    # ── Flow table display ──

    def _show_flow(self, r: RouterNode) -> None:
        self.info_router = r
        self.right_panel.set_title(f"Router  {r.name}")
        self.right_panel.fp_path_short.configure(text="")
        self.right_panel.fp_path_sec.configure(text="")

        for w in self.right_panel.fp_inner_short.winfo_children():
            w.destroy()
        for w in self.right_panel.fp_inner_sec.winfo_children():
            w.destroy()

        if not r.connected_to_sdn:
            self.right_panel.show_not_connected()
            return

        entries_short = self.flow_tables_short.get(r.name, [])
        entries_sec = self.flow_tables_sec.get(r.name, [])

        if not entries_short:
            self.right_panel.show_no_entries_short()
        else:
            self.right_panel.render_table(
                self.right_panel.fp_inner_short,
                entries_short,
                self.right_panel.fp_canvas_short,
                self.right_panel.fp_path_short,
                "Shortest",
            )

        if not entries_sec:
            self.right_panel.show_no_entries_sec()
        else:
            self.right_panel.render_table(
                self.right_panel.fp_inner_sec,
                entries_sec,
                self.right_panel.fp_canvas_sec,
                self.right_panel.fp_path_sec,
                "2nd Shortest",
            )

    # ── Packet simulation ──

    def _router_by_name(self, name: str) -> RouterNode | None:
        for r in self.routers:
            if r.name == name:
                return r
        return None

    def _flow_entry(self, src: str, dst: str) -> dict[str, Any] | None:
        for entry in self.flow_tables_short.get(src, []):
            if entry.get("dst") == dst:
                return cast(dict[str, Any], entry)
        return None

    def _start_packet_sim(self) -> None:
        if self.weight_editor is not None:
            self._close_weight_editor(commit=True)

        for lnk in self.links:
            lnk.highlight(False)

        src = self.sidebar.src_var.get().strip().upper()
        dst = self.sidebar.dst_var.get().strip().upper()

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

        next_hop = str(flow_entry.get("next_hop", "—")) if flow_entry else "—"
        if next_hop == "—":
            self.status(f"Packet dropped: destination {dst} unreachable")
            self.simulator.animate(
                [(src_router.x, src_router.y)],
                dropped=True,
                on_complete=lambda: self.status(f"Packet dropped at {src}"),
            )
            return

        path_text = str(flow_entry.get("path", "")) if flow_entry else ""
        path_nodes = [name.strip() for name in path_text.split("-->")]
        points: list[tuple[float, float]] = []
        for name in path_nodes:
            rtr = self._router_by_name(name)
            if rtr is not None:
                points.append((rtr.x, rtr.y))

        path_links: list[LinkEdge] = []
        for i in range(len(path_nodes) - 1):
            n1_name = path_nodes[i]
            n2_name = path_nodes[i + 1]
            for lnk in self.links:
                if {lnk.n1.name, lnk.n2.name} == {n1_name, n2_name}:
                    path_links.append(lnk)
                    break
        for lnk in path_links:
            lnk.highlight(True)

        def on_complete() -> None:
            for lnk in path_links:
                lnk.highlight(False)
            self.status(f"Packet delivered to {dst}")

        self.status(f"Packet started: {src} -> {dst}")
        self.simulator.animate(
            points,
            dropped=False,
            on_complete=on_complete,
        )

    # ── Misc ──

    def _deselect(self) -> None:
        if isinstance(self.selected_node, RouterNode):
            self.selected_node.set_selected(False)
        self.selected_node = None
        self.mode = "idle"
        self.sidebar.btn_connect.configure(fg=TEXT_COLOR)
        self.sidebar.btn_sdn.configure(fg=TEXT_COLOR)
        self.sidebar.btn_del_link.configure(fg=TEXT_COLOR)

    def _clear_all(self, confirm: bool = True) -> None:
        if confirm and (not messagebox.askyesno("Clear Canvas", "Remove all nodes and links?")):
            return
        self.simulator.cancel()
        self.canvas.delete("all")
        self.routers.clear()
        self.links.clear()
        self.sdn_node = None
        self.flow_tables_short = {}
        self.flow_tables_sec = {}
        self.info_router = None
        self.selected_node = None
        self.canvas_handler.drag_node = None
        self.mode = "idle"
        RouterNode.reset()
        self.right_panel.clear()
        self.status("Canvas cleared")

    def _load_topology(self) -> None:
        self.topo_manager.load()

    def _save_topology(self) -> None:
        self.topo_manager.save()

    def status(self, msg: str) -> None:
        self.header.set_status(msg)
