"""Topology save/load manager for the SDN Network Visualizer."""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable

from .models import LinkEdge, RouterNode, SDNNode


class TopologyManager:
    """Handles serialization, deserialization, saving, and loading of network topologies."""

    def __init__(
        self,
        *,
        get_routers: Callable[[], list[RouterNode]],
        get_sdn_node: Callable[[], SDNNode | None],
        get_links: Callable[[], list[LinkEdge]],
        on_clear_all: Callable[[bool], None],
        on_set_sdn_node: Callable[[SDNNode], None],
        get_canvas: Callable[[], tk.Canvas],
        add_router: Callable[[RouterNode], None],
        add_link: Callable[[LinkEdge], None],
        set_flow_tables: Callable[[dict, dict], None],
        compute_flows: Callable[[], None],
        status: Callable[[str], None],
    ) -> None:
        self._get_routers = get_routers
        self._get_sdn_node = get_sdn_node
        self._get_links = get_links
        self._on_clear_all = on_clear_all
        self._on_set_sdn_node = on_set_sdn_node
        self._get_canvas = get_canvas
        self._add_router = add_router
        self._add_link = add_link
        self._set_flow_tables = set_flow_tables
        self._compute_flows = compute_flows
        self._status = status

    def serialize(self) -> dict[str, Any]:
        routers = [
            {
                "name": r.name,
                "x": round(r.x, 2),
                "y": round(r.y, 2),
                "connected_to_sdn": bool(r.connected_to_sdn),
            }
            for r in self._get_routers()
        ]
        routers.sort(key=lambda item: str(item["name"]))
        links = [
            {"n1": l.n1.name, "n2": l.n2.name, "weight": int(l.weight)}
            for l in self._get_links()
        ]
        links.sort(key=lambda item: (str(item["n1"]), str(item["n2"])))

        sdn: dict[str, float] | None = None
        sdn_node = self._get_sdn_node()
        if sdn_node is not None:
            sdn = {"x": round(sdn_node.x, 2), "y": round(sdn_node.y, 2)}

        return {"sdn": sdn, "routers": routers, "links": links}

    def apply(self, topo: dict[str, Any]) -> None:
        self._on_clear_all(False)
        canvas = self._get_canvas()

        sdn_data = topo.get("sdn")
        if isinstance(sdn_data, dict):
            sx = float(sdn_data.get("x", 500.0))
            sy = float(sdn_data.get("y", 100.0))
            self._on_set_sdn_node(SDNNode(canvas, sx, sy))

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
            r = RouterNode(canvas, rx, ry)
            if r.name != name:
                old_name = r.name
                r.name = name
                if r._tid is not None:
                    canvas.itemconfig(r._tid, text=name)
                for cid in r.ids():
                    tags = list(canvas.gettags(cid))
                    tags = [f"R_{name}" if t == f"R_{old_name}" else t for t in tags]
                    canvas.itemconfig(cid, tags=tuple(tags))
            self._add_router(r)
            router_map[name] = r

        sdn_node = self._get_sdn_node()
        for item in topo.get("routers", []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().upper()
            if name in router_map:
                connect = bool(item.get("connected_to_sdn", False))
                router_map[name].set_sdn(connect and sdn_node is not None)

        for item in topo.get("links", []):
            if not isinstance(item, dict):
                continue
            n1 = str(item.get("n1", "")).strip().upper()
            n2 = str(item.get("n2", "")).strip().upper()
            if n1 not in router_map or n2 not in router_map or n1 == n2:
                continue
            weight = int(item.get("weight", 1)) if str(item.get("weight", "1")).isdigit() else 1
            self._add_link(LinkEdge(canvas, router_map[n1], router_map[n2], max(1, weight)))

        self._set_flow_tables({}, {})
        self._compute_flows()
        routers = self._get_routers()
        links = self._get_links()
        self._status(f"Topology loaded: {len(routers)} routers, {len(links)} links")

    def load(self) -> None:
        initial_dir = os.path.dirname(os.path.abspath(__file__))
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
            self.apply(topo)
        except Exception as exc:
            messagebox.showerror("Load Topology Failed", str(exc))

    def save(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Topology JSON",
            defaultextension=".json",
            initialfile="saved_topology.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            topo = self.serialize()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(topo, f, indent=2)
            self._status(f"Topology saved: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Save Topology Failed", str(exc))
