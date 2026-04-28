"""
Arduino AI Studio v3.0 - Pagrindinis GUI
Didelis pokalbių langas, nuapvalinti mygtukai, paprastas UX
"""
import customtkinter as ctk
import threading
import json
import sys
import os
import re
from pathlib import Path
from tkinter import messagebox, scrolledtext
import tkinter as tk

# ─── Spalvų schema ───────────────────────────────────────────────
COLORS = {
    "bg":          "#0f1117",   # labai tamsus fonas
    "panel":       "#1a1d27",   # šoniniai paneliai
    "card":        "#1e2235",   # kortelės
    "border":      "#2a2d3e",   # rėmeliai
    "accent":      "#3b82f6",   # mėlyna (pagrindinis)
    "accent2":     "#6366f1",   # violetinė (AI)
    "success":     "#22c55e",   # žalia
    "warning":     "#f59e0b",   # oranžinė
    "error":       "#ef4444",   # raudona
    "text":        "#e2e8f0",   # pagrindinis tekstas
    "text_dim":    "#64748b",   # blankus tekstas
    "user_msg":    "#1e3a5f",   # vartotojo žinutės fonas
    "ai_msg":      "#1e2a1e",   # AI žinutės fonas
    "code_bg":     "#0d1117",   # kodo blokas
}

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"

def load_config() -> dict:
    default = {
        "ai_provider": "groq",
        "groq_api_key": "",
        "groq_model": "llama-3.1-8b-instant",
        "ollama_url": "http://localhost:11434",
        "default_model": "llama3.1:8b",
        "arduino_cli_path": str(PROJECT_ROOT / "tools" / "arduino-cli.exe"),
        "workspace_dir": str(PROJECT_ROOT / "workspace" / "sketch"),
        "available_boards": [
            {"name": "Arduino Nano (Old Bootloader / CH340)", "fqbn": "arduino:avr:nano:cpu=atmega328old"},
            {"name": "Arduino Nano (New Bootloader)", "fqbn": "arduino:avr:nano:cpu=atmega328"},
            {"name": "Arduino Uno", "fqbn": "arduino:avr:uno"},
            {"name": "Arduino Mega 2560", "fqbn": "arduino:avr:mega"},
            {"name": "ESP32", "fqbn": "esp32:esp32:esp32"},
            {"name": "ESP32-C3", "fqbn": "esp32:esp32:esp32c3"},
        ],
        "max_fix_iterations": 3,
        "ai_timeout": 60,
        "serial_baud": 115200,
        "auto_install_cores": True,
        "theme": "dark",
        "version": "3.0.0"
    }
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            default.update(saved)
        except:
            pass
    return default

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


