
import math
import tkinter as tk

from .theme import (
    ACCENT,
    LINK_COLOR,
    LINK_TEXT,
    ROUTER_CONN,
    ROUTER_FILL,
    ROUTER_OUT,
    SDN_FILL,
    SDN_OUT,
    SDN_R,
    SELECT_CLR,
    ROUTER_R,
)


class RouterNode:
    _counter = 0

    @classmethod
    def reset(cls) -> None:
        cls._counter = 0

    def __init__(self, canvas: tk.Canvas, x: float, y: float) -> None:
        RouterNode._counter += 1
        self.name = chr(64 + RouterNode._counter)
        self.x, self.y = x, y
        self.canvas = canvas
        self.connected_to_sdn = False
        self.r = ROUTER_R
        self._oid: int | None = None
        self._tid: int | None = None
        self._draw()

    def _draw(self) -> None:
        r, x, y = self.r, self.x, self.y
        fill = ROUTER_CONN if self.connected_to_sdn else ROUTER_FILL
        self._oid = self.canvas.create_oval(
            x - r,
            y - r,
            x + r,
            y + r,
            fill=fill,
            outline=ROUTER_OUT,
            width=2,
            tags=("node", f"R_{self.name}"),
        )
        self._tid = self.canvas.create_text(
            x,
            y,
            text=self.name,
            fill="#1e1e2e",
            font=("Consolas", 13, "bold"),
            tags=("node", f"R_{self.name}"),
        )

    def ids(self) -> list[int]:
        return [cid for cid in [self._oid, self._tid] if cid is not None]

    def move_to(self, x: float, y: float) -> None:
        dx, dy = x - self.x, y - self.y
        self.x, self.y = x, y
        for cid in self.ids():
            self.canvas.move(cid, dx, dy)

    def set_sdn(self, connected: bool) -> None:
        self.connected_to_sdn = connected
        if self._oid is not None:
            self.canvas.itemconfig(
                self._oid, fill=ROUTER_CONN if connected else ROUTER_FILL
            )

    def set_selected(self, on: bool) -> None:
        if self._oid is not None:
            self.canvas.itemconfig(
                self._oid, outline=SELECT_CLR if on else ROUTER_OUT, width=3 if on else 2
            )


class SDNNode:
    def __init__(self, canvas: tk.Canvas, x: float, y: float) -> None:
        self.x, self.y = x, y
        self.canvas = canvas
        self.r = SDN_R
        self._pid: int | None = None
        self._lid: int | None = None
        self._sid: int | None = None
        self._draw()

    def _hex_pts(self, x: float, y: float, r: float) -> list[float]:
        pts: list[float] = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts += [x + r * math.cos(a), y + r * math.sin(a)]
        return pts

    def _draw(self) -> None:
        x, y, r = self.x, self.y, self.r
        self._pid = self.canvas.create_polygon(
            self._hex_pts(x, y, r),
            fill=SDN_FILL,
            outline=SDN_OUT,
            width=2,
            tags=("node", "sdn_node"),
        )
        self._lid = self.canvas.create_text(
            x,
            y - 7,
            text="SDN",
            fill="#1e1e2e",
            font=("Consolas", 10, "bold"),
            tags=("node", "sdn_node"),
        )
        self._sid = self.canvas.create_text(
            x,
            y + 8,
            text="CTRL",
            fill="#1e1e2e",
            font=("Consolas", 8),
            tags=("node", "sdn_node"),
        )

    def ids(self) -> list[int]:
        return [cid for cid in [self._pid, self._lid, self._sid] if cid is not None]

    def move_to(self, x: float, y: float) -> None:
        dx, dy = x - self.x, y - self.y
        self.x, self.y = x, y
        for cid in self.ids():
            self.canvas.move(cid, dx, dy)

    def set_selected(self, on: bool) -> None:
        if self._pid is not None:
            self.canvas.itemconfig(
                self._pid, outline=SELECT_CLR if on else SDN_OUT, width=3 if on else 2
            )


class LinkEdge:
    def __init__(self, canvas: tk.Canvas, n1: RouterNode, n2: RouterNode, weight: int = 1) -> None:
        self.canvas = canvas
        self.n1, self.n2 = n1, n2
        self.weight = weight
        self._lid: int | None = None
        self._wid: int | None = None
        self._draw()

    def _draw(self) -> None:
        x1, y1, x2, y2 = self.n1.x, self.n1.y, self.n2.x, self.n2.y
        self._lid = self.canvas.create_line(
            x1,
            y1,
            x2,
            y2,
            fill=LINK_COLOR,
            width=2,
            dash=(5, 3),
            tags=("link",),
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self._wid = self.canvas.create_text(
            mx,
            my - 11,
            text=str(self.weight),
            fill=LINK_TEXT,
            font=("Consolas", 9, "bold"),
            tags=("link_lbl",),
        )
        self.canvas.tag_lower("link")
        self.canvas.tag_lower("link_lbl")

    def ids(self) -> list[int]:
        return [cid for cid in [self._lid, self._wid] if cid is not None]

    def has_item(self, item_id: int) -> bool:
        return item_id in self.ids()

    def set_weight(self, weight: int) -> None:
        self.weight = weight
        if self._wid is not None:
            self.canvas.itemconfig(self._wid, text=str(weight))

    def label_center(self) -> tuple[float, float]:
        x1, y1 = self.n1.x, self.n1.y
        x2, y2 = self.n2.x, self.n2.y
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        return mx, my - 11

    def refresh(self) -> None:
        x1, y1 = self.n1.x, self.n1.y
        x2, y2 = self.n2.x, self.n2.y
        if self._lid is not None:
            self.canvas.coords(self._lid, x1, y1, x2, y2)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if self._wid is not None:
            self.canvas.coords(self._wid, mx, my - 11)

    def delete(self) -> None:
        if self._lid is not None:
            self.canvas.delete(self._lid)
        if self._wid is not None:
            self.canvas.delete(self._wid)

    def highlight(self, on: bool) -> None:
        if self._lid is not None:
            self.canvas.itemconfig(
                self._lid, fill=ACCENT if on else LINK_COLOR, width=3 if on else 2
            )
