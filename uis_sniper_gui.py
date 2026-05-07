import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import webbrowser
import traceback
from datetime import datetime

# --- NÁSILNÉ IMPORTY PRO PYINSTALLER (aby nevynechal soubory v .exe) ---
import selenium.webdriver.chrome.webdriver
import selenium.webdriver.common.service
import selenium.webdriver.common.options
import selenium.webdriver.chrome.options
import selenium.webdriver.chrome.service
# -----------------------------------------------------------------------

from smart_sniper.application.cancellation import CancellationToken
from smart_sniper.application.dto import (
    Credentials,
    EnrolledTermsCommand,
    TcSniperCommand,
    UisDogCommand,
    UisScanCommand,
    UisSniperCommand,
)
from smart_sniper.bootstrap import build_container
from smart_sniper.domain.target_parser import parse_blacklist, parse_targets
from smart_sniper.infrastructure.config_store import JsonConfigStore

# --- GLOBÁLNÍ KONFIGURACE ---
UIS_LOGIN_URL = "https://is.czu.cz/auth/"
OUTLOOK_URL = "https://outlook.office.com/mail/"
MOODLE_LOGIN_URL = "https://moodle.czu.cz/login/index.php"
COFFEE_URL = "https://buymeacoffee.com/colorvant"

# --- BARVY (DARK MODE) ---
COLOR_BG = "#1e1e1e"
COLOR_FRAME = "#2b2b2b"
COLOR_TEXT = "#ffffff"
COLOR_ENTRY_BG = "#3c3c3c"
COLOR_BTN_START = "#006400" 
COLOR_BTN_STOP = "#8b0000"  
COLOR_BTN_SCAN = "#005f9e"
COLOR_BTN_DOG = "#A0522D"
COLOR_ACCENT = "#FFD700"    
COLOR_INFO = "#4FC3F7"

# =============================================================================
# POMOCNÁ TŘÍDA PRO CONFIG
# =============================================================================
class ConfigManager:
    def __init__(self):
        self.store = JsonConfigStore()

    def load(self):
        return self.store.load()

    def save(self, data):
        self.store.save(data)


class CallbackLogger:
    def __init__(self, callback):
        self.callback = callback

    def log(self, message):
        self.callback(message)

# =============================================================================
# TŘÍDA: LAUNCHER (ROZCESTNÍK)
# =============================================================================
class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.container = build_container(root)
        self.root.title("Smart Sniper - ČZU Tools")
        self.root.geometry("400x500")
        self.root.configure(bg=COLOR_BG)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=10, font=("Segoe UI", 12, "bold"), background="#444", foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', '#555')])

        tk.Label(root, text="Vyber nástroj", font=("Segoe UI", 20, "bold"), bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(40, 20))

        btn_uis = ttk.Button(root, text="UIS SNIPER (Zkoušky)", command=self.open_uis_sniper)
        btn_uis.pack(fill=tk.X, padx=50, pady=10)

        btn_tc = ttk.Button(root, text="TC SNIPER (Moodle Testy)", command=self.open_tc_sniper)
        btn_tc.pack(fill=tk.X, padx=50, pady=10)
        
        btn_enrolled = ttk.Button(root, text="📋 Zapsané termíny (Přehled)", command=self.open_enrolled)
        btn_enrolled.pack(fill=tk.X, padx=50, pady=10)
        
        tk.Label(root, text="v2.20 Update Master", font=("Segoe UI", 8), bg=COLOR_BG, fg="gray").pack(side=tk.BOTTOM, pady=5)
        
        btn_coffee = tk.Button(root, text="☕ Podpořit autora", bg=COLOR_ACCENT, fg="black", font=("Segoe UI", 10, "bold"), command=lambda: webbrowser.open(COFFEE_URL))
        btn_coffee.pack(side=tk.BOTTOM, pady=10)

    def open_uis_sniper(self):
        new_window = tk.Toplevel(self.root)
        UISSniperApp(new_window, self.container)

    def open_tc_sniper(self):
        new_window = tk.Toplevel(self.root)
        TCSniperApp(new_window, self.container)

    def open_enrolled(self):
        new_window = tk.Toplevel(self.root)
        EnrolledTermsApp(new_window, self.container)

