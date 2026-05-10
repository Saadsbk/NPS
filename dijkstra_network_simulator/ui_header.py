"""Header bar component for the SDN Network Visualizer."""

import tkinter as tk

from .theme import ACCENT, HEADER_BG, MUTED_TEXT


class HeaderBar:
    """Top header bar showing title and status messages."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.status_lbl: tk.Label
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
            fg=MUTED_TEXT,
            font=("Consolas", 9),
        )
        self.status_lbl.pack(side="right", padx=16)

    def set_status(self, msg: str) -> None:
        self.status_lbl.configure(text=msg)
