"""Header bar component for the SDN Network Visualizer."""

import tkinter as tk

from .theme import ACCENT, HEADER_BG, TEXT_COLOR, SELECT_CLR


class HeaderBar:
    """Top header bar showing title and status messages."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.status_lbl: tk.Label
        self._blink_id: str | None = None
        self._build(root)

    def _build(self, root: tk.Tk) -> None:
        hdr = tk.Frame(root, bg=HEADER_BG, height=52)
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
            fg=TEXT_COLOR,
            font=("Consolas", 10, "bold"),
        )
        self.status_lbl.pack(side="right", padx=16)

    def set_status(self, msg: str) -> None:
        self.status_lbl.configure(text=msg)
        self._start_blink()

    def _start_blink(self) -> None:
        if self._blink_id is not None:
            self.root.after_cancel(self._blink_id)
        
        def blink_step(step: int) -> None:
            if step > 5:
                self.status_lbl.configure(fg=TEXT_COLOR)
                self._blink_id = None
                return
            color = SELECT_CLR if step % 2 == 0 else TEXT_COLOR
            self.status_lbl.configure(fg=color)
            self._blink_id = self.root.after(150, lambda: blink_step(step + 1))
            
        blink_step(0)
