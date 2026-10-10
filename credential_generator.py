import base64
import hashlib
import subprocess
import io
import json
import os
import random
import secrets
import shutil
import string
import sys
import tempfile
import uuid
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import json
import urllib.request
import webbrowser
from tkinter import messagebox

CURRENT_VERSION = "1.0.2"
GITHUB_REPO = "gustav1230943-create/ACC-Generator-Releases"


def check_for_updates():
    """Prüft, ob auf GitHub eine neuere Version veröffentlicht wurde."""
    api_url = (
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    )

    try:
        request = urllib.request.Request(
            api_url,
            headers={"User-Agent": "ACC-Generator-Updater"}
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            release = json.loads(response.read().decode("utf-8"))

        latest_version = release["tag_name"].lstrip("v")
        release_url = release["html_url"]

        def version_tuple(version):
            return tuple(int(part) for part in version.split("."))

        if version_tuple(latest_version) > version_tuple(CURRENT_VERSION):
            answer = messagebox.askyesno(
                "Update verfügbar",
                f"Eine neue Version ist verfügbar: {latest_version}\n\n"
                "Möchtest du die Release-Seite öffnen?"
            )

            if answer:
                webbrowser.open(release_url)

    except Exception:
        # Das Programm soll auch ohne Internet weiter starten.
        pass


try:
    from PIL import Image, ImageEnhance, ImageTk

    PIL_OK = True
    _RESAMPLING = getattr(Image, "Resampling", Image)
    RESAMPLE_FAST = _RESAMPLING.BICUBIC
    RESAMPLE_BEST = _RESAMPLING.LANCZOS
except ImportError:
    PIL_OK = False

if sys.platform == "win32":
    import ctypes

    kernel32 = ctypes.windll.kernel32
    console_window = kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)
        kernel32.FreeConsole()

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAVE_FILE = os.path.join(BASE_DIR, "credentials.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
CUSTOM_BG_FILE = os.path.join(BASE_DIR, "background_custom.png")

DEFAULT_SETTINGS = {
    "email": "AllahGibtsNich@proton.me",
    "password_length": 16,
    "use_uppercase": True,
    "use_lowercase": True,
    "use_digits": True,
    "use_symbols": True,
    "username_separator": "_",
    "username_number_min": 10,
    "username_number_max": 9999,
    "auto_copy": False,
    "auto_copy_field": "all",
    "show_password": False,
    "confirm_delete": True,
    "bg_enabled": True,
    "bg_mode": "default",
    "bg_brightness": 55,
}

ADJECTIVES = [
    "silent", "rapid", "fuzzy", "neon", "swift", "dark", "cold", "wild", "lazy", "tiny",
    "fancy", "shiny", "brave", "quick", "sneaky", "grumpy", "spooky", "lucky", "chilly", "dusty",
]
NOUNS = [
    "panda", "falcon", "penguin", "cactus", "robot", "ninja", "comet", "wizard", "goblin", "raven",
    "titan", "pixel", "vortex", "cipher", "specter", "phantom", "dagger", "nomad", "glitch", "vector",
]

BG = "#0f0f0f"
CARD = "#1a1a1a"
BORDER = "#2a2a2a"
TEXT = "#f0f0f0"
MUTED = "#888888"
MUTED_ON_IMAGE = "#b8b8b8"
ACCENT = "#4ade80"
ACCENT_DIM = "#166534"
BTN_BG = "#ffffff"
BTN_FG = "#0f0f0f"
TAB_ACTIVE = "#ffffff"
TAB_INACTIVE = "#555555"
DANGER = "#ef4444"
WARNING = "#fbbf24"


def load_json(path, default):
    if not os.path.exists(path):
        return default.copy() if isinstance(default, dict) else default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict) and isinstance(data, dict):
            merged = default.copy()
            merged.update(data)
            return merged
        if isinstance(default, list) and isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        if os.path.exists(path):
            try:
                os.replace(path, path + ".bak")
            except OSError:
                pass
    return default.copy() if isinstance(default, dict) else default


def save_json_atomic(path, data):
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".cred_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Verschlüsselter Tresor
#
# credentials.json wird nie im Klartext gespeichert. Unter Windows schützt
# DPAPI (CryptProtectData) die Daten: Der Schlüssel gehört zum Windows-Konto
# des Benutzers. Die Datei lässt sich nur mit demselben Konto auf demselben PC
# entschlüsseln - kopiert jemand die Datei, ist sie wertlos.
# Auf anderen Systemen (Linux/macOS) wird Fernet (pip install cryptography)
# mit einem Schlüssel in der Benutzer-Home-Datei (nur für den Benutzer lesbar) verwendet.
# ---------------------------------------------------------------------------
VAULT_MAGIC = b"ACCV1"
VAULT_DPAPI = b"\x01"
VAULT_FERNET = b"\x02"
_VAULT_ENTROPY = b"ACC-Generator-Vault-v1"
KEY_FILE = os.path.join(os.path.expanduser("~"), ".acc_generator.key")


class VaultError(Exception):
    """Der Tresor konnte nicht gelesen oder entschlüsselt werden."""


def _dpapi_call(data, protect):
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def make_blob(raw):
        buf = ctypes.create_string_buffer(raw, len(raw))
        return DataBlob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    blob_in, _keep1 = make_blob(data)
    blob_entropy, _keep2 = make_blob(_VAULT_ENTROPY)
    blob_out = DataBlob()
    ui_forbidden = 0x1
    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(blob_in), "ACC Generator", ctypes.byref(blob_entropy),
            None, None, ui_forbidden, ctypes.byref(blob_out),
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, ctypes.byref(blob_entropy),
            None, None, ui_forbidden, ctypes.byref(blob_out),
        )
    if not ok:
        raise OSError("DPAPI-Aufruf fehlgeschlagen (Fehlercode %s)" % ctypes.GetLastError())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _get_fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise VaultError(
            "Für die Verschlüsselung außerhalb von Windows wird 'cryptography' benötigt:\n"
            "pip install cryptography"
        )
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return Fernet(f.read().strip())
    key = Fernet.generate_key()
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return Fernet(key)


def vault_encrypt(data):
    if sys.platform == "win32":
        return VAULT_MAGIC + VAULT_DPAPI + _dpapi_call(data, protect=True)
    return VAULT_MAGIC + VAULT_FERNET + _get_fernet().encrypt(data)


def vault_decrypt(blob):
    if not blob.startswith(VAULT_MAGIC) or len(blob) <= len(VAULT_MAGIC):
        raise VaultError("Kein gültiger Tresor.")
    method = blob[len(VAULT_MAGIC):len(VAULT_MAGIC) + 1]
    payload = blob[len(VAULT_MAGIC) + 1:]
    try:
        if method == VAULT_DPAPI:
            if sys.platform != "win32":
                raise VaultError("Dieser Tresor wurde unter Windows erstellt.")
            return _dpapi_call(payload, protect=False)
        if method == VAULT_FERNET:
            return _get_fernet().decrypt(payload)
    except VaultError:
        raise
    except Exception as exc:
        raise VaultError(str(exc))
    raise VaultError("Unbekanntes Tresor-Format.")


def save_credentials(path, entries):
    """Speichert die Einträge verschlüsselt (atomar)."""
    plain = json.dumps(entries, indent=2, ensure_ascii=False).encode("utf-8")
    blob = vault_encrypt(plain)
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".cred_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def load_credentials(path):
    """Liest verschlüsselte oder (alte) Klartext-Dateien.

    Gibt (Liste, war_klartext) zurück. Wirft VaultError, wenn die Datei
    nicht entschlüsselt werden kann."""
    if not os.path.exists(path):
        return [], False
    with open(path, "rb") as f:
        raw = f.read()
    if not raw.strip():
        return [], False
    if raw.startswith(VAULT_MAGIC):
        try:
            data = json.loads(vault_decrypt(raw).decode("utf-8"))
        except VaultError:
            raise
        except ValueError as exc:
            raise VaultError(str(exc))
        was_plain = False
    else:
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise VaultError("Datei ist weder Tresor noch gültiges JSON: %s" % exc)
        was_plain = True
    if not isinstance(data, list):
        raise VaultError("Die Datei enthält keine Liste.")
    return data, was_plain


def password_strength(password):
    if not password or password == "—":
        return 0, "—", MUTED
    score = 0
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in string.punctuation for c in password):
        score += 1

    labels = [
        (2, "Schwach", DANGER),
        (4, "Mittel", WARNING),
        (5, "Gut", ACCENT),
        (6, "Sehr stark", ACCENT),
    ]
    for threshold, label, color in labels:
        if score <= threshold:
            return score, label, color
    return score, "Sehr stark", ACCENT


