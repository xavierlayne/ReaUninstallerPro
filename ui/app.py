import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Dict, Any

from ..core import (
    scan_installed_programs, InstalledProgram, run_uninstaller_command,
    ResidualScanner, clean_residual_items, ResidualItem,
    ForceUninstaller,
    scan_uwp_apps, remove_uwp_app, UwpApp,
    scan_browser_extensions, delete_browser_extension, BrowserExtension,
    scan_startup_items, delete_startup_item, StartupItem,
    scan_software_health, fix_health_issues, HealthIssue,
    FileShredder,
    InstallSnapshot,
    REABridge
)

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

class ModernUninstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ReaUninstallerPro — by xavierlayne (github.com/xavierlayne)")
        self.geometry("1220x780")
        self.minsize(1020, 660)

        # Set Window Icon
        ico = resource_path("app.ico")
        if os.path.isfile(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        # High-End Modern Cyber Palette for ReaUninstallerPro
        self.colors = {
            "bg": "#090a0f",              # Ultra-deep luxury dark
            "sidebar": "#11131a",         # Sleek modern sidebar
            "sidebar_hover": "#1c202d",
            "sidebar_active": "#262b3d",
            "accent": "#6366f1",          # ReaUninstallerPro electric indigo/violet
            "accent_hover": "#4f46e5",
            "cyan": "#38bdf8",            # Cyber cyan
            "cyan_hover": "#0284c7",
            "purple": "#a855f7",          # Pro purple
            "card_bg": "#151822",         # Modern card surface
            "card_bg_alt": "#1c202d",
            "border": "#242938",
            "text": "#ffffff",
            "text_muted": "#8d95a5",
            "danger": "#f43f5e",          # Coral red
            "danger_hover": "#e11d48",
            "warning": "#f59e0b",
            "tree_bg": "#151822",
            "tree_alt": "#1a1e2b",
            "tree_fg": "#e2e8f0",
            "tree_select": "#6366f1"
        }
        self.configure(bg=self.colors["bg"])

        # States
        self.installed_programs: List[InstalledProgram] = []
        self.uwp_apps: List[UwpApp] = []
        self.browser_exts: List[BrowserExtension] = []
        self.startup_items: List[StartupItem] = []
        self.health_issues: List[HealthIssue] = []
        self.pre_install_snapshot = None

        self._init_styles()
        self._build_layout()

        self.show_programs_view()
        self.refresh_programs()

    def _init_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=self.colors["tree_bg"],
            foreground=self.colors["tree_fg"],
            fieldbackground=self.colors["tree_bg"],
            rowheight=35,
            font=("Segoe UI", 10),
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", "#1a382e")],
            foreground=[("selected", "#00c58e")]
        )
        style.configure(
            "Treeview.Heading",
            background="#20242e",
            foreground="#f8fafc",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat",
            padding=(8, 6)
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#282d3a")]
        )
        style.configure("Vertical.TScrollbar", background="#20242e", borderwidth=0, arrowcolor="#858c9e")

    def _build_layout(self):
        # 1. Header with Status Indicators
        header = tk.Frame(self, bg=self.colors["sidebar"], height=62, highlightthickness=1, highlightbackground=self.colors["border"])
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=self.colors["sidebar"])
        title_box.pack(side=tk.LEFT, padx=22)

        # Logo icon badge
        logo_badge = tk.Label(
            title_box,
            text=" R ",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg=self.colors["accent"],
            padx=7,
            pady=2
        )
        logo_badge.pack(side=tk.LEFT, padx=(0, 10))

        app_title = tk.Label(
            title_box,
            text="ReaUninstaller",
            font=("Segoe UI", 15, "bold"),
            fg="#ffffff",
            bg=self.colors["sidebar"]
        )
        app_title.pack(side=tk.LEFT)

        pro_badge = tk.Label(
            title_box,
            text=" PRO ",
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg=self.colors["purple"],
            padx=6,
            pady=2
        )
        pro_badge.pack(side=tk.LEFT, padx=(6, 12))

        app_sub = tk.Label(
            title_box,
            text="|  Derin Kaldırma, Akıllı Temizlik & Sistem Güvenliği",
            font=("Segoe UI", 9),
            fg=self.colors["text_muted"],
            bg=self.colors["sidebar"]
        )
        app_sub.pack(side=tk.LEFT)

        # Right status indicator
        status_box = tk.Frame(header, bg=self.colors["sidebar"])
        status_box.pack(side=tk.RIGHT, padx=22)

        # GitHub Author badge
        gh_btn = tk.Label(
            status_box,
            text="GitHub: xavierlayne",
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["cyan"],
            bg=self.colors["card_bg"],
            padx=10,
            pady=3,
            cursor="hand2"
        )
        gh_btn.pack(side=tk.LEFT, padx=(0, 14))
        gh_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/xavierlayne"))

        dot = tk.Canvas(status_box, width=10, height=10, bg=self.colors["sidebar"], highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=self.colors["accent"], outline="")
        dot.pack(side=tk.LEFT, padx=(0, 6))

        self.header_status = tk.Label(
            status_box,
            text="Sistem Koruması Aktif",
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["sidebar"]
        )
        self.header_status.pack(side=tk.LEFT)

        # 2. Main Body Container
        container = tk.Frame(self, bg=self.colors["bg"])
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left Sidebar
        self.sidebar = tk.Frame(container, bg=self.colors["sidebar"], width=240, highlightthickness=1, highlightbackground=self.colors["border"])
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.nav_buttons = {}
        nav_items = [
            ("programs", "  Tüm Programlar", self.show_programs_view),
            ("uwp", "  Windows Uygulamaları", self.show_uwp_view),
            ("browsers", "  Tarayıcı Eklentileri", self.show_browsers_view),
            ("health", "  Yazılım Sağlığı", self.show_health_view),
            ("startup", "  Başlangıç Yöneticisi", self.show_startup_view),
            ("tools", "  Zorla Kaldır & Araçlar", self.show_tools_view),
        ]

        tk.Label(
            self.sidebar,
            text="KONTROL PANELİ",
            font=("Segoe UI", 8, "bold"),
            fg=self.colors["text_muted"],
            bg=self.colors["sidebar"]
        ).pack(anchor=tk.W, padx=18, pady=(20, 8))

        for key, text, cmd in nav_items:
            f = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
            f.pack(fill=tk.X, padx=10, pady=2)

            # Left indicator bar
            bar = tk.Frame(f, bg=self.colors["sidebar"], width=4)
            bar.pack(side=tk.LEFT, fill=tk.Y)

            btn = tk.Button(
                f,
                text=text,
                font=("Segoe UI", 10),
                fg=self.colors["text_muted"],
                bg=self.colors["sidebar"],
                activebackground=self.colors["sidebar_hover"],
                activeforeground="#ffffff",
                anchor="w",
                padx=12,
                pady=10,
                bd=0,
                cursor="hand2",
                command=cmd
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.nav_buttons[key] = (btn, bar)

        # Author card in sidebar bottom
        author_frame = tk.Frame(self.sidebar, bg=self.colors["card_bg"], padx=12, pady=10, highlightthickness=1, highlightbackground=self.colors["border"])
        author_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 14))

        tk.Label(author_frame, text="YAPIMCI & GELİŞTİRİCİ", font=("Segoe UI", 8, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        dev_link = tk.Label(author_frame, text="github.com/xavierlayne", font=("Segoe UI", 8, "underline"), fg=self.colors["cyan"], bg=self.colors["card_bg"], cursor="hand2")
        dev_link.pack(anchor=tk.W, pady=(2, 0))
        dev_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/xavierlayne"))

        # Info card in sidebar bottom
        info_frame = tk.Frame(self.sidebar, bg=self.colors["card_bg"], padx=14, pady=12, highlightthickness=1, highlightbackground=self.colors["border"])
        info_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 8))

        tk.Label(info_frame, text="Akıllı Güvenlik Laboratuvarı", font=("Segoe UI", 9, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(
            info_frame,
            text="Gelişmiş ikili dosya inceleme ve derin sistem analiz motoruyla yazılımları tam kontrol altında tutun.",
            font=("Segoe UI", 8),
            fg=self.colors["text_muted"],
            bg=self.colors["card_bg"],
            wraplength=190,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(4, 0))

        # Right Content View Area
        self.content_area = tk.Frame(container, bg=self.colors["bg"])
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def _set_active_nav(self, active_key: str):
        for key, (btn, bar) in self.nav_buttons.items():
            if key == active_key:
                btn.configure(bg=self.colors["sidebar_active"], fg=self.colors["accent"], font=("Segoe UI", 10, "bold"))
                bar.configure(bg=self.colors["accent"])
            else:
                btn.configure(bg=self.colors["sidebar"], fg=self.colors["text_muted"], font=("Segoe UI", 10))
                bar.configure(bg=self.colors["sidebar"])

    def _clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def _create_stat_card(self, parent, title: str, value: str, subtext: str, color: str = "#00c58e"):
        card = tk.Frame(parent, bg=self.colors["card_bg"], padx=16, pady=12, highlightthickness=1, highlightbackground=self.colors["border"])
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg=self.colors["text_muted"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(card, text=value, font=("Segoe UI", 16, "bold"), fg=color, bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=(2, 0))
        tk.Label(card, text=subtext, font=("Segoe UI", 8), fg=self.colors["text_muted"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        return card

    # ==========================================
    # VIEW 1: PROGRAMS (TÜM PROGRAMLAR)
    # ==========================================
    def show_programs_view(self):
        self._set_active_nav("programs")
        self._clear_content()

        # Top Stat Cards
        stats_frame = tk.Frame(self.content_area, bg=self.colors["bg"])
        stats_frame.pack(fill=tk.X, padx=18, pady=(16, 8))

        total_progs = len(self.installed_programs)
        large_progs = sum(1 for p in self.installed_programs if p.size_kb > 100 * 1024)
        total_size_mb = sum(p.size_kb for p in self.installed_programs) // 1024
        size_str = f"{total_size_mb / 1024:.1f} GB" if total_size_mb > 1024 else f"{total_size_mb} MB"

        self._create_stat_card(stats_frame, "TOPLAM YAZILIM", str(total_progs or "..."), "Kayıtlı uygulama", self.colors["text"])
        self._create_stat_card(stats_frame, "BÜYÜK BOYUTLU", str(large_progs or "..."), ">100 MB programlar", self.colors["warning"])
        self._create_stat_card(stats_frame, "KAPLANAN ALAN", size_str if total_progs else "...", "Tahmini disk boyutu", self.colors["accent"])

        # Action and filter bar
        action_bar = tk.Frame(self.content_area, bg=self.colors["bg"], pady=12, padx=18)
        action_bar.pack(fill=tk.X)

        tk.Label(action_bar, text="Ara:", font=("Segoe UI", 10), fg=self.colors["text_muted"], bg=self.colors["bg"]).pack(side=tk.LEFT, padx=(0, 6))
        self.prog_search_var = tk.StringVar()
        self.prog_search_var.trace_add("write", lambda *args: self._filter_programs_table())
        search_entry = tk.Entry(
            action_bar,
            textvariable=self.prog_search_var,
            font=("Segoe UI", 10),
            bg=self.colors["card_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            width=24
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 14), ipady=5)

        self.prog_filter_var = tk.StringVar(value="Tümü")
        filter_cb = ttk.Combobox(
            action_bar,
            textvariable=self.prog_filter_var,
            values=["Tümü", "Büyük Boyutlu (>100MB)", "Son Yüklenenler"],
            state="readonly",
            width=22
        )
        filter_cb.pack(side=tk.LEFT, padx=(0, 14))
        filter_cb.bind("<<ComboboxSelected>>", lambda e: self._filter_programs_table())

        btn_refresh = tk.Button(action_bar, text="Yenile", font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=self.refresh_programs)
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_rea = tk.Button(action_bar, text="Derin İncele", font=("Segoe UI", 9, "bold"), bg=self.colors["cyan_hover"], fg="#ffffff", bd=0, padx=14, pady=6, cursor="hand2", command=self.inspect_selected_rea)
        btn_rea.pack(side=tk.RIGHT, padx=4)

        btn_residuals = tk.Button(action_bar, text="Kalıntı Ara", font=("Segoe UI", 9, "bold"), bg=self.colors["accent"], fg="#ffffff", bd=0, padx=14, pady=6, cursor="hand2", command=self.scan_selected_residuals)
        btn_residuals.pack(side=tk.RIGHT, padx=4)

        btn_uninstall = tk.Button(action_bar, text="Kaldır", font=("Segoe UI", 9, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=self.uninstall_selected_program)
        btn_uninstall.pack(side=tk.RIGHT, padx=4)

        # Table container
        table_frame = tk.Frame(self.content_area, bg=self.colors["bg"], padx=18)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        cols = ("name", "version", "publisher", "size", "date")
        self.prog_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        self.prog_tree.heading("name", text="Program Adı", anchor=tk.W)
        self.prog_tree.heading("version", text="Sürüm", anchor=tk.W)
        self.prog_tree.heading("publisher", text="Yayıncı", anchor=tk.W)
        self.prog_tree.heading("size", text="Boyut", anchor=tk.E)
        self.prog_tree.heading("date", text="Yükleme Tarihi", anchor=tk.CENTER)

        self.prog_tree.column("name", width=340, anchor=tk.W)
        self.prog_tree.column("version", width=120, anchor=tk.W)
        self.prog_tree.column("publisher", width=180, anchor=tk.W)
        self.prog_tree.column("size", width=100, anchor=tk.E)
        self.prog_tree.column("date", width=110, anchor=tk.CENTER)

        self.prog_tree.tag_configure("even", background=self.colors["tree_bg"])
        self.prog_tree.tag_configure("odd", background=self.colors["tree_alt"])

        # Context Menu
        self.prog_menu = tk.Menu(self, tearoff=0, bg=self.colors["sidebar"], fg=self.colors["text"], activebackground=self.colors["accent"], activeforeground="#ffffff")
        self.prog_menu.add_command(label="Kaldır", command=self.uninstall_selected_program)
        self.prog_menu.add_command(label="Kalıntı Taraması Yap", command=self.scan_selected_residuals)
        self.prog_menu.add_separator()
        self.prog_menu.add_command(label="Kurulum Klasörünü Aç (Gezgin)", command=self.open_selected_folder)
        self.prog_menu.add_separator()
        self.prog_menu.add_command(label="İncele: Detect It Easy ile Analiz Et", command=lambda: self.launch_rea_for_selected("die"))
        self.prog_menu.add_command(label="İncele: dnSpy ile .NET Kaynak Kodunu Aç", command=lambda: self.launch_rea_for_selected("dnspy"))
        self.prog_menu.add_command(label="İncele: x64dbg ile Makine Kodunu Ayrıştır", command=lambda: self.launch_rea_for_selected("x64dbg"))

        self.prog_tree.bind("<Button-3>", self._show_prog_context_menu)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.prog_tree.yview)
        self.prog_tree.configure(yscrollcommand=scroll_y.set)

        self.prog_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self._filter_programs_table()

    def _show_prog_context_menu(self, event):
        item = self.prog_tree.identify_row(event.y)
        if item:
            self.prog_tree.selection_set(item)
            self.prog_menu.post(event.x_root, event.y_root)

    def refresh_programs(self):
        self.header_status.config(text="Programlar taranıyor...")
        def _task():
            progs = scan_installed_programs()
            self.installed_programs = progs
            self.after(0, lambda: self._on_programs_scanned(len(progs)))
        threading.Thread(target=_task, daemon=True).start()

    def _on_programs_scanned(self, count):
        self.header_status.config(text=f"{count} kurulu program bulundu.")
        self._filter_programs_table()

    def _filter_programs_table(self):
        if not hasattr(self, "prog_tree") or not self.prog_tree.winfo_exists():
            return

        for row in self.prog_tree.get_children():
            self.prog_tree.delete(row)

        search_q = self.prog_search_var.get().lower().strip()
        filter_mode = self.prog_filter_var.get()

        for idx, prog in enumerate(self.installed_programs):
            if filter_mode == "Büyük Boyutlu (>100MB)" and prog.size_kb < 100 * 1024:
                continue
            if search_q and search_q not in prog.name.lower() and search_q not in prog.publisher.lower():
                continue

            tag = "even" if idx % 2 == 0 else "odd"
            self.prog_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(prog.name, prog.version or "-", prog.publisher or "-", prog.formatted_size, prog.formatted_date),
                tags=(tag,)
            )

    def _get_selected_programs(self) -> List[InstalledProgram]:
        selected = self.prog_tree.selection()
        if not selected:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen listeden bir veya daha fazla program seçin.")
            return []
        return [self.installed_programs[int(s)] for s in selected]

    def open_selected_folder(self):
        progs = self._get_selected_programs()
        if not progs:
            return
        loc = progs[0].install_location
        if loc and os.path.isdir(loc):
            import subprocess
            subprocess.Popen(["explorer.exe", loc])
        else:
            messagebox.showinfo("Konum Yok", "Bu programın kayıtlı bir kurulum klasörü bulunamadı.")

    def _find_prog_exe(self, prog: InstalledProgram) -> Optional[str]:
        if prog.install_location and os.path.isdir(prog.install_location):
            for root, _, files in os.walk(prog.install_location):
                for f in files:
                    if f.lower().endswith(".exe"):
                        return os.path.join(root, f)
        return None

    def launch_rea_for_selected(self, tool_name: str):
        progs = self._get_selected_programs()
        if not progs:
            return
        prog = progs[0]
        exe_file = self._find_prog_exe(prog)
        if exe_file:
            REABridge.launch_tool(tool_name, exe_file)
            self.header_status.config(text=f"{tool_name.upper()} başlatıldı: {os.path.basename(exe_file)}")
        else:
            REABridge.launch_tool(tool_name)

    def inspect_selected_rea(self):
        progs = self._get_selected_programs()
        if not progs:
            return
        prog = progs[0]
        exe_file = self._find_prog_exe(prog)

        if not exe_file:
            exe_file = filedialog.askopenfilename(title=f"'{prog.name}' için İncelenecek .EXE Dosyasını Seçin", filetypes=[("Executable", "*.exe;*.dll")])
            if not exe_file:
                return

        info = REABridge.inspect_binary_quick(exe_file)
        msg = (
            f"İkili Dosya Ön Analizi (PE Telemetrisi):\n\n"
            f"Dosya: {os.path.basename(exe_file)}\n"
            f"Mimari: {info['architecture']}\n"
            f"Alt Sistem: {info['subsystem']}\n"
            f".NET / CLR Runtime: {'EVET' if info['has_dotnet'] else 'Hayır'}\n"
            f"Paketleyici (Packer) Şüphesi: {'YÜKSEK (Yüksek Entropi)' if info['is_packed'] else 'Normal'}\n"
            f"Bölümler: {', '.join(info['sections'][:4])}\n\n"
            "Bu dosyayı harici inceleme araçlarıyla açmak ister misiniz?"
        )

        dlg = tk.Toplevel(self)
        dlg.title(f"Derin Güvenlik & Dosya Analizi — {prog.name}")
        dlg.geometry("560x360")
        dlg.configure(bg=self.colors["bg"])
        dlg.transient(self)

        tk.Label(dlg, text="İkili Dosya Güvenlik & Mimari Raporu", font=("Segoe UI", 12, "bold"), fg=self.colors["cyan"], bg=self.colors["bg"]).pack(anchor=tk.W, padx=20, pady=(16, 8))
        txt = tk.Text(dlg, font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=12, height=10)
        txt.insert("1.0", msg)
        txt.configure(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True, padx=20)

        btn_row = tk.Frame(dlg, bg=self.colors["bg"], pady=12, padx=20)
        btn_row.pack(fill=tk.X)

        tk.Button(btn_row, text="Detect It Easy ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg=self.colors["cyan"], bd=0, padx=12, pady=6, cursor="hand2", command=lambda: [REABridge.launch_tool("die", exe_file), dlg.destroy()]).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text="dnSpy (.NET) ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg=self.colors["accent"], bd=0, padx=12, pady=6, cursor="hand2", command=lambda: [REABridge.launch_tool("dnspy", exe_file), dlg.destroy()]).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text="x64dbg ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=lambda: [REABridge.launch_tool("x64dbg", exe_file), dlg.destroy()]).pack(side=tk.LEFT, padx=4)

    def uninstall_selected_program(self):
        progs = self._get_selected_programs()
        if not progs:
            return

        if len(progs) == 1:
            prog = progs[0]
            ans = messagebox.askyesnocancel(
                "Kaldırma Onayı",
                f"'{prog.name}' programını kaldırmak istiyor musunuz?\n\n"
                f"Evet: Resmi kaldırıcıyı çalıştırır ve bittikten sonra derin kalıntı taraması yapar.\n"
                f"Hayır: Doğrudan derin kalıntı taraması yapar (kaldırıcı bozuksa kullanın)."
            )
            if ans is None:
                return

            if ans is True:
                if not prog.uninstall_string:
                    messagebox.showerror("Kaldırıcı Bulunamadı", "Bu program için standart kaldırma komutu kayıtlı değil. Doğrudan 'Zorla Kaldır' veya 'Kalıntı Ara' seçeneğini kullanabilirsiniz.")
                    return

                self.header_status.config(text=f"'{prog.name}' kaldırılıyor...")
                def _run():
                    try:
                        proc = run_uninstaller_command(prog.uninstall_string)
                        proc.wait()
                        self.after(0, lambda: self._prompt_residuals_cleanup(prog))
                    except Exception as e:
                        self.after(0, lambda: messagebox.showerror("Hata", f"Kaldırma başlatılamadı: {e}"))
                threading.Thread(target=_run, daemon=True).start()
            else:
                self._prompt_residuals_cleanup(prog)
        else:
            names = "\n".join(f"- {p.name}" for p in progs[:8])
            if len(progs) > 8:
                names += f"\n... ve {len(progs) - 8} program daha"
            if not messagebox.askyesno("Toplu Kaldırma Onayı", f"Seçilen {len(progs)} program sırayla kaldırılacaktır:\n\n{names}\n\nDevam edilsin mi?"):
                return

            def _batch():
                for p in progs:
                    if p.uninstall_string:
                        self.after(0, lambda name=p.name: self.header_status.config(text=f"Kaldırılıyor: {name}..."))
                        try:
                            proc = run_uninstaller_command(p.uninstall_string, quiet=True)
                            proc.wait()
                        except Exception:
                            pass
                self.after(0, self.refresh_programs)
                self.after(0, lambda: messagebox.showinfo("Tamamlandı", f"{len(progs)} program için toplu kaldırma işlemi tamamlandı."))
            threading.Thread(target=_batch, daemon=True).start()

    def scan_selected_residuals(self):
        progs = self._get_selected_programs()
        if not progs:
            return
        self._prompt_residuals_cleanup(progs[0])

    def _prompt_residuals_cleanup(self, prog: InstalledProgram):
        self.header_status.config(text=f"'{prog.name}' kalıntıları taranıyor...")
        def _scan():
            residuals = ResidualScanner.scan_for_program(prog.name, prog.publisher, prog.install_location)
            self.after(0, lambda: self._show_residuals_dialog(prog.name, residuals))
        threading.Thread(target=_scan, daemon=True).start()

    def _show_residuals_dialog(self, app_name: str, residuals: List[ResidualItem]):
        self.header_status.config(text="Kalıntı taraması tamamlandı.")
        if not residuals:
            messagebox.showinfo("Kalıntı Yok", f"'{app_name}' için hiçbir artık dosya veya kayıt defteri anahtarı bulunamadı. Sistem tertemiz!")
            self.refresh_programs()
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Kalıntı Temizliği — {app_name}")
        dlg.geometry("760x540")
        dlg.configure(bg=self.colors["bg"])
        dlg.transient(self)
        dlg.grab_set()

        lbl = tk.Label(dlg, text=f"'{app_name}' için {len(residuals)} kalıntı tespit edildi:", font=("Segoe UI", 11, "bold"), fg=self.colors["accent"], bg=self.colors["bg"])
        lbl.pack(anchor=tk.W, padx=20, pady=(16, 8))

        list_frame = tk.Frame(dlg, bg=self.colors["bg"], padx=20)
        list_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("type", "path", "details")
        tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        tree.heading("type", text="Tür", anchor=tk.W)
        tree.heading("path", text="Konum / Kayıt Defteri", anchor=tk.W)
        tree.heading("details", text="Açıklama", anchor=tk.W)
        tree.column("type", width=120, anchor=tk.W)
        tree.column("path", width=400, anchor=tk.W)
        tree.column("details", width=180, anchor=tk.W)

        for i, item in enumerate(residuals):
            tree.insert("", tk.END, iid=str(i), values=(item.item_type, item.path, item.details))

        sc = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sc.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

        btn_bar = tk.Frame(dlg, bg=self.colors["bg"], pady=14, padx=20)
        btn_bar.pack(fill=tk.X)

        def _do_clean():
            ans = messagebox.askyesno("Kalıntıları Sil", f"Listelenen {len(residuals)} kalıntıyı kalıcı olarak silmek istediğinizden emin misiniz?", parent=dlg)
            if not ans:
                return
            success, fail, errors = clean_residual_items(residuals)
            dlg.destroy()
            msg = f"Kalıntı temizleme tamamlandı:\n- Başarıyla silinen: {success}"
            if fail > 0:
                msg += f"\n- Silinemeyen: {fail}"
            messagebox.showinfo("Sonuç", msg)
            self.refresh_programs()

        btn_clean = tk.Button(btn_bar, text="Tüm Kalıntıları Temizle", font=("Segoe UI", 10, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=_do_clean)
        btn_clean.pack(side=tk.RIGHT)

        btn_cancel = tk.Button(btn_bar, text="İptal", font=("Segoe UI", 10), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=16, pady=6, cursor="hand2", command=dlg.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=8)

    # ==========================================
    # VIEW 2: WINDOWS APPS / BLOATWARE
    # ==========================================
    def show_uwp_view(self):
        self._set_active_nav("uwp")
        self._clear_content()

        # Stat cards
        stats_frame = tk.Frame(self.content_area, bg=self.colors["bg"])
        stats_frame.pack(fill=tk.X, padx=18, pady=(16, 8))

        total_uwp = len(self.uwp_apps)
        rec_uwp = sum(1 for a in self.uwp_apps if a.is_recommended_removal)
        crit_uwp = sum(1 for a in self.uwp_apps if a.is_critical_system)

        self._create_stat_card(stats_frame, "TOPLAM PAKET", str(total_uwp or "..."), "Windows Store / Yerleşik", self.colors["text"])
        self._create_stat_card(stats_frame, "ÖNERİLEN (BLOATWARE)", str(rec_uwp or "..."), "Güvenle kaldırılabilir", self.colors["accent"])
        self._create_stat_card(stats_frame, "ÖNERİLMEZ (SİSTEM)", str(crit_uwp or "..."), "Temel sistem dosyası", self.colors["danger"])

        action_bar = tk.Frame(self.content_area, bg=self.colors["bg"], pady=12, padx=18)
        action_bar.pack(fill=tk.X)

        tk.Label(action_bar, text="Kategori Filtresi:", font=("Segoe UI", 10), fg=self.colors["text_muted"], bg=self.colors["bg"]).pack(side=tk.LEFT, padx=(0, 6))
        self.uwp_filter_var = tk.StringVar(value="Tümü")
        uwp_cb = ttk.Combobox(
            action_bar,
            textvariable=self.uwp_filter_var,
            values=["Tümü", "Önerilenler (Gereksiz Bloatware)", "Önerilmez (Kritik Sistem)", "Standart Uygulamalar"],
            state="readonly",
            width=28
        )
        uwp_cb.pack(side=tk.LEFT, padx=(0, 16))
        uwp_cb.bind("<<ComboboxSelected>>", lambda e: self._render_uwp_table())

        btn_refresh = tk.Button(action_bar, text="Yenile", font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=self.refresh_uwp)
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_batch_rec = tk.Button(action_bar, text="Önerilenleri Toplu Kaldır", font=("Segoe UI", 9, "bold"), bg=self.colors["accent"], fg="#0d0f12", bd=0, padx=14, pady=6, cursor="hand2", command=self.remove_all_recommended_uwp)
        btn_batch_rec.pack(side=tk.RIGHT, padx=4)

        btn_remove = tk.Button(action_bar, text="Seçileni Kaldır", font=("Segoe UI", 9, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=self.remove_selected_uwp)
        btn_remove.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(self.content_area, bg=self.colors["bg"], padx=18)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        cols = ("name", "category", "version", "publisher")
        self.uwp_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="extended")
        self.uwp_tree.heading("name", text="Uygulama Adı", anchor=tk.W)
        self.uwp_tree.heading("category", text="Güvenlik Durumu / Kategori", anchor=tk.CENTER)
        self.uwp_tree.heading("version", text="Sürüm", anchor=tk.W)
        self.uwp_tree.heading("publisher", text="Yayıncı Kimliği", anchor=tk.W)

        self.uwp_tree.column("name", width=280, anchor=tk.W)
        self.uwp_tree.column("category", width=220, anchor=tk.CENTER)
        self.uwp_tree.column("version", width=120, anchor=tk.W)
        self.uwp_tree.column("publisher", width=340, anchor=tk.W)

        self.uwp_tree.tag_configure("recommended", foreground="#00c58e")
        self.uwp_tree.tag_configure("critical", foreground="#ef4444")
        self.uwp_tree.tag_configure("standard", foreground="#e2e8f0")

        sc = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.uwp_tree.yview)
        self.uwp_tree.configure(yscrollcommand=sc.set)
        self.uwp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_uwp()

    def refresh_uwp(self):
        self.header_status.config(text="Windows uygulamaları taranıyor...")
        def _task():
            apps = scan_uwp_apps()
            self.uwp_apps = apps
            self.after(0, self._render_uwp_table)
        threading.Thread(target=_task, daemon=True).start()

    def _render_uwp_table(self):
        if not hasattr(self, "uwp_tree") or not self.uwp_tree.winfo_exists():
            return
        for r in self.uwp_tree.get_children():
            self.uwp_tree.delete(r)

        filter_mode = self.uwp_filter_var.get()
        visible_count = 0

        for i, app in enumerate(self.uwp_apps):
            if filter_mode == "Önerilenler (Gereksiz Bloatware)" and not app.is_recommended_removal:
                continue
            if filter_mode == "Önerilmez (Kritik Sistem)" and not app.is_critical_system:
                continue
            if filter_mode == "Standart Uygulamalar" and (app.is_recommended_removal or app.is_critical_system):
                continue

            if app.is_critical_system:
                tag = "critical"
            elif app.is_recommended_removal:
                tag = "recommended"
            else:
                tag = "standard"

            self.uwp_tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(app.display_name, app.category_status, app.version, app.publisher),
                tags=(tag,)
            )
            visible_count += 1

        rec_count = sum(1 for a in self.uwp_apps if a.is_recommended_removal)
        crit_count = sum(1 for a in self.uwp_apps if a.is_critical_system)
        self.header_status.config(text=f"{visible_count} uygulama gösteriliyor ({rec_count} Önerilen, {crit_count} Sistem).")

    def remove_selected_uwp(self):
        selected_iids = self.uwp_tree.selection()
        if not selected_iids:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen kaldırılacak Windows uygulamasını seçin.")
            return

        selected_apps = [self.uwp_apps[int(iid)] for iid in selected_iids]

        has_critical = any(a.is_critical_system for a in selected_apps)
        if has_critical:
            crit_names = [a.display_name for a in selected_apps if a.is_critical_system]
            warn_msg = (
                "DİKKAT — KRİTİK SİSTEM UYARISI!\n\n"
                f"Seçtiğiniz uygulamalar arasında temel sistem dosyası bulunuyor:\n- " + "\n- ".join(crit_names[:5]) +
                "\n\nBu bileşenlerin silinmesi Windows'un kararsız çalışmasına neden olabilir. Yine de devam etmek istiyor musunuz?"
            )
            if not messagebox.askyesno("Kritik Sistem Dosyası", warn_msg, icon="warning"):
                return
        else:
            if len(selected_apps) == 1:
                if not messagebox.askyesno("Onay", f"'{selected_apps[0].display_name}' uygulamasını kaldırmak istiyor musunuz?"):
                    return
            else:
                if not messagebox.askyesno("Onay", f"Seçilen {len(selected_apps)} uygulamayı kaldırmak istiyor musunuz?"):
                    return

        def _remove_worker():
            for app in selected_apps:
                self.after(0, lambda name=app.display_name: self.header_status.config(text=f"'{name}' kaldırılıyor..."))
                remove_uwp_app(app.package_full_name)
            self.after(0, self.refresh_uwp)
            self.after(0, lambda: messagebox.showinfo("Tamamlandı", f"{len(selected_apps)} uygulama başarıyla kaldırıldı."))
        threading.Thread(target=_remove_worker, daemon=True).start()

    def remove_all_recommended_uwp(self):
        rec_apps = [a for a in self.uwp_apps if a.is_recommended_removal]
        if not rec_apps:
            messagebox.showinfo("Durum Tertemiz", "Sisteminizde kaldırılması önerilen gereksiz bloatware uygulaması bulunmuyor!")
            return

        app_list = "\n".join(f"- {a.display_name}" for a in rec_apps[:12])
        if len(rec_apps) > 12:
            app_list += f"\n... ve {len(rec_apps) - 12} uygulama daha"

        confirm = messagebox.askyesno(
            "Önerilenleri Toplu Kaldır",
            f"Tespit edilen {len(rec_apps)} adet gereksiz bloatware uygulaması sistemden güvenle temizlenecek:\n\n"
            f"{app_list}\n\n"
            "Tümünü kaldırmak istiyor musunuz?"
        )
        if not confirm:
            return

        def _batch_remove():
            for app in rec_apps:
                self.after(0, lambda name=app.display_name: self.header_status.config(text=f"Kaldırılıyor: {name}..."))
                remove_uwp_app(app.package_full_name)
            self.after(0, self.refresh_uwp)
            self.after(0, lambda: messagebox.showinfo("Temizlendi", f"{len(rec_apps)} adet önerilen bloatware uygulaması başarıyla temizlendi."))
        threading.Thread(target=_batch_remove, daemon=True).start()

    # ==========================================
    # VIEW 3: BROWSER EXTENSIONS
    # ==========================================
    def show_browsers_view(self):
        self._set_active_nav("browsers")
        self._clear_content()

        action_bar = tk.Frame(self.content_area, bg=self.colors["bg"], pady=14, padx=18)
        action_bar.pack(fill=tk.X)

        tk.Label(action_bar, text="Tarayıcı Eklentileri & Eklenti Temizliği", font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["bg"]).pack(side=tk.LEFT)

        btn_refresh = tk.Button(action_bar, text="Yenile", font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=self.refresh_browsers)
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_remove = tk.Button(action_bar, text="Eklentiyi Kaldır", font=("Segoe UI", 9, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=self.remove_selected_extension)
        btn_remove.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(self.content_area, bg=self.colors["bg"], padx=18)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        cols = ("browser", "name", "version", "id")
        self.browser_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        self.browser_tree.heading("browser", text="Tarayıcı", anchor=tk.W)
        self.browser_tree.heading("name", text="Eklenti Adı", anchor=tk.W)
        self.browser_tree.heading("version", text="Sürüm", anchor=tk.CENTER)
        self.browser_tree.heading("id", text="Eklenti ID", anchor=tk.W)

        self.browser_tree.column("browser", width=140, anchor=tk.W)
        self.browser_tree.column("name", width=340, anchor=tk.W)
        self.browser_tree.column("version", width=100, anchor=tk.CENTER)
        self.browser_tree.column("id", width=260, anchor=tk.W)

        sc = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.browser_tree.yview)
        self.browser_tree.configure(yscrollcommand=sc.set)
        self.browser_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_browsers()

    def refresh_browsers(self):
        self.header_status.config(text="Tarayıcı eklentileri taranıyor...")
        def _task():
            exts = scan_browser_extensions()
            self.browser_exts = exts
            self.after(0, self._render_browsers_table)
        threading.Thread(target=_task, daemon=True).start()

    def _render_browsers_table(self):
        if not hasattr(self, "browser_tree") or not self.browser_tree.winfo_exists():
            return
        for r in self.browser_tree.get_children():
            self.browser_tree.delete(r)

        for i, ext in enumerate(self.browser_exts):
            self.browser_tree.insert("", tk.END, iid=str(i), values=(ext.browser, ext.name, ext.version, ext.ext_id))
        self.header_status.config(text=f"{len(self.browser_exts)} tarayıcı eklentisi bulundu.")

    def remove_selected_extension(self):
        sel = self.browser_tree.selection()
        if not sel:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen silinecek eklentiyi seçin.")
            return
        ext = self.browser_exts[int(sel[0])]
        if not messagebox.askyesno("Onay", f"'{ext.name}' eklentisini {ext.browser} tarayıcısından silmek istiyor musunuz?"):
            return

        if delete_browser_extension(ext.folder_path):
            messagebox.showinfo("Başarılı", f"'{ext.name}' eklentisi başarıyla kaldırıldı.")
            self.refresh_browsers()
        else:
            messagebox.showerror("Hata", "Eklenti dosyaları silinemedi. Tarayıcının kapalı olduğundan emin olun.")

    # ==========================================
    # VIEW 4: SOFTWARE HEALTH (YAZILIM SAĞLIĞI)
    # ==========================================
    def show_health_view(self):
        self._set_active_nav("health")
        self._clear_content()

        stats_frame = tk.Frame(self.content_area, bg=self.colors["bg"])
        stats_frame.pack(fill=tk.X, padx=18, pady=(16, 8))

        total_issues = len(self.health_issues)
        broken_links = sum(1 for h in self.health_issues if h.category == "Bozuk Kısayol")
        temp_leftovers = total_issues - broken_links

        self._create_stat_card(stats_frame, "TOPLAM KALINTI", str(total_issues or "..."), "Temizlenebilir öğe", self.colors["warning"])
        self._create_stat_card(stats_frame, "BOZUK KISAYOLLAR", str(broken_links or "..."), "Hedefi silinmiş .lnk", self.colors["text"])
        self._create_stat_card(stats_frame, "GEÇİCİ DOSYALAR", str(temp_leftovers or "..."), "Kurulum artıkları", self.colors["accent"])

        action_bar = tk.Frame(self.content_area, bg=self.colors["bg"], pady=12, padx=18)
        action_bar.pack(fill=tk.X)

        tk.Label(action_bar, text="Yazılım Sağlığı ve Sistem Temizliği", font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["bg"]).pack(side=tk.LEFT)

        btn_refresh = tk.Button(action_bar, text="Taramayı Yenile", font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=self.refresh_health)
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_fix = tk.Button(action_bar, text="Tümünü Temizle / Onar", font=("Segoe UI", 9, "bold"), bg=self.colors["accent"], fg="#0d0f12", bd=0, padx=16, pady=6, cursor="hand2", command=self.fix_health)
        btn_fix.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(self.content_area, bg=self.colors["bg"], padx=18)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        cols = ("cat", "title", "path", "size")
        self.health_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        self.health_tree.heading("cat", text="Sorun Türü", anchor=tk.W)
        self.health_tree.heading("title", text="Başlık / Açıklama", anchor=tk.W)
        self.health_tree.heading("path", text="Dosya Yolu", anchor=tk.W)
        self.health_tree.heading("size", text="Boyut", anchor=tk.E)

        self.health_tree.column("cat", width=140, anchor=tk.W)
        self.health_tree.column("title", width=280, anchor=tk.W)
        self.health_tree.column("path", width=360, anchor=tk.W)
        self.health_tree.column("size", width=90, anchor=tk.E)

        sc = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.health_tree.yview)
        self.health_tree.configure(yscrollcommand=sc.set)
        self.health_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_health()

    def refresh_health(self):
        self.header_status.config(text="Sistem sağlık taraması yapılıyor...")
        def _task():
            issues = scan_software_health()
            self.health_issues = issues
            self.after(0, self._render_health_table)
        threading.Thread(target=_task, daemon=True).start()

    def _render_health_table(self):
        if not hasattr(self, "health_tree") or not self.health_tree.winfo_exists():
            return
        for r in self.health_tree.get_children():
            self.health_tree.delete(r)

        for i, iss in enumerate(self.health_issues):
            self.health_tree.insert("", tk.END, iid=str(i), values=(iss.category, iss.title, iss.path, iss.formatted_size))
        self.header_status.config(text=f"{len(self.health_issues)} sağlık sorunu / kalıntı bulundu.")

    def fix_health(self):
        if not self.health_issues:
            messagebox.showinfo("Durum Mükemmel", "Temizlenecek veya onarılacak herhangi bir sorun bulunamadı.")
            return

        if not messagebox.askyesno("Onay", f"Listelenen {len(self.health_issues)} adet artık ve bozuk kısayol temizlensin mi?"):
            return

        fixed = fix_health_issues(self.health_issues)
        messagebox.showinfo("Tamamlandı", f"{fixed} adet sorun başarıyla temizlendi.")
        self.refresh_health()

    # ==========================================
    # VIEW 5: STARTUP MANAGER (BAŞLANGIÇ YÖNETİCİSİ)
    # ==========================================
    def show_startup_view(self):
        self._set_active_nav("startup")
        self._clear_content()

        action_bar = tk.Frame(self.content_area, bg=self.colors["bg"], pady=14, padx=18)
        action_bar.pack(fill=tk.X)

        tk.Label(action_bar, text="Windows Başlangıç Programları", font=("Segoe UI", 11, "bold"), fg=self.colors["text"], bg=self.colors["bg"]).pack(side=tk.LEFT)

        btn_refresh = tk.Button(action_bar, text="Yenile", font=("Segoe UI", 9), bg=self.colors["card_bg"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=self.refresh_startup)
        btn_refresh.pack(side=tk.RIGHT, padx=4)

        btn_remove = tk.Button(action_bar, text="Başlangıçtan Kaldır", font=("Segoe UI", 9, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=self.remove_selected_startup)
        btn_remove.pack(side=tk.RIGHT, padx=4)

        table_frame = tk.Frame(self.content_area, bg=self.colors["bg"], padx=18)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        cols = ("name", "loc", "cmd")
        self.startup_tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        self.startup_tree.heading("name", text="Öğe Adı", anchor=tk.W)
        self.startup_tree.heading("loc", text="Konum", anchor=tk.W)
        self.startup_tree.heading("cmd", text="Komut / Hedef", anchor=tk.W)

        self.startup_tree.column("name", width=220, anchor=tk.W)
        self.startup_tree.column("loc", width=180, anchor=tk.W)
        self.startup_tree.column("cmd", width=440, anchor=tk.W)

        sc = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.startup_tree.yview)
        self.startup_tree.configure(yscrollcommand=sc.set)
        self.startup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sc.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_startup()

    def refresh_startup(self):
        self.header_status.config(text="Başlangıç programları taranıyor...")
        def _task():
            items = scan_startup_items()
            self.startup_items = items
            self.after(0, self._render_startup_table)
        threading.Thread(target=_task, daemon=True).start()

    def _render_startup_table(self):
        if not hasattr(self, "startup_tree") or not self.startup_tree.winfo_exists():
            return
        for r in self.startup_tree.get_children():
            self.startup_tree.delete(r)

        for i, item in enumerate(self.startup_items):
            self.startup_tree.insert("", tk.END, iid=str(i), values=(item.name, item.location_type, item.command))
        self.header_status.config(text=f"{len(self.startup_items)} başlangıç öğesi kayıtlı.")

    def remove_selected_startup(self):
        sel = self.startup_tree.selection()
        if not sel:
            messagebox.showwarning("Seçim Yapılmadı", "Lütfen başlangıçtan silinecek öğeyi seçin.")
            return
        item = self.startup_items[int(sel[0])]
        if not messagebox.askyesno("Onay", f"'{item.name}' öğesini başlangıçtan kaldırmak istiyor musunuz?"):
            return

        if delete_startup_item(item):
            messagebox.showinfo("Başarılı", f"'{item.name}' başlangıçtan kaldırıldı.")
            self.refresh_startup()
        else:
            messagebox.showerror("Hata", "Kayıt defteri veya dosya silinemedi.")

    # ==========================================
    # VIEW 6: TOOLS (ZORLA KALDIR, DOSYA PARÇALAYICI, KURULUM İZLEYİCİ)
    # ==========================================
    def show_tools_view(self):
        self._set_active_nav("tools")
        self._clear_content()

        scroll_canvas = tk.Canvas(self.content_area, bg=self.colors["bg"], bd=0, highlightthickness=0)
        scroll_bar = ttk.Scrollbar(self.content_area, orient="vertical", command=scroll_canvas.yview)
        scrollable_frame = tk.Frame(scroll_canvas, bg=self.colors["bg"], padx=20, pady=20)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scroll_bar.pack(side="right", fill="y")

        # TOOL 1: FORCE UNINSTALL
        card1 = tk.Frame(scrollable_frame, bg=self.colors["card_bg"], padx=18, pady=18, highlightthickness=1, highlightbackground=self.colors["border"])
        card1.pack(fill=tk.X, pady=(0, 16))

        tk.Label(card1, text="Zorla Kaldır (Force Uninstall)", font=("Segoe UI", 12, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(card1, text="Kaldırıcısı bozuk olan, kilitli veya Denetim Masasında görünmeyen program dosyalarını zorla temizler ve ilgili tüm Registry kayıtlarını siler.", font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=(2, 10))

        force_box = tk.Frame(card1, bg=self.colors["card_bg"])
        force_box.pack(fill=tk.X)

        self.force_path_var = tk.StringVar()
        force_entry = tk.Entry(force_box, textvariable=self.force_path_var, font=("Segoe UI", 10), bg="#141518", fg=self.colors["text"], insertbackground=self.colors["text"], bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        force_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def _browse_force():
            p = filedialog.askdirectory(title="Zorla Kaldırılacak Program Klasörünü Seçin")
            if not p:
                p = filedialog.askopenfilename(title="Zorla Kaldırılacak Dosyayı Seçin")
            if p:
                self.force_path_var.set(p)

        tk.Button(force_box, text="Gözat...", font=("Segoe UI", 9), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=_browse_force).pack(side=tk.LEFT, padx=(0, 8))

        def _do_force():
            target = self.force_path_var.get().strip()
            if not target or not os.path.exists(target):
                messagebox.showerror("Hata", "Lütfen geçerli bir dosya veya klasör seçin.")
                return
            if not messagebox.askyesno("DİKKAT — Zorla Kaldırma", f"'{target}' konumu zorla silinecek ve tüm süreçleri sonlandırılacaktır. Devam edilsin mi?"):
                return
            res = ForceUninstaller.force_delete_target(target)
            if res["success"]:
                msg = f"Başarıyla zorla kaldırıldı!\n- Sonlandırılan süreçler: {len(res['killed_processes'])}\n- Temizlenen Registry anahtarları: {res['purged_registry_keys']}"
                messagebox.showinfo("Başarılı", msg)
                self.force_path_var.set("")
            else:
                messagebox.showerror("Hata", f"İşlem başarısız: {res['error']}")

        tk.Button(force_box, text="ZORLA KALDIR", font=("Segoe UI", 9, "bold"), bg=self.colors["danger"], fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=_do_force).pack(side=tk.LEFT)

        # TOOL 2: FILE SHREDDER
        card2 = tk.Frame(scrollable_frame, bg=self.colors["card_bg"], padx=18, pady=18, highlightthickness=1, highlightbackground=self.colors["border"])
        card2.pack(fill=tk.X, pady=(0, 16))

        tk.Label(card2, text="Kalıcı Dosya Parçalayıcı (File Shredder)", font=("Segoe UI", 12, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(card2, text="DoD 5220.22-M 3 geçişli rastgele byte üzerine yazma standardı ile dosyaları kurtarılamaz biçimde yok eder.", font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=(2, 10))

        shred_box = tk.Frame(card2, bg=self.colors["card_bg"])
        shred_box.pack(fill=tk.X)

        self.shred_path_var = tk.StringVar()
        shred_entry = tk.Entry(shred_box, textvariable=self.shred_path_var, font=("Segoe UI", 10), bg="#141518", fg=self.colors["text"], insertbackground=self.colors["text"], bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        shred_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def _browse_shred():
            p = filedialog.askopenfilename(title="Parçalanacak Dosyayı Seçin")
            if not p:
                p = filedialog.askdirectory(title="Parçalanacak Klasörü Seçin")
            if p:
                self.shred_path_var.set(p)

        tk.Button(shred_box, text="Gözat...", font=("Segoe UI", 9), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=_browse_shred).pack(side=tk.LEFT, padx=(0, 8))

        def _do_shred():
            target = self.shred_path_var.get().strip()
            if not target or not os.path.exists(target):
                messagebox.showerror("Hata", "Lütfen parçalanacak geçerli bir dosya veya klasör seçin.")
                return
            if not messagebox.askyesno("GERİ DÖNDÜRÜLEMEZ SİLME", f"'{target}' dosyası/klasörü 3 aşamalı DoD standardıyla tamamen yok edilecek. Hiçbir kurtarma yazılımı geri getiremez. Onaylıyor musunuz?"):
                return
            succ, fail = FileShredder.shred_target(target, passes=3)
            messagebox.showinfo("Tamamlandı", f"Parçalama işlemi tamamlandı!\n- Başarılı: {succ} dosya\n- Başarısız: {fail} dosya")
            self.shred_path_var.set("")

        tk.Button(shred_box, text="PARÇALA & YOK ET", font=("Segoe UI", 9, "bold"), bg="#b91c1c", fg="#ffffff", bd=0, padx=16, pady=6, cursor="hand2", command=_do_shred).pack(side=tk.LEFT)

        # TOOL 3: INSTALL MONITOR
        card3 = tk.Frame(scrollable_frame, bg=self.colors["card_bg"], padx=18, pady=18, highlightthickness=1, highlightbackground=self.colors["border"])
        card3.pack(fill=tk.X)

        tk.Label(card3, text="Kurulum İzleyici & Anlık Görüntü (Install Monitor)", font=("Segoe UI", 12, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(card3, text="Bir program kurmadan önce sistem durumunu kaydeder. Kurulum tamamlandıktan sonra ikinci görüntüyü alarak oluşturulan tüm dosyaları ve Registry anahtarlarını tam log olarak çıkarır.", font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["card_bg"], wraplength=700, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 10))

        snap_box = tk.Frame(card3, bg=self.colors["card_bg"])
        snap_box.pack(fill=tk.X)

        self.snap_status_lbl = tk.Label(snap_box, text="Ön Görüntü Durumu: Alınmadı", font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["card_bg"])
        self.snap_status_lbl.pack(side=tk.LEFT, padx=(0, 16))

        def _take_pre():
            self.snap_status_lbl.config(text="Ön Görüntü alınıyor, lütfen bekleyin...")
            def _t():
                snap = InstallSnapshot.take_snapshot()
                self.pre_install_snapshot = snap
                self.after(0, lambda: self.snap_status_lbl.config(text=f"Ön Görüntü Hazır ({len(snap['files'])} dosya, {len(snap['hklm_keys']) + len(snap['hkcu_keys'])} anahtar)"))
                self.after(0, lambda: messagebox.showinfo("Hazır", "Kurulum öncesi sistem anlık görüntüsü alındı.\nŞimdi kurmak istediğiniz programı yükleyin, ardından 'Kurulum Sonrası Analiz Et' butonuna tıklayın."))
            threading.Thread(target=_t, daemon=True).start()

        tk.Button(snap_box, text="1. Kurulum Öncesi Görüntü Al", font=("Segoe UI", 9, "bold"), bg=self.colors["cyan_hover"], fg="#ffffff", bd=0, padx=14, pady=6, cursor="hand2", command=_take_pre).pack(side=tk.LEFT, padx=(0, 8))

        def _take_post():
            if not self.pre_install_snapshot:
                messagebox.showerror("Hata", "Lütfen önce 'Kurulum Öncesi Görüntü Al' butonuna tıklayın.")
                return
            self.snap_status_lbl.config(text="Kurulum sonrası analiz yapılıyor...")
            def _t():
                post_snap = InstallSnapshot.take_snapshot()
                diff = InstallSnapshot.compare_snapshots(self.pre_install_snapshot, post_snap)
                import json
                log_file = os.path.join(os.path.expanduser("~"), "Desktop", "kurulum_izleme_kaydi.json")
                with open(log_file, "w", encoding="utf-8") as lf:
                    json.dump(diff, lf, indent=2, ensure_ascii=False)
                self.after(0, lambda: self.snap_status_lbl.config(text="Analiz tamamlandı ve masaüstüne kaydedildi."))
                msg = (
                    f"Kurulum Analizi Tamamlandı!\n\n"
                    f"- Yeni Oluşturulan Dosyalar: {len(diff['new_files'])}\n"
                    f"- Yeni HKLM Kayıt Defteri Anahtarları: {len(diff['new_hklm_keys'])}\n"
                    f"- Yeni HKCU Kayıt Defteri Anahtarları: {len(diff['new_hkcu_keys'])}\n\n"
                    f"Rapor masaüstünüze kaydedildi:\n{log_file}"
                )
                self.after(0, lambda: messagebox.showinfo("Kurulum İzi Çıkarıldı", msg))
            threading.Thread(target=_t, daemon=True).start()

        tk.Button(snap_box, text="2. Kurulum Sonrası Analiz Et", font=("Segoe UI", 9, "bold"), bg=self.colors["accent"], fg="#0d0f12", bd=0, padx=14, pady=6, cursor="hand2", command=_take_post).pack(side=tk.LEFT)

    # ==========================================
    # VIEW 7: ADVANCED ANALYSIS & SECURITY LABORATORY
    # ==========================================
    def show_rea_view(self):
        self._set_active_nav("rea")
        self._clear_content()

        scroll_canvas = tk.Canvas(self.content_area, bg=self.colors["bg"], bd=0, highlightthickness=0)
        scroll_bar = ttk.Scrollbar(self.content_area, orient="vertical", command=scroll_canvas.yview)
        scrollable_frame = tk.Frame(scroll_canvas, bg=self.colors["bg"], padx=20, pady=20)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scroll_bar.pack(side="right", fill="y")

        # Header Title
        title_box = tk.Frame(scrollable_frame, bg=self.colors["bg"])
        title_box.pack(fill=tk.X, pady=(0, 14))

        tk.Label(title_box, text="İleri İkili Dosya & Güvenlik Laboratuvarı", font=("Segoe UI", 13, "bold"), fg=self.colors["accent"], bg=self.colors["bg"]).pack(anchor=tk.W)
        tk.Label(title_box, text="Sisteminizdeki gelişmiş analiz araç setiyle entegre: Detect It Easy, dnSpy ve x64dbg doğrudan kontrol edilebilir.", font=("Segoe UI", 9), fg=self.colors["text_muted"], bg=self.colors["bg"]).pack(anchor=tk.W, pady=(2, 0))

        # 3 Tool Cards
        tools_row = tk.Frame(scrollable_frame, bg=self.colors["bg"])
        tools_row.pack(fill=tk.X, pady=(0, 16))

        # CARD 1: DIE
        c_die = tk.Frame(tools_row, bg=self.colors["card_bg"], padx=16, pady=16, highlightthickness=1, highlightbackground=self.colors["border"])
        c_die.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        tk.Label(c_die, text="Detect It Easy (DIE)", font=("Segoe UI", 11, "bold"), fg=self.colors["cyan"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(c_die, text="Derleyici, koruma (packer), PE başlıkları ve kriptografik imza tespiti yapar.", font=("Segoe UI", 8), fg=self.colors["text_muted"], bg=self.colors["card_bg"], wraplength=190, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 12))
        tk.Button(c_die, text="DIE Başlat", font=("Segoe UI", 9, "bold"), bg=self.colors["cyan_hover"], fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("die")).pack(anchor=tk.W)

        # CARD 2: dnSpy
        c_dnspy = tk.Frame(tools_row, bg=self.colors["card_bg"], padx=16, pady=16, highlightthickness=1, highlightbackground=self.colors["border"])
        c_dnspy.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        tk.Label(c_dnspy, text="dnSpy (.NET Çözücü)", font=("Segoe UI", 11, "bold"), fg=self.colors["purple"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(c_dnspy, text="C# ve .NET ile yazılmış programları doğrudan saf kaynak koduna dönüştürür ve düzenler.", font=("Segoe UI", 8), fg=self.colors["text_muted"], bg=self.colors["card_bg"], wraplength=190, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 12))
        tk.Button(c_dnspy, text="dnSpy Başlat", font=("Segoe UI", 9, "bold"), bg=self.colors["accent"], fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("dnspy")).pack(anchor=tk.W)

        # CARD 3: x64dbg
        c_x64 = tk.Frame(tools_row, bg=self.colors["card_bg"], padx=16, pady=16, highlightthickness=1, highlightbackground=self.colors["border"])
        c_x64.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        tk.Label(c_x64, text="x64dbg Disassembler", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(c_x64, text="C, C++, Rust yerel kodlarını Assembly (makine dili) seviyesinde adım adım ayrıştırır.", font=("Segoe UI", 8), fg=self.colors["text_muted"], bg=self.colors["card_bg"], wraplength=190, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 12))
        tk.Button(c_x64, text="x64dbg Başlat", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("x64dbg")).pack(anchor=tk.W)

        # Quick Binary Inspector Box
        inspect_card = tk.Frame(scrollable_frame, bg=self.colors["card_bg"], padx=18, pady=18, highlightthickness=1, highlightbackground=self.colors["border"])
        inspect_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(inspect_card, text="Hızlı İkili Dosya & PE Güvenlik Analizi", font=("Segoe UI", 11, "bold"), fg=self.colors["accent"], bg=self.colors["card_bg"]).pack(anchor=tk.W)
        tk.Label(inspect_card, text="Bir .exe veya .dll seçerek dosyanın mimarisini, koruma durumunu ve kütüphane bağlarını anında inceleyin.", font=("Segoe UI", 8), fg=self.colors["text_muted"], bg=self.colors["card_bg"]).pack(anchor=tk.W, pady=(2, 10))

        file_box = tk.Frame(inspect_card, bg=self.colors["card_bg"])
        file_box.pack(fill=tk.X)

        self.rea_file_var = tk.StringVar()
        f_entry = tk.Entry(file_box, textvariable=self.rea_file_var, font=("Segoe UI", 10), bg="#090a0f", fg=self.colors["text"], insertbackground=self.colors["text"], bd=0, highlightthickness=1, highlightbackground=self.colors["border"])
        f_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        def _browse_binary():
            f = filedialog.askopenfilename(title="İncelenecek İkili Dosyayı Seçin", filetypes=[("İkili Dosyalar", "*.exe;*.dll;*.sys;*.bin")])
            if f:
                self.rea_file_var.set(f)
                _analyze_now()

        tk.Button(file_box, text="Dosya Seç...", font=("Segoe UI", 9), bg=self.colors["sidebar"], fg=self.colors["text"], bd=0, padx=12, pady=6, cursor="hand2", command=_browse_binary).pack(side=tk.LEFT, padx=(0, 8))

        # Output telemetry box
        self.rea_out_txt = tk.Text(inspect_card, font=("Consolas", 9), bg="#090a0f", fg=self.colors["cyan"], bd=0, padx=12, pady=12, height=9)
        self.rea_out_txt.pack(fill=tk.BOTH, expand=True, pady=(12, 12))
        self.rea_out_txt.insert("1.0", "Lütfen yukarıdan incelenecek bir .exe veya .dll dosyası seçin...")
        self.rea_out_txt.configure(state="disabled")

        def _analyze_now():
            fp = self.rea_file_var.get().strip()
            if not fp or not os.path.isfile(fp):
                return
            info = REABridge.inspect_binary_quick(fp)
            report = (
                f"--- DOSYA GÜVENLİK & MİMARİ RAPORU ---\n"
                f"Hedef: {fp}\n"
                f"Boyut: {os.path.getsize(fp) / 1024:.1f} KB\n"
                f"Mimari: {info['architecture']}\n"
                f"Alt Sistem: {info['subsystem']}\n"
                f".NET Framework / CLR: {'MEVCUT (C# / VB.NET)' if info['has_dotnet'] else 'Yok (Yerel Native Kod)'}\n"
                f"Paketleyici / Şifreleme Durumu: {'YÜKSEK ENTROPİ — Olası Packer / Koruma Var' if info['is_packed'] else 'Standart Kod'}\n"
                f"PE Bölümleri ({len(info['sections'])}): {', '.join(info['sections'])}\n"
            )
            self.rea_out_txt.configure(state="normal")
            self.rea_out_txt.delete("1.0", tk.END)
            self.rea_out_txt.insert("1.0", report)
            self.rea_out_txt.configure(state="disabled")

        btn_bar = tk.Frame(inspect_card, bg=self.colors["card_bg"])
        btn_bar.pack(fill=tk.X)

        tk.Button(btn_bar, text="Detect It Easy ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg=self.colors["cyan"], bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("die", self.rea_file_var.get().strip())).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_bar, text="dnSpy ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg=self.colors["accent"], bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("dnspy", self.rea_file_var.get().strip())).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_bar, text="x64dbg ile Aç", font=("Segoe UI", 9, "bold"), bg=self.colors["sidebar"], fg="#ffffff", bd=0, padx=12, pady=6, cursor="hand2", command=lambda: REABridge.launch_tool("x64dbg", self.rea_file_var.get().strip())).pack(side=tk.LEFT)
