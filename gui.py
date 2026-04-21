import tkinter as tk
from tkinter import ttk

from dijkstra_network_simulator.main import App
from dijkstra_network_simulator.theme import BTN_BG, PANEL_BG, TEXT_COLOR


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Vertical.TScrollbar",
        background=BTN_BG,
        troughcolor=PANEL_BG,
        arrowcolor=TEXT_COLOR,
        bordercolor=PANEL_BG,
        lightcolor=BTN_BG,
        darkcolor=BTN_BG,
    )
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()