def format_datetime(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%d.%m.%Y  %H:%M")
    except (ValueError, TypeError):
        return "—"


# ---------------------------------------------------------------------------
# Hintergrundbild
#
# tkinter kennt keine Transparenz. Damit das Bild trotzdem "hinter" den Karten
# sichtbar ist, bekommt jede freie Fläche (BgFrame / BgCanvas) genau den
# Bildausschnitt, der an ihrer Position im Fenster liegt. Die Karten selbst
# bleiben solide und liegen darüber.
# ---------------------------------------------------------------------------
class Backdrop:
    def __init__(self, root):
        self.root = root
        self.widgets = []
        self.source = None
        self.enabled = True
        self.brightness = 0.55
        self._version = 0
        self._job = None
        self._cache_key = None
        self._cache_img = None
        root.bind("<Configure>", self._on_root_configure, add="+")

    def set_source(self, image):
        self.source = image
        self._version += 1

    def register(self, widget):
        self.widgets.append(widget)
        widget.bind("<Configure>", lambda e: self.schedule(), add="+")
        widget.bind("<Map>", lambda e: self.schedule(), add="+")

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self.schedule()

    def schedule(self, delay=30):
        if self._job is None:
            self._job = self.root.after(delay, self.refresh)

    def _render_full(self, width, height):
        key = (width, height, self._version, round(self.brightness, 3))
        if key == self._cache_key:
            return self._cache_img
        src = self.source
        sw, sh = src.size
        scale = max(width / sw, height / sh)
        nw = max(width, int(sw * scale + 0.999))
        nh = max(height, int(sh * scale + 0.999))
        img = src.resize((nw, nh), RESAMPLE_FAST)
        left, top = (nw - width) // 2, (nh - height) // 2
        img = img.crop((left, top, left + width, top + height))
        if self.brightness < 0.999:
            img = ImageEnhance.Brightness(img).enhance(self.brightness)
        self._cache_key, self._cache_img = key, img
        return img

    def refresh(self):
        self._job = None
        width, height = self.root.winfo_width(), self.root.winfo_height()
        if width < 10 or height < 10:
            return
        full = None
        if PIL_OK and self.enabled and self.source is not None:
            full = self._render_full(width, height)
        ox, oy = self.root.winfo_rootx(), self.root.winfo_rooty()
        for widget in self.widgets:
            if not widget.winfo_exists() or not widget.winfo_viewable():
                continue
            if full is None:
                widget.apply_backdrop(None)
                continue
            cw, ch = widget.winfo_width(), widget.winfo_height()
            if cw < 2 or ch < 2:
                continue
            x = widget.winfo_rootx() - ox
            y = widget.winfo_rooty() - oy
            widget.apply_backdrop(ImageTk.PhotoImage(full.crop((x, y, x + cw, y + ch))))


class BgFrame(tk.Frame):
    """Frame, der das Hintergrundbild an seiner Position anzeigt."""

    def __init__(self, master, backdrop, **kw):
        kw.setdefault("bg", BG)
        super().__init__(master, **kw)
        self._photo = None
        self._bg_label = tk.Label(self, bd=0, highlightthickness=0, bg=BG)
        self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        backdrop.register(self)

    def apply_backdrop(self, photo):
        self._photo = photo
        self._bg_label.configure(image=photo if photo is not None else "")


class BgCanvas(tk.Canvas):
    """Canvas mit festem (mitscrollendem) Hintergrundbild."""

    def __init__(self, master, backdrop, **kw):
        kw.setdefault("bg", BG)
        super().__init__(master, highlightthickness=0, bd=0, **kw)
        self._photo = None
        self._bg_item = self.create_image(0, 0, anchor="nw")
        backdrop.register(self)

    def apply_backdrop(self, photo):
        self._photo = photo
        self.itemconfigure(self._bg_item, image=photo if photo is not None else "")
        self.pin_backdrop()

    def pin_backdrop(self):
        self.coords(self._bg_item, self.canvasx(0), self.canvasy(0))
        self.tag_lower(self._bg_item)


class CardCanvas(BgCanvas):
    """Scrollbare Fläche, auf der Karten untereinander liegen.
    Zwischen den Karten bleibt das Hintergrundbild sichtbar."""

    def __init__(self, master, backdrop, inset=0, gap=8, pad_top=0, **kw):
        super().__init__(master, backdrop, **kw)
        self.inset = inset
        self.gap = gap
        self.pad_top = pad_top
        self._cards = []
        self._busy = False
        self.bind("<Configure>", lambda e: self.relayout(), add="+")

    def set_cards(self, widgets):
        for item, widget in self._cards:
            self.delete(item)
            widget.destroy()
        self._cards = [
            (self.create_window(0, 0, window=w, anchor="nw"), w) for w in widgets
        ]
        self.relayout()

    def relayout(self):
        width = self.winfo_width()
        if self._busy or width < 10:
            return
        self._busy = True
        try:
            self.update_idletasks()
            inner = width - 2 * self.inset
            y = self.pad_top
            for item, widget in self._cards:
                self.coords(item, self.inset, y)
                self.itemconfigure(item, width=inner)
                y += widget.winfo_reqheight() + self.gap
            total = max(y - self.gap, 0) + self.pad_top
            self.configure(scrollregion=(0, 0, width, total))
        finally:
            self._busy = False


def link_scrollbar(canvas, scrollbar):
    def on_scroll(first, last):
        scrollbar.set(first, last)
        canvas.pin_backdrop()

    canvas.configure(yscrollcommand=on_scroll)
    scrollbar.configure(command=canvas.yview)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Credential Generator")
        self.geometry("620x720")
        self.minsize(520, 560)
        self.configure(bg=BG)

        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.credentials = self._load_vault()
        self._normalize_credentials()
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.render_history())

        self.email_var = tk.StringVar(value=self.settings["email"])
        self.username_var = tk.StringVar(value="—")
        self.password_var = tk.StringVar(value="—")
        self.password_display_var = tk.StringVar(value="—")
        self.show_password_var = tk.BooleanVar(value=self.settings.get("show_password", False))
        self.strength_var = tk.StringVar(value="—")

        self.current_tab = 0
        self.backdrop = Backdrop(self)
        self._sync_backdrop(reload_image=True)

        self._build_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._update_password_display()
        self.render_history()
        self._update_stats()
        self._update_bg_source_label()
        self.after(50, self.backdrop.refresh)

    def _load_vault(self):
        try:
            data, was_plain = load_credentials(SAVE_FILE)
        except VaultError as exc:
            backup = None
            if os.path.exists(SAVE_FILE):
                backup = SAVE_FILE + datetime.now().strftime(".gesperrt_%Y%m%d_%H%M%S")
                try:
                    shutil.copy2(SAVE_FILE, backup)
                except OSError:
                    backup = None
            messagebox.showerror(
                "Tresor nicht lesbar",
                "credentials.json konnte nicht entschlüsselt werden.\n"
                "Die Datei ist an das Windows-Konto gebunden, mit dem sie erstellt wurde.\n\n"
                f"Details: {exc}\n\n"
                + (f"Eine Kopie wurde gesichert unter:\n{backup}\n\n" if backup else "")
                + "Die Anwendung startet mit einer leeren Liste.",
            )
            return []
        if was_plain:
            # Alte Klartext-Datei einmalig verschlüsseln und ersetzen.
            try:
                save_credentials(SAVE_FILE, data)
            except (OSError, VaultError):
                pass
        return data

    def _normalize_credentials(self):
        for entry in self.credentials:
            if "id" not in entry:
                entry["id"] = uuid.uuid4().hex
            if "email" not in entry:
                entry["email"] = self.settings.get("email", DEFAULT_SETTINGS["email"])

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TScale", background=CARD, troughcolor=BG, borderwidth=0)
        style.configure("TCheckbutton", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TCombobox", fieldbackground=BG, background=CARD, foreground=TEXT)

    # ------------------------------------------------------------------ UI
    @staticmethod
    def _shadow_text(canvas, x, y, text, font, fill):
        shadow = canvas.create_text(x + 1, y + 1, text=text, font=font, fill="#000000", anchor="w")
        main = canvas.create_text(x, y, text=text, font=font, fill=fill, anchor="w")
        return shadow, main

    @staticmethod
    def _set_shadow_text(canvas, ids, text):
        for item in ids:
            canvas.itemconfigure(item, text=text)

    def _build_ui(self):
        self.header = BgCanvas(self, self.backdrop, height=76)
        self.header.pack(fill="x")
        self._shadow_text(self.header, 24, 30, "Credential Generator", ("Segoe UI", 18, "bold"), TEXT)
        self._subtitle_ids = self._shadow_text(
            self.header, 24, 56, "", ("Segoe UI", 10), MUTED_ON_IMAGE,
        )

        self.tabbar = BgFrame(self, self.backdrop)
        self.tabbar.pack(fill="x")

        self.status_var = tk.StringVar(value="Bereit")
        self.status_bar = BgCanvas(self, self.backdrop, height=32)
        self.status_bar.pack(side="bottom", fill="x")
        self._status_ids = self._shadow_text(
            self.status_bar, 24, 16, "Bereit", ("Segoe UI", 9), MUTED_ON_IMAGE,
        )
        self.status_var.trace_add(
            "write",
            lambda *_: self._set_shadow_text(self.status_bar, self._status_ids, self.status_var.get()),
        )

        self.content = BgFrame(self, self.backdrop)
        self.content.pack(fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._tab_frames = []
        self._tab_buttons = []

        def make_tab(title):
            index = len(self._tab_frames)
            outer = BgFrame(self.content, self.backdrop)
            outer.grid(row=0, column=0, sticky="nsew")
            inner = BgFrame(outer, self.backdrop)
            inner.pack(fill="both", expand=True, padx=16, pady=(0, 8))
            self._tab_frames.append(outer)
            button = tk.Button(
                self.tabbar, text=title, font=("Segoe UI", 10), relief="flat", bd=0,
                highlightthickness=0, cursor="hand2", padx=18, pady=8,
                command=lambda i=index: self.select_tab(i),
            )
            button.pack(side="left", padx=(18 if index == 0 else 2, 2), pady=(6, 8))
            self._tab_buttons.append(button)
            return inner

        self.tab_generator = make_tab("Generator")
        self.tab_email = make_tab("ProtonMail")
        self.tab_history = make_tab("Verlauf")
        self.tab_settings = make_tab("Einstellungen")

        self._build_generator_tab()
        self._build_email_tab()
        self._build_history_tab()
        self._build_settings_tab()
        self.select_tab(0)

    def select_tab(self, index):
        self.current_tab = index
        for i, (frame, button) in enumerate(zip(self._tab_frames, self._tab_buttons)):
            if i == index:
                frame.grid()
                button.configure(
                    bg=TAB_ACTIVE, fg=BTN_FG, activebackground=TAB_ACTIVE, activeforeground=BTN_FG,
                )
            else:
                frame.grid_remove()
                button.configure(
                    bg=CARD, fg=MUTED, activebackground=BORDER, activeforeground=TEXT,
                )
        self.update_idletasks()
        self.backdrop.refresh()

    def _build_generator_tab(self):
        stats = tk.Frame(self.tab_generator, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        stats.pack(fill="x", padx=8, pady=(8, 12))

        stats_inner = tk.Frame(stats, bg=CARD)
        stats_inner.pack(fill="x", padx=16, pady=12)
        self.stat_total = self._stat_box(stats_inner, "Gespeichert", "0", side="left")
        self.stat_last = self._stat_box(stats_inner, "Zuletzt", "—", side="left", padx=(24, 0))
        self.stat_strength = self._stat_box(stats_inner, "Stärke", "—", side="right")

        card = tk.Frame(self.tab_generator, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=8, pady=(0, 12))

        self._make_email_field(card)
        self._make_field(card, "Benutzername", self.username_var, on_regenerate=self.regenerate_username)
        self._make_field(
            card, "Passwort", self.password_display_var,
            on_regenerate=self.regenerate_password, last=True,
        )

        toggle_row = tk.Frame(card, bg=CARD)
        toggle_row.pack(fill="x", padx=16, pady=(0, 12))
        tk.Checkbutton(
            toggle_row, text="Passwort anzeigen", variable=self.show_password_var,
            bg=CARD, fg=MUTED, selectcolor=CARD, activebackground=CARD,
            activeforeground=TEXT, font=("Segoe UI", 9),
            command=self._update_password_display,
        ).pack(anchor="w")

        btn_row = BgFrame(self.tab_generator, self.backdrop)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))

        self._primary_button(btn_row, "Generieren", self.generate).pack(side="left", fill="x", expand=True)
        self._ghost_button(btn_row, "Alles kopieren", self.copy_all).pack(side="left", padx=(8, 0))
        self._ghost_button(btn_row, "Neu (ohne Speichern)", self.preview_only).pack(side="left", padx=(8, 0))

        hint_card = tk.Frame(self.tab_generator, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        hint_card.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(
            hint_card,
            text="Tipp: Strg+G generiert · Strg+C kopiert alles · Einzelne Felder über „Kopieren“",
            bg=CARD, fg=MUTED, font=("Segoe UI", 9), wraplength=500, justify="left",
        ).pack(anchor="w", padx=16, pady=10)

    def _build_email_tab(self):
        hero = tk.Frame(self.tab_email, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        hero.pack(fill="x", padx=8, pady=(8, 12))

        hero_inner = tk.Frame(hero, bg=CARD)
        hero_inner.pack(fill="x", padx=20, pady=20)
        tk.Label(
            hero_inner, text="ProtonMail", bg=CARD, fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            hero_inner,
            text="Deine feste E-Mail-Adresse für alle generierten Accounts.",
            bg=CARD, fg=MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 16))

        self.email_display_label = tk.Label(
            hero_inner, textvariable=self.email_var, bg=CARD, fg=ACCENT,
            font=("Consolas", 16, "bold"), anchor="w",
        )
        self.email_display_label.pack(anchor="w", fill="x")

        self.email_count_label = tk.Label(
            hero_inner, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9),
        )
        self.email_count_label.pack(anchor="w", pady=(10, 0))
        self._update_email_stats()

        card = tk.Frame(self.tab_email, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=8, pady=(0, 12))

        tk.Label(
            card, text="E-MAIL BEARBEITEN", bg=CARD, fg=MUTED, font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(16, 6))

        entry_row = tk.Frame(card, bg=CARD)
        entry_row.pack(fill="x", padx=16, pady=(0, 12))
        email_entry = tk.Entry(
            entry_row, textvariable=self.email_var, bg=BG, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Consolas", 12),
        )
        email_entry.pack(fill="x", ipady=8)

        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(fill="x", padx=16, pady=(0, 16))
        self._primary_button(btn_row, "Speichern", self.save_email).pack(side="left", fill="x", expand=True)
        self._ghost_button(btn_row, "Kopieren", lambda: self._copy_var(self.email_var)).pack(side="left", padx=(8, 0))
        self._ghost_button(btn_row, "ProtonMail öffnen", self.open_protonmail).pack(side="left", padx=(8, 0))

        info = tk.Frame(self.tab_email, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        info.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(
            info,
            text=(
                "Diese Adresse wird bei jedem „Generieren“ automatisch mitgespeichert.\n"
                "Änderungen gelten für alle neuen Einträge im Verlauf.\n"
                "Tipp: Strg+E kopiert die E-Mail direkt."
            ),
            bg=CARD, fg=MUTED, font=("Segoe UI", 9), justify="left",
        ).pack(anchor="w", padx=16, pady=14)

    def _build_history_tab(self):
        toolbar = BgFrame(self.tab_history, self.backdrop)
        toolbar.pack(fill="x", padx=8, pady=(8, 8))

        actions = BgFrame(toolbar, self.backdrop)
        actions.pack(side="right", padx=(8, 0))
        self._ghost_button(actions, "Export", self.export_credentials).pack(side="left", padx=(0, 6))
        self._ghost_button(actions, "Import", self.import_credentials).pack(side="left", padx=(0, 6))
        self._ghost_button(actions, "Ordner öffnen", self.open_json).pack(side="left", padx=(0, 6))
        self._ghost_button(actions, "Alles löschen", self.clear_history, fg=DANGER).pack(side="left")

        search_frame = tk.Frame(toolbar, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        search_frame.pack(side="left", fill="x", expand=True)
        tk.Label(search_frame, text="Suche", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(12, 6), pady=8)
        search_entry = tk.Entry(
            search_frame, textvariable=self._search_var, bg=BG, fg=TEXT, width=8,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)

        list_container = BgFrame(self.tab_history, self.backdrop)
        list_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.history_canvas = CardCanvas(list_container, self.backdrop, gap=8)
        scrollbar = tk.Scrollbar(list_container, orient="vertical")
        link_scrollbar(self.history_canvas, scrollbar)
        self.history_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _settings_card(self, parent, title):
        card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(
            card, text=title, bg=CARD, fg=TEXT, font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))
        return card

    def _check(self, parent, text, var, command=None):
        return tk.Checkbutton(
            parent, text=text, variable=var, bg=CARD, fg=TEXT, selectcolor=BG,
            activebackground=CARD, activeforeground=TEXT, font=("Segoe UI", 10),
            command=command,
        )

    def _build_settings_tab(self):
        container = BgFrame(self.tab_settings, self.backdrop)
        container.pack(fill="both", expand=True)
        self.settings_canvas = CardCanvas(container, self.backdrop, inset=8, gap=12, pad_top=8)
        scrollbar = tk.Scrollbar(container, orient="vertical")
        link_scrollbar(self.settings_canvas, scrollbar)
        self.settings_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas = self.settings_canvas
        cards = []

        # --- Passwort
        card = self._settings_card(canvas, "Passwort")
        self._settings_row(card, "Länge")
        length_row = tk.Frame(card, bg=CARD)
        length_row.pack(fill="x", padx=16, pady=(0, 8))
        self.length_var = tk.IntVar(value=self.settings["password_length"])
        self.length_label = tk.Label(length_row, text=str(self.length_var.get()), bg=CARD, fg=ACCENT, font=("Segoe UI", 11, "bold"))
        self.length_label.pack(side="right")

        def on_length(val):
            self.length_var.set(int(float(val)))
            self.length_label.config(text=str(self.length_var.get()))

        self.length_scale = ttk.Scale(
            length_row, from_=8, to=64, orient="horizontal",
            command=on_length,
        )
        self.length_scale.set(self.settings["password_length"])
        self.length_scale.pack(side="left", fill="x", expand=True, padx=(0, 12))

        checks = tk.Frame(card, bg=CARD)
        checks.pack(fill="x", padx=16, pady=(0, 14))
        self.use_upper_var = tk.BooleanVar(value=self.settings["use_uppercase"])
        self.use_lower_var = tk.BooleanVar(value=self.settings["use_lowercase"])
        self.use_digits_var = tk.BooleanVar(value=self.settings["use_digits"])
        self.use_symbols_var = tk.BooleanVar(value=self.settings["use_symbols"])
        for text, var in [
            ("Großbuchstaben", self.use_upper_var),
            ("Kleinbuchstaben", self.use_lower_var),
            ("Ziffern", self.use_digits_var),
            ("Sonderzeichen", self.use_symbols_var),
        ]:
            self._check(checks, text, var).pack(anchor="w", pady=2)
        cards.append(card)

        # --- Benutzername
        card = self._settings_card(canvas, "Benutzername")
        self._settings_row(card, "Trennzeichen")
        sep_row = tk.Frame(card, bg=CARD)
        sep_row.pack(fill="x", padx=16, pady=(0, 8))
        self.separator_var = tk.StringVar(value=self.settings["username_separator"])
        for sep, label in [("_", "Unterstrich (_)"), (".", "Punkt (.)"), ("", "Keins")]:
            tk.Radiobutton(
                sep_row, text=label, value=sep, variable=self.separator_var,
                bg=CARD, fg=TEXT, selectcolor=BG, activebackground=CARD,
                activeforeground=TEXT, font=("Segoe UI", 10),
            ).pack(side="left", padx=(0, 16))

        range_row = tk.Frame(card, bg=CARD)
        range_row.pack(fill="x", padx=16, pady=(0, 14))
        tk.Label(range_row, text="Zahl von", bg=CARD, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        self.num_min_var = tk.StringVar(value=str(self.settings["username_number_min"]))
        self.num_max_var = tk.StringVar(value=str(self.settings["username_number_max"]))
        tk.Entry(range_row, textvariable=self.num_min_var, width=8, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", padx=8)
        tk.Label(range_row, text="bis", bg=CARD, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(range_row, textvariable=self.num_max_var, width=8, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat").pack(side="left", padx=8)
        cards.append(card)

        # --- Verhalten
        card = self._settings_card(canvas, "Verhalten")
        behavior = tk.Frame(card, bg=CARD)
        behavior.pack(fill="x", padx=16, pady=(0, 14))
        self.auto_copy_var = tk.BooleanVar(value=self.settings.get("auto_copy", False))
        self.confirm_delete_var = tk.BooleanVar(value=self.settings.get("confirm_delete", True))
        self._check(behavior, "Nach Generieren automatisch kopieren", self.auto_copy_var).pack(anchor="w", pady=2)
        self._check(behavior, "Löschen bestätigen", self.confirm_delete_var).pack(anchor="w", pady=2)

        copy_row = tk.Frame(behavior, bg=CARD)
        copy_row.pack(fill="x", pady=(6, 0))
        tk.Label(copy_row, text="Auto-Kopie:", bg=CARD, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        self.auto_copy_field_var = tk.StringVar(value=self.settings.get("auto_copy_field", "all"))
        ttk.Combobox(
            copy_row, textvariable=self.auto_copy_field_var, state="readonly", width=18,
            values=["all", "username", "password", "email"],
        ).pack(side="left", padx=(8, 0))
        cards.append(card)

        # --- Hintergrund
        card = self._settings_card(canvas, "Hintergrund")
        self.bg_enabled_var = tk.BooleanVar(value=self.settings.get("bg_enabled", True))
        self._check(
            card, "Hintergrundbild anzeigen", self.bg_enabled_var, command=self._on_bg_toggle,
        ).pack(anchor="w", padx=16, pady=(0, 2))
        self.bg_source_label = tk.Label(
            card, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9), anchor="w",
        )
        self.bg_source_label.pack(fill="x", padx=16, pady=(0, 10))

        self._settings_row(card, "Helligkeit")
        bright_row = tk.Frame(card, bg=CARD)
        bright_row.pack(fill="x", padx=16, pady=(0, 10))
        self.bg_brightness_label = tk.Label(
            bright_row, text="", bg=CARD, fg=ACCENT, font=("Segoe UI", 11, "bold"), width=5, anchor="e",
        )
        self.bg_brightness_label.pack(side="right")
        self.bg_brightness_scale = ttk.Scale(
            bright_row, from_=10, to=100, orient="horizontal", command=self._on_bg_brightness,
        )
        self.bg_brightness_scale.set(self._bg_brightness_value())
        self.bg_brightness_scale.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.bg_brightness_scale.bind("<ButtonRelease-1>", lambda e: self._save_settings_file())

        bg_btn_row = tk.Frame(card, bg=CARD)
        bg_btn_row.pack(fill="x", padx=16, pady=(0, 14 if PIL_OK else 8))
        self._primary_button(bg_btn_row, "Eigenes Bild auswählen…", self.choose_background).pack(
            side="left", fill="x", expand=True,
        )
        self._ghost_button(bg_btn_row, "Standardbild", self.reset_background).pack(side="left", padx=(8, 0))
        if not PIL_OK:
            tk.Label(
                card,
                text="Pillow ist nicht installiert – Hintergrundbilder sind deaktiviert.\nInstallieren mit:  pip install pillow",
                bg=CARD, fg=WARNING, font=("Segoe UI", 9), justify="left", anchor="w",
            ).pack(fill="x", padx=16, pady=(0, 14))
        cards.append(card)

        # --- Speicherort
        card = self._settings_card(canvas, "Speicherort")
        tk.Label(
            card, text=f"Credentials (verschlüsselt):\n{SAVE_FILE}\n\nEinstellungen:\n{SETTINGS_FILE}",
            bg=CARD, fg=MUTED, font=("Consolas", 9), justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 14))
        cards.append(card)

        # --- Buttons
        card = tk.Frame(canvas, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack(fill="x", padx=16, pady=14)
        self._primary_button(btn_row, "Einstellungen speichern", self._save_settings_from_ui).pack(side="left", fill="x", expand=True)
        self._ghost_button(btn_row, "Zurücksetzen", self.reset_settings).pack(side="left", padx=(8, 0))
        cards.append(card)

        canvas.set_cards(cards)

    def _settings_row(self, parent, label):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 4))

    def _stat_box(self, parent, label, value, side="left", padx=0):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(side=side, padx=padx)
        tk.Label(frame, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        val_label = tk.Label(frame, text=value, bg=CARD, fg=TEXT, font=("Segoe UI", 14, "bold"))
        val_label.pack(anchor="w")
        return val_label

    def _primary_button(self, parent, text, command):
        return tk.Button(
            parent, text=text, bg=BTN_BG, fg=BTN_FG, font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2", command=command, padx=16, pady=10,
            activebackground="#dddddd", activeforeground=BTN_FG,
        )

    def _ghost_button(self, parent, text, command, fg=MUTED):
        return tk.Button(
            parent, text=text, bg=BG, fg=fg, font=("Segoe UI", 9),
            relief="flat", cursor="hand2", command=command, padx=10, pady=8,
            activebackground=BORDER, activeforeground=TEXT,
        )

    def _make_field(self, parent, label, var, readonly=False, on_regenerate=None, last=False):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(frame, text=label.upper(), bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        row = tk.Frame(frame, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        if readonly:
            display = tk.Label(row, textvariable=var, bg=CARD, fg=TEXT, font=("Consolas", 11), anchor="w")
        else:
            display = tk.Label(row, textvariable=var, bg=CARD, fg=TEXT, font=("Consolas", 11), anchor="w")
        display.pack(side="left", fill="x", expand=True)

        if on_regenerate:
            tk.Button(
                row, text="Neu", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 9),
                cursor="hand2", command=on_regenerate, activebackground=BORDER,
            ).pack(side="right", padx=(6, 0))

        tk.Button(
            row, text="Kopieren", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 9),
            cursor="hand2", command=lambda v=var: self._copy_var(v), activebackground=BORDER,
        ).pack(side="right")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(10, 16 if last else 0))

    def _make_email_field(self, parent):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(frame, text="E-MAIL", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        row = tk.Frame(frame, bg=CARD)
        row.pack(fill="x", pady=(4, 0))
        email_entry = tk.Entry(
            row, textvariable=self.email_var, bg=CARD, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Consolas", 11),
        )
        email_entry.pack(side="left", fill="x", expand=True, ipady=2)
        email_entry.bind("<FocusOut>", lambda e: self.save_email(silent=True))
        email_entry.bind("<Return>", lambda e: self.save_email())

        tk.Button(
            row, text="Speichern", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 9),
            cursor="hand2", command=self.save_email, activebackground=BORDER,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            row, text="Kopieren", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 9),
            cursor="hand2", command=lambda: self._copy_var(self.email_var), activebackground=BORDER,
        ).pack(side="right")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(10, 0))

    def _bind_shortcuts(self):
        self.bind("<Control-g>", lambda e: self.generate())
        self.bind("<Control-G>", lambda e: self.generate())
        self.bind("<Control-c>", lambda e: self.copy_all())
        self.bind("<Control-C>", lambda e: self.copy_all())
        self.bind("<Control-e>", lambda e: self._copy_var(self.email_var))
        self.bind("<Control-E>", lambda e: self._copy_var(self.email_var))
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", lambda e: self._scroll_active(-1))
        self.bind_all("<Button-5>", lambda e: self._scroll_active(1))

    def _scroll_active(self, units):
        canvas = {2: self.history_canvas, 3: self.settings_canvas}.get(self.current_tab)
        if canvas is not None:
            canvas.yview_scroll(units, "units")

    def _on_mousewheel(self, event):
        units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
        self._scroll_active(units)

    def _copy_var(self, var):
        text = var.get()
        if text and text != "—":
            self._copy(text)

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("In Zwischenablage kopiert")

    def set_status(self, text):
        self.status_var.set(text)
        self.title(text)
        self.after(1500, lambda: (self.status_var.set("Bereit"), self.title("Credential Generator")))

    # ---------------------------------------------------------- Hintergrund
    def _bg_brightness_value(self):
        try:
            value = int(self.settings.get("bg_brightness", DEFAULT_SETTINGS["bg_brightness"]))
        except (TypeError, ValueError):
            value = DEFAULT_SETTINGS["bg_brightness"]
        return max(10, min(100, value))

    def _load_background_source(self):
        if not PIL_OK:
            return None
        if self.settings.get("bg_mode") == "custom" and os.path.exists(CUSTOM_BG_FILE):
            try:
                with Image.open(CUSTOM_BG_FILE) as img:
                    return img.convert("RGB")
            except Exception:
                pass
        try:
            with Image.open(io.BytesIO(base64.b64decode(DEFAULT_BG_B64))) as img:
                return img.convert("RGB")
        except Exception:
            return None

    def _sync_backdrop(self, reload_image=False):
        if reload_image:
            self.backdrop.set_source(self._load_background_source())
        self.backdrop.enabled = bool(self.settings.get("bg_enabled", True))
        self.backdrop.brightness = self._bg_brightness_value() / 100
        self.backdrop.refresh()

    def _update_bg_source_label(self):
        custom = self.settings.get("bg_mode") == "custom" and os.path.exists(CUSTOM_BG_FILE)
        self.bg_source_label.config(
            text="Aktuell: eigenes Bild" if custom else "Aktuell: Standardbild",
        )

    def _on_bg_toggle(self):
        self.settings["bg_enabled"] = self.bg_enabled_var.get()
        self._save_settings_file()
        self._sync_backdrop()

    def _on_bg_brightness(self, value):
        percent = int(float(value))
        self.bg_brightness_label.config(text=f"{percent}%")
        self.settings["bg_brightness"] = percent
        self.backdrop.brightness = percent / 100
        self.backdrop.schedule()

    def choose_background(self):
        if not PIL_OK:
            messagebox.showerror(
                "Pillow fehlt",
                "Für Hintergrundbilder wird Pillow benötigt.\n\nInstallieren mit:\npip install pillow",
            )
            return
        path = filedialog.askopenfilename(
            title="Hintergrundbild auswählen",
            filetypes=[("Bilder", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((2000, 2000), RESAMPLE_BEST)
                img.save(CUSTOM_BG_FILE, "PNG")
        except Exception as e:
            messagebox.showerror("Bild konnte nicht geladen werden", str(e))
            return
        self.settings["bg_mode"] = "custom"
        self.settings["bg_enabled"] = True
        self.bg_enabled_var.set(True)
        self._save_settings_file()
        self._sync_backdrop(reload_image=True)
        self._update_bg_source_label()
        self.set_status("Hintergrundbild geändert")

    def _remove_custom_background(self):
        try:
            if os.path.exists(CUSTOM_BG_FILE):
                os.remove(CUSTOM_BG_FILE)
        except OSError:
            pass

    def reset_background(self):
        self.settings["bg_mode"] = "default"
        self.settings["bg_enabled"] = True
        self.bg_enabled_var.set(True)
        self._remove_custom_background()
        self._save_settings_file()
        self._sync_backdrop(reload_image=True)
        self._update_bg_source_label()
        self.set_status("Standard-Hintergrund aktiv")

    # ----------------------------------------------------------- Credentials
    def _update_email_stats(self):
        email = self.email_var.get().strip()
        if not email:
            self.email_count_label.config(text="Keine E-Mail hinterlegt")
            return
        count = sum(1 for e in self.credentials if e.get("email", "").lower() == email.lower())
        domain = email.split("@")[-1] if "@" in email else "—"
        self.email_count_label.config(
            text=f"Domain: {domain}  ·  {count} Einträge im Verlauf mit dieser Adresse",
        )

    def save_email(self, silent=False):
        email = self.email_var.get().strip()
        if not email or "@" not in email:
            if not silent:
                messagebox.showerror("Ungültige E-Mail", "Bitte eine gültige E-Mail-Adresse eingeben.")
            return
        if email == self.settings.get("email"):
            return
        self.settings["email"] = email
        try:
            save_json_atomic(SETTINGS_FILE, self.settings)
        except OSError as e:
            if not silent:
                messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return
        self._update_email_stats()
        if not silent:
            self.set_status("E-Mail gespeichert")

    def open_protonmail(self):
        webbrowser.open("https://mail.proton.me")
        self.set_status("ProtonMail im Browser geöffnet")

    def _update_password_display(self):
        password = self.password_var.get()
        if self.show_password_var.get():
            self.password_display_var.set(password)
        else:
            self.password_display_var.set("•" * len(password) if password and password != "—" else "—")
        self.settings["show_password"] = self.show_password_var.get()
        self._save_settings_file()
        _, label, color = password_strength(password)
        self.strength_var.set(label)
        self.stat_strength.config(text=label, fg=color)

    def _build_password(self):
        chars = ""
        if self.settings.get("use_uppercase", True):
            chars += string.ascii_uppercase
        if self.settings.get("use_lowercase", True):
            chars += string.ascii_lowercase
        if self.settings.get("use_digits", True):
            chars += string.digits
        if self.settings.get("use_symbols", True):
            chars += "!@#$%^&*"
        if not chars:
            chars = string.ascii_letters + string.digits
        length = max(8, int(self.settings.get("password_length", 16)))
        return "".join(secrets.choice(chars) for _ in range(length))

    def _build_username(self):
        adj = secrets.choice(ADJECTIVES)
        noun = secrets.choice(NOUNS)
        sep = self.settings.get("username_separator", "_")
        num_min = int(self.settings.get("username_number_min", 10))
        num_max = int(self.settings.get("username_number_max", 9999))
        if num_min > num_max:
            num_min, num_max = num_max, num_min
        num = num_min + secrets.randbelow(num_max - num_min + 1)
        return f"{adj}{sep}{noun}{num}"

    def regenerate_username(self):
        username = self._build_username()
        self.username_var.set(username)
        self.set_status("Neuer Benutzername")

    def regenerate_password(self):
        password = self._build_password()
        self.password_var.set(password)
        self._update_password_display()
        self.set_status("Neues Passwort")

    def preview_only(self):
        self.username_var.set(self._build_username())
        self.password_var.set(self._build_password())
        self._update_password_display()
        self.set_status("Vorschau erstellt (nicht gespeichert)")

    def generate(self):
        self.settings["email"] = self.email_var.get().strip() or DEFAULT_SETTINGS["email"]
        username = self._build_username()
        password = self._build_password()
        self.username_var.set(username)
        self.password_var.set(password)
        self._update_password_display()

        entry = {
            "id": uuid.uuid4().hex,
            "email": self.settings["email"],
            "username": username,
            "password": password,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.credentials.insert(0, entry)
        try:
            save_credentials(SAVE_FILE, self.credentials)
        except (OSError, VaultError) as e:
            messagebox.showerror("Speichern fehlgeschlagen", f"credentials.json konnte nicht gespeichert werden:\n{e}")
            self.credentials.pop(0)
            return

        self.render_history()
        self._update_stats()
        self._update_email_stats()
        self.set_status("Credentials generiert & gespeichert")

        if self.settings.get("auto_copy"):
            field = self.settings.get("auto_copy_field", "all")
            if field == "all":
                self.copy_all(silent=True)
            elif field == "username":
                self._copy(username)
            elif field == "password":
                self._copy(password)
            elif field == "email":
                self._copy(self.settings["email"])

    def copy_all(self, silent=False):
        username = self.username_var.get()
        password = self.password_var.get()
        email = self.email_var.get()
        if username == "—" or password == "—":
            if not silent:
                messagebox.showinfo("Info", "Noch nichts generiert.")
            return
        text = f"E-Mail: {email}\nBenutzername: {username}\nPasswort: {password}"
        self._copy(text)
        if not silent:
            self.set_status("Alle Felder kopiert")

    def _update_stats(self):
        total = len(self.credentials)
        self.stat_total.config(text=str(total))
        self._set_shadow_text(self.header, self._subtitle_ids, f"{total} Einträge gespeichert")
        if self.credentials:
            last = format_datetime(self.credentials[0].get("generated_at", ""))
            self.stat_last.config(text=last)
        else:
            self.stat_last.config(text="—")

    def _filtered_credentials(self):
        query = self._search_var.get().strip().lower()
        if not query:
            return self.credentials
        result = []
        for entry in self.credentials:
            haystack = " ".join([
                entry.get("username", ""),
                entry.get("password", ""),
                entry.get("email", ""),
                entry.get("generated_at", ""),
            ]).lower()
            if query in haystack:
                result.append(entry)
        return result

    def render_history(self):
        canvas = self.history_canvas
        entries = self._filtered_credentials()
        cards = []

        if not entries:
            empty = "Keine Treffer." if self._search_var.get().strip() else "Noch keine Einträge — auf „Generieren“ klicken."
            card = tk.Frame(canvas, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            tk.Label(card, text=empty, bg=CARD, fg=MUTED, font=("Segoe UI", 10)).pack(pady=16)
            canvas.set_cards([card])
            return

        for entry in entries:
            row = tk.Frame(canvas, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            cards.append(row)

            left = tk.Frame(row, bg=CARD)
            left.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            tk.Label(left, text=entry.get("username", "—"), bg=CARD, fg=TEXT, font=("Consolas", 10), anchor="w").pack(fill="x")
            tk.Label(left, text=entry.get("password", "—"), bg=CARD, fg=MUTED, font=("Consolas", 10), anchor="w").pack(fill="x")
            tk.Label(
                left,
                text=f"{entry.get('email', '—')}  ·  {format_datetime(entry.get('generated_at', ''))}",
                bg=CARD, fg=MUTED, font=("Segoe UI", 8), anchor="w",
            ).pack(fill="x", pady=(2, 0))

            actions = tk.Frame(row, bg=CARD)
            actions.pack(side="right", padx=8, pady=6)
            tk.Button(
                actions, text="Alles", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 8),
                cursor="hand2", activebackground=BORDER,
                command=lambda e=entry: self._copy_entry(e),
            ).pack(fill="x", pady=1)
            tk.Button(
                actions, text="User", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 8),
                cursor="hand2", activebackground=BORDER,
                command=lambda u=entry.get("username", ""): self._copy(u),
            ).pack(fill="x", pady=1)
            tk.Button(
                actions, text="Pass", bg=CARD, fg=MUTED, relief="flat", font=("Segoe UI", 8),
                cursor="hand2", activebackground=BORDER,
                command=lambda p=entry.get("password", ""): self._copy(p),
            ).pack(fill="x", pady=1)
            tk.Button(
                actions, text="Löschen", bg=CARD, fg=DANGER, relief="flat", font=("Segoe UI", 8),
                cursor="hand2", activebackground=BORDER,
                command=lambda entry_id=entry.get("id"): self.delete_entry(entry_id),
            ).pack(fill="x", pady=1)

        canvas.set_cards(cards)

    def _copy_entry(self, entry):
        text = (
            f"E-Mail: {entry.get('email', '—')}\n"
            f"Benutzername: {entry.get('username', '—')}\n"
            f"Passwort: {entry.get('password', '—')}"
        )
        self._copy(text)

    def delete_entry(self, entry_id):
        if self.settings.get("confirm_delete", True):
            if not messagebox.askyesno("Eintrag löschen", "Diesen Eintrag wirklich löschen?"):
                return
        self.credentials = [e for e in self.credentials if e.get("id") != entry_id]
        try:
            save_credentials(SAVE_FILE, self.credentials)
        except OSError as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return
        self.render_history()
        self._update_stats()
        self._update_email_stats()
        self.set_status("Eintrag gelöscht")

    def clear_history(self):
        if not self.credentials:
            return
        if self.settings.get("confirm_delete", True):
            if not messagebox.askyesno("Verlauf leeren", "Alle gespeicherten Credentials löschen?"):
                return
        self.credentials = []
        try:
            save_credentials(SAVE_FILE, self.credentials)
        except OSError as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return
        self.render_history()
        self._update_stats()
        self._update_email_stats()
        self.set_status("Verlauf geleert")

    def export_credentials(self):
        if not messagebox.askokcancel(
            "Export im Klartext",
            "Der Export ist NICHT verschlüsselt - alle Passwörter stehen lesbar in der Datei.\n"
            "Bewahre sie sicher auf und lösche sie nach der Nutzung.\n\nTrotzdem exportieren?",
            icon="warning",
        ):
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="credentials_export.json",
        )
        if not path:
            return
        try:
            save_json_atomic(path, self.credentials)
            self.set_status("Export erfolgreich")
        except OSError as e:
            messagebox.showerror("Export fehlgeschlagen", str(e))

    def import_credentials(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            imported, _ = load_credentials(path)
        except (OSError, VaultError) as e:
            messagebox.showerror("Import fehlgeschlagen", str(e))
            return
        added = 0
        existing_ids = {e.get("id") for e in self.credentials}
        for entry in imported:
            if not isinstance(entry, dict):
                continue
            if "id" not in entry or entry["id"] in existing_ids:
                entry = entry.copy()
                entry["id"] = uuid.uuid4().hex
            existing_ids.add(entry["id"])
            self.credentials.append(entry)
            added += 1
        try:
            save_credentials(SAVE_FILE, self.credentials)
        except (OSError, VaultError) as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return
        self.render_history()
        self._update_stats()
        self._update_email_stats()
        self.set_status(f"{added} Einträge importiert")

    def open_json(self):
        # credentials.json ist verschlüsselt und nicht mehr direkt lesbar.
        try:
            os.startfile(BASE_DIR)
        except AttributeError:
            messagebox.showinfo("Info", f"Der Tresor liegt hier (verschlüsselt):\n{SAVE_FILE}")

    def _save_settings_file(self):
        try:
            save_json_atomic(SETTINGS_FILE, self.settings)
        except OSError:
            pass

    def _save_settings_from_ui(self, silent=False):
        try:
            num_min = int(self.num_min_var.get())
            num_max = int(self.num_max_var.get())
        except ValueError:
            messagebox.showerror("Ungültige Eingabe", "Zahlenbereich muss numerisch sein.")
            return

        self.settings.update({
            "email": self.email_var.get().strip() or DEFAULT_SETTINGS["email"],
            "password_length": int(self.length_var.get()),
            "use_uppercase": self.use_upper_var.get(),
            "use_lowercase": self.use_lower_var.get(),
            "use_digits": self.use_digits_var.get(),
            "use_symbols": self.use_symbols_var.get(),
            "username_separator": self.separator_var.get(),
            "username_number_min": num_min,
            "username_number_max": num_max,
            "auto_copy": self.auto_copy_var.get(),
            "auto_copy_field": self.auto_copy_field_var.get(),
            "confirm_delete": self.confirm_delete_var.get(),
            "show_password": self.show_password_var.get(),
            "bg_enabled": self.bg_enabled_var.get(),
            "bg_brightness": self._bg_brightness_value(),
        })

        try:
            save_json_atomic(SETTINGS_FILE, self.settings)
        except OSError as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return

        if not silent:
            self.set_status("Einstellungen gespeichert")

    def reset_settings(self):
        if not messagebox.askyesno("Zurücksetzen", "Alle Einstellungen auf Standard zurücksetzen?"):
            return
        self.settings = DEFAULT_SETTINGS.copy()
        self._remove_custom_background()
        self.email_var.set(self.settings["email"])
        self.length_var.set(self.settings["password_length"])
        self.length_scale.set(self.settings["password_length"])
        self.length_label.config(text=str(self.settings["password_length"]))
        self.use_upper_var.set(self.settings["use_uppercase"])
        self.use_lower_var.set(self.settings["use_lowercase"])
        self.use_digits_var.set(self.settings["use_digits"])
        self.use_symbols_var.set(self.settings["use_symbols"])
        self.separator_var.set(self.settings["username_separator"])
        self.num_min_var.set(str(self.settings["username_number_min"]))
        self.num_max_var.set(str(self.settings["username_number_max"]))
        self.auto_copy_var.set(self.settings["auto_copy"])
        self.auto_copy_field_var.set(self.settings["auto_copy_field"])
        self.confirm_delete_var.set(self.settings["confirm_delete"])
        self.bg_enabled_var.set(self.settings["bg_enabled"])
        self.bg_brightness_scale.set(self.settings["bg_brightness"])
        self._sync_backdrop(reload_image=True)
        self._update_bg_source_label()
        self._save_settings_file()
        self._update_email_stats()
        self.set_status("Einstellungen zurückgesetzt")


# Standard-Hintergrundbild (JPEG, Base64) – wird verwendet, solange kein eigenes Bild gewählt ist.
DEFAULT_BG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBAUEBAYFBQUGBgYHCQ4JCQgICRINDQoOFRIWFhUSFBQXGiEcFxgfGRQUHScd"
    "HyIjJSUlFhwpLCgkKyEkJST/2wBDAQYGBgkICREJCREkGBQYJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQkJCQk"
    "JCQkJCQkJCQkJCQkJCT/wAARCAH0AfQDASIAAhEBAxEB/8QAHQAAAAcBAQEAAAAAAAAAAAAAAAIDBAUGBwEICf/EAFoQAAED"
    "AwEDBgYLDAcGBQQDAAEAAgMEBREhBhIxBxNBUWGyIjJxc7HRCBQVIyVCU1SBkZMWJDM0NUNSYnKSobMmRHSCosHSY2R1o8Lh"
    "J0Vlg5QXVYTxGMPw/8QAGAEBAQEBAQAAAAAAAAAAAAAAAAECAwT/xAAfEQEBAQEBAQEBAQEBAQAAAAAAARECMSESQTIDImH/"
    "2gAMAwEAAhEDEQA/AMNudyrhcasCuqxieT88/wDSPam3ulcPn9X9s/1oXP8AKdZ5+TvlIDVZ9Dn3TuHz+r+2f6133TuHz+r+"
    "2f602wjYVU5F0uHz6r+2f60YXS4fP6v7Z/rTZqMEU5FyuHz+r+2f60YXO4fP6v7Z/rTYBdARDkXO4fP6v7Z/rSjbncM/j9X9"
    "s/1pq1uUo0Ip0253D5/V/bP9aOLncPn9X9s/1pq0JVrUQ6bc7h8/q/tn+tHbc7h8/q/tn+tNmtz0JVkfYgcNuVw0+/6v7Z/r"
    "SzblcPn9X9s71puyPholmR9QUUuy43DI+/6v7V3rS7LlcNPv+r+1d603ZEepLMi4KVThlxuGn3/V/au9aVbcK7T79q/tnetI"
    "sjzjRLMi4IFm19d89q/tnetKNuFd89q/tnetJNj7EoyIoshUV1d89qvpld60oK+t+eVP2rvWk2xHqSjYkUdtdXfPKn7V3rSg"
    "r6755Ufau9aI2LTglGxKW4vjvt2v6Kyo+1d610VtcONZUfau9aAj7F3m1AYVtdj8cqftXetD27XfPKn7V3rQEfYu832Kg3t2"
    "r+d1H2rvWue3av51Ufau9a5uAIboQwPb1b0VdQP/AHXetD29XfPKj7V3rQ3M9CHNHqQFNdXfPKj7V3rXDXV3RWVH2rvWjOi7"
    "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"
    "5JndbzlWCCBsbQAOCVMYKOGYTAUIrzgJTCSkOASqySc7CSJzlHe7QlIqVdHanDHYwmoIAOSlYnc64NaiKbylVXOwU1GPjPMh"
    "HXjQf5qvWqgOG6KZ2uaavaN0ZHgwtDR5eJT61W7dA8FR0h5a6PdDdNSrHSwaA44JrR02g0UxBFuNAVkY6pvc4x7j1rTnwoJB"
    "/hKzCODdHBatdG/BVUP9i/0LOfa5HUnRyZc0VZNg4926Tn/YH0hRJg8in9ioty5SnPGI+kLPN+t9/wCVyciOR3Ijl1cZSL03"
    "kTh6byLOtG0nFYVtPHnaK5af1mT0rdX8ViW00R93bgQP6w/0rNuNcqzURg50SFIzFwpdOEzD/iCkJ2cU3pGZuFN51neCKvdc"
    "PGULOOKnK4eMoWoHFZaRU/EqOnUlPxKjp1plHS8Uzl8ZPZeKZzcVUT+yw+D5POnutQXdlvyfJ5091qCKhK38o1Xnn94qPvg+"
    "DXY/TapCt/KVT55/eKZ3fW3vH6w9KtjNivxMzjRPYWZ+hIws1Giewt0+lVlatihiKq/aZ/mrrRdCpux/4Kp/ab/mrjRLFdeP"
    "Fgo+DVTb1C2O91gHyhd9JAP+auVH8VVa+RZvlZ+0D/ALKmsEeehP6OP3+PT4w9KQp4+Gik6OLM8enxh6UK2FnFOWcE2ZxTqP"
    "gunLlSrOIVd2xYHzUjsdD/8AJWJnEKE2nbvPpuwO/wAlevDj1Wmx6cEfmuxLiI9SO2I9S5yOq12AYs9OOoEfxKkUxso3bZCP"
    "L6Sny7Tx5764QinRHXD0JSVXtsacPsFYP0mgf4gsXrqHGchbjtSzfs8zevHpCy650WhOMYXO3HbnxnVVTuhlbIDgscDkdhyt"
    "b2jxJR0V4gaXF8LWu14grOrjSeE7RW577jXcnFIy2yNZVta5rXP8TLXcD1cVlojXTtulv3Wkh0Z3xk6EdIz1qtyEGcQggfpE"
    "nBwkH3GrtThHViRjSA6SJzT4DunB6VHV9xaZjVNY6NvAOPxiqluJ6zVzI5RTNGdTu6q6WatY6RsRaQ48f1V54+6V0V5h5px8"
    "GUSYzqG9q1CzbXxbjaZjgXTSbzXn43aUZla/C4FmnQnFO/MmFR6TamKB/NOk3pB4xadFP2u9xVLxrg+lRrFofI2Fm8VyC4Ml"
    "du5SbJoposO6lFt3Iahxa/QFaZxYw4O4FGUXFWMAGHapdtTvfGRMPHHATKsqOaadQEjLcWMaSXHQ4VZrNpqKrDzDPzha8R4b"
    "r4ROgS1U9HWjfAJy1w4rkla1rtFVKm4TUtLAHvYXiXLznQN1ISjLoJ6rec/EeM5AyFnWvysE9WAS/GQBrrwUraQ9zDM/gT4I"
    "7FVLZSz3GbnJ3PDN4ncGgx0K7wtDICwDADcLVRSK2EVF9qZSM5fxU9QU2GgY1Ua2P7+lPU9WGiYMZwsw6p5TwBoAA+lO2M0C"
    "JCPBHalwF1kcqb3FubfUj/ZO9CohhV9rx95z+bd6FTjF2LPTXFMub7FNbJx7tfK7GPej6QmHN6cFLbMtxWy6fmz6Qsz1vu/F"
    "jciORiiuXVykIvTeROXJtIstabP4rHdo2fDdwOOM7/StifxWS7RR/DFb55/pKxY6xV52Yzom1MzFfTnH51neCkqiNNYGfftP"
    "51neCIt9d8ZQtQpqu+MoWoWVRVTxKjp1I1PEqOnWkMJuKZy8U9l4plLxTUWDZb8nyedPdaghst+T5POnutQVEJWflKp88/vF"
    "NLp+Iu8o9Kc1v5SqfPP7xTa4a0TvKPStJUVCzXgnsDdOCQibrwTyBuoRlZNlGlrJ+1wVwo1U9lwA2YfrBWyk0WK6TxPUR0AV"
    "fvbfhqpP7PoCn6I+KoW7szdqj+76AsqSpYtBkalStHDiaM4+MPSmdLC44UxSRODo9PjhIVpLOKdMTWNOo105cuizTwUPtCN5"
    "8Hkd/kphh1Ci723efF5Cr1SVCiPsRxGlmx9iUEfYsNWp20jFviHl9JTxNbYPvKMeX0lOl058cr6CBQQK0iM2hbvWxw/Wb6Qq"
    "DcKfOdMq/X5wNvcP1gqbWsGui5dfK68eKHdabdcdFY9lmF+xU8bNTHM8hp4HKi7vE3LtFL7HOxYayPoy44WXRSLjViqhlZJv"
    "CZvDI8ZZ3drddqYcxR1EjonHRrn43Nckn61c9pJ/ahkZvPA3jgNUG2vjrHMppGhxyAS7446iqxWa1eaXf50tM7xulwPBvapK"
    "n2praAuqnSCN4DQGgF2cfono4K17TWKjmpQ+GBsUgJcXb2Dp0Y7VRbxHQsjDBUyvcM+A6PAb9OVuMVYbTtzIyaLnat/vszw/"
    "A8JoxoVa7bt+326wx1xja1m4Rw3u3yrFTIY3yubI17y3dGO0pGnmqt7eDuCflP1Y9WWDlRp54S2aoacHGR0p9/8AUKhkqmNj"
    "laSRklx4BeVGXGqijZGyVzWt6inNNeayA7xle7s3lPy1OnrOPb63OaHGdgz0dKZVvKjbIC4MmjLW6OLjgg9WPoXlZ+0lfFLv"
    "8485BGN4jpSTamqrDmSQ7z+LjxT8n6bvfeWFtZJJS2+Jw3g1jhkjU9IP0pGzXCoo2OiMj2zP8IFwx05B8qzPZuhjqp2yTzZa"
    "1oIa/gSCFoduY+tqhHRtDGgDLnDe3tdD2cCpY1zVsfeqo0sTJy2SduQzXOSetWew2N72Qy1BcGsGQze0Luv/ALJC0bPOmkEl"
    "Qxha0ANLeJ68/wAFcoqATBm9lrGkENBxlZjWnVBDzYBIUm1+G8E2aQ3GiNzmi0yhIiH1kx/XKsFEAGqr00v3zL+2fSrJQyZa"
    "oiXiGgSwTeF/ghLA5XWMdE60ZpJh+ofQqoI8q2VX4CQfqlVvc0Gix01wbmLsUjs+zdq5D+pj+ITYsyn1lbipf+wpIvV+JlyI"
    "5GKK5bYhF6byJw9N5FGjaRZbfYs3WrP+1d6VqUnSs3vcW9cKo41Erljp0lVioj4plEzFbB5xvpUtUx8VHsYfbcPnG+lZVYq7"
    "i5QlR0qZrulQtR0oI2p4lR06kKjiVHT9K0yYS8Uzl4p3NxTKXxkkRYdlvyfJ5091qCGy35Pk86e61BVUDW/lKp88/vFN605p"
    "HD9YelL1pHunU+ef3ikKvWmPlHpWksNYW6hPoG9ibQt1CewN0USRP7N8Jv2grTSnUKsWEbof2kFWSlOoWW1go9MHqUZdGZuk"
    "3930BSNG4FuEzrW71xl06vQFlS1Izgpijb4cX7YUfSQjRTNHE0PYe0Kwq5RHwQE6jTOLgE7Yt6xThvQmF31fH5CnrCBhM7nq"
    "+PyKMmAbgI4bxQRt7ClWpi36Ukf0+lLl3amlHIBTM+n0pR0o610lc8LlwRC8AHJTZ9S0JCSrx0qWtSCXyVvtE6/GCqFdM0Z1"
    "U1f6/dosZ4uCpdwuA11XPqunMRt2nblykdkKlrbdVDow4/xCrFfWb7iM8VIbMVnM26pkdncdlgI6+P8AkprSo7fAl73hujXb"
    "3gjiqNTVTnyjwt3qd1K7bWy882RgJJPT0LOqvML91ui6cufTQrNLHcIXQVjd6ocMF3AOHQVT9qdj+fk5yA829oI3ODc9adWC"
    "tkaxkT5Hb7dWkngehWe4TRVdLpgP3QXAJuHrFKuxT00hbI9n93pSMVO6MYxkK23uilE2QMtKhTbapzvAbkdiusWGXNtA1bqm"
    "lS50Yy0KaFnrnfmiU7pdjq2rIDoXEHowrpirwB843hrhWOzWWVzfbEgwCMNbgklXPZ/kvq3ygSUjC3qK0mg5PwxkeIImOa0N"
    "B7Fm9NTln2yuw09dLvPjfHGfFaR4xytl2Z2Iitkj5SQ90jQ36B0KWs1jZRU7BuNc4dSsNPTtGHFuAOCzrXgU1G2nYBgJwNAj"
    "kgpvNK1jckoR2SXdTf2w4nimtTVgBN6GrM9VuDgEVFUtY01Mu7K13hnOOg54Kz22rBGrlglXf6jZHlDqKCvlPM12ZWZ6CSdF"
    "rFnu0cgb4WQRkFBf6Wdp0ynrHhVujrmu3ev0qViqgcYP0LUrHUP5z7xJ+yVBAaKTlqMwSDPxSolsgwpSTB91PLSMVDz+qmO+"
    "D0p5anjn3/sIt8SxPBJuK4XhEdIFpiOOKbyFHdIEg9wKlrRKV2ioN3Zmuqj1yOV7kcNVSbq0GrqNPjlYb5VqpYdVHNaRVx6f"
    "Hb6VNVTAoxzR7Yj/AGx6VGkjXHioaoPFS1cdXKGqDxQR1RxKj6jpT6o4lR9R0rTJhMdU0kPhJzMfCTSQ6rSJ/Zh27Qyj/anu"
    "tQQ2W1t8nnT3WoIagq0/CVT55/eKSm1hI7V2uPwjVHqmf3iiOO9GVQIRqE9hGhTSHoT2DgpROWY43voVhpXahV21nj9CnqZ2"
    "oWLWlgoncESdua158noCJRSDRGdIH1TyD0gfwUVI0w4KXpeLfKFE03QpWleMtHaFYVa4XjdHkThsii46gADVLCpwc5WmKk2y"
    "6hNLjKC9mNdEgKzXimFxrfDZr0Ikh0ZgOKSdU4zrhRMleBxcU1lubP0lnWsW+mrsUzdUnLcO1VuC6t9rs8JNqm8NBxlWH5WO"
    "W446UxnuZ11VXrL+yGNz5JQxg4knACoe1HLJYrAwtNV7amPCOAg/xUX5GibRXP70b+319hVPnqZJs7gcfICVjN99kDcawc3b"
    "7bFA0OzvzHfJ+hUu7cpO1F9a2Cpuk0UAdnm4Pe2n6lr8p+p/HoC/3e2WK0S3G5V0TCGkMp43h0sh6sDh5Sn+yVzfftj6W6Qx"
    "Nhjm3nCMa41K8oz1kspIL3Y7TqvSPsYdo6e47PVmzlU0F1PLvxZ6nap+Wf1pLaCocHlvT1Km1bd+Ulahyi7HVMEslTS5fGNc"
    "NWWSGWOTdlaW+VNxOilLIY5OBPkUu2ukwMHUDBUTGejglWSuaccSrDT987Zn5laM9YT+1UNHLOA5wYD/ABUGS5xyAnEUrYnB"
    "x0cOCtWNMtmy4qmsMDGSdQwrNQ7ICGQSFm6Mdaq+wN/9+jjfMxzAQPGWqNdlc7W5IY0luZDGARw609jha1wOAUsyIOGSlo42"
    "M6FUdhYT0YTxg3W46ki1zQFx8xaMBCwpLJu6KOrKpoaQUWqq8Z1UBcLkGg5KLzBbncgzQHKVsb3vZLUtGcjdb5VA00NReqzm"
    "Is68T0AK7UdFHRUO61hEcXSetZ9WvNHskX+1dq7bMzx3QDJ+lTXJfyiw3CGKiq5N2pjAbknxgoH2SXh3e2zHi4Pz9ax+huEt"
    "BM2WF5jeDkELpOXPcv17jt14buNOcjryp2mue9g9C8z7C8r8UkbKS6PDXtwBITo5a1a9qKaeNskNQ1zT+ss2LsrSjct6KQZO"
    "jSo1ldnHhFV5t7BhkdvjBaUyivQOPDWWoujazTxk9tlZ787Xi3CpEd4zjw1I2y7jnneHwblaRd/bn6yIavtVe91Wni9c91Gd"
    "aaflYTUgjVySfOOgKE902fpLnug39IqfoxLSTcdFUri7eqJT2qUfcB+kVXK2sbz0nhHimrIa1Q0US78O39oelO56jezqmL5P"
    "fG+VRTusfqVEVDhkp7VTbxOqjah4BKBlUOGTqo6oeOtO6h4yVHzvC0yayHBKZzP1KcSuTOVwGi1qLLssfg+Tzp7rUEXZVw9z"
    "5POnutQRFer3fCFV55/eKKw5BCTuDsXCr8/J3iuRyBVJTqIYIT2HgmLHApzFIAQCpWkxRyc2Qc6Kap6lvWq1BLunOdFIQT4x"
    "ros1VmirmtI3SnEE4acniTnKr8U4BynUdbg9izjWrTT1jcAZUhSVbTINeCpzK0A6aJ3HczGNCmGr0LiwcSm9XeebcGh51GVU"
    "Pdh+DqU1qLq57g7eIwMK/U+La+/SA6SEJpU3x0njPKp9XfIqVnOTTtjYOJccBVu4cptioi7Nc2Rw4tYclVNaNNdSRo4lM5rg"
    "/rKx2u5Z6mrl9r2O2yvfqN+UZ/wpAXLlCufvtTUx2+F/Xhjj5GjVML00HaHlNt2z7TA+odJKOMbOIWeXzl2uUzHR26Lmmng5"
    "+D/AK0s2Kv8AWWvnrhZZ7hE5ngvZFuHGOOeJWW7U7Gso4n1tvZO2NjiJYJRh8eFrGb1f4i7vttfryMVdyqHt47u+QPqCr8sr"
    "nklxJPaunQlJF29otY57aLneKMSAAF0DCI7iqAOK1PkAubqDaqWMPLd+Pe8uFlo4q28mtwFr2toZ3Ehjnbhx2qW/Fnr3VBBT"
    "XygaXhpcR9az3a/kwglBkZGdeloxjyq3bIVZfAwA8BqriAyduHtDgegrm615NvGyVVaZSA1z2BRDqbD9/VpC9RbRbEQ3BrnU"
    "7Wgng3CybaLYeSkc4GAxP7RoqzYzkNP6YCMYyxu845UhV2aSJxa4OGOkJFkUsQ3Th7B0YyVZUkJUE9VSyskpnEAHJwtd2X2l"
    "uVRHGJ3A50z04We22WPeA3dRwJ6FcrVVBuNM/SsdNyNJpKx7mdP0p6yfTLiqjRXUMaN6QeTKem7tI0JKjViwPq2AcUyqbiGt"
    "zlQst1A68qJq7qXEhpIVJEncLrj/APahoxUXaq5qIadLuhoR6S11NzHOPGYv4q7bPbLCNjXTMEUB13Tq5/lSA1is0VPEIYRl"
    "v52X9LsCc3aYcxzEXgsAxgKWme2OERRN3QBjKgrid2Jz8KxNeXfZIVsbtoKGjb40UW+R1ZWMOOCr1yuXb3Y26uMgfvsiIiaf"
    "JlUN5w5bjl1dpWKQsILSQexS9LtJXUjRzVTIwjtUI1yOHBWxFypeVO/UzNxtUT2lTlo5abpA4Nq4Y6hvXwP1rLnjdGQjQyZc"
    "B1pZFnVj0VZOVSzXRzI3yPp5T0OGmfKrUNoaenaJfbsEQ63v3T/FZhyfbES1kdJFRPpRcKrwjJLqWt7AtffyIPbRjn7y6qld"
    "4rZ4stz1A9C5tyo9+2FKMZulM3yyDJXBtcHcK0fSsy5RG0FDWvsF3ElBUw4Iexu8PLoqrBZrzgPsd3hrozq2Mvw7HkKth+no"
    "mmvsrox74SlvdqT9Irz1T7e7SWFxgrqGQ7pxkjCnLVyuwTOa2siLHdbVPyv61tYvTs+MVGTXDflecnUqsUW0dPXwiaCUOaej"
    "Oq665bzic8VLFlT8lYP0imslZjpKhn3HtSL7jnpVnJqWmrXHg8phPWPcfGTKStG7xTaSrajOnE9S8k4ckHSOdxKayVILjglJ"
    "e2T1rUiaXlfxTSR+SivqMk5KQfNqqlq17LP+D5POnutQSGyr/g+Tj+FPdagiartxl+EKrz8neKSZOMprc6jFyqx1Tyd4psKr"
    "XiUE0ypGeKcsqQBqq77c7UoK848ZDVmjq8DOU6ZWjd4qqMrzjxkuyvOOKki/pbY647vjJYXHHFyqD7zDTM3p52RD9dwyoyp2"
    "9ooXlkG/UOH6PBMP20gXNu6PDSVRf6ekjMk87Y2Dpc7Cyyq2i2guYLadjaWP9JxA/io6SGjad673l87j40MOp+sqzk/bQLry"
    "r22gJbCZKhw/ROAVXZ9u9qNoJTHbqJzGH4wbwVXF+ttES2htUZcPzk/hE/Qkq3a661cXNOq3xs6GxDcA+pX8petS1Zba+odz"
    "l9vjYxxDA/ecPoCL7e2StYxFS1VxnbpvyO3WZ8iqheXkkknynJXCWjicImrHNtvcCNyjjp6GPhiGMA/XxU9yWbT0Nt25oq/a"
    "CR08O9xlO8ATpk5VEpqeeqlDKaF8xdwDBklTtPsXdXhrqnmKJh13qiQN/hxTNNe44dsdl6e1yV093ovajG7wIeB9C8ybSbZw"
    "bZbQXySmgY22RxuEZDcF46z/AAVQprRZYAKarvFXcJHnSGkzuZ8pSm11xtuzVo9zrbCYKuoGH+Fkho6z9Ki6zSZ+JHAdeEWN"
    "uRkopBc7tKX3cNAC0ySdoVzBXfj4RgEBApO2zmlmhnacOje1/wBRTADVOKc64Uqx7d5OLmytttNUZ/DMa5aVTuBAXnrkDvvt"
    "7Zqngc73ylcY3A8Qt/tsnORg5WP63bqRboUhX22muEZZURNeO0JZqVByFU3GbbQclDa1zpLfNgnhHLw+tZ7deT65W17nS0sj"
    "QOloLgfpXoxcIByCAQeOQh+nmJ1olpm7zocduEtT1RhIB0wt6uWxtruGXCPmXniWaA/QqLfeTZkTnPa/DehzWrLcqnw3JrXZ"
    "CXF3J6Sjy7F1kbvAZI9vXuEJel2Or5HDEbnE8BhF0zfXyTeKTorRsxsbW3Tdnm8BjtcHoCmNkuTk01S2tuTsADwYR09pWgBj"
    "IYwyNga0dASJajLbY6S1xBrGbx6z1p1K84wNAlJHapGQjC0z+jaUKs7YVjbfZKypccCGJzyewBWd2pWT+yFvfuPsHUxMk3Za"
    "17YGDrGclT+pryJdqp1ZX1NY85dNI55+kqKcclP6vxMqPK6SMugowKKgmIOdRhFY/mnhxGmV0LkrcsJ6kGr+3rjTe4W0Nhe9"
    "8tKwHdiGcdhC1j/+U1C21x+3LLNFcWjD2nG6T2H/ALLz7sJtibPI6hrJ3R0shG68fEVju9fVRu3auipLlSSAFj+b1I/aHSst"
    "K3tvtZVbZ7QVF2qt0GTRrR8UdSghPLA4Pikcxw6WnCs7oNl655bNFV22YcC3D4wT/FNp9jpZml9suFFXt6GtfuvPkaVZAypd"
    "r7vTAsdO2dn6Mrd70pyL1ZrhHi4WkRS9ElOQ3H0KIrLRcKAn21SSw4OPCaU1VZtWeGhhL/gm8tYRqGS+CR/FSUG0G01nw6qg"
    "NRDw3w3OR5VRgXN4HCdUt3r6LSGqkaP0c6KYa0Kl5QKWoDRUROgd0niFKxXumqcczM14PSCs4G0cdT4FZRQvJ4PaN1yVgNsm"
    "w+kq5aV/VLwH0pi60GavwNNUga/KpRrLvSjwJDUx9fEFdZtS7G7NHuOHEYUTVwNdxSTq7VVyO9xTEBsrcnoS4rHOGQ7IVkVM"
    "urNeKIakHpKiPbJ6SjCoJ6Uw1f8AZaYe58mp/CnutQUbstVH3Pk86e61BRNVy6T/AAlVnrnk7xTF05wjXOT7+qnHgJXn/EVW"
    "qq8VD5HMpmE9rlRPmoA8Z2EkbpAJBG2Tfe44a1upJVcdHUzeFV1HNtd8Te1VhtdLbrdQvrJtxsgHvO9xz1qglwu9Rb5xCaWQ"
    "vxnBCaS3C7Vcerm0sZ4ZOE9ve2NWykjjjipy54J54s8IeRU81cr3te97nuByd46FBPU1vZWVTYXzzVcsrg0BmuNVK3ulr9mK"
    "11FSW/BaARMI88R1qxbL3G2WKyurrrJSx1EgzCxgy4DrXdoeUS5m1MdbuamEhwZCzekaUGZ1lbW1EjjVSvc48QUg06qWistx"
    "ujnVE+5FvHV0p3cpdlotNCMVNa+pf8nAM/xQRTTkJ3TWS4V7gKekkcD8bGAPpU1Dc4acNjtlkia8cJJRvH1JZlLfLm/eq6p0"
    "cXVkNA+hAhFsnBRDnLtd6WlA1MbDvuISsEmz9GXClttVXv8Aiuldhp+hKOt9itnvlZcGyO6WsOcrj9s7TQOIt9qikcOEkjjk"
    "oHlPdtoa1ggtlLFb4zw9rRAOP97ilBsy4E1N9u7I5Dq4SS77iqzXbc3msaWMnEDT0RjAUBUVM9S8vmlc9x4klBdajai07Pl4"
    "tDX1NVjdE0gG63tCplZWz19S+oqHl8jzkkpFq6eCAMbvPz0I7kIBoT1hB2gQJ/GSg4JNvjJToQBKw+MkUow4KDY/Y/X32jtF"
    "U0DnENqGiRgJ0yF6xsk5bG0E8V4X2Cu5s21dsrD4gkDHY7dF7hsx3oo/oXOunKyxv3glmcEyhfrhPGOyrEpTKG8ggqjhdhY7"
    "y18slu2Ekp7WyI1dZKOclZG/dMbPL1nqVs5WuUmh5NdmZa+Y79bKCylhbxe/oPkXhi+Xqu2iutRdLjM+aqqHl73OOfoCkhbj"
    "dpfZVblOI6bZ/cJ4vkmLiB2LR+RDlmtnKE6ooZmtp7jCN8Mfj3xvZ5F40OoT7ZfaGu2Q2go73b5HRz0r94YPjDpB7CrYn6fR"
    "4oj3ZVf2F2yo9udmKK+UTm7lQwbzQfEd0g/TlTrjlZalJyccpAlKy4ASBC0uOEZXmH2U+0IqLzb7FA84p2maQA6ZPD/Nennv"
    "bHG57jgNGT5F4T5VdoTtFtxdrgHB7OeLIyOG6DgehJGbVMqnaFvUmiUmfv57UmAtRB0EEFUcC67gVwI41UCGMaKcs+1lysre"
    "bhlD4OmORoIULIN16M0aILsNrrFdCPdK3Ohf0yRepB9ktlfmS1XWLf4hrjuOCpJahukIsq9/0mtUW7zzp4RpzcmHtx5frTGe"
    "uoKp7m3O0Niccbz6bwTntCgKK+3G3vDoaqTA+K45Clo9thNgXGihmz4zxkEog77FbK1pdQ3JjJePNz+AfJlR1XYK+lBfzQkY"
    "PjMOQnoqLLc3+9PfTuPAP4fWjmkrKU79HVZA4bjsoK69j2HD2FuE7tdNFWVTY5amOmB4PfwUw65TOG7X0MUzv0y3wj9KaSwW"
    "ypJ3C+F/6J4BBfLPsXTUFNLJUXSCobKwsYYnZAKq98tNXbXviq+alY3g46E9qENwqLZQsgonRyuacl4OQkr5tM2+0jG11M+K"
    "qj4SN0DvKgjKOjprhLzbJm0zzw3zofpU5JZnW6gDBUxuqCSQAc5CqAd1KVkufMwwAQlwLfGJwSgXfXTU4xPHqOnoKVp7rDJg"
    "Zwe1RtwucT2MkhLt7GHMdqEyNTTygEs3HfqoNT2Wqovc+Twx+FPdagqjszWxsoZRzz/wp7rUEBb9c4qapqGg7znSPyP7xVVm"
    "rJJCQ3DQTnRHu0zprjUvPTK/vFIx00kgBDSO0oEy97tC4lO46evu0jcCR4JxnGgCI6ljjbl9Q0HqaMqy2e8U1opi4mSWR7S0"
    "D9FQFuGw9aYon0nNyMDfDJkGhUG6yvgcRPPDHjtypGtuc1ZHuQmSPr6Mpk6jiY0vllAPb0qhRraFpD5TNVOHDPBPWVtUcx0l"
    "PHA08McQo5tfSwjcYznMdJCLLeqpzN1hEbeoIJQ0c0w3qyqH95yDamz0Ou66eUdfBQD6iSZ2Xvc4nrKIgscm1ro2gUdMyIj4"
    "yiau8V1cTz87nZ7UyLsLqDn0n6UEEEHUEEEHMIr0dJjwnIFohus1QeF3oXCUCY4lHC4uBAYBKNCSBR2uHShT2GVzN0tOHNOQ"
    "eor2zyRbQC/7H2+pc7elDAx/XkaLxHFqvSHsYNrqepjrLBUPEVSwh8LTpvjXICy1zcejmcQQnkbsgJrGMAJwx2Go0W38LktQ"
    "yCF80jg1jAXOJ6ANSky7Kx/2TW3ztkdg32+nk3Ky6uMAwTkM+MQpKleeOWblEm5Q9tKqpZITb6ZxhpWDhuDp8pVF3cprTze9"
    "g9KcNkytyMuhFcNCjFFl8VEbb7GLlIGz9+dsxcKjm6K4uzEXcGy9X0r1uXZC+abK6eiqYKineY5YpBI1w6COC998l22TNt9h"
    "7ZdmuBldGGTDqeNCstyrVKdURqDtSgjSs8p10Nm2DvNWx2JBTOaz9o6BeDqlxeXuccl2pK9ceyb2hFr2HioGSbstdLu9u6OK"
    "8hTP8EpHPoyPHCKjlFxlaQG8UZcCMEBQjt4oqVa1AjUeCN5CPVoKVnaDE4JtEcNwUCyCCBQFcikAo6K9AVGhrKinGIpXt8hR"
    "VzCCRi2hqmgNlDZR2py24UFU3MkZhd15yoXC6QMIJsRNxvU04+tFdNUx5EoEjT0EKFaXMzukjyJeG51EQwSHgcN5BM0ktvkd"
    "u1dKQ3raVOy0NDcaVtHBGY2xgljjqc6KntuUUjgJIiwn4zSnba4mXnIpsPHBA0uNAadxa0OdunBwExAxx0UxXVVRUuDhuh2M"
    "EjpTF8hz75E0nrwgl9nPxOXzp7rUEawCM0026C0c6dP7rUEEBXn79qPOv7xXYmuc0Fz8N7SuV/47Uedf3im+TjGThA9xTMGX"
    "Hf7AgbhG0eBGNOGUxQQLS1k0hPhYB6kmXOd4zifKgQgg6BhHRQjICI6IUdBzGelGaFwBGbxQDC5hKhFKAmECuuKKgHBFZ4Tx"
    "5coHTtRofGJQLOGCkyjk6opCAmV3K7hFwgNg9CAC60oAoFonYcrdspUVVD8L2yd8Fbb3iQFvxhnVU9qs2xNcyC7NglPvc7TG"
    "QeCLHtDky5QqbbuyMnyGVjABKw6bx6wrq0ryFydXeq2W2mdTxyFjN87o6CvV1puXt+hjlON4jXCxa6RIO8q8Veyk2uO0XKG+"
    "3RSF1Na2cy0dG9nwivZVfU+1qSafONxhK8C8pVunk2nrKh2XSzSue4npySkZ6VSnfhoCeRP3lc+T3YYXN8vtqMlrozqejtVb"
    "2issuzV3loJR4hO6eghaZw3CPS0VRdK2ChpWGSaZ4Y0DrKR5zABXojkH5LW0lNHtLdIc1FQM07Dxjb1+VS3Fk0wn5Aom7IR0"
    "7cG4hm+9zdfCPR/BOfY33u4bI7S1exl0DmQ1OXwb2ga8f9sre6KljxuEfSqNt9slDbaqC/Uce5JBIHnd00BypK1jVhqhIWtb"
    "kngmlqrW3C3U9U3GJWA/SqXyzbZv2Q2MrJ6d4FTK0xMz0E6ZTV1519kRt63azbV1FSSb1HbAYmjoL+krJnPyCEpJI+R0k0zy"
    "6WVxe5x4klIOGVqOVojhlBoRghwVQA1d3e1cBwu7yKG6lWBJq07PbAXi/wAU0zIXU8MUJn52RvgvA6lLcVWnjeGEywWvIKfP"
    "y1xDhjBwmU34UlEKNXSiNXVR0nCIjOKDdVRzCLhHyk8qAIIIIAihGRUK5xQ8i4UEBmVMsbsh5S3tx7uIafKE2QyhizbN4NHK"
    "f9qe61Bc2abmhk86e61BDEBX/jtR51/eKbpxX/jtR51/eKboOoIIIgyC6uFF11dRCjBLQCutRSjNQGC7nC4F1AcFcJ0Rc4XN"
    "7PQgB4oLmV1MHHHAR4hhiI7hhKxDIAQSds2cuV4pKyro6d0sNG3emLdS0ZxwTGopp6RwbPE6NxGQHDBx1rWOQy7+4z6yZ9HC"
    "2hAxVyyDIew/E1//ANortUcnVl2oqaq8VNqmbTyAuhc2XXd6MLNuLJa82Ip0XpGm5N9g7FYYp7ncWVLOcfLTxuG6XkDxHH6F"
    "5+v1XDX3WoqaakbRwPeTHA05DArKWYYNXF1vFcWkdBTyhmMFRHK04LHByZFHY9Zqt8obX7empbpEPwjGu06cBeidjXbtmi8g"
    "XnnkmuYumzDYZSDJSu3DrnQ8Fs+y1c8Rc2x3ggrF+OkW+8yia2zwtOXvaQAsIuvJW+417qyeJwA14rd6eDntXDRN70IYKF53"
    "egqaMasFjioXzRRMwGjCgOV+3W6fZGWpnYxtVG9ojk4Hp0VyoTrVOyBr0nCwflU2xff717Qp5c0dEd0Y+M/J1VlOocciVltl"
    "825gprpuujawvZG7g9wxovXMLIqWNsbGhjGjDWgYAC8LWC9TbObQ0N1hcWmGUOOOpesGbXsus1A+J+6ypY2Ro6wU6TlpFKN5"
    "u8Ea6UDbpaKmlkAO+wgZRLa773aSpKI5YoK1sJ7ZpLCyjqmPE0D3M8LTIzosp9kYx9bTRQknmYQXkeRb1gBYB7Ia6RUtrqQH"
    "4km96YrCvMMrsvIRCVwuyUAVtzriCBXFTHVZdi9lqPaqqdSVF2ht8ziGwiRuedcfijqVaS9FVSUVQyoicWyRneaR0FFa5W8i"
    "sVmvkEF1nMVuLQ3eacl7vKtaY6n2G2bmtFJTOp4SNxlRI7e3c8PoWecmVzdtzs7U2ua6Bl2gnE8TZnZL/JnqW0T7HNuuzrKO"
    "7yOq5fGLnDxXdGPIsWNyPIe3lorLVtFUCrEeZnGRjoxhrgeoKsTs3cHrW87YbMbMXSsis9XtBHDWUjCDnp14ErELtDFDPLFF"
    "KJmRvIbIPjDrVjHRk0o2Ukwo+VpHXBcBXSUAFR1EISiK4qYCILmUDwQcQyiruE0cQCCCAq5ldXERZ9mT94y+dPdagubMn7xk"
    "86e6EFRBXD8dqPOv7xTdOLh+O1HnX94puori6uLqICCCCoCCCCmAyM1FRmooyCC5kIO5QJwEXe7ECcoOZXVzpXU0dJ1ATyhp"
    "X1lZBTRY35Xhgz1lMh4TglmucHBzSWkcCOIVHpHkz2IorZbKnZ6+3SiEtXKyXmGv1LerVaVdtjaajsslNanvpxvBzGh+NcaD"
    "J6F4tF1rufbUGqm59vCQPIcB5VKu292lcxrHXyuLGneDTKSMrGN89L3yySRWOit2zrd900RdPNI7xSSeGVkznK57bcpMu2dq"
    "t9LNRRMnpWBj5xjfkIHSqUidXQXV1oyjLTJJyMxccg1BpXI5evad3moXPIbUMy0frD/9r01sNDz0RLxjVeNdl7ibZfKOqGcR"
    "yt3vJnVe0Ni54jA1zDo5ocufTpzV7ha2KPiqntrc2Utvk17FYn1AMRx1LJuUq9b1QKVr+A1x0lZkatUjbXbOLZ/ZyvdGfvqo"
    "BjiGdRnOq8/wbzy6R5y5xyT1lWHlCvL7jeXUzXnmqcbmM9Kr8JwwBdJHPqi1PhDdWv8AI7fZLo+KGpnyaAbrA4/FWQVA97JU"
    "3ydXv3F2jhc92Ipjzb/pSpzfr3HZ6xk9IxzTxCkBVluipOxtyPtcMe7PUrmAx4BI4rFdfR/bBdwyvKvsk7u2TaOK2xuPvI5x"
    "4z0nH/depp5IqWB8rjgMGT5F4X5Sr4/aDbK51zpDIHykNJ6hotT6zbkxV85Rc4QJwUXOVtzwdBALuQgKHLqIUbKC2cmd6t9h"
    "2qp665TSxQxgkFnX2qy7T8uO1NdWVkNFc3R0cjnCPA8IN8qy8IwDQMl2Ea0rPVT1Ez5pZHSSSHec5xySUi8ncOVxzwOGqIZC"
    "RgIhEHVKDguBgRkQAjdC5lDKUDKI4oOKJvIV0FdKKF0lUcQQQCgKggghoFAIFAILLsz+IyedPdaghsz+IyedPdagqiBr/wAd"
    "qPOv7xTdOK/8dqPOv7xTdRQXVxdRAQQQVAQQQQGQCCCijLhyuBcRHUECgigggggAOCjc6QioIDiUHsXS5p6UmuFArjpB4owS"
    "Lc5wEsEHWo+UmuhBx47VwFAlcwgVY4tOQcFereSLaE3DZyhnL9Q3m3DPSNF5QYcLauQW/F0VZa5CPeyJWN8vFZ/jXPX16TrL"
    "rHBQOkLsaLzzyibUiE1lQ1wLhljB1k5V+2u2mFBaX778DBxlea9r73JX1fNtflgOSesqRrqoKSV9RNJNIcuecklKRcEgzil2"
    "jRac/RpvwZTVj3RPa9pw5pyCnMviFNnaIPVfJRfxfdnaKpbJmZg5uUdo6VrdDVc5TjPRxXkrkE2o9zrzLa5ne91Iy0E6bwXp"
    "y31fvLcOWK7S/DflNvzbJsbcanfw/my1vlK8Q1UpnnfITkuOSV6Q9kjtCabZyC1scecnfvO14ALzSXZWuYx36BCKQgTqhla1"
    "hwlAOQIQAQGQBwCepcyhvYQFErjw0XTl3FFc0ZyNEZqDu7hDCNkIEjCoIuLpXFAMoIIIE3HKKjORUxByuIqCLoyCKghoLq4g"
    "iAggggsOzhxQv84fQEF3ZwfeL/Of9LUEXUJX/jtR51/eKQS1w/Hajzr/AEpFE1xBBBB1BBBFBBBBEBGCKjooIiMFxEcXQguK"
    "gyCBQUUEEEEAAXOlDKAGUCjOCMiNRkHUFxBB1BcQQGCtXJreBZ9raSRzi1kuY3duVU0rTzup545mndcxwIPUg1nlh2ldFIy3"
    "xyZJ8IhZE6QyyFxPFPdor1Nfbi6qlOpaGhMI+CytpdgwlAUiEcHCqFHatKbvSrnZCI5uioWstc+13alrGOLXRSB2QvY+yt0i"
    "uFrp6prsiRgd9C8VvXobkm2n57YwtL8S0rd0+ToU6jXNUvl5v5um1ZpWvJbTtwfKVmBUvtXcTc79WVTn7xdIfoUMEkSuoIIK"
    "oCCCCAZQQQQdReC6gTkYQd3l36UlwRgUBlxdRTogCKTld3kU6oCoILqDiCCCqAgggpQFxdXEAQQQQWHZ44on+cPdCC5s7+Iv"
    "84fQEFRDV347Uedf6Ugl678dqPOu9KRUHEEEEAyuri6iggggg6uLpXEtAQQQTUBBBBNAQQQQBBBBUGQQC6ooLq4V1LQAguBd"
    "QGQQQQBcIyuoIEnJSPoRXjKUp43yvDI2lzjwAQKAZ0B8I8ApmxbL19+dI2Bu5zfjbw6FK7P7IXenn9uzUB5tkZcQ7Gcdi0Gm"
    "ZJW2FtTbIIaKdng85JoHHrUWRk972frbFUtgqWZc5u8C3XTtUU7wgtprqaaK2M9vRMrax+MSxjO6Vmd92YutJUSzvoi1hcSQ"
    "3XCSlitSDBVg2S2omsbKumD8MnjI49KgntIyCMEJDpVQq95fI5xOSTkrgRV1qsoMggghoILhKGVLQMoZRMoZQGQRSgmgzigD"
    "lExnpRgE0HXDwRUCgKuLpXEHEEEEQF1cXUUEEEEHEEEEAQQQRE9YDijf5w+gIIWH8Uf5w+gIKiIrvx2o8670pBL1349Uedf6"
    "SkFAEEEEAQQQQdQQQRQQQQQBBBBAEEF1C1xBBBVAQQQQBBBBQGQQQwiggggg6uhFQQGQK4hhAbideCuOzu0dhtmCaLclAxvv"
    "ORlU4lEIyUG5WXaqC8wzNpHfg2Zed3oKdGvinohLbY2VIj8Exh2BvLGLRfKyzuLqZ+7veMOsK27L7bffboKpscUTwcY08IqW"
    "NL1TVhgpG+3GthllPvcbz4pTG87UW23VAZXbxeRkFrdHBUzanbF8lYIKbm3xxYIdjJB7Cq1c73V3ZzOfdkMGAMdCgsd+vey9"
    "aHOit0pmPSDuhUmYsMjjGCG50yjSOIbpoklpl1dC4uhAZFXcriagqCCCKCCCCAIIIIAgggEAQ6CioIOFBBdRPHEEEEAXVxdQ"
    "BBBBFcCCAQQgIIIIiesP4o/zh9AQQsP4o/zh9AQVETcdLhU+df3im6cXH8oVXnn94puoAggggCCCCAIIFBF11BcQQ11cXUEA"
    "XcriCFBBdwuIgIIIKgIIIIAgulcUARkVGKKCCCCABGXFzKAFcK6VwoDtdwSnFIBKNKA6CLlAnCAsvAaogQcSTquoAF1cQyhX"
    "coLhQQBBBBAEAgggKggggCCC6haKgggiAggggCCCCAIIIIAggggCCCCAIIIIJ6wAmjfj5Q+gIJzsxGHUEh/2pH+FqCod3HZa"
    "i90Kr32o/DP6W/pHsTf7lqL5Wo+tvqQQUA+5ai+VqPrb6kPuWovlaj62+pBBUD7lqL5Wo+tvqQ+5ai+VqPrb6kEEA+5ai+Vq"
    "Prb6kPuWovlaj62+pBBAPuWovlaj62+pD7lqL5Wo+tvqQQQD7lqL5Wo+tvqQ+5ai+VqPrb6kEEBvuVovlaj62+pD7laL5Wo+"
    "tvqQQQD7lqL5Wo+tvqXTsrRfK1H1t9SCCLRTstRZ/C1H1t9S4NlaI/naj62+pBBEKt2Tovl6r95vqRvuSovl6r95v+lBBAPu"
    "Sovl6r95v+lA7JUWPw9V+83/AEoIICnZKi+Xqv3m+pD7kqL5er/eb6kEEHPuSovl6r95vqQ+5Ki+Xqv3m+pBBAo3ZGiP5+q/"
    "eb/pXDslRZ/D1X7zf9KCCAw2Qovl6r95v+lcdsjRAfh6r95v+lBBAUbJUWfw9V+83/SlBshRfL1X7zf9KCCA33IUXziq+tn+"
    "lEdshRfL1X7zf9KCCBP7kaL5eq/eb/pRhsjRY/D1X7zf9KCCDh2Sovl6r95v+lc+5Ki+Xq/3m+pBBAb7kqL5xV/vN/0ortkq"
    "L5eq/eb/AKUEEA+5Kix+Hqv3m+pJnZaiB/C1H1t9SCCAp2Wovlaj62+pF+5eiH52o+tvqQQQc+5ukH52o+tvqRXbOUvytR+8"
    "PUggoov3PUvyk/1j1Iv3PUvyk31j1IIKo59z1L8pN9Y9SJ7hU3yk31j1IIIDGx0/yk31j1InuHTfKTfWPUggpVd9wqf5Sb6x"
    "6kPcOn+Um+sepBBVHDZaf9OX6x6kSS0wMIw+T+HqQQQJ+5sWPHk/h6kX3Niz40n8PUggg6y2xH48n8PUnEdngkGskv0EepBB"
    "AcWKmJxzk31j1JVuzlIfzk31j1IIKC4bK7L0ftCX36p/DHpb+i3sQQQVH//Z"
)

CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "gustav1230943-create/ACC-Generator-Releases"
RELEASE_ASSET = "Acc.Generator.exe"


def check_for_updates():
    # Nur die gebaute EXE aktualisieren, nicht den Python-Testlauf.
    if not getattr(sys, "frozen", False):
        return

    api_url = (
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    )

    try:
        request = urllib.request.Request(
            api_url,
            headers={"User-Agent": "ACC-Generator-Updater"}
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            release = json.loads(response.read().decode("utf-8"))

        latest = release["tag_name"].lstrip("v")

        def version_tuple(version):
            return tuple(int(x) for x in version.split("."))

        if version_tuple(latest) <= version_tuple(CURRENT_VERSION):
            return

        asset = next(
            (
                item for item in release.get("assets", [])
                if item["name"] == RELEASE_ASSET
            ),
            None
        )

        if not asset:
            messagebox.showerror(
                "Update-Fehler",
                f"Die Datei {RELEASE_ASSET} fehlt im neuesten Release."
            )
            return

        if not messagebox.askyesno(
            "Update verfügbar",
            f"Neue Version: {latest}\n"
            f"Aktuelle Version: {CURRENT_VERSION}\n\n"
            "Möchtest du das Update jetzt installieren?"
        ):
            return

        target = os.path.abspath(sys.executable)
        new_file = os.path.join(
            tempfile.gettempdir(),
            f"acc_generator_update_{os.getpid()}.exe"
        )

        # Neue EXE herunterladen.
        download_request = urllib.request.Request(
            asset["browser_download_url"],
            headers={"User-Agent": "ACC-Generator-Updater"}
        )

        with urllib.request.urlopen(
            download_request, timeout=60
        ) as response:
            with open(new_file, "wb") as file:
                file.write(response.read())

        if os.path.getsize(new_file) == 0:
            raise RuntimeError("Die heruntergeladene Datei ist leer.")

        # Hilfs-BAT wartet auf das Ende der laufenden EXE,
        # ersetzt sie und startet sie anschließend neu.
        helper = os.path.join(
            tempfile.gettempdir(),
            f"acc_generator_update_{os.getpid()}.bat"
        )

        script = r'''@echo off
setlocal
set "TARGET=%~1"
set "NEWFILE=%~2"
set "PID=%~3"

:wait
tasklist /FI "PID eq %PID%" /NH | findstr /C:"%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait
)

copy /Y "%NEWFILE%" "%TARGET%" >nul
if errorlevel 1 goto cleanup

start "" "%TARGET%"

:cleanup
del "%NEWFILE%" >nul 2>&1
del "%~f0" >nul 2>&1
'''

        with open(helper, "w", encoding="utf-8") as file:
            file.write(script)

        subprocess.Popen(
            [
                "cmd.exe", "/c", helper,
                target, new_file, str(os.getpid())
            ],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Hauptprogramm beenden, damit die EXE ersetzt werden kann.
        sys.exit(0)

    except Exception:
        # Bei Netzwerkproblemen soll das Programm normal starten.
        try:
            if "new_file" in locals() and os.path.exists(new_file):
                os.remove(new_file)
        except OSError:
            pass


import hashlib
import urllib.request
import tempfile
import os


def test_release_checksum():
    base_url = (
        "https://github.com/gustav1230943-create/"
        "ACC-Generator-Releases/releases/download/v1.0.1/"
    )

    expected_hash = (
        "c000770bc8b67f0e7080d7c50fded871"
        "a7c11660bf4e8183b6276b4c0cbce6eb"
    )

    exe_url = base_url + "Acc.Generator.exe"

    try:
        with urllib.request.urlopen(exe_url, timeout=60) as response:
            data = response.read()

        actual_hash = hashlib.sha256(data).hexdigest()

        if actual_hash == expected_hash:
            print("SHA-256 erfolgreich geprüft.")
            return True

        print("FEHLER: SHA-256 stimmt nicht überein.")
        return False

    except Exception as exc:
        print(f"Prüfung fehlgeschlagen: {exc}")
        return False


if __name__ == "__main__":
    check_for_updates()
    app = App()
    app.mainloop()
