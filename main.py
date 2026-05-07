import tkinter as tk

from uis_sniper_gui import LauncherApp


def main() -> None:
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

