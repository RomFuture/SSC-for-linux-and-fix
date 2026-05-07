import tkinter as tk

from smart_sniper.application.ports import LoggerPort


class TkTextLogger(LoggerPort):
    def __init__(self, root: tk.Misc, widget: tk.Text) -> None:
        self.root = root
        self.widget = widget

    def log(self, message: str) -> None:
        def _write() -> None:
            try:
                self.widget.insert(tk.END, message + "\n")
                self.widget.see(tk.END)
            except Exception:
                pass

        self.root.after(0, _write)

