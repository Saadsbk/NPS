import tkinter as tk
from typing import Any, Callable, cast


class PacketSimulationHandler:
    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas
        self.packet_items: list[int] = []
        self.running = False
        self._after_id: str | None = None

    def cancel(self) -> None:
        if self._after_id is not None:
            self.canvas.after_cancel(self._after_id)
            self._after_id = None
        for item_id in self.packet_items:
            self.canvas.delete(item_id)
        self.packet_items.clear()
        self.running = False

    def _spawn_packet(self, x: float, y: float, dropped: bool) -> None:
        fill = "#ff7b72" if dropped else "#f4d35e"
        outline = "#b42318" if dropped else "#8a6a00"

        body = self.canvas.create_rectangle(
            x - 10,
            y - 7,
            x + 10,
            y + 7,
            fill=fill,
            outline=outline,
            width=2,
            tags=("packet",),
        )
        flap = cast(
            Any,
            self.canvas,
        ).create_line(
            x - 10,
            y - 7,
            x,
            y,
            x + 10,
            y - 7,
            fill=outline,
            width=2,
            tags=("packet",),
        )
        self.packet_items = [body, flap]

        for item_id in self.packet_items:
            self.canvas.tag_raise(item_id)

    def _move_packet_to(self, x: float, y: float) -> None:
        if not self.packet_items:
            return
        bbox = self.canvas.bbox(self.packet_items[0])
        if not bbox:
            return
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        dx = x - cx
        dy = y - cy
        for item_id in self.packet_items:
            self.canvas.move(item_id, dx, dy)

    def animate(
        self,
        points: list[tuple[float, float]],
        dropped: bool,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        self.cancel()
        if not points:
            if on_complete is not None:
                on_complete()
            return

        self.running = True
        self._spawn_packet(points[0][0], points[0][1], dropped=dropped)

        if len(points) == 1:
            self._after_id = self.canvas.after(3000, self.cancel)
            if on_complete is not None:
                on_complete()
            return

        segments: list[list[tuple[float, float]]] = []
        steps_per_segment = 18

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            seg_points: list[tuple[float, float]] = []
            for step in range(1, steps_per_segment + 1):
                t = step / steps_per_segment
                seg_points.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
            segments.append(seg_points)

        flat_points = [pt for seg in segments for pt in seg]

        def _tick(index: int) -> None:
            if not self.running:
                return
            if index >= len(flat_points):
                self.running = False
                if on_complete is not None:
                    on_complete()
                self._after_id = self.canvas.after(3000, self.cancel)
                return
            px, py = flat_points[index]
            self._move_packet_to(px, py)
            self._after_id = self.canvas.after(28, lambda: _tick(index + 1))

        _tick(0)

    @staticmethod
    def halfway_point(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