class ChatMessage:
    """Viena žinutė pokalbių lange"""
    def __init__(self, parent, role: str, text: str, code: str = ""):
        self.role = role  # "user" | "ai" | "system"
        self.code = code
        self.frame = ctk.CTkFrame(parent,
            fg_color=COLORS["user_msg"] if role == "user" else
                     COLORS["ai_msg"] if role == "ai" else
                     COLORS["card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.frame.pack(fill="x", padx=8, pady=4)

        # Ikona + autoriai
        header = ctk.CTkFrame(self.frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8,2))

        icon = "👤" if role == "user" else "🤖" if role == "ai" else "ℹ️"
        label = "Tu" if role == "user" else "Arduino AI" if role == "ai" else "Sistema"
        ctk.CTkLabel(header, text=f"{icon} {label}",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS["accent"] if role == "user" else
                                COLORS["accent2"] if role == "ai" else
                                COLORS["text_dim"]).pack(side="left")

        # Tekstas
        if text:
            msg_label = ctk.CTkLabel(self.frame, text=text,
                                     wraplength=600, justify="left",
                                     font=ctk.CTkFont(size=13),
                                     text_color=COLORS["text"],
                                     anchor="w")
            msg_label.pack(fill="x", padx=12, pady=(2, 6))

        # Kodo blokas
        if code:
            code_frame = ctk.CTkFrame(self.frame,
                                       fg_color=COLORS["code_bg"],
                                       corner_radius=8, border_width=1,
                                       border_color=COLORS["border"])
            code_frame.pack(fill="x", padx=12, pady=(2, 8))

            code_header = ctk.CTkFrame(code_frame, fg_color="transparent")
            code_header.pack(fill="x", padx=8, pady=(4,0))
            ctk.CTkLabel(code_header, text="📄 Arduino kodas",
                         font=ctk.CTkFont(size=10),
                         text_color=COLORS["text_dim"]).pack(side="left")

            code_text = ctk.CTkTextbox(code_frame,
                                        height=min(300, code.count('\n')*18+40),
                                        font=ctk.CTkFont(family="Courier New", size=12),
                                        fg_color=COLORS["code_bg"],
                                        text_color="#a8d8a8",
                                        wrap="none",
                                        border_width=0)
            code_text.pack(fill="x", padx=8, pady=(4,8))
            code_text.insert("1.0", code)
            code_text.configure(state="disabled")


class ArduinoAIStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_data = load_config()
        self.current_code = ""
        self.selected_port = tk.StringVar(value="")
        self.selected_fqbn = tk.StringVar(value="")
        self.selected_board_name = tk.StringVar(value="Pasirink boardą")
        self.ai_running = False

        # Importai su patikrinimais
        self._import_modules()

        self.title("🤖 Arduino AI Studio v3.0")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self._auto_detect_boards()
        self.after(500, self._check_ai_status)

    def _import_modules(self):
        """Importuoti modulius"""
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from core.ai_client import AIClient
            from core.arduino import ArduinoManager
            self.ai = AIClient(self.config_data)
            self.arduino = ArduinoManager(self.config_data)
        except Exception as e:
            messagebox.showerror("Klaida", f"Modulių importas nepavyko:\n{e}")
            sys.exit(1)

    # ─── UI statyba ───────────────────────────────────────────────

    def _build_ui(self):
        """Pastatyti visą UI"""
        # Viršutinė juosta
        self._build_topbar()

        # Pagrindinis konteineris
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=8, pady=(0,8))
        main.columnconfigure(0, weight=0)   # kairysis panel
        main.columnconfigure(1, weight=1)   # pokalbių langas
        main.rowconfigure(0, weight=1)

        # Kairysis panel
        self._build_left_panel(main)

        # Dešinysis - pokalbių langas
        self._build_chat_area(main)

    def _build_topbar(self):
        """Viršutinė juosta su pavadinimu ir statusu"""
        bar = ctk.CTkFrame(self, fg_color=COLORS["panel"],
                           corner_radius=0, height=50)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(bar,
                     text="🤖 Arduino AI Studio",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS["text"]
                     ).pack(side="left", padx=16)

        # AI statusas
        self.ai_status_label = ctk.CTkLabel(bar,
                                             text="⏳ Tikrinama...",
                                             font=ctk.CTkFont(size=12),
                                             text_color=COLORS["text_dim"])
        self.ai_status_label.pack(side="left", padx=16)

        # Dešiniai mygtukai
        btn_frame = ctk.CTkFrame(bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=8)

        ctk.CTkButton(btn_frame, text="⚙️ Nustatymai",
                      width=130, height=34,
                      corner_radius=20,
                      fg_color=COLORS["card"],
                      hover_color=COLORS["border"],
                      command=self._open_settings
                      ).pack(side="right", padx=4, pady=8)

        ctk.CTkButton(btn_frame, text="🗑️ Išvalyti",
                      width=100, height=34,
                      corner_radius=20,
                      fg_color=COLORS["card"],
                      hover_color=COLORS["border"],
                      command=self._clear_chat
                      ).pack(side="right", padx=4, pady=8)

    def _build_left_panel(self, parent):
        """Kairysis panel - board pasirinkimas ir mygtukai"""
        panel = ctk.CTkFrame(parent, fg_color=COLORS["panel"],
                              corner_radius=12, width=240)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        panel.pack_propagate(False)

        # ── Board sekcija ──
        self._section_label(panel, "🔌 PLOKŠTĖ (BOARD)")

        # Auto detekcija mygtukas
        ctk.CTkButton(panel,
                      text="🔍 Rasti automatiškai",
                      height=38, corner_radius=20,
                      font=ctk.CTkFont(size=13),
                      fg_color=COLORS["accent"],
                      hover_color="#2563eb",
                      command=self._auto_detect_boards
                      ).pack(fill="x", padx=12, pady=(4, 2))

        # Board pasirinkimas
        self.board_dropdown = ctk.CTkOptionMenu(panel,
                                                 values=["Ieškom..."],
                                                 variable=self.selected_board_name,
                                                 command=self._on_board_select,
                                                 height=36, corner_radius=8,
                                                 fg_color=COLORS["card"],
                                                 button_color=COLORS["border"],
                                                 font=ctk.CTkFont(size=12))
        self.board_dropdown.pack(fill="x", padx=12, pady=2)

        # Board info
        self.board_info = ctk.CTkLabel(panel, text="Neprijungta",
                                        font=ctk.CTkFont(size=10),
                                        text_color=COLORS["text_dim"],
                                        wraplength=200)
        self.board_info.pack(padx=12, pady=(2, 8))

        # ── COM portas ──
        self._section_label(panel, "🔗 COM PORTAS")

        self.port_dropdown = ctk.CTkOptionMenu(panel,
                                                values=["Nėra"],
                                                variable=self.selected_port,
                                                height=36, corner_radius=8,
                                                fg_color=COLORS["card"],
                                                button_color=COLORS["border"],
                                                font=ctk.CTkFont(size=12))
        self.port_dropdown.pack(fill="x", padx=12, pady=2)

        ctk.CTkButton(panel, text="🔄 Atnaujinti",
                      height=30, corner_radius=16,
                      fg_color=COLORS["card"],
                      hover_color=COLORS["border"],
                      font=ctk.CTkFont(size=11),
                      command=self._refresh_ports
                      ).pack(fill="x", padx=12, pady=(2, 12))

        # ── Veiksmai ──
        self._section_label(panel, "⚡ VEIKSMAI")

        self.compile_btn = ctk.CTkButton(panel,
                                          text="⚙️ Kompiliuoti",
                                          height=40, corner_radius=20,
                                          fg_color=COLORS["warning"],
                                          hover_color="#d97706",
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          command=self._do_compile)
        self.compile_btn.pack(fill="x", padx=12, pady=3)

        self.upload_btn = ctk.CTkButton(panel,
                                         text="📤 Įkelti į boardą",
                                         height=40, corner_radius=20,
                                         fg_color=COLORS["success"],
                                         hover_color="#16a34a",
                                         font=ctk.CTkFont(size=13, weight="bold"),
                                         command=self._do_upload)
        self.upload_btn.pack(fill="x", padx=12, pady=3)

        self.fix_btn = ctk.CTkButton(panel,
                                      text="🔧 AI Taisyti klaidas",
                                      height=40, corner_radius=20,
                                      fg_color=COLORS["accent2"],
                                      hover_color="#4f46e5",
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      command=self._do_fix)
        self.fix_btn.pack(fill="x", padx=12, pady=3)

        # ── Spartieji mygtukai ──
        self._section_label(panel, "⚡ GREITI PAVYZDŽIAI")

        quick_buttons = [
            ("💡 LED mirksėjimas", "Parašyk LED mirksėjimo kodą Arduino Nano - LED ant pin 13, mirksi kas 500ms"),
            ("🌡️ Temperatūra DHT11", "Parašyk kodą Arduino Nano su DHT11 temperatūros davikliu, rodyti Serial Monitor"),
            ("🔊 Buzzer melodija", "Parašyk paprastą melodiją su buzzer Arduino Nano pin 8"),
            ("📺 LCD 16x2 tekstas", "Parašyk kodą rodyti tekstą 16x2 LCD ekrane su I2C adapteriu"),
            ("🎮 Servo valdymas", "Parašyk servo variklio valdymą su potenciometru Arduino Nano"),
        ]
        for label, prompt in quick_buttons:
            ctk.CTkButton(panel, text=label,
                          height=30, corner_radius=16,
                          fg_color=COLORS["card"],
                          hover_color=COLORS["border"],
                          font=ctk.CTkFont(size=11),
                          command=lambda p=prompt: self._quick_prompt(p)
                          ).pack(fill="x", padx=12, pady=2)

        # Tuščia vieta apačioje
        ctk.CTkLabel(panel, text="v3.0 | github.com/arunas",
                     font=ctk.CTkFont(size=9),
                     text_color=COLORS["text_dim"]
                     ).pack(side="bottom", pady=8)

    def _build_chat_area(self, parent):
        """Dešinysis - pokalbių + įvestis"""
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=0)
        right.columnconfigure(0, weight=1)

        # ── Pokalbių langas ──
        chat_container = ctk.CTkFrame(right, fg_color=COLORS["panel"],
                                       corner_radius=12)
        chat_container.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        # Antraštė
        chat_header = ctk.CTkFrame(chat_container, fg_color=COLORS["card"],
                                    corner_radius=0, height=36)
        chat_header.pack(fill="x")
        chat_header.pack_propagate(False)
        ctk.CTkLabel(chat_header, text="💬 Pokalbis su AI",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS["text"]).pack(side="left", padx=12, pady=8)

        self.status_label = ctk.CTkLabel(chat_header, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color=COLORS["warning"])
        self.status_label.pack(side="right", padx=12)

        # Scrollable chat area
        self.chat_scroll = ctk.CTkScrollableFrame(chat_container,
                                                   fg_color="transparent",
                                                   scrollbar_button_color=COLORS["border"])
        self.chat_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Pirmoji žinutė
        self._add_system_message(
            "👋 Sveiki! Aš esu Arduino AI asistentas.\n\n"
            "📝 Kairėje pasirink savo boardą (arba spausk 'Rasti automatiškai')\n"
            "💬 Apačioje parašyk ką nori padaryti paprastais žodžiais\n"
            "🤖 AI sugeneruos kodą ir padės jį įkelti į boardą\n\n"
            "Pavyzdys: 'Noriu kad LED ant pin 13 mirksėtų kas sekundę'"
        )

        # ── Įvesties zona ──
        input_frame = ctk.CTkFrame(right, fg_color=COLORS["panel"],
                                    corner_radius=12, height=130)
        input_frame.grid(row=1, column=0, sticky="ew")
        input_frame.pack_propagate(False)
        input_frame.columnconfigure(0, weight=1)

        # Tekstas
        self.input_box = ctk.CTkTextbox(input_frame,
                                         height=70,
                                         font=ctk.CTkFont(size=14),
                                         fg_color=COLORS["card"],
                                         text_color=COLORS["text"],
                                         border_color=COLORS["border"],
                                         border_width=1,
                                         corner_radius=10,
                                         wrap="word")
        self.input_box.grid(row=0, column=0, padx=(12,6), pady=(10,4), sticky="ew")
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)  # Shift+Enter = nauja eilutė

        # Placeholder tekstas
        self._set_placeholder()

        # Mygtukai
        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.grid(row=0, column=1, padx=(0,12), pady=10)

        self.send_btn = ctk.CTkButton(btn_row,
                                       text="📨 Siųsti",
                                       width=110, height=36,
                                       corner_radius=20,
                                       fg_color=COLORS["accent"],
                                       hover_color="#2563eb",
                                       font=ctk.CTkFont(size=13, weight="bold"),
                                       command=self._send_message)
        self.send_btn.pack(pady=3)

        ctk.CTkButton(btn_row,
                      text="⌨️ Ctrl+↵",
                      width=110, height=28,
                      corner_radius=16,
                      fg_color="transparent",
                      hover_color=COLORS["card"],
                      font=ctk.CTkFont(size=10),
                      text_color=COLORS["text_dim"],
                      command=self._send_message
                      ).pack(pady=1)

        # Patarimas apačioje
        hint_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        hint_frame.grid(row=1, column=0, columnspan=2, padx=12, sticky="ew")
        ctk.CTkLabel(hint_frame,
                     text="💡 Enter = siųsti  |  Shift+Enter = nauja eilutė  |  Rašyk paprastai: 'Noriu LED mirksėjimą'",
                     font=ctk.CTkFont(size=10),
                     text_color=COLORS["text_dim"]).pack(side="left")

    # ─── Pagalbinės UI funkcijos ───────────────────────────────────

    def _section_label(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_dim"]
                     ).pack(anchor="w", padx=14, pady=(10, 2))

    def _set_placeholder(self):
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", "Pvz: Noriu kad LED ant 13 nogo mirksėtų kas pusę sekundės...")
        self.input_box.configure(text_color=COLORS["text_dim"])
        self.input_box.bind("<FocusIn>", self._clear_placeholder)

    def _clear_placeholder(self, event=None):
        current = self.input_box.get("1.0", "end").strip()
        if current.startswith("Pvz:"):
            self.input_box.delete("1.0", "end")
            self.input_box.configure(text_color=COLORS["text"])
        self.input_box.unbind("<FocusIn>")

    def _add_system_message(self, text: str):
        ChatMessage(self.chat_scroll, "system", text)

    def _add_user_message(self, text: str):
        ChatMessage(self.chat_scroll, "user", text)

    def _add_ai_message(self, text: str, code: str = ""):
        ChatMessage(self.chat_scroll, "ai", text, code)

    def _scroll_to_bottom(self):
        self.after(100, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def _set_status(self, text: str, color: str = None):
        self.status_label.configure(text=text,
                                     text_color=color or COLORS["warning"])

    def _set_ai_status(self, text: str, color: str = None):
        self.ai_status_label.configure(text=text,
                                        text_color=color or COLORS["text_dim"])

    # ─── Board detekcija ──────────────────────────────────────────

    def _auto_detect_boards(self):
        """Automatiškai rasti boardus"""
        boards = self.arduino.detect_boards()
        ports = self.arduino.list_ports()

        # Atnaujinti port dropdown
        port_list = [b["port"] for b in boards] + [p for p in ports
                     if p not in [b["port"] for b in boards]]
        if port_list:
            self.port_dropdown.configure(values=port_list)
            self.selected_port.set(port_list[0])
        else:
            self.port_dropdown.configure(values=["Nėra"])
            self.selected_port.set("Nėra")

        # Atnaujinti board dropdown
        all_boards = self.config_data.get("available_boards", [])
        auto_names = []

        if boards:
            # Rasta automatiškai — pirmi sąraše
            for b in boards:
                if b["auto_detected"]:
                    auto_names.append(f"✅ {b['name']} ({b['port']})")
            self.selected_fqbn.set(boards[0]["fqbn"])
            self.selected_port.set(boards[0]["port"])
            info = f"✅ Rastas: {boards[0]['name']}\n{boards[0]['port']} | VID:{boards[0]['vid']} PID:{boards[0]['pid']}"
            self.board_info.configure(text=info, text_color=COLORS["success"])

        manual_names = [b["name"] for b in all_boards]
        all_names = auto_names + ["─────"] + manual_names if auto_names else manual_names

        self.board_dropdown.configure(values=all_names)
        if auto_names:
            self.selected_board_name.set(auto_names[0])
        elif manual_names:
            self.selected_board_name.set(manual_names[0])
            self.selected_fqbn.set(all_boards[0]["fqbn"])
            self.board_info.configure(text="⚠️ Boardas neprijungtas arba neatpažintas",
                                       text_color=COLORS["warning"])

    def _on_board_select(self, selection: str):
        """Kai vartotojas pasirenka boardą"""
        if selection.startswith("─") or selection.startswith("✅"):
            # Automatiškai atrastas — fqbn jau nustatytas
            return
        # Ieškome rank sąraše
        for b in self.config_data.get("available_boards", []):
            if b["name"] == selection:
                self.selected_fqbn.set(b["fqbn"])
                self.board_info.configure(text=f"📌 {b['fqbn']}",
                                           text_color=COLORS["text_dim"])
                break

    def _refresh_ports(self):
        self._auto_detect_boards()
        self._set_status("✅ Atnaujinta", COLORS["success"])
        self.after(2000, lambda: self._set_status(""))

    # ─── AI ryšio patikrinimas ────────────────────────────────────

    def _check_ai_status(self):
        def check():
            if self.config_data.get("ai_provider") == "groq":
                key = self.config_data.get("groq_api_key", "")
                if key and key.startswith("gsk_"):
                    self.after(0, lambda: self._set_ai_status("✅ Groq prijungtas", COLORS["success"]))
                else:
                    self.after(0, lambda: self._set_ai_status("⚠️ Groq be rakto — eik į Nustatymus", COLORS["warning"]))
            else:
                # Tikrinti Ollama
                try:
                    import requests
                    r = requests.get(self.config_data.get("ollama_url","") + "/api/tags", timeout=3)
                    if r.status_code == 200:
                        self.after(0, lambda: self._set_ai_status("✅ Ollama prisijungta", COLORS["success"]))
                    else:
                        self.after(0, lambda: self._set_ai_status("❌ Ollama nepasiekiama", COLORS["error"]))
                except:
                    self.after(0, lambda: self._set_ai_status("❌ Ollama nepasiekiama", COLORS["error"]))
        threading.Thread(target=check, daemon=True).start()

    # ─── Žinučių siuntimas ────────────────────────────────────────

    def _on_enter(self, event):
        """Enter klavišas"""
        if not event.state & 0x1:  # Shift nespaustas
            self._send_message()
            return "break"

    def _quick_prompt(self, prompt: str):
        """Greito pavyzdžio mygtukas"""
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", prompt)
        self.input_box.configure(text_color=COLORS["text"])
        self._send_message()

    def _send_message(self):
        """Siųsti žinutę AI"""
        if self.ai_running:
            return
        text = self.input_box.get("1.0", "end").strip()
        if not text or text.startswith("Pvz:"):
            return

        # Papildyti su board kontekstu
        board_name = self.selected_board_name.get().replace("✅ ", "").split("(")[0].strip()
        fqbn = self.selected_fqbn.get()
        if fqbn:
            full_prompt = f"[Board: {board_name}]\n\n{text}"
        else:
            full_prompt = text

        self._add_user_message(text)
        self.input_box.delete("1.0", "end")
        self._scroll_to_bottom()

        # Sukurti AI žinutės rėmą
        ai_frame = ctk.CTkFrame(self.chat_scroll,
                                  fg_color=COLORS["ai_msg"],
                                  corner_radius=12,
                                  border_width=1,
                                  border_color=COLORS["border"])
        ai_frame.pack(fill="x", padx=8, pady=4)

        header = ctk.CTkFrame(ai_frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8,2))
        ctk.CTkLabel(header, text="🤖 Arduino AI",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS["accent2"]).pack(side="left")

        # Streaming tekstas
        stream_label = ctk.CTkLabel(ai_frame, text="⏳ Galvoju...",
                                     wraplength=580, justify="left",
                                     font=ctk.CTkFont(size=13),
                                     text_color=COLORS["text_dim"],
                                     anchor="w")
        stream_label.pack(fill="x", padx=12, pady=(2,6))

        def run_ai():
            self.ai_running = True
            self.send_btn.configure(state="disabled", text="⏳...")
            self._set_status("🤖 AI rašo...", COLORS["accent2"])

            collected = [""]

            def on_chunk(token: str):
                collected[0] += token
                # Atnaujinti UI kiekvienam chunk
                display = collected[0][:500] + ("..." if len(collected[0]) > 500 else "")
                self.after(0, lambda: stream_label.configure(
                    text=display, text_color=COLORS["text"]))
                self.after(0, self._scroll_to_bottom)

            code, error = self.ai.generate(full_prompt, on_chunk)

            def finish():
                if error:
                    stream_label.configure(text=f"❌ {error}", text_color=COLORS["error"])
                else:
                    self.current_code = code
                    # Parodyti trumpą tekstą ir kodą
                    explanation = "✅ Kodas sugeneruotas!"
                    stream_label.configure(text=explanation, text_color=COLORS["success"])

                    if code:
                        # Kodo blokas
                        code_frame = ctk.CTkFrame(ai_frame,
                                                   fg_color=COLORS["code_bg"],
                                                   corner_radius=8,
                                                   border_width=1,
                                                   border_color=COLORS["border"])
                        code_frame.pack(fill="x", padx=12, pady=(2,8))

                        ch = ctk.CTkFrame(code_frame, fg_color="transparent")
                        ch.pack(fill="x", padx=8, pady=(4,0))
                        ctk.CTkLabel(ch, text="📄 Arduino kodas",
                                     font=ctk.CTkFont(size=10),
                                     text_color=COLORS["text_dim"]).pack(side="left")

                        lines = code.count('\n') + 1
                        code_box = ctk.CTkTextbox(code_frame,
                                                   height=min(350, lines * 18 + 30),
                                                   font=ctk.CTkFont(family="Courier New", size=12),
                                                   fg_color=COLORS["code_bg"],
                                                   text_color="#a8d8a8",
                                                   wrap="none",
                                                   border_width=0)
                        code_box.pack(fill="x", padx=8, pady=(2,8))
                        code_box.insert("1.0", code)
                        code_box.configure(state="disabled")

                self.ai_running = False
                self.send_btn.configure(state="normal", text="📨 Siųsti")
                self._set_status("")
                self._scroll_to_bottom()

            self.after(0, finish)

        threading.Thread(target=run_ai, daemon=True).start()

    # ─── Kompiliavimas ir įkėlimas ────────────────────────────────

    def _get_board_params(self) -> tuple[str, str]:
        """Gauti fqbn ir port"""
        fqbn = self.selected_fqbn.get()
        port = self.selected_port.get()
        return fqbn, port

    def _do_compile(self):
        if not self.current_code:
            messagebox.showwarning("Nėra kodo", "Pirmiausia sugeneruok kodą su AI!")
            return
        fqbn, _ = self._get_board_params()
        if not fqbn:
            messagebox.showwarning("Nėra board", "Pasirink boardą kairėje!")
            return

        self.arduino.save_sketch(self.current_code)
        self._set_status("⚙️ Kompiliuojama...", COLORS["warning"])
        self.compile_btn.configure(state="disabled")

        def run():
            ok, output = self.arduino.compile(fqbn)
            def done():
                self.compile_btn.configure(state="normal")
                if ok:
                    self._add_system_message("✅ Kompiliavimas sėkmingas!")
                    self._set_status("✅ Sukompiliuota", COLORS["success"])
                else:
                    self._add_system_message(f"❌ Kompiliavimo klaida:\n\n{output}")
                    self._set_status("❌ Klaida", COLORS["error"])
                self._scroll_to_bottom()
            self.after(0, done)

        threading.Thread(target=run, daemon=True).start()

    def _do_upload(self):
        if not self.current_code:
            messagebox.showwarning("Nėra kodo", "Pirmiausia sugeneruok kodą su AI!")
            return
        fqbn, port = self._get_board_params()
        if not fqbn:
            messagebox.showwarning("Nėra board", "Pasirink boardą kairėje!")
            return
        if not port or port == "Nėra":
            messagebox.showwarning("Nėra porto", "Prijunk boardą ir pasirink COM portą!")
            return

        self.arduino.save_sketch(self.current_code)
        self._set_status("📤 Įkeliama...", COLORS["warning"])
        self.upload_btn.configure(state="disabled")

        def run():
            ok_c, out_c = self.arduino.compile(fqbn, lambda t: self.after(0, lambda: self._set_status(t)))
            if not ok_c:
                # Auto taisymas
                self.after(0, lambda: self._add_system_message("⚠️ Kompiliavimo klaida — AI bando taisyti..."))
                fixed_code, fix_err = self.ai.fix_error(self.current_code, out_c)
                if fixed_code and not fix_err:
                    self.current_code = fixed_code
                    self.arduino.save_sketch(fixed_code)
                    ok_c, out_c = self.arduino.compile(fqbn)
                    if not ok_c:
                        self.after(0, lambda: self._add_system_message(f"❌ Nepavyko ištaisyti:\n{out_c}"))
                        self.after(0, lambda: self.upload_btn.configure(state="normal"))
                        self.after(0, lambda: self._set_status("❌ Klaida", COLORS["error"]))
                        return

            ok_u, out_u = self.arduino.upload(fqbn, port)

            def done():
                self.upload_btn.configure(state="normal")
                if ok_u:
                    self._add_system_message(f"🎉 Kodas sėkmingai įkeltas į {port}!")
                    self._set_status("✅ Įkelta!", COLORS["success"])
                else:
                    self._add_system_message(f"❌ Įkėlimo klaida:\n{out_u}")
                    self._set_status("❌ Įkėlimo klaida", COLORS["error"])
                self._scroll_to_bottom()
            self.after(0, done)

        threading.Thread(target=run, daemon=True).start()

    def _do_fix(self):
        if not self.current_code:
            messagebox.showwarning("Nėra kodo", "Pirmiausia sugeneruok kodą!")
            return
        fqbn, _ = self._get_board_params()
        if not fqbn:
            messagebox.showwarning("Nėra board", "Pasirink boardą!")
            return

        self.arduino.save_sketch(self.current_code)
        self._set_status("🔧 Tikrinama ir taisoma...", COLORS["accent2"])

        def run():
            ok, error_out = self.arduino.compile(fqbn)
            if ok:
                self.after(0, lambda: self._add_system_message("✅ Kodas jau teisingas! Klaidų nėra."))
                self.after(0, lambda: self._set_status(""))
                return

            self.after(0, lambda: self._set_status("🤖 AI taisomi...", COLORS["accent2"]))
            fixed, err = self.ai.fix_error(self.current_code, error_out)
            if err:
                self.after(0, lambda: self._add_system_message(f"❌ AI klaida: {err}"))
                self.after(0, lambda: self._set_status("❌ Klaida", COLORS["error"]))
                return

            self.current_code = fixed
            ok2, out2 = self.arduino.compile(fqbn)

            def done():
                if ok2:
                    self._add_ai_message("✅ Klaidos ištaisytos! Kodas sukompiliuotas.", fixed)
                    self._set_status("✅ Ištaisyta", COLORS["success"])
                else:
                    self._add_system_message(f"⚠️ Dar yra klaidų:\n{out2}")
                    self._set_status("⚠️ Dar klaidų", COLORS["warning"])
                self._scroll_to_bottom()
            self.after(0, done)

        threading.Thread(target=run, daemon=True).start()

    # ─── Kiti ────────────────────────────────────────────────────

    def _clear_chat(self):
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()
        self.current_code = ""
        self._add_system_message("🧹 Pokalbi išvalytas. Pradėk iš naujo!")

    def _open_settings(self):
        SettingsWindow(self)


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.config_data = parent.config_data.copy()

        self.title("⚙️ Nustatymai")
        self.geometry("600x600")
        self.configure(fg_color=COLORS["bg"])
        self.grab_set()

        ctk.CTkLabel(self, text="⚙️ Nustatymai",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=COLORS["text"]).pack(pady=16)

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["panel"], corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0,8))

        # ── AI teikėjas ──
        self._section(scroll, "🤖 AI TEIKĖJAS")

        self.provider_var = tk.StringVar(value=self.config_data.get("ai_provider","groq"))
        ctk.CTkSegmentedButton(scroll,
                                values=["groq", "ollama"],
                                variable=self.provider_var,
                                font=ctk.CTkFont(size=13)
                                ).pack(fill="x", padx=12, pady=4)

        # Groq
        self._label(scroll, "Groq API raktas (groq.com → nemokamas):")
        self.groq_key_entry = ctk.CTkEntry(scroll, height=36, corner_radius=10,
                                            placeholder_text="gsk_...",
                                            fg_color=COLORS["card"],
                                            border_color=COLORS["border"],
                                            show="*")
        self.groq_key_entry.pack(fill="x", padx=12, pady=2)
        self.groq_key_entry.insert(0, self.config_data.get("groq_api_key", ""))

        ctk.CTkButton(scroll, text="🌐 Atidaryti groq.com",
                      height=32, corner_radius=16,
                      fg_color=COLORS["card"],
                      command=lambda: __import__("webbrowser").open("https://console.groq.com")
                      ).pack(padx=12, pady=2, anchor="w")

        # Groq modelis
        self._label(scroll, "Groq modelis:")
        self.groq_model_var = tk.StringVar(value=self.config_data.get("groq_model","llama-3.1-8b-instant"))
        ctk.CTkOptionMenu(scroll, values=[
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "deepseek-r1-distill-llama-70b",
            "gemma2-9b-it"
        ], variable=self.groq_model_var,
            height=34, corner_radius=8,
            fg_color=COLORS["card"]
        ).pack(fill="x", padx=12, pady=2)

        # Ollama
        self._label(scroll, "Ollama URL (jei naudoji lokalų):")
        self.ollama_url_entry = ctk.CTkEntry(scroll, height=36, corner_radius=10,
                                              fg_color=COLORS["card"],
                                              border_color=COLORS["border"])
        self.ollama_url_entry.pack(fill="x", padx=12, pady=2)
        self.ollama_url_entry.insert(0, self.config_data.get("ollama_url","http://localhost:11434"))

        # ── Arduino CLI ──
        self._section(scroll, "🔧 ARDUINO CLI")
        self._label(scroll, "arduino-cli.exe kelias:")
        self.cli_entry = ctk.CTkEntry(scroll, height=36, corner_radius=10,
                                       fg_color=COLORS["card"],
                                       border_color=COLORS["border"])
        self.cli_entry.pack(fill="x", padx=12, pady=2)
        self.cli_entry.insert(0, self.config_data.get("arduino_cli_path",""))

        ctk.CTkLabel(scroll,
                     text="ℹ️ Jei arduino-cli aplanke 'tools' — palieka tokį: tools\\arduino-cli.exe",
                     font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"],
                     wraplength=540).pack(padx=12, anchor="w")

        # Mygtukai
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=8)

        ctk.CTkButton(btn_row, text="💾 Išsaugoti",
                      height=40, corner_radius=20,
                      fg_color=COLORS["success"],
                      hover_color="#16a34a",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._save
                      ).pack(side="right", padx=4)

        ctk.CTkButton(btn_row, text="❌ Atšaukti",
                      height=40, corner_radius=20,
                      fg_color=COLORS["card"],
                      command=self.destroy
                      ).pack(side="right", padx=4)

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLORS["text_dim"]
                     ).pack(anchor="w", padx=12, pady=(14,2))

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=12),
                     text_color=COLORS["text"]
                     ).pack(anchor="w", padx=12, pady=(6,0))

    def _save(self):
        self.config_data["ai_provider"] = self.provider_var.get()
        self.config_data["groq_api_key"] = self.groq_key_entry.get().strip()
        self.config_data["groq_model"] = self.groq_model_var.get()
        self.config_data["ollama_url"] = self.ollama_url_entry.get().strip()
        self.config_data["arduino_cli_path"] = self.cli_entry.get().strip()

        save_config(self.config_data)
        self.parent_app.config_data = self.config_data
        self.parent_app._import_modules()
        self.parent_app._check_ai_status()
        messagebox.showinfo("✅", "Nustatymai išsaugoti!")
        self.destroy()


def launch():
    app = ArduinoAIStudio()
    app.mainloop()

if __name__ == "__main__":
    launch()