# =============================================================================
# TŘÍDA: UIS SNIPER
# =============================================================================
class UISSniperApp:
    def __init__(self, root, container):
        self.root = root
        self.container = container
        self.root.title("UIS Sniper - ČZU Dark Edition (Stable)")
        self.root.geometry("700x980")
        self.root.resizable(True, True)
        self.root.configure(bg=COLOR_BG)
        
        self.driver = None
        self.is_running = False
        self.thread = None
        self.cancel_token = None
        
        self.config = ConfigManager()
        self.saved_data = self.config.load()
        
        self.scanned_data = self.saved_data.get("scanned_data", {}) 
        self.all_subjects = self.saved_data.get("all_subjects", [])
        self.outlook_mode = tk.BooleanVar(value=False)

        self.setup_ui()

    def setup_ui(self):
        # --- STYLY ---
        style = ttk.Style()
        style.theme_use('clam') 
        
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR_ACCENT)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("TButton", padding=6, font=("Segoe UI", 10), background="#444", foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', '#555')])
        style.configure("TCombobox", fieldbackground=COLOR_ENTRY_BG, background="#444", foreground=COLOR_TEXT, arrowcolor="white")
        style.map("TCombobox", fieldbackground=[('readonly', COLOR_ENTRY_BG)], selectbackground=[('readonly', '#555')])
        style.configure("TCheckbutton", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))

        # --- HLAVNÍ SCROLLOVACÍ PLÁTNO ---
        main_canvas = tk.Canvas(self.root, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        main_canvas.bind_all("<MouseWheel>", lambda event: main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        main_canvas.bind_all("<Button-4>", lambda _event: main_canvas.yview_scroll(-1, "units"))
        main_canvas.bind_all("<Button-5>", lambda _event: main_canvas.yview_scroll(1, "units"))

        content_frame = ttk.Frame(scrollable_frame, padding="15")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 1. PŘIHLAŠOVACÍ ÚDAJE
        lbl_frame_login = ttk.LabelFrame(content_frame, text="1. Přihlašovací údaje (UIS)", padding="10")
        lbl_frame_login.pack(fill=tk.X, pady=5)

        ttk.Label(lbl_frame_login, text="Login:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.entry_user = tk.Entry(lbl_frame_login, width=25, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.entry_user.insert(0, self.saved_data.get("username", "")) 
        self.entry_user.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(lbl_frame_login, text="Heslo:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.entry_pass = tk.Entry(lbl_frame_login, width=25, show="*", bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.entry_pass.grid(row=0, column=3, sticky=tk.W, padx=5)

        # 2. AUTOMATICKÉ NAČTENÍ
        lbl_frame_scan = ttk.LabelFrame(content_frame, text="2. Automatické načtení (Doporučeno)", padding="10")
        lbl_frame_scan.pack(fill=tk.X, pady=5)
        
        lbl_scan_info = ttk.Label(lbl_frame_scan, text="Klikni pro načtení učitelů a předmětů + detekci tvé fakulty. Data se uloží pro příště.", wraplength=600)
        lbl_scan_info.pack(pady=(0, 5))
        
        self.btn_scan = tk.Button(lbl_frame_scan, text="🔄 Načíst data z UIS", bg=COLOR_BTN_SCAN, fg="white", font=("Segoe UI", 10, "bold"), command=self.start_scan)
        self.btn_scan.pack(fill=tk.X)

        # 3. VÝBĚR PŘEDMĚTU
        lbl_frame_creator = ttk.LabelFrame(content_frame, text="3. Vybrat předmět ke sledování", padding="10")
        lbl_frame_creator.pack(fill=tk.X, pady=5)

        self.frame_detected = tk.Frame(lbl_frame_creator, bg=COLOR_BG)
        self.frame_detected.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        tk.Label(self.frame_detected, text="Fakulta/Obor:", font=("Segoe UI", 9, "bold"), bg=COLOR_BG, fg=COLOR_TEXT).pack(side=tk.LEFT)
        saved_study_info = self.saved_data.get("study_info", "--- (Načte se po přihlášení) ---")
        self.lbl_study_info = tk.Label(self.frame_detected, text=saved_study_info, font=("Segoe UI", 9), bg=COLOR_BG, fg=COLOR_INFO)
        self.lbl_study_info.pack(side=tk.LEFT, padx=5)

        ttk.Label(lbl_frame_creator, text="Učitel:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.cb_teacher = ttk.Combobox(lbl_frame_creator, width=38)
        self.cb_teacher.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.cb_teacher.bind("<<ComboboxSelected>>", self.on_teacher_selected) 
        ttk.Label(lbl_frame_creator, text="(např. Jadrná)", font=("Segoe UI", 8), foreground="#888").grid(row=2, column=2, sticky=tk.W)

        ttk.Label(lbl_frame_creator, text="Předmět:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.cb_subject = ttk.Combobox(lbl_frame_creator, width=38) 
        self.cb_subject.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(lbl_frame_creator, text="(např. Teorie řízení)", font=("Segoe UI", 8), foreground="#888").grid(row=3, column=2, sticky=tk.W)

        if self.scanned_data:
            self.cb_teacher['values'] = sorted(list(self.scanned_data.keys()))
        if self.all_subjects:
            self.cb_subject['values'] = sorted(self.all_subjects)

        ttk.Label(lbl_frame_creator, text="Konkrétní datum:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_date = tk.Entry(lbl_frame_creator, width=15, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.entry_date.grid(row=4, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Label(lbl_frame_creator, text="(např. 22.01 nebo prázdné)", font=("Segoe UI", 8), foreground="#888").grid(row=4, column=2, sticky=tk.W)

        btn_add = tk.Button(lbl_frame_creator, text="⬇️ PŘIDAT DO SEZNAMU", bg="#444", fg="white", font=("Segoe UI", 9, "bold"), command=self.add_target)
        btn_add.grid(row=5, column=0, columnspan=3, pady=10, sticky=tk.EW)

        # 4. SEZNAM TERMÍNŮ
        lbl_frame_targets = ttk.LabelFrame(content_frame, text="4. Seznam hlídaných termínů (Priorita shora dolů)", padding="10")
        lbl_frame_targets.pack(fill=tk.BOTH, expand=True, pady=5)
        
        container_list = tk.Frame(lbl_frame_targets, bg=COLOR_BG)
        container_list.pack(fill=tk.BOTH, expand=True)
        
        frame_list = tk.Frame(container_list, bg=COLOR_BG)
        frame_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_list = tk.Scrollbar(frame_list)
        scrollbar_list.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.list_targets = tk.Listbox(frame_list, height=5, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, selectbackground=COLOR_ACCENT, selectforeground="black", font=("Consolas", 10), yscrollcommand=scrollbar_list.set)
        self.list_targets.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_list.config(command=self.list_targets.yview)
        
        frame_btns = tk.Frame(container_list, bg=COLOR_BG)
        frame_btns.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        tk.Button(frame_btns, text="⬆️", bg="#444", fg="white", width=4, command=self.move_up).pack(pady=2)
        tk.Button(frame_btns, text="⬇️", bg="#444", fg="white", width=4, command=self.move_down).pack(pady=2)
        tk.Button(frame_btns, text="🗑️", bg="#8b0000", fg="white", width=4, command=self.delete_item).pack(pady=(10, 2))

        saved_targets_str = self.saved_data.get("targets", "")
        if saved_targets_str:
            for line in saved_targets_str.split("\n"):
                if line.strip() and not line.startswith("#"):
                    self.list_targets.insert(tk.END, line.strip())

        # 5. BLACKLIST
        lbl_frame_blacklist = ttk.LabelFrame(content_frame, text="5. Ignorované termíny (Blacklist)", padding="10")
        lbl_frame_blacklist.pack(fill=tk.X, pady=5)
        
        ttk.Label(lbl_frame_blacklist, text="Zde napiš co nechceš (odděl středníkem). Např: 24.01; 8:00; Novák").pack(anchor=tk.W)
        self.entry_blacklist = tk.Entry(lbl_frame_blacklist, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.entry_blacklist.pack(fill=tk.X, pady=2)
        self.entry_blacklist.insert(0, self.saved_data.get("blacklist", ""))

        # 6. OVLÁDÁNÍ
        lbl_frame_control = ttk.LabelFrame(content_frame, text="6. Ovládání", padding="10")
        lbl_frame_control.pack(fill=tk.X, pady=5)

        self.chk_outlook = ttk.Checkbutton(lbl_frame_control, text="📧 Aktivovat Outlook Watcher (Čekání na email)", variable=self.outlook_mode, onvalue=True, offvalue=False)
        self.chk_outlook.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(lbl_frame_control, text="Pozor: E-maily mají zpoždění. Vhodné jen pro nové termíny.", font=("Segoe UI", 8), foreground="gray").pack(anchor=tk.W, pady=(0, 10))

        btn_frame = ttk.Frame(lbl_frame_control)
        btn_frame.pack(fill=tk.X)

        self.btn_start = tk.Button(btn_frame, text="🚀 SPUSTIT SNIPER", bg=COLOR_BTN_START, fg="white", font=("Segoe UI", 12, "bold"), command=self.start_sniper)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_dog = tk.Button(btn_frame, text="🐶 NASTAVIT HLÍDACÍHO PSA", bg=COLOR_BTN_DOG, fg="white", font=("Segoe UI", 12, "bold"), command=self.start_dog_mode)
        self.btn_dog.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.btn_stop = tk.Button(btn_frame, text="🛑 ZASTAVIT", bg=COLOR_BTN_STOP, fg="white", font=("Segoe UI", 12, "bold"), command=self.stop_sniper, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # LOG
        lbl_frame_log = ttk.LabelFrame(content_frame, text="Log (Průběh)", padding="10")
        lbl_frame_log.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txt_log = scrolledtext.ScrolledText(lbl_frame_log, height=8, state='normal', bg="#000000", fg="#00ff00", font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        btn_coffee = tk.Button(content_frame, text="☕ Líbi se ti aplikace? Podpoř autora na Buy Me a Coffee", bg=COLOR_ACCENT, fg="black", font=("Segoe UI", 10, "bold"), command=lambda: webbrowser.open(COFFEE_URL))
        btn_coffee.pack(fill=tk.X, pady=10)

    # --- UI METODY ---
    def log(self, msg):
        try:
            self.txt_log.insert(tk.END, f"{msg}\n")
            self.txt_log.see(tk.END)
        except: pass

    def save_config(self):
        targets = "\n".join(self.list_targets.get(0, tk.END))
        study_info_text = self.lbl_study_info.cget("text")
        data = {
            "username": self.entry_user.get(),
            "targets": targets,
            "blacklist": self.entry_blacklist.get(),
            "scanned_data": self.scanned_data,
            "all_subjects": self.all_subjects,
            "study_info": study_info_text
        }
        self.config.save(data)

    def on_teacher_selected(self, event):
        t = self.cb_teacher.get()
        if t in self.scanned_data:
            self.cb_subject['values'] = sorted(list(self.scanned_data[t]))
            if self.scanned_data[t]: self.cb_subject.current(0)
        else:
            self.cb_subject['values'] = sorted(self.all_subjects)

    def add_target(self):
        subj = self.cb_subject.get().strip()
        teach = self.cb_teacher.get().strip()
        date = self.entry_date.get().strip()
        
        if not subj:
            messagebox.showwarning("Chyba", "Musíš vybrat nebo napsat název předmětu!")
            return

        line = f"{subj};{date};{teach}"
        self.list_targets.insert(tk.END, line)
        
        self.cb_subject.set('')
        self.cb_teacher.set('')
        self.entry_date.delete(0, tk.END)
        self.save_config()

    def move_up(self):
        idx = self.list_targets.curselection()
        if not idx or idx[0] == 0: return
        text = self.list_targets.get(idx[0])
        self.list_targets.delete(idx[0])
        self.list_targets.insert(idx[0]-1, text)
        self.list_targets.selection_set(idx[0]-1)
        self.save_config()
    
    def move_down(self):
        idx = self.list_targets.curselection()
        if not idx or idx[0] == self.list_targets.size()-1: return
        text = self.list_targets.get(idx[0])
        self.list_targets.delete(idx[0])
        self.list_targets.insert(idx[0]+1, text)
        self.list_targets.selection_set(idx[0]+1)
        self.save_config()

    def delete_item(self):
        idx = self.list_targets.curselection()
        if idx: 
            self.list_targets.delete(idx[0])
            self.save_config()

    def get_targets(self):
        raw = self.list_targets.get(0, tk.END)
        targets = []
        for line in raw:
            line = line.strip()
            if not line: continue
            parts = line.split(";")
            if len(parts) >= 1:
                targets.append({"subject": parts[0].strip(), "date": parts[1].strip() if len(parts)>1 else "", "filter": parts[2].strip() if len(parts)>2 else "", "original_line": line})
        return targets
    
    def remove_target_from_gui(self, original_line):
        def _remove():
            try:
                items = self.list_targets.get(0, tk.END)
                if original_line in items:
                    idx = items.index(original_line)
                    self.list_targets.delete(idx)
                    self.save_config()
            except: pass
        self.root.after(0, _remove)

    def update_study_info_ui(self, info_text):
        def _update():
            self.lbl_study_info.config(text=info_text)
        self.root.after(0, _update)

    def run_sniper_process(self):
        try:
            command = UisSniperCommand(
                credentials=Credentials(
                    username=self.entry_user.get(),
                    password=self.entry_pass.get(),
                ),
                targets=parse_targets(self.list_targets.get(0, tk.END)),
                blacklist=parse_blacklist(self.entry_blacklist.get()),
                use_outlook=self.outlook_mode.get(),
                cancellation=self.cancel_token,
            )
            self.container.run_uis_sniper.execute(
                command,
                self,
                on_target_enrolled=lambda line: self.remove_target_from_gui(line),
                on_study_info=lambda text: self.update_study_info_ui(text),
            )
        except Exception as e:
            self.log(f"CHYBA: {e}")
            traceback.print_exc()
        finally:
            self.root.after(0, self.reset_ui)

    def start_sniper(self):
        self.is_running = True
        self.cancel_token = CancellationToken()
        self.btn_start.config(state="disabled")
        self.btn_dog.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.thread = threading.Thread(target=self.run_sniper_process)
        self.thread.daemon = True
        self.thread.start()
    
    def start_scan(self):
        self.btn_scan.config(state="disabled", text="⏳ Načítám...")
        self.thread = threading.Thread(target=self.scan_process)
        self.thread.daemon = True
        self.thread.start()
    
    def scan_process(self):
        try:
            command = UisScanCommand(
                credentials=Credentials(
                    username=self.entry_user.get(),
                    password=self.entry_pass.get(),
                )
            )
            result = self.container.scan_uis_data.execute(
                command,
                self,
                on_study_info=lambda text: self.update_study_info_ui(text),
            )
            if result:
                self.scanned_data = result.teacher_to_subjects
                self.all_subjects = result.all_subjects
                self.root.after(
                    0,
                    lambda: [
                        self.save_config(),
                        messagebox.showinfo("OK", "Data načtena"),
                        self.update_comboboxes(),
                    ],
                )
        finally:
            self.root.after(0, lambda: self.btn_scan.config(state="normal", text="🔄 Načíst data z UIS"))

    def update_comboboxes(self):
        self.cb_teacher['values'] = sorted(list(self.scanned_data.keys()))
        self.cb_subject['values'] = sorted(self.all_subjects)

    def start_dog_mode(self):
        self.is_running = True
        self.cancel_token = CancellationToken()
        self.btn_dog.config(state="disabled")
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_dog, daemon=True).start()

    def run_dog(self):
        try:
            command = UisDogCommand(
                credentials=Credentials(
                    username=self.entry_user.get(),
                    password=self.entry_pass.get(),
                ),
                targets=parse_targets(self.list_targets.get(0, tk.END)),
                blacklist=parse_blacklist(self.entry_blacklist.get()),
                cancellation=self.cancel_token,
            )
            self.container.run_uis_dog.execute(command, self)
        finally:
            self.root.after(0, self.reset_ui)

    def stop_sniper(self):
        self.is_running = False
        if self.cancel_token:
            self.cancel_token.cancel()
    
    def reset_ui(self):
        self.is_running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_dog.config(state="normal")
        self.log("--- ZASTAVENO ---")

# =============================================================================
# TŘÍDA: TC SNIPER (Moodle)
# =============================================================================
class TCSniperApp:
    def __init__(self, root, container):
        self.root = root
        self.container = container
        self.root.title("TC Sniper - Moodle Dark (Stable)")
        self.root.geometry("500x600")
        self.root.configure(bg=COLOR_BG)
        self.driver = None
        self.is_running = False
        self.cancel_token = None
        self.config = ConfigManager()
        self.saved_data = self.config.load()

        # Styl
        style = ttk.Style()
        style.theme_use('clam') 
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_TEXT)
        style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR_ACCENT)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("TButton", padding=6, font=("Segoe UI", 10), background="#444", foreground="white", borderwidth=0)
        style.map("TButton", background=[('active', '#555')])
        style.configure("TCheckbutton", background=COLOR_BG, foreground=COLOR_TEXT, font=("Segoe UI", 10))
        
        lbl = ttk.LabelFrame(root, text="Nastavení", padding=10)
        lbl.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(lbl, text="URL Testu:", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=0, column=0, sticky=tk.W)
        self.e_url = tk.Entry(lbl, width=38, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_url.grid(row=0, column=1, pady=2)
        self.e_url.insert(0, self.saved_data.get("tc_url", ""))

        tk.Label(lbl, text="Název testu (volitelně):", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=1, column=0, sticky=tk.W)
        self.e_tc_filter = tk.Entry(lbl, width=38, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_tc_filter.grid(row=1, column=1, pady=2)
        self.e_tc_filter.insert(0, self.saved_data.get("tc_filter", ""))
        
        tk.Label(lbl, text="(např. 'sekce 3')", bg=COLOR_BG, fg="gray", font=("Segoe UI", 8)).grid(row=2, column=1, sticky=tk.W)

        tk.Label(lbl, text="Dny / Data (např. 15, 24.04.):", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=3, column=0, sticky=tk.W)
        self.e_days = tk.Entry(lbl, width=38, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_days.grid(row=3, column=1, pady=2)
        self.e_days.insert(0, self.saved_data.get("tc_days", "15"))
        
        tk.Label(lbl, text="Čas od (HH:MM):", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=4, column=0, sticky=tk.W)
        self.e_t1 = tk.Entry(lbl, width=38, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_t1.grid(row=4, column=1, pady=2)
        self.e_t1.insert(0, self.saved_data.get("tc_t1", "12:00"))
        
        tk.Label(lbl, text="Čas do (HH:MM):", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=5, column=0, sticky=tk.W)
        self.e_t2 = tk.Entry(lbl, width=38, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_t2.grid(row=5, column=1, pady=2)
        self.e_t2.insert(0, self.saved_data.get("tc_t2", "19:00"))

        self.chk_book = tk.BooleanVar(value=True)
        tk.Checkbutton(lbl, text="Zarezervovat / Změnit", variable=self.chk_book, bg=COLOR_BG, fg=COLOR_TEXT, selectcolor=COLOR_BG, activebackground=COLOR_BG, activeforeground=COLOR_TEXT).grid(row=6, columnspan=2, pady=5)

        self.btn_run = tk.Button(root, text="START", bg=COLOR_BTN_START, fg="white", command=self.run)
        self.btn_run.pack(fill=tk.X, padx=10)
        self.btn_stop = tk.Button(root, text="STOP", bg=COLOR_BTN_STOP, fg="white", command=self.stop, state="disabled")
        self.btn_stop.pack(fill=tk.X, padx=10, pady=5)
        
        self.txt = scrolledtext.ScrolledText(root, height=8, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.txt.pack(fill=tk.BOTH, padx=10)

    def log(self, m):
        def _log():
            try:
                self.txt.insert(tk.END, m+"\n")
                self.txt.see(tk.END)
            except: pass
        self.root.after(0, _log)
    
    def run(self):
        self.is_running = True
        self.cancel_token = CancellationToken()
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        # Save config
        self.config.save({
            "tc_url": self.e_url.get(), 
            "tc_filter": self.e_tc_filter.get(),
            "tc_days": self.e_days.get(),
            "tc_t1": self.e_t1.get(),
            "tc_t2": self.e_t2.get()
        })
        threading.Thread(target=self.process, daemon=True).start()

    def stop(self):
        self.is_running = False
        if self.cancel_token:
            self.cancel_token.cancel()

    def process(self):
        if not self.e_url.get().strip():
            self.root.after(0, lambda: messagebox.showerror("Chyba", "Vyplň URL testu."))
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
            self.is_running = False
            return
        try:
            # Validate time early to preserve previous UX behavior.
            datetime.strptime(self.e_t1.get().strip(), "%H:%M")
            datetime.strptime(self.e_t2.get().strip(), "%H:%M")
        except ValueError:
            self.root.after(0, lambda: messagebox.showerror("Chyba", "Špatný formát času! Použij HH:MM (např. 08:00)"))
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
            self.is_running = False
            return

        command = TcSniperCommand(
            credentials=Credentials(
                username=self.saved_data.get("username", ""),
                password="",
            ),
            tc_url=self.e_url.get().strip(),
            tc_filter=self.e_tc_filter.get().strip(),
            days=[d.strip() for d in self.e_days.get().split(",") if d.strip()],
            start_time=self.e_t1.get().strip(),
            end_time=self.e_t2.get().strip(),
            should_book=self.chk_book.get(),
            cancellation=self.cancel_token,
        )
        try:
            self.container.run_tc_sniper.execute(command, self)
        except Exception as e:
            self.log(f"Err: {e}")
        finally:
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
            self.is_running = False

# =============================================================================
# TŘÍDA: PŘEHLED ZAPSANÝCH TERMÍNŮ
# =============================================================================
class EnrolledTermsApp:
    def __init__(self, root, container):
        self.root = root
        self.container = container
        self.root.title("Přehled zapsaných termínů (UIS & Moodle TC)")
        self.root.geometry("850x650")
        self.root.configure(bg=COLOR_BG)
        
        self.config = ConfigManager()
        self.saved_data = self.config.load()
        
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        top_frame = tk.Frame(self.root, bg=COLOR_BG)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(top_frame, text="Login:", bg=COLOR_BG, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=(0,5))
        self.e_user = tk.Entry(top_frame, bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_user.insert(0, self.saved_data.get("username", ""))
        self.e_user.pack(side=tk.LEFT, padx=5)
        
        tk.Label(top_frame, text="Heslo:", bg=COLOR_BG, fg=COLOR_TEXT).pack(side=tk.LEFT, padx=5)
        self.e_pass = tk.Entry(top_frame, show="*", bg=COLOR_ENTRY_BG, fg=COLOR_TEXT, insertbackground='white')
        self.e_pass.pack(side=tk.LEFT, padx=5)
        
        btn_load = tk.Button(top_frame, text="🔄 Načíst moje termíny", bg=COLOR_BTN_SCAN, fg="white", font=("Segoe UI", 10, "bold"), command=self.start_fetch)
        btn_load.pack(side=tk.LEFT, padx=20)
        
        frame_split = tk.Frame(self.root, bg=COLOR_BG)
        frame_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        frame_uis = ttk.LabelFrame(frame_split, text="🏛️ UIS Zkoušky")
        frame_uis.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.txt_uis = scrolledtext.ScrolledText(frame_uis, bg="black", fg="#00ff00", font=("Consolas", 10))
        self.txt_uis.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Načíst uložená data po zapnutí
        saved_uis = self.saved_data.get("enrolled_uis", "")
        if saved_uis:
            self.txt_uis.insert(tk.END, saved_uis + "\n")
        
        frame_tc = ttk.LabelFrame(frame_split, text="🎓 Moodle TC Testy")
        frame_tc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.txt_tc = scrolledtext.ScrolledText(frame_tc, bg="black", fg="#00ff00", font=("Consolas", 10))
        self.txt_tc.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Načíst uložená data po zapnutí
        saved_tc = self.saved_data.get("enrolled_tc", "")
        if saved_tc:
            self.txt_tc.insert(tk.END, saved_tc + "\n")

    def log_uis(self, msg):
        self.root.after(0, lambda: [self.txt_uis.insert(tk.END, msg + "\n"), self.txt_uis.see(tk.END)])
        
    def log_tc(self, msg):
        self.root.after(0, lambda: [self.txt_tc.insert(tk.END, msg + "\n"), self.txt_tc.see(tk.END)])

    def start_fetch(self):
        self.txt_uis.delete('1.0', tk.END)
        self.txt_tc.delete('1.0', tk.END)
        threading.Thread(target=self.fetch_process, daemon=True).start()

    def save_results(self):
        """Uloží aktuálně vypsané termíny do config souboru"""
        data = {
            "enrolled_uis": self.txt_uis.get('1.0', tk.END).strip(),
            "enrolled_tc": self.txt_tc.get('1.0', tk.END).strip()
        }
        self.config.save(data)

    def fetch_process(self):
        try:
            command = EnrolledTermsCommand(
                credentials=Credentials(
                    username=self.e_user.get().strip(),
                    password=self.e_pass.get().strip(),
                ),
                tc_url=self.saved_data.get("tc_url", ""),
            )
            self.container.fetch_enrolled_terms.execute(
                command,
                CallbackLogger(self.log_uis),
                CallbackLogger(self.log_tc),
            )
        except Exception as e:
            self.log_uis(f"CHYBA: {e}")
            self.log_tc(f"CHYBA: {e}")
        finally:
            self.root.after(0, self.save_results)

if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()
