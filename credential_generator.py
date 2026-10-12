import base64
import hashlib
import io
import json
import math
import os
import secrets
import string
import subprocess
import sys
import tempfile
import threading
import urllib.request
import uuid
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont

CURRENT_VERSION = "1.0.7"
GITHUB_REPO = "gustav1230943-create/ACC-Generator-Releases"
RELEASE_ASSET = "Acc.Generator.exe"
APP_NAME = "ACC Generator"

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

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
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
    "use_symbols": False,
    "first_letter": False,
    "no_ambiguous": False,
    "unique_chars": False,
    "save_on_generate": True,
    "username_separator": "_",
    "username_number_min": 10,
    "username_number_max": 9999,
    "auto_copy": False,
    "auto_copy_field": "all",
    "show_password": True,
    "confirm_delete": True,
    "bg_enabled": True,
    "bg_mode": "default",
    "bg_brightness": 35,
    "theme": "original",
    "layout": "classic",
    "password_mode": "random",
    "window_transparency": 0,
}

ADJECTIVES = [
    "silent", "rapid", "fuzzy", "neon", "swift", "dark", "cold", "wild", "lazy", "tiny",
    "fancy", "shiny", "brave", "quick", "sneaky", "grumpy", "spooky", "lucky", "chilly", "dusty",
]
NOUNS = [
    "panda", "falcon", "penguin", "cactus", "robot", "ninja", "comet", "wizard", "goblin", "raven",
    "titan", "pixel", "vortex", "cipher", "specter", "phantom", "dagger", "nomad", "glitch", "vector",
]

PASSPHRASE_WORDS = sorted(set(ADJECTIVES + NOUNS + [
    "amber", "anchor", "arrow", "atlas", "badger", "banjo", "beacon", "bison", "blaze", "bolt", "breeze", "bridge",
    "canyon", "carbon", "castle", "cedar", "cloud", "cobalt", "coral", "cosmos", "crane", "crystal", "delta",
    "desert", "dragon", "eagle", "ember", "engine", "falcon", "fern", "flint", "forest", "frost", "galaxy",
    "garnet", "glacier", "granite", "harbor", "hawk", "helix", "island", "ivory", "jaguar", "jungle", "kayak",
    "kernel", "lagoon", "lantern", "lemon", "lotus", "lynx", "magnet", "maple", "marble", "meadow", "meteor",
    "mint", "monsoon", "nebula", "nectar", "oasis", "ocean", "onyx", "orbit", "otter", "panther", "pepper",
    "pilot", "planet", "plasma", "prism", "quartz", "radar", "rapids", "reef", "river", "rocket", "saber",
    "saffron", "sahara", "signal", "silver", "summit", "sunset", "tiger", "timber", "topaz", "tundra", "turbo",
    "velvet", "violet", "voyage", "walnut", "willow", "winter", "zephyr", "zenith",
]))
SYMBOL_CHARS = "!@#$%^&*-_=+?."   # nur noch für die Analyse eigener Passwörter
PW_MIN, PW_MAX = 8, 40               # Steam: mind. 8 Zeichen
AMBIGUOUS = set("Il1O0o|`'\"")
COMMON_PASSWORDS = {
    "password", "passwort", "123456", "12345678", "123456789", "qwerty", "qwertz", "hallo",
    "letmein", "admin", "welcome", "iloveyou", "abc123", "111111", "dragon", "monkey",
}

# --- Farben ---------------------------------------------------------------
BG = "#0a0b0d"          # Fensterhintergrund (hinter dem Panel)
PANEL = "#121316"       # großes, abgerundetes Hauptpanel
CARD = "#17181c"        # Karten
CARD2 = "#1d1f24"       # Karten in Karten
FIELD = "#0e0f12"       # Eingabefelder
BORDER = "#2a2c33"
BORDER_SOFT = "#222329"
TEXT = "#eceef2"
MUTED = "#8b8f99"
ACCENT = "#7aa7ff"
ACCENT_2 = "#5a84e0"
ACCENT_DARK = "#0b1220"
GREEN = "#4ade80"
YELLOW = "#e5b454"
PURPLE = "#b48cff"
ORANGE = "#f59e0b"
DANGER = "#ef4444"
TRACK = "#2c2e35"

UI = "Segoe UI"
MONO = "Consolas"
SELECT_BG = "#1f2a40"      # aktiver Tab / Auswahl
SELECT_BORDER = "#34507f"

# ---------------------------------------------------------------------------
# Designs (angelehnt an Qt Fluent, Dear ImGui, NiceGUI, Flet/Material 3, Textual)
# Innerhalb eines Designs muss jeder Wert eindeutig sein (wird beim Umschalten gemappt).
# ---------------------------------------------------------------------------
THEME_KEYS = ("BG", "PANEL", "CARD", "CARD2", "FIELD", "BORDER", "BORDER_SOFT", "TEXT", "MUTED", "ACCENT",
              "ACCENT_2", "ACCENT_DARK", "GREEN", "TRACK", "SELECT_BG", "SELECT_BORDER", "UI", "MONO")
THEMES = {
    "original": dict(label="Original",
                     BG=BG, PANEL=PANEL, CARD=CARD, CARD2=CARD2, FIELD=FIELD, BORDER=BORDER, BORDER_SOFT=BORDER_SOFT,
                     TEXT=TEXT, MUTED=MUTED, ACCENT=ACCENT, ACCENT_2=ACCENT_2, ACCENT_DARK=ACCENT_DARK, GREEN=GREEN,
                     TRACK=TRACK, SELECT_BG=SELECT_BG, SELECT_BORDER=SELECT_BORDER, UI=UI, MONO=MONO),
    "fluent": dict(label="Fluent",
                   BG="#1a1a1a", PANEL="#202020", CARD="#2b2b2b", CARD2="#333333", FIELD="#1d1d1d", BORDER="#404040",
                   BORDER_SOFT="#383838", TEXT="#ffffff", MUTED="#a8a8a8", ACCENT="#60a5fa", ACCENT_2="#3b82f6",
                   ACCENT_DARK="#0a1626", GREEN="#6ccb5f", TRACK="#454545", SELECT_BG="#1f3550",
                   SELECT_BORDER="#2f5c8f", UI="Segoe UI Variable Text", MONO="Cascadia Mono"),
    "imgui": dict(label="ImGui",
                  BG="#0b0b0b", PANEL="#0f0f0f", CARD="#16181d", CARD2="#1f2a3a", FIELD="#1d2f4a", BORDER="#3d3d4d",
                  BORDER_SOFT="#2a2a33", TEXT="#f0f0f0", MUTED="#8a8f99", ACCENT="#4296fa", ACCENT_2="#2d6fc4",
                  ACCENT_DARK="#ffffff", GREEN="#5ad468", TRACK="#252a33", SELECT_BG="#26466e",
                  SELECT_BORDER="#3b80d6", UI="Verdana", MONO="Lucida Console"),
    "nicegui": dict(label="NiceGUI",
                    BG="#0b0b12", PANEL="#0f0f17", CARD="#14141f", CARD2="#1b1b2a", FIELD="#11111a", BORDER="#2e2e44",
                    BORDER_SOFT="#232334", TEXT="#ececf4", MUTED="#9696aa", ACCENT="#7c5cff", ACCENT_2="#6243e8",
                    ACCENT_DARK="#fafaff", GREEN="#22c55e", TRACK="#2a2a3d", SELECT_BG="#241c45",
                    SELECT_BORDER="#4a3a99", UI="Segoe UI", MONO="Consolas"),
    "material": dict(label="Material",
                     BG="#121118", PANEL="#16151c", CARD="#1d1b23", CARD2="#26232e", FIELD="#211f28", BORDER="#3b3845",
                     BORDER_SOFT="#2d2a35", TEXT="#e6e1e9", MUTED="#9a96a8", ACCENT="#d0bcff", ACCENT_2="#b69df8",
                     ACCENT_DARK="#381e72", GREEN="#4ade80", TRACK="#34313d", SELECT_BG="#332d4a",
                     SELECT_BORDER="#5b4d82", UI="Segoe UI", MONO="Consolas"),
    "terminal": dict(label="Terminal",
                     BG="#13131a", PANEL="#1a1b26", CARD="#1f2335", CARD2="#24283b", FIELD="#16161f", BORDER="#3b4261",
                     BORDER_SOFT="#292e42", TEXT="#c0caf5", MUTED="#737aa2", ACCENT="#bb9af7", ACCENT_2="#9d7cd8",
                     ACCENT_DARK="#11111a", GREEN="#9ece6a", TRACK="#2f3549", SELECT_BG="#2a2440",
                     SELECT_BORDER="#5a4a8a", UI="Cascadia Mono", MONO="Consolas"),
    "multitool": dict(label="Multitool",
                      BG="#0e0e0e", PANEL="#121212", CARD="#1a1a1a", CARD2="#262626", FIELD="#141414",
                      BORDER="#343434", BORDER_SOFT="#2a2a2a", TEXT="#f2f2f2", MUTED="#8c8c8c", ACCENT="#ffffff",
                      ACCENT_2="#e6e6e6", ACCENT_DARK="#0a0a0a", GREEN="#4ade80", TRACK="#2f2f2f",
                      SELECT_BG="#2c2c2c", SELECT_BORDER="#4a4a4a", UI="Segoe UI", MONO="Consolas"),
}
CURRENT_THEME = "original"


def apply_theme(name):
    """Setzt die Farb-/Schrift-Konstanten auf ein Design. Muss VOR dem Aufbau der Fenster laufen."""
    global CURRENT_THEME
    import types
    name = name if name in THEMES else "original"
    g = globals()
    old = {k: g[k] for k in THEME_KEYS}
    new = {k: THEMES[name][k] for k in THEME_KEYS}
    mapping = {old[k]: new[k] for k in THEME_KEYS if old[k] != new[k]}
    g.update(new)
    CURRENT_THEME = name
    if not mapping:
        return

    def conv(value):
        if isinstance(value, str):
            return mapping.get(value, value)
        if isinstance(value, tuple) and value and isinstance(value[0], str) and value[0] in mapping:
            return (mapping[value[0]],) + value[1:]
        return value

    # Standardwerte von Funktionen (z. B. fill=CARD, font=(UI, 9)) mitziehen
    for obj in list(g.values()):
        funcs = []
        if isinstance(obj, type) and obj.__module__ == __name__:
            funcs = [getattr(f, "__func__", f) for f in vars(obj).values()
                     if isinstance(f, (types.FunctionType, staticmethod))]
        elif isinstance(obj, types.FunctionType) and obj.__module__ == __name__:
            funcs = [obj]
        for f in funcs:
            if f.__defaults__:
                f.__defaults__ = tuple(conv(v) for v in f.__defaults__)
            if f.__kwdefaults__:
                f.__kwdefaults__ = {k: conv(v) for k, v in f.__kwdefaults__.items()}


LOAD_WARNINGS = []


def _read_text(path):
    """Liest Textdateien robust – auch wenn sie nicht als UTF-8 gespeichert wurden."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")   # kann jedes Byte dekodieren


def _backup_broken(path):
    target = path + ".bak"
    n = 1
    while os.path.exists(target):
        target = f"{path}.bak{n}"
        n += 1
    try:
        os.replace(path, target)
        LOAD_WARNINGS.append(
            f"{os.path.basename(path)} war beschädigt und wurde gesichert als:\n{target}"
        )
    except OSError:
        pass


def load_json(path, default):
    fallback = default.copy() if isinstance(default, dict) else list(default)
    if not os.path.exists(path):
        return fallback
    try:
        text = _read_text(path).strip()
        if not text:
            return fallback
        data = json.loads(text)
    except OSError:
        return fallback
    except ValueError:      # JSONDecodeError / UnicodeDecodeError
        _backup_broken(path)
        return fallback
    if isinstance(default, dict) and isinstance(data, dict):
        merged = default.copy()
        merged.update(data)
        return merged
    if isinstance(default, list) and isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    _backup_broken(path)
    return fallback


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


def format_datetime(iso_string):
    try:
        return datetime.fromisoformat(iso_string).strftime("%d.%m.%Y  %H:%M")
    except (ValueError, TypeError):
        return "—"


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


# ---------------------------------------------------------------------------
# Passwort-Analyse
# ---------------------------------------------------------------------------
def _plural(value, one, many):
    value = int(value)
    return f"{value} {one if value == 1 else many}"


def format_duration(seconds):
    if seconds < 1:
        return "sofort"
    if seconds < 60:
        return _plural(seconds, "Sekunde", "Sekunden")
    if seconds < 3600:
        return _plural(seconds / 60, "Minute", "Minuten")
    if seconds < 86400:
        return _plural(seconds / 3600, "Stunde", "Stunden")
    if seconds < 86400 * 365:
        return _plural(seconds / 86400, "Tag", "Tage")
    years = seconds / 31557600
    if years < 1000:
        return _plural(years, "Jahr", "Jahre")
    if years < 1e6:
        return "Tausende Jahre"
    if years < 1e9:
        return "Millionen Jahre"
    if years < 1e12:
        return "Milliarden Jahre"
    return "Billionen+ Jahre"


def analyze_password(pw):
    n = len(pw)
    upper = sum(1 for c in pw if c.isupper())
    lower = sum(1 for c in pw if c.islower())
    digits = sum(1 for c in pw if c.isdigit())
    symbols = n - upper - lower - digits
    pool = (26 if upper else 0) + (26 if lower else 0) + (10 if digits else 0) + (33 if symbols else 0)
    unique = len(set(pw))

    bits = n * math.log2(pool) if pool > 1 else 0.0
    if n:
        bits *= 0.6 + 0.4 * (unique / n)          # Wiederholungen kosten Entropie
    if pw.lower() in COMMON_PASSWORDS or (n and unique <= 2):
        bits = min(bits, 10.0)
    bits = min(bits, 1000.0)

    classes = sum(1 for x in (upper, lower, digits, symbols) if x)
    complexity = 0
    if n:
        complexity = round(min(100, classes / 4 * 50 + min(n, 20) / 20 * 30 + unique / n * 20))

    if n == 0:
        level, label, color = 0, "—", MUTED
    elif bits < 28:
        level, label, color = 1, "Sehr schwach", DANGER
    elif bits < 36:
        level, label, color = 2, "Schwach", ORANGE
    elif bits < 60:
        level, label, color = 3, "Mittel", YELLOW
    elif bits < 90:
        level, label, color = 4, "Stark", GREEN
    else:
        level, label, color = 5, "Exzellent", GREEN

    guesses = 2 ** max(bits - 1, 0)
    times = {
        "online": format_duration(guesses / 100) if n else "—",
        "fast": format_duration(guesses / 1e10) if n else "—",
        "slow": format_duration(guesses / 1e4) if n else "—",
    }
    return {
        "length": n, "unique": unique, "upper": upper, "lower": lower, "digits": digits,
        "symbols": symbols, "bits": bits, "complexity": complexity, "level": level,
        "label": label, "color": color, "times": times,
        "checks": [
            ("Min. 12 Zeichen", n >= 12),
            ("Großbuchstaben", upper > 0),
            ("Kleinbuchstaben", lower > 0),
            ("Zahlen", digits > 0),
            ("Steam-kompatibel", n >= 8 and symbols == 0),
            ("Kaum Wiederholungen", n > 0 and unique / n >= 0.6),
        ],
    }


def hibp_count(password):
    """k-Anonymität: nur die ersten 5 Zeichen des SHA-1-Hashes verlassen den PC."""
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    request = urllib.request.Request(
        f"https://api.pwnedpasswords.com/range/{prefix}",
        headers={"User-Agent": "ACC-Generator", "Add-Padding": "true"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8", "replace")
    for line in body.splitlines():
        part, _, count = line.partition(":")
        if part.strip() == suffix:
            return int(count.strip() or 0)
    return 0


# ---------------------------------------------------------------------------
# Hintergrundbild (wird um das abgerundete Hauptpanel herum sichtbar)
# ---------------------------------------------------------------------------
class Backdrop:
    def __init__(self, root):
        self.root = root
        self.widgets = []
        self.source = None
        self.enabled = True
        self.brightness = 0.35
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


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------
def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
        x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


def parent_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return PANEL


class Shell(tk.Canvas):
    """Fensterfläche: Hintergrundbild + großes abgerundetes Panel mit dem Inhalt."""

    MARGIN = 12
    RADIUS = 18

    def __init__(self, master, backdrop):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0)
        self._photo = None
        self._bg_item = self.create_image(0, 0, anchor="nw")
        self.panel = tk.Frame(self, bg=PANEL)
        inset = self.MARGIN + 6
        self._win = self.create_window(inset, inset, window=self.panel, anchor="nw")
        self.bind("<Configure>", self._redraw, add="+")
        backdrop.register(self)

    def apply_backdrop(self, photo):
        self._photo = photo
        self.itemconfigure(self._bg_item, image=photo if photo is not None else "")
        self.tag_lower(self._bg_item)

    def _redraw(self, _=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50 or h < 50:
            return
        m = self.MARGIN
        self.delete("shape")
        round_rect(self, m, m, w - m, h - m, self.RADIUS, fill=PANEL, outline=BORDER, tags="shape")
        self.tag_raise("shape", self._bg_item)
        inset = m + 6
        self.itemconfigure(self._win, width=w - 2 * inset, height=h - 2 * inset)


class RoundCard(tk.Canvas):
    """Abgerundete Karte. Inhalt kommt in `.body`."""

    def __init__(self, master, fill=CARD, border=BORDER_SOFT, radius=12, pad=14, fixed=False, **kw):
        super().__init__(
            master, bg=kw.pop("bg", parent_bg(master)), highlightthickness=0, bd=0,
            width=10, height=10, **kw,
        )
        self.fill, self.border, self.radius, self.pad, self.fixed = fill, border, radius, pad, fixed
        self.body = tk.Frame(self, bg=fill)
        self._win = self.create_window(pad, pad, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw, add="+")
        if not fixed:
            self.body.bind("<Configure>", self._fit, add="+")
            self.after_idle(self._fit_initial)

    def _fit_initial(self):
        if self.winfo_exists():
            self.body.update_idletasks()
            self._fit()

    def _fit(self, _=None):
        if not self.winfo_exists():
            return
        h = self.body.winfo_reqheight() + 2 * self.pad
        w = self.body.winfo_reqwidth() + 2 * self.pad
        if int(self.cget("height")) != h or int(self.cget("width")) != w:
            self.configure(height=h, width=w)

    def set_border(self, color):
        self.border = color
        self.itemconfigure("shape", outline=color)

    def _redraw(self, _=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("shape")
        round_rect(self, 1, 1, w - 2, h - 2, self.radius, fill=self.fill, outline=self.border, tags="shape")
        self.tag_lower("shape")
        self.itemconfigure(self._win, width=max(1, w - 2 * self.pad))
        if self.fixed:
            self.itemconfigure(self._win, height=max(1, h - 2 * self.pad))


class RoundButton(tk.Canvas):
    def __init__(self, master, text, command=None, fill=CARD2, fg=TEXT, border=None, hover=None,
                 radius=9, font=(UI, 9, "bold"), height=34, width=None, padx=14, gradient=None):
        self._font = tkfont.Font(font=font)
        self._padx = padx
        self._fixed_width = width
        w = width or self._font.measure(text) + 2 * padx
        super().__init__(
            master, width=w, height=height, bg=parent_bg(master), highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self.text, self.command = text, command
        self.fill, self.fg, self.border, self.gradient = fill, fg, border, gradient
        self.hover = hover
        self.radius = radius
        self._hovered = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._click)

    def _click(self, event):
        if 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height() and self.command:
            self.command()

    def _set_hover(self, value):
        self._hovered = value
        self._draw()

    def restyle(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)
        if "text" in kw and not self._fixed_width:
            self.configure(width=self._font.measure(self.text) + 2 * self._padx)
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        r = self.radius
        if self.gradient:
            c0, c1 = self.gradient
            if self._hovered:
                c0, c1 = mix(c0, "#ffffff", 0.12), mix(c1, "#ffffff", 0.12)
            for x in range(w):
                if x < r:
                    dx = r - x - 0.5
                elif x > w - 1 - r:
                    dx = x - (w - 1 - r) + 0.5
                else:
                    dx = 0
                dy = r - math.sqrt(max(0.0, r * r - dx * dx)) if dx else 0
                self.create_line(x, dy, x, h - dy, fill=mix(c0, c1, x / max(1, w - 1)))
        else:
            fill = self.fill
            if self._hovered:
                fill = self.hover or mix(fill, "#ffffff", 0.07)
            round_rect(self, 1, 1, w - 2, h - 2, r, fill=fill, outline=self.border or fill)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg, font=self._font)


class Toggle(tk.Canvas):
    def __init__(self, master, variable, command=None):
        super().__init__(master, width=48, height=26, bg=parent_bg(master), highlightthickness=0,
                         bd=0, cursor="hand2")
        self.var, self.command = variable, command
        self.bind("<Button-1>", self._toggle)
        self.var.trace_add("write", lambda *_: self.draw())
        self.draw()

    def _toggle(self, _=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def draw(self):
        self.delete("all")
        on = bool(self.var.get())
        track = ACCENT if on else "#34363d"
        round_rect(self, 1, 2, 46, 24, 11, fill=track, outline=track)
        x = 34 if on else 13
        self.create_oval(x - 8, 5, x + 8, 21, fill="#ffffff" if on else "#9a9ea8", outline="")


class CheckBox(tk.Canvas):
    def __init__(self, master, variable, command=None, size=18):
        super().__init__(master, width=size, height=size, bg=parent_bg(master),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.var, self.command, self.size = variable, command, size
        self.bind("<Button-1>", self.toggle)
        self.var.trace_add("write", lambda *_: self.draw())
        self.draw()

    def toggle(self, _=None):
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def draw(self):
        self.delete("all")
        s = self.size
        if self.var.get():
            round_rect(self, 1, 1, s - 1, s - 1, 4, fill=ACCENT, outline=ACCENT)
            self.create_line(4.5, s / 2, s / 2 - 1, s - 5, s - 4, 4.5, fill=ACCENT_DARK, width=2.2,
                             capstyle="round", joinstyle="round")
        else:
            round_rect(self, 1, 1, s - 1, s - 1, 4, fill=FIELD, outline="#4a4d55")


class CheckTile(RoundCard):
    def __init__(self, master, text, variable, command=None):
        super().__init__(master, fill=CARD, radius=10, pad=12)
        self.box = CheckBox(self.body, variable, command)
        self.box.pack(side="right")
        label = tk.Label(self.body, text=text, bg=CARD, fg=TEXT, font=(UI, 10, "bold"), anchor="w",
                         cursor="hand2")
        label.pack(side="left", fill="x", expand=True)
        for widget in (self, self.body, label):
            widget.bind("<Button-1>", self.box.toggle)
        for widget in (self, self.body, label, self.box):
            widget.bind("<Enter>", lambda e: self.set_border("#3a3d46"), add="+")
            widget.bind("<Leave>", lambda e: self.set_border(BORDER_SOFT), add="+")


class Slider(tk.Canvas):
    def __init__(self, master, from_, to, value, command=None, on_release=None):
        super().__init__(master, height=24, width=120, bg=parent_bg(master), highlightthickness=0,
                         bd=0, cursor="hand2")
        self.from_, self.to, self.value = from_, to, value
        self.command, self.on_release = command, on_release
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda e: self.on_release and self.on_release())

    def set(self, value):
        self.value = int(max(self.from_, min(self.to, value)))
        self.draw()

    def _drag(self, event):
        pad = 10
        w = max(1, self.winfo_width() - 2 * pad)
        value = round(self.from_ + (event.x - pad) / w * (self.to - self.from_))
        value = int(max(self.from_, min(self.to, value)))
        if value != self.value:
            self.value = value
            self.draw()
            if self.command:
                self.command(value)

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30 or h < 10:
            return
        pad, cy = 10, h / 2
        x = pad + (self.value - self.from_) / max(1, self.to - self.from_) * (w - 2 * pad)
        self.create_line(pad, cy, w - pad, cy, fill=TRACK, width=4, capstyle="round")
        self.create_line(pad, cy, x, cy, fill=ACCENT_2, width=4, capstyle="round")
        self.create_oval(x - 8, cy - 8, x + 8, cy + 8, fill=ACCENT, outline=parent_bg(self), width=2)


class Segments(tk.Canvas):
    def __init__(self, master, count=5):
        super().__init__(master, height=8, width=100, bg=parent_bg(master), highlightthickness=0, bd=0)
        self.count, self.level, self.color = count, 0, ACCENT
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, level, color=ACCENT):
        self.level, self.color = level, color
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        if w < 40:
            return
        gap = 6
        seg = (w - gap * (self.count - 1)) / self.count
        for i in range(self.count):
            x1 = i * (seg + gap) + 3
            x2 = x1 + seg - 6
            self.create_line(x1, 4, x2, 4, width=6, capstyle="round",
                             fill=self.color if i < self.level else TRACK)


class Bar(tk.Canvas):
    def __init__(self, master, color=ACCENT, height=8):
        super().__init__(master, height=height, width=100, bg=parent_bg(master), highlightthickness=0, bd=0)
        self.fraction, self.color = 0.0, color
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, fraction, color=None):
        self.fraction = max(0.0, min(1.0, fraction))
        if color:
            self.color = color
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 12 or h < 4:
            return
        cy = h / 2
        self.create_line(4, cy, w - 4, cy, width=h - 2, capstyle="round", fill=TRACK)
        if self.fraction > 0:
            self.create_line(4, cy, 4 + (w - 8) * self.fraction, cy, width=h - 2, capstyle="round",
                             fill=self.color)


class ScrollFrame(tk.Frame):
    def __init__(self, master, bg=PANEL, style="Panel.Slim.Vertical.TScrollbar"):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style=style)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._on_canvas)

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)
        self._update_region()

    def _update_region(self, _=None):
        need = self.inner.winfo_reqheight()
        have = self.canvas.winfo_height()
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), max(need, have)))
        if have > 1:
            if need <= have:
                self.scrollbar.grid_remove()
                self.canvas.yview_moveto(0)
            else:
                self.scrollbar.grid()

    def scroll(self, units):
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(units, "units")

    def to_top(self):
        self.canvas.yview_moveto(0)


class Segmented(tk.Frame):
    """Auswahl aus mehreren Optionen als Button-Gruppe."""

    def __init__(self, master, variable, options, command=None):
        super().__init__(master, bg=parent_bg(master))
        self.var, self.command = variable, command
        self.buttons = {}
        for i, (value, label) in enumerate(options):
            btn = RoundButton(self, label, command=lambda v=value: self._select(v), height=30,
                              font=(UI, 9, "bold"), padx=12)
            btn.pack(side="left", padx=(0 if i == 0 else 6, 0))
            self.buttons[value] = btn
        self.var.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    def _select(self, value):
        self.var.set(value)
        if self.command:
            self.command()

    def refresh(self):
        current = self.var.get()
        for value, btn in self.buttons.items():
            if value == current:
                btn.restyle(fill=SELECT_BG, fg=ACCENT, border=SELECT_BORDER)
            else:
                btn.restyle(fill=CARD2, fg=MUTED, border=BORDER)


def make_entry(master, variable, font=(MONO, 11), **kw):
    return tk.Entry(
        master, textvariable=variable, bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat",
        font=font, bd=5, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT,
        disabledbackground=FIELD, readonlybackground=FIELD, **kw,
    )


# ---------------------------------------------------------------------------
# Tools: 2FA, Notizen, Encoder, Zeitzonen, Einheiten, Zufall, Shortcuts, Statistik
# ---------------------------------------------------------------------------
import base64 as _b64
import hmac as _hmac
import struct as _struct
import time as _time
import urllib.parse as _urlparse
from datetime import timedelta

try:
    import tzdata  # noqa: F401  (Zeitzonen-Daten für Windows, wird mit in die EXE gepackt)
except ImportError:
    pass
try:
    from zoneinfo import ZoneInfo
    ZoneInfo("Europe/Berlin")
    TZ_OK = True
except Exception:
    ZoneInfo = None
    TZ_OK = False

TOOLS_FILE = os.path.join(BASE_DIR, "tools.json")
DEFAULT_TOOLS = {"notes": [], "totp": [], "shortcuts": []}

TIMEZONES = [
    ("Deutschland", "Europe/Berlin"),
    ("UK / London", "Europe/London"),
    ("Türkei", "Europe/Istanbul"),
    ("Russland (Moskau)", "Europe/Moscow"),
    ("USA Ost (New York)", "America/New_York"),
    ("USA West (Los Angeles)", "America/Los_Angeles"),
    ("Brasilien (São Paulo)", "America/Sao_Paulo"),
    ("Indien", "Asia/Kolkata"),
    ("China", "Asia/Shanghai"),
    ("Japan", "Asia/Tokyo"),
    ("Australien (Sydney)", "Australia/Sydney"),
    ("UTC", "UTC"),
]

UNITS = {
    "Länge": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "inch": 0.0254, "ft": 0.3048,
              "yard": 0.9144, "mile": 1609.344},
    "Gewicht": {"g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.0283495, "lb": 0.453592},
    "Temperatur": {"°C": None, "°F": None, "K": None},
    "Daten": {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "KiB": 1024, "MiB": 1024 ** 2,
              "GiB": 1024 ** 3},
}

PRESET_SHORTCUTS = [
    ("Steam", "https://store.steampowered.com"), ("Discord", "https://discord.com/app"),
    ("ProtonMail", "https://mail.proton.me"), ("YouTube", "https://youtube.com"),
    ("Twitch", "https://twitch.tv"), ("GitHub", "https://github.com"),
]

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _b32_key(secret):
    s = "".join(secret.split()).replace("-", "").upper().rstrip("=")
    if not s or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in s):
        raise ValueError("Der Schlüssel muss Base32 sein (Buchstaben A-Z und Ziffern 2-7).")
    return _b64.b32decode(s + "=" * (-len(s) % 8))


def totp_code(secret, digits=6, period=30, algo="SHA1", for_time=None):
    key = _b32_key(secret)
    counter = int((_time.time() if for_time is None else for_time) // period)
    digestmod = {"SHA1": hashlib.sha1, "SHA256": hashlib.sha256, "SHA512": hashlib.sha512}.get(algo, hashlib.sha1)
    digest = _hmac.new(key, _struct.pack(">Q", counter), digestmod).digest()
    offset = digest[-1] & 0x0F
    value = (int.from_bytes(digest[offset:offset + 4], "big") & 0x7FFFFFFF) % (10 ** digits)
    return str(value).zfill(digits)


def parse_totp(name, text):
    """Nimmt einen Base32-Schlüssel oder einen otpauth://totp/...-Link."""
    text = (text or "").strip()
    entry = {"name": (name or "").strip(), "digits": 6, "period": 30, "algo": "SHA1"}
    if text.lower().startswith("otpauth://"):
        url = _urlparse.urlparse(text)
        if url.netloc.lower() != "totp":
            raise ValueError("Nur zeitbasierte Codes (otpauth://totp/…) werden unterstützt.")
        query = _urlparse.parse_qs(url.query)
        secret = (query.get("secret") or [""])[0]
        label = _urlparse.unquote(url.path.lstrip("/"))
        issuer = (query.get("issuer") or [""])[0]
        if not entry["name"]:
            entry["name"] = issuer or label.split(":")[0] or label
        try:
            entry["digits"] = int((query.get("digits") or ["6"])[0])
            entry["period"] = int((query.get("period") or ["30"])[0])
        except ValueError:
            raise ValueError("Der otpauth-Link ist fehlerhaft.")
        entry["algo"] = (query.get("algorithm") or ["SHA1"])[0].upper()
        if entry["digits"] not in (6, 7, 8) or not 10 <= entry["period"] <= 120:
            raise ValueError("Diese Code-Einstellungen werden nicht unterstützt.")
    else:
        secret = text
    if not entry["name"]:
        raise ValueError("Gib einen Namen ein (z. B. Discord).")
    entry["secret"] = "".join(secret.split()).replace("-", "").upper()
    totp_code(entry["secret"], entry["digits"], entry["period"], entry["algo"])  # prüft den Schlüssel
    entry["id"] = uuid.uuid4().hex
    return entry


class PEntry(tk.Entry):
    """Eingabefeld mit Platzhaltertext."""

    def __init__(self, master, placeholder="", font=(UI, 10), **kw):
        super().__init__(
            master, bg=FIELD, fg=MUTED, insertbackground=TEXT, relief="flat", font=font, bd=5,
            highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, **kw,
        )
        self.placeholder = placeholder
        self._ph = False
        self.bind("<FocusIn>", self._hide, add="+")
        self.bind("<FocusOut>", self._show, add="+")
        self._show()

    def _show(self, _=None):
        if not self.get() and self.placeholder:
            self._ph = True
            self.config(fg=MUTED)
            self.insert(0, self.placeholder)

    def _hide(self, _=None):
        if self._ph:
            self._ph = False
            self.delete(0, "end")
            self.config(fg=TEXT)

    def value(self):
        return "" if self._ph else self.get()

    def set(self, text):
        self._hide()
        self.delete(0, "end")
        self.insert(0, text)
        self.config(fg=TEXT)
        if not text and self.focus_get() is not self:
            self._show()


class NavItem(tk.Frame):
    def __init__(self, master, text, command):
        super().__init__(master, bg=CARD, cursor="hand2")
        self.command, self.active = command, False
        self.mark = tk.Frame(self, bg=CARD, width=3)
        self.mark.pack(side="left", fill="y", pady=6)
        self.label = tk.Label(self, text=text, bg=CARD, fg=MUTED, font=(UI, 10), anchor="w", cursor="hand2")
        self.label.pack(side="left", fill="x", expand=True, padx=(9, 6), pady=7)
        for w in (self, self.label, self.mark):
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", lambda e: self._paint(hover=True))
            w.bind("<Leave>", lambda e: self._paint())

    def set_active(self, value):
        self.active = value
        self._paint()

    def _paint(self, hover=False):
        bg = SELECT_BG if self.active else (CARD2 if hover else CARD)
        for w in (self, self.label):
            w.config(bg=bg)
        self.mark.config(bg=ACCENT if self.active else bg)
        self.label.config(fg=ACCENT if self.active else (TEXT if hover else MUTED),
                          font=(UI, 10, "bold" if self.active else "normal"))


TOOL_PAGES = [
    ("history", "Verlauf", "KONTEN"),
    ("stats", "Statistik", "KONTEN"),
    ("email", "E-Mail", "KONTEN"),
    ("totp", "2FA-Codes", "KONTEN"),
    ("notes", "Notizen", "TOOLS"),
    ("encoder", "Encoder / Hash", "TOOLS"),
    ("time", "Zeitzonen", "TOOLS"),
    ("units", "Einheiten", "TOOLS"),
    ("random", "Zufall", "TOOLS"),
    ("shortcuts", "Shortcuts", "TOOLS"),
]


class ToolsMixin:
    # ---------------------------------------------------------- Grundgerüst
    def _load_tools(self):
        data = load_json(TOOLS_FILE, DEFAULT_TOOLS)
        for key in DEFAULT_TOOLS:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key] = [x for x in data[key] if isinstance(x, dict)]
        self.tools = data

    def _save_tools(self):
        try:
            save_json_atomic(TOOLS_FILE, self.tools)
            return True
        except OSError as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e), parent=self)
            return False

    def _build_tools_tab(self):
        tab = self.tab_tools
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        side = RoundCard(tab, pad=8, fixed=True, radius=14)
        side.configure(width=196)
        side.grid(row=0, column=0, sticky="nsw", padx=(14, 8), pady=10)
        self._tool_nav = {}
        section = None
        for key, title, sec in TOOL_PAGES:
            if sec != section:
                section = sec
                tk.Label(side.body, text=sec, bg=CARD, fg=MUTED, font=(UI, 7, "bold")).pack(
                    anchor="w", padx=10, pady=(10 if key != TOOL_PAGES[0][0] else 4, 3))
            item = NavItem(side.body, title, lambda k=key: self.show_tool(k))
            item.pack(fill="x", pady=1)
            self._tool_nav[key] = item

        self.tool_area = tk.Frame(tab, bg=PANEL)
        self.tool_area.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=0)
        self.tool_area.grid_rowconfigure(0, weight=1)
        self.tool_area.grid_columnconfigure(0, weight=1)
        self._tool_pages = {}
        self._tool_builders = {
            "history": self._build_history_tab, "stats": self._build_stats_page,
            "email": self._build_email_tab, "totp": self._build_totp_page, "notes": self._build_notes_page,
            "encoder": self._build_encoder_page, "time": self._build_time_page,
            "units": self._build_units_page, "random": self._build_random_page,
            "shortcuts": self._build_shortcuts_page,
        }
        self.current_tool = None
        # Verlauf + E-Mail sofort bauen (werden vom Generator aktualisiert)
        for key in ("history", "email"):
            self._ensure_tool(key)
        self.show_tool("history")

    def _ensure_tool(self, key):
        if key not in self._tool_pages:
            frame = tk.Frame(self.tool_area, bg=PANEL)
            frame.grid(row=0, column=0, sticky="nsew")
            frame.grid_remove()
            self._tool_pages[key] = frame
            if key == "history":
                self.tab_history = frame
            elif key == "email":
                self.tab_email = frame
            self._tool_page_frame = frame
            self._tool_builders[key]()
        return self._tool_pages[key]

    def show_tool(self, key):
        self._ensure_tool(key)
        for k, frame in self._tool_pages.items():
            if k == key:
                frame.grid()
            else:
                frame.grid_remove()
        for k, item in self._tool_nav.items():
            item.set_active(k == key)
        self.current_tool = key
        if key == "stats":
            self.refresh_stats()
        if key == "totp":
            self._totp_tick()
        if key == "time":
            self._clock_tick()
        if key == "notes" and hasattr(self, "note_text"):
            self._render_note_list()

    def _tool_visible(self, key):
        return getattr(self, "current_tab", 0) == 1 and self.current_tool == key

    def _tool_page(self, title, subtitle, scroll=True):
        frame = self._tool_page_frame
        head = tk.Frame(frame, bg=PANEL)
        head.pack(fill="x", padx=8, pady=(12, 8))
        tk.Label(head, text=title, bg=PANEL, fg=TEXT, font=(UI, 15, "bold")).pack(anchor="w")
        tk.Label(head, text=subtitle, bg=PANEL, fg=MUTED, font=(UI, 9)).pack(anchor="w")
        if not scroll:
            body = tk.Frame(frame, bg=PANEL)
            body.pack(fill="both", expand=True, padx=8, pady=(0, 10))
            return body
        sf = ScrollFrame(frame, bg=PANEL)
        sf.pack(fill="both", expand=True, padx=(8, 4), pady=(0, 10))
        return sf.inner

    @staticmethod
    def _result_card(parent, var, size=18):
        card = RoundCard(parent, pad=16)
        card.pack(fill="x", pady=(0, 10))
        tk.Label(card.body, textvariable=var, bg=CARD, fg=ACCENT, font=(MONO, size, "bold")).pack()
        return card

    @staticmethod
    def _combo(parent, var, values, width=24):
        return ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width,
                            style="Dark.TCombobox", font=(UI, 10))

    # ------------------------------------------------------------ Statistik
    def _build_stats_page(self):
        root = self._tool_page("Statistik", "Überblick über alles, was du generiert hast.")
        self.stat_tiles = tk.Frame(root, bg=PANEL)
        self.stat_tiles.pack(fill="x", pady=(0, 10))
        self.stat_values = {}
        for i, (key, label) in enumerate((("total", "GESAMT"), ("today", "HEUTE"), ("week", "7 TAGE"),
                                          ("month", "DIESER MONAT"))):
            self.stat_tiles.grid_columnconfigure(i, weight=1, uniform="st")
            tile = RoundCard(self.stat_tiles, pad=12)
            tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0 if i == 3 else 4))
            value = tk.Label(tile.body, text="0", bg=CARD, fg=TEXT, font=(MONO, 18, "bold"))
            value.pack(anchor="w")
            tk.Label(tile.body, text=label, bg=CARD, fg=MUTED, font=(UI, 7, "bold")).pack(anchor="w")
            self.stat_values[key] = value

        chart = RoundCard(root, pad=12)
        chart.pack(fill="x", pady=(0, 10))
        tk.Label(chart.body, text="LETZTE 7 TAGE", bg=CARD, fg=TEXT, font=(UI, 8, "bold")).pack(anchor="w")
        self.stats_canvas = tk.Canvas(chart.body, bg=CARD, height=150, highlightthickness=0, bd=0)
        self.stats_canvas.pack(fill="x", pady=(6, 0))
        self.stats_canvas.bind("<Configure>", lambda e: self._draw_stats_chart())

        self.reuse_card = RoundCard(root, pad=12)
        self.reuse_card.pack(fill="x", pady=(0, 10))

        leak = RoundCard(root, pad=12)
        leak.pack(fill="x")
        tk.Label(leak.body, text="LEAK-CHECK FÜR ALLE GESPEICHERTEN PASSWÖRTER", bg=CARD, fg=TEXT,
                 font=(UI, 8, "bold")).pack(anchor="w")
        tk.Label(leak.body, text="Prüft bei haveibeenpwned.com. Gesendet werden nur die ersten 5 Zeichen "
                                 "des SHA-1-Hashes, nie das Passwort.", bg=CARD, fg=MUTED, font=(UI, 8),
                 wraplength=600, justify="left").pack(anchor="w", pady=(2, 8))
        row = tk.Frame(leak.body, bg=CARD)
        row.pack(fill="x")
        self.leak_all_btn = RoundButton(row, "Alle prüfen", command=self.leak_check_all, height=32,
                                        fill=ACCENT, fg=ACCENT_DARK)
        self.leak_all_btn.pack(side="left")
        self.leak_all_label = tk.Label(row, text="", bg=CARD, fg=MUTED, font=(UI, 9), justify="left",
                                       wraplength=480)
        self.leak_all_label.pack(side="left", padx=10)

    def refresh_stats(self):
        if "stats" not in self._tool_pages:
            return
        now = datetime.now()
        today = week = month = 0
        daily = [0] * 7
        for entry in self.credentials:
            try:
                ts = datetime.fromisoformat(entry.get("generated_at", ""))
            except (TypeError, ValueError):
                continue
            days_ago = (now.date() - ts.date()).days
            if days_ago == 0:
                today += 1
            if 0 <= days_ago < 7:
                week += 1
                daily[6 - days_ago] += 1
            if ts.year == now.year and ts.month == now.month:
                month += 1
        for key, value in (("total", len(self.credentials)), ("today", today), ("week", week),
                           ("month", month)):
            self.stat_values[key].config(text=str(value))
        self._stats_daily = daily
        self._draw_stats_chart()

        body = self.reuse_card.body
        for child in body.winfo_children():
            child.destroy()
        groups = {}
        for entry in self.credentials:
            if entry.get("password"):
                groups.setdefault(entry["password"], []).append(entry)
        groups = [g for g in groups.values() if len(g) > 1]
        tk.Label(body, text="DOPPELT VERWENDETE PASSWÖRTER", bg=CARD, fg=TEXT, font=(UI, 8, "bold")).pack(anchor="w")
        if not groups:
            tk.Label(body, text="Keine – jeder Eintrag hat sein eigenes Passwort.", bg=CARD, fg=GREEN,
                     font=(UI, 9)).pack(anchor="w", pady=(4, 0))
        else:
            for group in groups[:6]:
                names = ", ".join(e.get("username", "?") for e in group[:5])
                tk.Label(body, text=f"{len(group)}×  {names}", bg=CARD, fg=ORANGE, font=(UI, 9),
                         anchor="w").pack(anchor="w", pady=(3, 0))

    def _draw_stats_chart(self):
        c = getattr(self, "stats_canvas", None)
        daily = getattr(self, "_stats_daily", None)
        if c is None or daily is None:
            return
        c.delete("all")
        w, h = max(c.winfo_width(), 200), 150
        bottom, top = 22, 16
        peak = max(daily) or 1
        gap = w / 7
        bar = min(46, gap * 0.55)
        today = datetime.now().date()
        for i, count in enumerate(daily):
            day = today - timedelta(days=6 - i)
            x0 = i * gap + (gap - bar) / 2
            x1 = x0 + bar
            y1 = h - bottom
            y0 = y1 - max(4, count / peak * (h - top - bottom))
            color = ACCENT if count else TRACK
            round_rect(c, x0, y0, x1, y1, 5, fill=color, outline=color)
            if count:
                c.create_text((x0 + x1) / 2, y0 - 8, text=str(count), fill=TEXT, font=(UI, 8, "bold"))
            c.create_text((x0 + x1) / 2, h - 9, text=WEEKDAYS[day.weekday()], fill=MUTED, font=(UI, 8))

    def leak_check_all(self):
        passwords = list(dict.fromkeys(e.get("password") for e in self.credentials if e.get("password")))
        if not passwords:
            self.leak_all_label.config(text="Keine gespeicherten Passwörter.", fg=MUTED)
            return
        self.leak_all_label.config(text=f"Prüfe 0 / {len(passwords)} …", fg=MUTED)

        def worker():
            leaked, failed = [], 0
            for i, pw in enumerate(passwords, 1):
                try:
                    if hibp_count(pw):
                        leaked.append(pw)
                except Exception:
                    failed += 1
                self.after(0, lambda i=i: self.leak_all_label.config(text=f"Prüfe {i} / {len(passwords)} …"))
                _time.sleep(0.15)

            def done():
                if failed == len(passwords):
                    self.leak_all_label.config(text="Keine Verbindung zu haveibeenpwned.com.", fg=ORANGE)
                elif leaked:
                    names = [e.get("username", "?") for e in self.credentials if e.get("password") in leaked]
                    self.leak_all_label.config(
                        text=f"{len(leaked)} Passwort(e) geleakt: {', '.join(names[:6])}"
                             f"{' …' if len(names) > 6 else ''} – bitte ändern!", fg=DANGER)
                else:
                    self.leak_all_label.config(text=f"Alle {len(passwords)} Passwörter sind sauber.", fg=GREEN)
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------- 2FA-Codes
    def _build_totp_page(self):
        root = self._tool_page("2FA-Codes", "Dieselben 6-stelligen Codes wie Google Authenticator.", scroll=False)
        add = RoundCard(root, pad=12)
        add.pack(fill="x", pady=(0, 6))
        row = tk.Frame(add.body, bg=CARD)
        row.pack(fill="x")
        RoundButton(row, "Hinzufügen", command=self.add_totp, height=34, fill=ACCENT, fg=ACCENT_DARK).pack(
            side="right", padx=(8, 0))
        self.totp_name = PEntry(row, "Name (z. B. Discord)", width=18)
        self.totp_name.pack(side="left", ipady=3)
        self.totp_secret = PEntry(row, "Schlüssel oder otpauth://-Link", font=(MONO, 10))
        self.totp_secret.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=3)
        self.totp_secret.bind("<Return>", lambda e: self.add_totp())
        tk.Label(add.body, text="Auf der Website bei 2FA „Code kann nicht gescannt werden?“ wählen und den "
                                "Schlüssel hier einfügen. Achtung: tools.json ist nicht verschlüsselt.",
                 bg=CARD, fg=MUTED, font=(UI, 8), wraplength=620, justify="left").pack(anchor="w", pady=(8, 0))
        self.totp_scroll = ScrollFrame(root, bg=PANEL)
        self.totp_scroll.pack(fill="both", expand=True, pady=(4, 0))
        self.render_totp()

    def render_totp(self):
        inner = self.totp_scroll.inner
        for child in inner.winfo_children():
            child.destroy()
        self._totp_rows = []
        if not self.tools["totp"]:
            card = RoundCard(inner, pad=16)
            card.pack(fill="x")
            tk.Label(card.body, text="Noch keine 2FA-Konten.", bg=CARD, fg=MUTED, font=(UI, 10)).pack()
            return
        for acc in self.tools["totp"]:
            card = RoundCard(inner, pad=12, radius=10)
            card.pack(fill="x", pady=(0, 6))
            body = card.body
            RoundButton(body, "Löschen", command=lambda a=acc: self.delete_totp(a), height=30, padx=10,
                        fill=CARD2, fg=DANGER, font=(UI, 8, "bold")).pack(side="right", padx=(6, 0))
            RoundButton(body, "Kopieren", command=lambda a=acc: self.copy_totp(a), height=30, padx=10,
                        fill=CARD2, font=(UI, 8, "bold")).pack(side="right")
            info = tk.Frame(body, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=acc.get("name", "?"), bg=CARD, fg=MUTED, font=(UI, 9, "bold")).pack(anchor="w")
            code = tk.Label(info, text="", bg=CARD, fg=TEXT, font=(MONO, 20, "bold"), cursor="hand2")
            code.pack(anchor="w")
            code.bind("<Button-1>", lambda e, a=acc: self.copy_totp(a))
            bar = Bar(info, height=5)
            bar.pack(fill="x", pady=(2, 0), padx=(0, 20))
            self._totp_rows.append((acc, code, bar))
        self._update_totp()

    def _update_totp(self):
        now = _time.time()
        for acc, label, bar in getattr(self, "_totp_rows", []):
            period = int(acc.get("period", 30))
            try:
                code = totp_code(acc["secret"], int(acc.get("digits", 6)), period, acc.get("algo", "SHA1"), now)
                half = len(code) // 2
                label.config(text=f"{code[:half]} {code[half:]}", fg=TEXT)
            except Exception:
                label.config(text="ungültiger Schlüssel", fg=DANGER)
            left = period - (now % period)
            bar.set(left / period, DANGER if left <= 5 else ACCENT)

    def _totp_tick(self):
        if getattr(self, "_totp_job", None):
            return
        def tick():
            self._totp_job = None
            if self._tool_visible("totp"):
                self._update_totp()
                self._totp_job = self.after(500, tick)
        tick()

    def add_totp(self):
        try:
            entry = parse_totp(self.totp_name.value(), self.totp_secret.value())
        except Exception as e:
            messagebox.showwarning("2FA", str(e) or "Dieser Schlüssel funktioniert nicht.", parent=self)
            return
        if any(a.get("secret") == entry["secret"] for a in self.tools["totp"]):
            messagebox.showinfo("2FA", "Dieser Schlüssel ist schon gespeichert.", parent=self)
            return
        self.tools["totp"].append(entry)
        if not self._save_tools():
            self.tools["totp"].remove(entry)
            return
        self.totp_name.set("")
        self.totp_secret.set("")
        self.render_totp()
        self.set_status(f"{entry['name']} hinzugefügt")

    def delete_totp(self, acc):
        if not messagebox.askyesno(
                "2FA löschen", f"„{acc.get('name')}“ löschen?\n\nStell sicher, dass 2FA auf der Seite deaktiviert "
                               "ist oder du Backup-Codes hast – sonst sperrst du dich aus.", parent=self):
            return
        self.tools["totp"] = [a for a in self.tools["totp"] if a is not acc]
        self._save_tools()
        self.render_totp()

    def copy_totp(self, acc):
        try:
            code = totp_code(acc["secret"], int(acc.get("digits", 6)), int(acc.get("period", 30)),
                             acc.get("algo", "SHA1"))
        except Exception:
            messagebox.showwarning("2FA", "Dieser Schlüssel ist ungültig.", parent=self)
            return
        self._copy(code)
        self.set_status(f"{acc.get('name')}: Code kopiert")

    # -------------------------------------------------------------- Notizen
    def _build_notes_page(self):
        root = self._tool_page("Notizen", "Werden automatisch gespeichert.", scroll=False)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        side = RoundCard(root, pad=8, fixed=True)
        side.configure(width=200)
        side.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        top = tk.Frame(side.body, bg=CARD)
        top.pack(fill="x", pady=(0, 6))
        RoundButton(top, "+", command=self.new_note, height=30, width=32, fill=ACCENT, fg=ACCENT_DARK,
                    font=(UI, 11, "bold")).pack(side="right", padx=(6, 0))
        self.note_search = PEntry(top, "Suchen …", width=10)
        self.note_search.pack(side="left", fill="x", expand=True, ipady=2)
        self.note_search.bind("<KeyRelease>", lambda e: self._render_note_list())
        self.note_list_scroll = ScrollFrame(side.body, bg=CARD, style="Card.Slim.Vertical.TScrollbar")
        self.note_list_scroll.pack(fill="both", expand=True)

        editor = RoundCard(root, pad=12, fixed=True)
        editor.grid(row=0, column=1, sticky="nsew")
        head = tk.Frame(editor.body, bg=CARD)
        head.pack(fill="x")
        RoundButton(head, "Löschen", command=self.delete_note, height=30, padx=10, fill=CARD2, fg=DANGER,
                    font=(UI, 8, "bold")).pack(side="right")
        self.note_status = tk.Label(head, text="", bg=CARD, fg=GREEN, font=(UI, 8))
        self.note_status.pack(side="right", padx=8)
        self.note_title = tk.Entry(head, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                                   font=(UI, 14, "bold"), highlightthickness=0)
        self.note_title.pack(side="left", fill="x", expand=True)
        self.note_title.bind("<KeyRelease>", self._schedule_note_save)
        tk.Frame(editor.body, bg=BORDER_SOFT, height=1).pack(fill="x", pady=8)
        self.note_text = tk.Text(editor.body, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                                 font=(MONO, 10), wrap="word", undo=True, highlightthickness=0,
                                 selectbackground=SELECT_BG)
        self.note_text.pack(fill="both", expand=True)
        self.note_text.bind("<KeyRelease>", self._schedule_note_save)

        if not self.tools["notes"]:
            self._add_note(save=False)
        self.open_note(self.tools["notes"][0]["id"])

    def _note(self, nid):
        return next((n for n in self.tools["notes"] if n.get("id") == nid), None)

    def _add_note(self, save=True):
        note = {"id": uuid.uuid4().hex, "title": "Neue Notiz", "text": "",
                "updated": datetime.now().isoformat(timespec="seconds")}
        self.tools["notes"].insert(0, note)
        if save:
            self._save_tools()
        return note

    def new_note(self):
        self._flush_note()
        note = self._add_note()
        self.open_note(note["id"])
        self.note_title.focus_set()
        self.note_title.select_range(0, "end")

    def open_note(self, nid):
        self._flush_note()
        note = self._note(nid)
        if note is None:
            return
        self._current_note = nid
        self.note_title.delete(0, "end")
        self.note_title.insert(0, note.get("title", ""))
        self.note_text.delete("1.0", "end")
        self.note_text.insert("1.0", note.get("text", ""))
        self.note_text.edit_reset()
        self._render_note_list()

    def _render_note_list(self):
        inner = self.note_list_scroll.inner
        for child in inner.winfo_children():
            child.destroy()
        query = self.note_search.value().strip().lower()
        notes = sorted(self.tools["notes"], key=lambda n: n.get("updated", ""), reverse=True)
        notes = [n for n in notes if not query or query in (n.get("title", "") + n.get("text", "")).lower()]
        if not notes:
            tk.Label(inner, text="Nichts gefunden.", bg=CARD, fg=MUTED, font=(UI, 9)).pack(pady=8)
            return
        for note in notes:
            active = note.get("id") == getattr(self, "_current_note", None)
            bg = SELECT_BG if active else CARD
            row = tk.Frame(inner, bg=bg, cursor="hand2")
            row.pack(fill="x", pady=1)
            title = tk.Label(row, text=(note.get("title") or "Ohne Titel")[:26], bg=bg,
                             fg=ACCENT if active else TEXT, font=(UI, 9, "bold"), anchor="w")
            title.pack(fill="x", padx=8, pady=(5, 0))
            preview = (note.get("text", "").strip().splitlines() or [""])[0][:30]
            sub = tk.Label(row, text=preview or " ", bg=bg, fg=MUTED, font=(UI, 8), anchor="w")
            sub.pack(fill="x", padx=8, pady=(0, 5))
            for w in (row, title, sub):
                w.bind("<Button-1>", lambda e, i=note.get("id"): self.open_note(i))

    def _schedule_note_save(self, _=None):
        if getattr(self, "_note_job", None):
            self.after_cancel(self._note_job)
        self._note_job = self.after(700, self._flush_note)

    def _flush_note(self):
        if getattr(self, "_note_job", None):
            self.after_cancel(self._note_job)
        self._note_job = None
        note = self._note(getattr(self, "_current_note", None))
        if note is None or not hasattr(self, "note_text"):
            return
        title = self.note_title.get().strip()
        text = self.note_text.get("1.0", "end-1c")
        if title == note.get("title") and text == note.get("text"):
            return
        note.update(title=title, text=text, updated=datetime.now().isoformat(timespec="seconds"))
        if self._save_tools():
            self.note_status.config(text="Gespeichert ✓")
            self.after(1200, lambda: self.note_status.config(text=""))
            self._render_note_list()

    def delete_note(self):
        note = self._note(getattr(self, "_current_note", None))
        if note is None:
            return
        if not messagebox.askyesno("Notiz löschen", f"„{note.get('title') or 'Ohne Titel'}“ löschen?", parent=self):
            return
        self._note_job and self.after_cancel(self._note_job)
        self._note_job = None
        self.tools["notes"] = [n for n in self.tools["notes"] if n is not note]
        if not self.tools["notes"]:
            self._add_note(save=False)
        self._save_tools()
        self._current_note = None
        self.open_note(self.tools["notes"][0]["id"])

    # -------------------------------------------------------------- Encoder
    def _build_encoder_page(self):
        root = self._tool_page("Encoder / Hash", "Text einfügen, Aktion wählen, Ergebnis kopieren.")
        tk.Label(root, text="EINGABE", bg=PANEL, fg=MUTED, font=(UI, 8, "bold")).pack(anchor="w")
        self.enc_input = tk.Text(root, height=6, bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat", bd=8,
                                 font=(MONO, 10), wrap="word", highlightthickness=1, highlightbackground=BORDER,
                                 highlightcolor=ACCENT)
        self.enc_input.pack(fill="x", pady=(4, 10))
        grid = tk.Frame(root, bg=PANEL)
        grid.pack(fill="x")
        actions = [
            ("Base64 kodieren", lambda t: _b64.b64encode(t.encode("utf-8")).decode("ascii")),
            ("Base64 dekodieren", lambda t: _b64.b64decode(t.encode("ascii"), validate=False).decode("utf-8")),
            ("URL kodieren", lambda t: _urlparse.quote(t, safe="")),
            ("URL dekodieren", _urlparse.unquote),
            ("MD5", lambda t: hashlib.md5(t.encode("utf-8")).hexdigest()),
            ("SHA-1", lambda t: hashlib.sha1(t.encode("utf-8")).hexdigest()),
            ("SHA-256", lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()),
            ("Großbuchstaben", str.upper),
        ]
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1, uniform="enc")
        for i, (label, func) in enumerate(actions):
            RoundButton(grid, label, command=lambda f=func: self._run_encoder(f), height=34, fill=CARD,
                        border=BORDER, font=(UI, 9)).grid(row=i // 4, column=i % 4, sticky="ew", padx=3, pady=3)
        RoundButton(root, "Leak-Check (Passwort)", command=self._encoder_leak, height=34, fill=CARD,
                    border=BORDER, font=(UI, 9)).pack(fill="x", padx=3, pady=(3, 10))
        head = tk.Frame(root, bg=PANEL)
        head.pack(fill="x")
        tk.Label(head, text="AUSGABE", bg=PANEL, fg=MUTED, font=(UI, 8, "bold")).pack(side="left")
        RoundButton(head, "Kopieren", command=lambda: self._copy(self.enc_output.get("1.0", "end-1c")),
                    height=28, padx=10, font=(UI, 8, "bold")).pack(side="right")
        RoundButton(head, "→ Eingabe", command=self._encoder_to_input, height=28, padx=10,
                    font=(UI, 8, "bold")).pack(side="right", padx=(0, 6))
        self.enc_output = tk.Text(root, height=5, bg=CARD, fg=ACCENT, relief="flat", bd=8, font=(MONO, 10),
                                  wrap="char", highlightthickness=1, highlightbackground=BORDER_SOFT)
        self.enc_output.pack(fill="x", pady=(4, 0))
        self._set_enc_output("—")

    def _set_enc_output(self, text):
        self.enc_output.config(state="normal")
        self.enc_output.delete("1.0", "end")
        self.enc_output.insert("1.0", text)
        self.enc_output.config(state="disabled")

    def _run_encoder(self, func):
        text = self.enc_input.get("1.0", "end-1c")
        if not text.strip():
            self._set_enc_output("Bitte zuerst etwas eingeben.")
            return
        try:
            self._set_enc_output(func(text.strip() if func is not str.upper else text))
        except Exception as e:
            self._set_enc_output(f"Fehler: {e}")

    def _encoder_to_input(self):
        out = self.enc_output.get("1.0", "end-1c")
        self.enc_input.delete("1.0", "end")
        self.enc_input.insert("1.0", out)

    def _encoder_leak(self):
        pw = self.enc_input.get("1.0", "end-1c").strip()
        if not pw:
            self._set_enc_output("Bitte zuerst ein Passwort eingeben.")
            return
        self._set_enc_output("Prüfe …")

        def worker():
            try:
                count = hibp_count(pw)
                text = (f"GELEAKT: {count:,}× in bekannten Datenlecks gefunden. Nicht benutzen!".replace(",", ".")
                        if count else "In keinem bekannten Datenleck gefunden.")
            except Exception:
                text = "Keine Verbindung zu haveibeenpwned.com."
            self.after(0, lambda: self._set_enc_output(text))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------ Zeitzonen
    def _build_time_page(self):
        root = self._tool_page("Zeitzonen", "Uhrzeit zwischen Zeitzonen umrechnen.")
        if not TZ_OK:
            tk.Label(root, text="Zeitzonen-Daten fehlen (pip install tzdata).", bg=PANEL, fg=ORANGE,
                     font=(UI, 9)).pack(anchor="w", pady=(0, 8))
        names = [n for n, _ in TIMEZONES]
        self.tz_from = tk.StringVar(value="Japan")
        self.tz_to = tk.StringVar(value="Deutschland")
        card = RoundCard(root, pad=14)
        card.pack(fill="x", pady=(0, 10))
        for label, var, with_time in (("VON", self.tz_from, True), ("NACH", self.tz_to, False)):
            row = tk.Frame(card.body, bg=CARD)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, bg=CARD, fg=MUTED, font=(UI, 8, "bold"), width=6, anchor="w").pack(side="left")
            self._combo(row, var, names).pack(side="left", fill="x", expand=True)
            if with_time:
                self.time_in = PEntry(row, "", font=(MONO, 11), width=7, justify="center")
                self.time_in.set(datetime.now().strftime("%H:%M"))
                self.time_in.pack(side="right", padx=(8, 0), ipady=2)
                self.time_in.bind("<Return>", lambda e: self.convert_time())
            else:
                RoundButton(row, "⇅", command=self._swap_tz, height=30, width=40).pack(side="right", padx=(8, 0))
        RoundButton(root, "Umrechnen", command=self.convert_time, height=40, radius=11, font=(UI, 10, "bold"),
                    fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2)).pack(fill="x", pady=(0, 10))
        self.time_result = tk.StringVar(value="—")
        self._result_card(root, self.time_result, size=16)
        live = RoundCard(root, pad=14)
        live.pack(fill="x")
        tk.Label(live.body, text="LIVE", bg=CARD, fg=TEXT, font=(UI, 8, "bold")).pack(anchor="w", pady=(0, 6))
        grid = tk.Frame(live.body, bg=CARD)
        grid.pack(fill="x")
        self.clock_labels = []
        for i, (name, zone) in enumerate(TIMEZONES):
            grid.grid_columnconfigure(i % 2 * 2 + 1, weight=1)
            tk.Label(grid, text=name, bg=CARD, fg=MUTED, font=(UI, 9), anchor="w").grid(
                row=i // 2, column=i % 2 * 2, sticky="w", pady=1)
            value = tk.Label(grid, text="--:--:--", bg=CARD, fg=TEXT, font=(MONO, 10, "bold"), anchor="e")
            value.grid(row=i // 2, column=i % 2 * 2 + 1, sticky="e", padx=(6, 18))
            self.clock_labels.append((zone, value))

    def _swap_tz(self):
        a, b = self.tz_from.get(), self.tz_to.get()
        self.tz_from.set(b)
        self.tz_to.set(a)

    def convert_time(self):
        if not TZ_OK:
            self.time_result.set("Zeitzonen-Daten fehlen")
            return
        try:
            h, m = (int(x) for x in self.time_in.value().strip().replace(".", ":").split(":"))
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError
        except ValueError:
            self.time_result.set("Format: HH:MM, z. B. 14:30")
            return
        zones = dict(TIMEZONES)
        src = datetime.now(ZoneInfo(zones[self.tz_from.get()])).replace(hour=h, minute=m, second=0, microsecond=0)
        dst = src.astimezone(ZoneInfo(zones[self.tz_to.get()]))
        diff = (dst.date() - src.date()).days
        note = {1: "  (nächster Tag)", -1: "  (Vortag)"}.get(diff, "" if diff == 0 else f"  ({diff:+d} Tage)")
        self.time_result.set(f"{dst.strftime('%H:%M')}{note}  ·  {self.tz_to.get()}")

    def _clock_tick(self):
        if getattr(self, "_clock_job", None):
            return
        def tick():
            self._clock_job = None
            if not self._tool_visible("time"):
                return
            for zone, label in self.clock_labels:
                try:
                    label.config(text=datetime.now(ZoneInfo(zone)).strftime("%H:%M:%S") if TZ_OK else "—")
                except Exception:
                    label.config(text="—")
            self._clock_job = self.after(1000, tick)
        tick()

    # ------------------------------------------------------------ Einheiten
    def _build_units_page(self):
        root = self._tool_page("Einheiten", "Länge, Gewicht, Temperatur und Datengrößen umrechnen.")
        self.unit_cat = tk.StringVar(value="Länge")
        self.unit_from = tk.StringVar()
        self.unit_to = tk.StringVar()
        self.unit_result = tk.StringVar(value="—")
        card = RoundCard(root, pad=14)
        card.pack(fill="x", pady=(0, 10))
        Segmented(card.body, self.unit_cat, [(k, k) for k in UNITS], command=self._refresh_units).pack(
            anchor="w", pady=(0, 10))
        row = tk.Frame(card.body, bg=CARD)
        row.pack(fill="x", pady=4)
        tk.Label(row, text="VON", bg=CARD, fg=MUTED, font=(UI, 8, "bold"), width=6, anchor="w").pack(side="left")
        self.unit_from_box = self._combo(row, self.unit_from, [], width=12)
        self.unit_from_box.pack(side="left")
        self.unit_value = PEntry(row, "", font=(MONO, 11), justify="center")
        self.unit_value.set("1")
        self.unit_value.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=2)
        self.unit_value.bind("<KeyRelease>", lambda e: self.convert_units(quiet=True))
        row = tk.Frame(card.body, bg=CARD)
        row.pack(fill="x", pady=4)
        tk.Label(row, text="NACH", bg=CARD, fg=MUTED, font=(UI, 8, "bold"), width=6, anchor="w").pack(side="left")
        self.unit_to_box = self._combo(row, self.unit_to, [], width=12)
        self.unit_to_box.pack(side="left")
        RoundButton(row, "⇅", command=self._swap_units, height=30, width=40).pack(side="left", padx=(8, 0))
        for box in (self.unit_from_box, self.unit_to_box):
            box.bind("<<ComboboxSelected>>", lambda e: self.convert_units(quiet=True))
        self._refresh_units()
        self._result_card(root, self.unit_result, size=18)

    def _refresh_units(self):
        units = list(UNITS[self.unit_cat.get()])
        self.unit_from_box.config(values=units)
        self.unit_to_box.config(values=units)
        self.unit_from.set(units[0])
        self.unit_to.set(units[1])
        self.convert_units(quiet=True)

    def _swap_units(self):
        a, b = self.unit_from.get(), self.unit_to.get()
        self.unit_from.set(b)
        self.unit_to.set(a)
        self.convert_units(quiet=True)

    @staticmethod
    def _convert_temp(value, src, dst):
        c = value if src == "°C" else (value - 32) * 5 / 9 if src == "°F" else value - 273.15
        return c if dst == "°C" else c * 9 / 5 + 32 if dst == "°F" else c + 273.15

    def convert_units(self, quiet=False):
        try:
            value = float(self.unit_value.value().replace(",", "."))
        except ValueError:
            self.unit_result.set("—" if quiet else "Bitte eine Zahl eingeben")
            return
        cat, src, dst = self.unit_cat.get(), self.unit_from.get(), self.unit_to.get()
        try:
            if cat == "Temperatur":
                result = self._convert_temp(value, src, dst)
            else:
                result = value * UNITS[cat][src] / UNITS[cat][dst]
        except (KeyError, TypeError, ZeroDivisionError):
            self.unit_result.set("—")
            return
        text = f"{result:,.6f}".rstrip("0").rstrip(".").replace(",", "X").replace(".", ",").replace("X", ".")
        self.unit_result.set(f"{text} {dst}")

    # --------------------------------------------------------------- Zufall
    def _build_random_page(self):
        root = self._tool_page("Zufall", "Zufallszahl, Würfel oder Münzwurf (kryptografisch sicher).")
        card = RoundCard(root, pad=14)
        card.pack(fill="x", pady=(0, 10))
        row = tk.Frame(card.body, bg=CARD)
        row.pack(fill="x")
        tk.Label(row, text="MIN", bg=CARD, fg=MUTED, font=(UI, 8, "bold")).pack(side="left")
        self.rand_min = PEntry(row, "", font=(MONO, 11), width=10, justify="center")
        self.rand_min.set("1")
        self.rand_min.pack(side="left", padx=(8, 20), ipady=2)
        tk.Label(row, text="MAX", bg=CARD, fg=MUTED, font=(UI, 8, "bold")).pack(side="left")
        self.rand_max = PEntry(row, "", font=(MONO, 11), width=10, justify="center")
        self.rand_max.set("100")
        self.rand_max.pack(side="left", padx=8, ipady=2)
        RoundButton(root, "Zufallszahl", command=self.roll_number, height=40, radius=11, font=(UI, 10, "bold"),
                    fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2)).pack(fill="x", pady=(0, 8))
        quick = tk.Frame(root, bg=PANEL)
        quick.pack(fill="x", pady=(0, 10))
        for i, (label, cmd) in enumerate((("Münze werfen", lambda: self.rand_result.set(
                secrets.choice(["Kopf", "Zahl"]))), ("Würfel (1–6)", lambda: self.rand_result.set(
                str(1 + secrets.randbelow(6)))), ("Ja / Nein", lambda: self.rand_result.set(
                secrets.choice(["Ja", "Nein"]))))):
            quick.grid_columnconfigure(i, weight=1, uniform="q")
            RoundButton(quick, label, command=cmd, height=36, fill=CARD, border=BORDER).grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0 if i == 2 else 4))
        self.rand_result = tk.StringVar(value="—")
        card = RoundCard(root, pad=26)
        card.pack(fill="x")
        tk.Label(card.body, textvariable=self.rand_result, bg=CARD, fg=ACCENT, font=(MONO, 32, "bold")).pack()

    def roll_number(self):
        try:
            lo, hi = int(float(self.rand_min.value())), int(float(self.rand_max.value()))
        except ValueError:
            self.rand_result.set("Zahlen eingeben")
            return
        if lo > hi:
            lo, hi = hi, lo
        self.rand_result.set(str(lo + secrets.randbelow(hi - lo + 1)))

    # ------------------------------------------------------------ Shortcuts
    def _build_shortcuts_page(self):
        root = self._tool_page("Shortcuts", "Mit einem Klick zu deinen Lieblingsseiten.")
        grid = tk.Frame(root, bg=PANEL)
        grid.pack(fill="x", pady=(0, 12))
        for i, (label, url) in enumerate(PRESET_SHORTCUTS):
            grid.grid_columnconfigure(i % 3, weight=1, uniform="ps")
            RoundButton(grid, label, command=lambda u=url: webbrowser.open(u), height=40, fill=CARD,
                        border=BORDER, font=(UI, 10, "bold")).grid(row=i // 3, column=i % 3, sticky="ew",
                                                                   padx=3, pady=3)
        tk.Label(root, text="EIGENE SHORTCUTS", bg=PANEL, fg=TEXT, font=(UI, 8, "bold")).pack(anchor="w", pady=(0, 6))
        add = tk.Frame(root, bg=PANEL)
        add.pack(fill="x", pady=(0, 8))
        RoundButton(add, "+ Hinzufügen", command=self.add_shortcut, height=34, fill=ACCENT, fg=ACCENT_DARK).pack(
            side="right", padx=(8, 0))
        self.sc_name = PEntry(add, "Name", width=16)
        self.sc_name.pack(side="left", ipady=3)
        self.sc_url = PEntry(add, "URL, z. B. reddit.com")
        self.sc_url.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=3)
        self.sc_url.bind("<Return>", lambda e: self.add_shortcut())
        self.sc_list = tk.Frame(root, bg=PANEL)
        self.sc_list.pack(fill="x")
        self.render_shortcuts()

    def render_shortcuts(self):
        for child in self.sc_list.winfo_children():
            child.destroy()
        if not self.tools["shortcuts"]:
            tk.Label(self.sc_list, text="Noch keine eigenen Shortcuts.", bg=PANEL, fg=MUTED,
                     font=(UI, 9)).pack(anchor="w", pady=6)
            return
        for item in self.tools["shortcuts"]:
            card = RoundCard(self.sc_list, pad=10, radius=10)
            card.pack(fill="x", pady=(0, 6))
            RoundButton(card.body, "✕", command=lambda it=item: self.remove_shortcut(it), height=30, width=34,
                        fill=CARD2, fg=DANGER).pack(side="right", padx=(6, 0))
            RoundButton(card.body, "Öffnen", command=lambda u=item.get("url", ""): webbrowser.open(u), height=30,
                        padx=12, fill=CARD2, font=(UI, 8, "bold")).pack(side="right")
            info = tk.Frame(card.body, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=item.get("label", "?"), bg=CARD, fg=TEXT, font=(UI, 10, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=item.get("url", ""), bg=CARD, fg=MUTED, font=(MONO, 8), anchor="w").pack(fill="x")

    def add_shortcut(self):
        label, url = self.sc_name.value().strip(), self.sc_url.value().strip()
        if not label or not url:
            messagebox.showwarning("Shortcut", "Bitte Name und URL eingeben.", parent=self)
            return
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        self.tools["shortcuts"].append({"label": label, "url": url})
        if self._save_tools():
            self.sc_name.set("")
            self.sc_url.set("")
            self.render_shortcuts()

    def remove_shortcut(self, item):
        self.tools["shortcuts"] = [s for s in self.tools["shortcuts"] if s is not item]
        self._save_tools()
        self.render_shortcuts()



# ---------------------------------------------------------------------------
# Multitool-Oberfläche (Seitenleiste) – Einstellungen → Design & Fenster → Oberfläche
# ---------------------------------------------------------------------------
import csv as _csv

MT_NAV = [
    ("PASSWORDS", [("generator", "Generator"), ("email", "Email"), ("stats", "Stats"), ("totp", "2FA codes")]),
    ("TOOLS", [("notes", "Notes"), ("encoder", "Encoder / Hash"), ("time", "Time zones"), ("units", "Units"),
               ("random", "Random"), ("shortcuts", "Shortcuts")]),
]
MT_SORTS = ["Newest first", "Oldest first", "Username A–Z", "Favorites first"]
MT_ALL_TAGS = "All tags"
MT_STRENGTH = {0: "—", 1: "Very weak", 2: "Weak", 3: "Medium", 4: "Strong", 5: "Very strong"}


class MtNavItem(tk.Canvas):
    """Seitenleisten-Eintrag: weißer Balken + hellerer, abgerundeter Hintergrund, wenn aktiv."""

    def __init__(self, master, text, command):
        self.base = master.cget("bg")
        super().__init__(master, height=38, width=200, bg=self.base, highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.command = text, command
        self.active = self.hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self.command())

    def set_active(self, value):
        self.active = value
        self._draw()

    def _set_hover(self, value):
        self.hover = value
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30:
            return
        if self.active or self.hover:
            fill = SELECT_BG if self.active else mix(self.base, "#ffffff", 0.045)
            round_rect(self, 18, 2, w - 12, h - 2, 8, fill=fill, outline=fill)
        if self.active:
            round_rect(self, 10, 9, 13, h - 9, 1.5, fill=ACCENT, outline=ACCENT)
        color = TEXT if (self.active or self.hover) else mix(TEXT, self.base, 0.25)
        self.create_text(30, h / 2, text=self.text, anchor="w", fill=color,
                         font=(UI, 10, "bold" if self.active else "normal"))


class MultitoolMixin:
    # ---------------------------------------------------------------- Aufbau
    def _mt_build_ui(self):
        self.eye_button = None              # gibt es nur im klassischen Layout
        self.title("Multitool")
        self.configure(bg=PANEL)
        side_bg = CARD

        root = tk.Frame(self, bg=PANEL)
        root.pack(fill="both", expand=True)
        side = tk.Frame(root, bg=side_bg, width=220)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(root, bg=BORDER_SOFT, width=1).pack(side="left", fill="y")
        main = tk.Frame(root, bg=PANEL)
        main.pack(side="left", fill="both", expand=True)

        # Logo
        logo = tk.Frame(side, bg=side_bg)
        logo.pack(fill="x", padx=20, pady=(24, 20))
        ic = tk.Canvas(logo, width=30, height=30, bg=side_bg, highlightthickness=0, bd=0)
        round_rect(ic, 1, 1, 29, 29, 8, fill=TEXT, outline=TEXT)
        ic.create_arc(10, 6, 20, 17, start=0, extent=180, style="arc", outline=side_bg, width=2.6)
        ic.create_line(10, 11, 10, 15, fill=side_bg, width=2.6)
        ic.create_line(20, 11, 20, 15, fill=side_bg, width=2.6)
        round_rect(ic, 7, 14, 23, 25, 3, fill=side_bg, outline=side_bg)
        ic.create_oval(13.5, 17.5, 16.5, 20.5, fill=TEXT, outline="")
        ic.pack(side="left")
        tk.Label(logo, text="Multitool", bg=side_bg, fg=TEXT, font=(UI, 15, "bold")).pack(side="left", padx=(10, 0))

        self._mt_nav = {}
        for i, (section, items) in enumerate(MT_NAV):
            tk.Label(side, text=section, bg=side_bg, fg=MUTED, font=(UI, 7, "bold")).pack(
                anchor="w", padx=22, pady=(4 if i == 0 else 18, 4))
            for key, title in items:
                item = MtNavItem(side, title, lambda k=key: self.mt_show(k))
                item.pack(fill="x")
                self._mt_nav[key] = item
        bottom = tk.Frame(side, bg=side_bg)
        bottom.pack(side="bottom", fill="x", pady=(0, 12))
        MtNavItem(bottom, "Mini mode", self.enter_mini_mode).pack(fill="x")
        self._mt_nav["settings"] = MtNavItem(bottom, "Settings", lambda: self.mt_show("settings"))
        self._mt_nav["settings"].pack(fill="x")

        # Fußzeile (Lizenzanzeige links, Status rechts)
        self.footer = tk.Frame(main, bg=PANEL)
        self.footer.pack(side="bottom", fill="x", padx=28, pady=(4, 10))
        tk.Label(self.footer, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=(UI, 8)).pack(side="right")

        content = tk.Frame(main, bg=PANEL)
        content.pack(fill="both", expand=True, padx=(20, 14), pady=(14, 0))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.content = content

        # Werkzeug-Seiten (dieselben wie im klassischen Layout)
        self.tool_area = content
        self._tool_pages = {}
        self._tool_nav = {k: v for k, v in self._mt_nav.items() if k not in ("generator", "settings")}
        self._tool_builders = {
            "stats": self._build_stats_page, "email": self._build_email_tab, "totp": self._build_totp_page,
            "notes": self._build_notes_page, "encoder": self._build_encoder_page, "time": self._build_time_page,
            "units": self._build_units_page, "random": self._build_random_page,
            "shortcuts": self._build_shortcuts_page,
        }
        self.current_tool = None

        self.mt_gen_page = tk.Frame(content, bg=PANEL)
        self.mt_gen_page.grid(row=0, column=0, sticky="nsew")
        self._mt_build_generator(self.mt_gen_page)

        self.tab_settings = tk.Frame(content, bg=PANEL)
        self.tab_settings.grid(row=0, column=0, sticky="nsew")
        tk.Label(self.tab_settings, text="Settings", bg=PANEL, fg=TEXT, font=(UI, 20, "bold")).pack(
            anchor="w", padx=8, pady=(4, 0))
        self._build_settings_tab()

        self._ensure_tool("email")          # wird für die E-Mail-Statistik gebraucht
        self.mt_show("generator")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _mt_input(self, parent, placeholder, font=None, width=None):
        card = RoundCard(parent, fill=FIELD, border=BORDER, radius=9, pad=7)
        kw = {"width": width} if width else {}
        entry = PEntry(card.body, placeholder, font=font or (UI, 10), **kw)
        entry.config(highlightthickness=0, bd=1, bg=FIELD, insertbackground=TEXT)
        entry.pack(fill="x", ipady=3)
        entry.bind("<FocusIn>", lambda e: card.set_border(MUTED), add="+")
        entry.bind("<FocusOut>", lambda e: card.set_border(BORDER), add="+")
        return card, entry

    @staticmethod
    def _mt_link(parent, text, command, fg=None, bg=None):
        bg = bg or parent.cget("bg")
        label = tk.Label(parent, text=text, bg=bg, fg=fg or MUTED, font=(UI, 9), cursor="hand2")
        label.bind("<Button-1>", lambda e: command())
        label.bind("<Enter>", lambda e: label.config(fg=TEXT))
        label.bind("<Leave>", lambda e: label.config(fg=getattr(label, "base_fg", fg or MUTED)))
        label.base_fg = fg or MUTED
        return label

    def _mt_build_generator(self, page):
        head = tk.Frame(page, bg=PANEL)
        head.pack(fill="x", padx=8, pady=(4, 12))
        tk.Label(head, text="Generator", bg=PANEL, fg=TEXT, font=(UI, 20, "bold")).pack(anchor="w")
        self.mt_count_label = tk.Label(head, text="", bg=PANEL, fg=MUTED, font=(UI, 9))
        self.mt_count_label.pack(anchor="w")

        # Karte mit E-Mail / Benutzername / Passwort
        card = RoundCard(page, fill=CARD, border=BORDER, radius=14, pad=18)
        card.pack(fill="x", padx=8)
        body = card.body
        rows = (("EMAIL", self.email_var, None, self.email_var),
                ("USERNAME", self.username_var, lambda: self.regenerate_username(), self.username_var),
                ("PASSWORD", self.password_display_var, lambda: self.regenerate_password(), self.password_var))
        for i, (label, show_var, new_cmd, copy_var) in enumerate(rows):
            tk.Label(body, text=label, bg=CARD, fg=MUTED, font=(UI, 8)).pack(anchor="w", pady=(0 if i == 0 else 12, 2))
            row = tk.Frame(body, bg=CARD)
            row.pack(fill="x")
            RoundButton(row, "Copy", command=lambda v=copy_var: self._copy_var(v), height=30, padx=16,
                        fill=CARD2, border=CARD2, font=(UI, 9)).pack(side="right")
            if new_cmd:
                self._mt_link(row, "New", new_cmd, bg=CARD).pack(side="right", padx=(0, 22))
            tk.Label(row, textvariable=show_var, bg=CARD, fg=TEXT, font=(MONO, 12), anchor="w").pack(
                side="left", fill="x", expand=True)
        strength = tk.Frame(body, bg=CARD)
        strength.pack(fill="x", pady=(10, 0))
        self.mt_leak_label = self._mt_link(strength, "Leak check", self._mt_leak_check, bg=CARD)
        self.mt_leak_label.pack(side="right", padx=(18, 4))
        self.mt_strength_label = tk.Label(strength, text="—", bg=CARD, fg=GREEN, font=(UI, 9))
        self.mt_strength_label.pack(side="right", padx=(18, 0))
        self.mt_strength_bar = Bar(strength, color=GREEN, height=6)
        self.mt_strength_bar.pack(side="left", fill="x", expand=True)

        # Label / Tags / Modus
        meta = tk.Frame(page, bg=PANEL)
        meta.pack(fill="x", padx=8, pady=(14, 0))
        meta.grid_columnconfigure(0, weight=3)
        meta.grid_columnconfigure(1, weight=2)
        c, self.mt_label_entry = self._mt_input(meta, "Label (e.g. Steam)")
        c.grid(row=0, column=0, sticky="ew")
        c, self.mt_tags_entry = self._mt_input(meta, "Tags (e.g. games)")
        c.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        self.mt_mode_var = tk.StringVar(value=self.settings.get("password_mode", "random"))
        Segmented(meta, self.mt_mode_var, [("random", "Random"), ("passphrase", "Passphrase")],
                  command=self._mt_on_mode).grid(row=0, column=2)

        RoundButton(page, "Generate", command=lambda: self.generate(), height=48, radius=10, fill=ACCENT,
                    fg=ACCENT_DARK, hover=ACCENT_2, font=(UI, 11, "bold")).pack(fill="x", padx=8, pady=(26, 8))

        # Bulk / CSV / Optionen
        bulk = tk.Frame(page, bg=PANEL)
        bulk.pack(fill="x", padx=8)
        tk.Label(bulk, text="Bulk", bg=PANEL, fg=MUTED, font=(UI, 9)).pack(side="left")
        c, self.mt_bulk_entry = self._mt_input(bulk, "", font=(UI, 10), width=4)
        self.mt_bulk_entry.set("5")
        self.mt_bulk_entry.config(justify="center")
        c.pack(side="left", padx=(10, 8))
        RoundButton(bulk, "Generate batch", command=lambda: self._mt_generate_batch(), height=32, padx=16,
                    fill=CARD2, border=CARD2, font=(UI, 9)).pack(side="left")
        self._mt_link(bulk, "Copy all as CSV", self._mt_copy_csv).pack(side="right", padx=(16, 4))
        self.mt_opts_link = self._mt_link(bulk, "Options ▾", self._mt_toggle_options)
        self.mt_opts_link.pack(side="right")

        self._mt_build_options(page)

        # Verlauf
        self.mt_hist_head = tk.Frame(page, bg=PANEL)
        self.mt_hist_head.pack(fill="x", padx=8, pady=(22, 8))
        self.mt_hist_title = tk.Label(self.mt_hist_head, text="History", bg=PANEL, fg=TEXT, font=(UI, 12, "bold"))
        self.mt_hist_title.pack(side="left")
        self._mt_link(self.mt_hist_head, "Open JSON", self.open_json).pack(side="right", padx=(18, 4))
        self._mt_link(self.mt_hist_head, "Clear", self.clear_history).pack(side="right")

        filters = tk.Frame(page, bg=PANEL)
        filters.pack(fill="x", padx=8, pady=(0, 8))
        filters.grid_columnconfigure(0, weight=1)
        c, self.mt_search = self._mt_input(filters, "Search username or label…")
        c.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.mt_search.bind("<KeyRelease>", lambda e: self._mt_render_history())
        self.mt_sort_var = tk.StringVar(value=MT_SORTS[0])
        self.mt_tag_var = tk.StringVar(value=MT_ALL_TAGS)
        sort = self._combo(filters, self.mt_sort_var, MT_SORTS, width=15)
        sort.grid(row=0, column=1, padx=(0, 8))
        self.mt_tag_box = self._combo(filters, self.mt_tag_var, [MT_ALL_TAGS], width=12)
        self.mt_tag_box.grid(row=0, column=2)
        for box in (sort, self.mt_tag_box):
            box.bind("<<ComboboxSelected>>", lambda e: self._mt_render_history())

        self.mt_hist = ScrollFrame(page, bg=PANEL)
        self.mt_hist.pack(fill="both", expand=True, padx=(8, 0), pady=(0, 6))

    def _mt_build_options(self, page):
        self.mt_opts = RoundCard(page, fill=CARD, border=BORDER, radius=12, pad=14)
        body = self.mt_opts.body
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text="Length", bg=CARD, fg=TEXT, font=(UI, 9)).pack(side="left")
        self.length_label = tk.Label(top, text=str(self.length_value), bg=CARD, fg=TEXT, font=(MONO, 10, "bold"))
        self.length_label.pack(side="right")
        self.length_slider = Slider(body, PW_MIN, PW_MAX, self.length_value, command=self._on_length,
                                    on_release=self._save_settings_file)
        self.length_slider.pack(fill="x", pady=(4, 8))
        grid = tk.Frame(body, bg=CARD)
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1, 2), weight=1)
        opts = [("Uppercase A–Z", self.use_upper_var, self._on_option_change),
                ("Lowercase a–z", self.use_lower_var, self._on_option_change),
                ("Digits 0–9", self.use_digits_var, self._on_option_change),
                ("Start with a letter", self.first_letter_var, self._on_option_change),
                ("No ambiguous chars", self.no_ambiguous_var, self._on_option_change),
                ("No repeated chars", self.unique_chars_var, self._on_option_change),
                ("Save to history", self.save_on_generate_var, self._on_mode_toggle),
                ("Show password", self.show_password_var, self._mt_on_show_password)]
        for i, (text, var, cmd) in enumerate(opts):
            cell = tk.Frame(grid, bg=CARD)
            cell.grid(row=i // 3, column=i % 3, sticky="w", pady=4)
            box = CheckBox(cell, var, cmd)
            box.pack(side="left")
            label = tk.Label(cell, text=text, bg=CARD, fg=TEXT, font=(UI, 9), cursor="hand2")
            label.pack(side="left", padx=(8, 0))
            label.bind("<Button-1>", box.toggle)
        self._mt_opts_visible = False

    # ------------------------------------------------------------ Navigation
    def mt_show(self, key):
        if key in ("generator", "settings"):
            for frame in self._tool_pages.values():
                frame.grid_remove()
            for k, frame in (("generator", self.mt_gen_page), ("settings", self.tab_settings)):
                if k == key:
                    frame.grid()
                else:
                    frame.grid_remove()
            for k, item in self._mt_nav.items():
                item.set_active(k == key)
            self.current_tab = 0 if key == "generator" else 2
        else:
            self.mt_gen_page.grid_remove()
            self.tab_settings.grid_remove()
            self._mt_nav["generator"].set_active(False)
            self._mt_nav["settings"].set_active(False)
            self.current_tab = 1
            self.show_tool(key)
        self.mt_current = key

    def _mt_select_tab(self, index):
        self.mt_show({0: "generator", 2: "settings"}.get(index, self.current_tool or "email"))

    # ----------------------------------------------------------- Generator
    def _entry_meta(self):
        if getattr(self, "layout", "classic") != "multitool" or not hasattr(self, "mt_label_entry"):
            return {}
        meta = {}
        label = self.mt_label_entry.value().strip()[:60]
        tags = [t.strip() for t in self.mt_tags_entry.value().replace(";", ",").split(",") if t.strip()][:8]
        if label:
            meta["label"] = label
        if tags:
            meta["tags"] = tags
        return meta

    def _mt_on_mode(self):
        self.settings["password_mode"] = self.mt_mode_var.get()
        self._save_settings_file()
        self.regenerate_password(silent=True)

    def _mt_on_show_password(self):
        self.settings["show_password"] = self.show_password_var.get()
        self._save_settings_file()
        self._update_password_display()

    def _mt_toggle_options(self):
        self._mt_opts_visible = not self._mt_opts_visible
        if self._mt_opts_visible:
            self.mt_opts.pack(fill="x", padx=8, pady=(12, 0), before=self.mt_hist_head)
            self.mt_opts_link.config(text="Options ▴")
        else:
            self.mt_opts.pack_forget()
            self.mt_opts_link.config(text="Options ▾")

    def _mt_refresh_strength(self):
        pw = self.password_var.get()
        pw = "" if pw == "—" else pw
        result = analyze_password(pw)
        color = GREEN if result["level"] >= 4 else result["color"]
        self.mt_strength_bar.set(result["level"] / 5, color)
        self.mt_strength_label.config(text=MT_STRENGTH.get(result["level"], "—"), fg=color)
        if pw != getattr(self, "_mt_last_pw", None):
            self._mt_last_pw = pw
            self._mt_leak_token = getattr(self, "_mt_leak_token", 0) + 1
            self.mt_leak_label.base_fg = MUTED
            self.mt_leak_label.config(text="Leak check", fg=MUTED)

    def _mt_leak_check(self):
        pw = getattr(self, "_mt_last_pw", "")
        if not pw:
            return
        token = self._mt_leak_token
        self.mt_leak_label.config(text="Checking…", fg=MUTED)

        def worker():
            try:
                count = hibp_count(pw)
                text, color = (f"Leaked {count:,}×".replace(",", "."), DANGER) if count else ("Not leaked ✓", GREEN)
            except Exception:
                text, color = "No connection", ORANGE

            def apply():
                if token == self._mt_leak_token:
                    self.mt_leak_label.base_fg = color
                    self.mt_leak_label.config(text=text, fg=color)
            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _mt_generate_batch(self):
        try:
            count = int(self.mt_bulk_entry.value().strip() or "5")
        except ValueError:
            count = 5
        count = max(1, min(100, count))
        self.mt_bulk_entry.set(str(count))
        self.settings["email"] = self.email_var.get().strip() or DEFAULT_SETTINGS["email"]
        stamp = datetime.now().isoformat(timespec="seconds")
        meta = self._entry_meta()
        batch = [{"id": uuid.uuid4().hex, "email": self.settings["email"], "username": self._build_username(),
                  "password": self._build_password(), "generated_at": stamp, **meta} for _ in range(count)]
        self.credentials[0:0] = batch
        try:
            save_json_atomic(SAVE_FILE, self.credentials)
        except OSError as e:
            del self.credentials[:count]
            messagebox.showerror("Save failed", str(e), parent=self)
            return
        self.username_var.set(batch[0]["username"])
        self.password_var.set(batch[0]["password"])
        self._update_password_display()
        self.render_history()
        self._update_counts()
        self.set_status(f"{count} entries generated")

    def _mt_copy_csv(self):
        if not self.credentials:
            self.set_status("Nothing to copy")
            return
        out = io.StringIO()
        writer = _csv.writer(out, lineterminator="\n")
        writer.writerow(["email", "username", "password", "label", "tags", "favorite", "generated_at"])
        for e in self.credentials:
            writer.writerow([e.get("email", ""), e.get("username", ""), e.get("password", ""), e.get("label", ""),
                             ";".join(e.get("tags", []) or []), "yes" if e.get("favorite") else "",
                             e.get("generated_at", "")])
        self._copy(out.getvalue())
        self.set_status(f"{len(self.credentials)} entries copied as CSV")

    # -------------------------------------------------------------- Verlauf
    def _mt_filtered(self):
        query = self.mt_search.value().strip().lower()
        tag = self.mt_tag_var.get()
        items = []
        for e in self.credentials:
            if tag != MT_ALL_TAGS and tag not in (e.get("tags") or []):
                continue
            if query and query not in f"{e.get('username', '')} {e.get('label', '')}".lower():
                continue
            items.append(e)
        sort = self.mt_sort_var.get()
        if sort == "Oldest first":
            items.sort(key=lambda e: e.get("generated_at", ""))
        elif sort == "Username A–Z":
            items.sort(key=lambda e: e.get("username", "").lower())
        else:
            items.sort(key=lambda e: e.get("generated_at", ""), reverse=True)
            if sort == "Favorites first":
                items.sort(key=lambda e: not e.get("favorite"))
        return items

    def _mt_render_history(self):
        if not hasattr(self, "mt_hist"):
            return
        total = len(self.credentials)
        self.mt_count_label.config(text=f"{total} {'entry' if total == 1 else 'entries'} saved")
        self.mt_hist_title.config(text=f"History ({total})")
        tags = sorted({t for e in self.credentials for t in (e.get("tags") or [])}, key=str.lower)
        self.mt_tag_box.config(values=[MT_ALL_TAGS] + tags)
        if self.mt_tag_var.get() not in [MT_ALL_TAGS] + tags:
            self.mt_tag_var.set(MT_ALL_TAGS)

        inner = self.mt_hist.inner
        for child in inner.winfo_children():
            child.destroy()
        entries = self._mt_filtered()
        if not entries:
            text = "No matches." if total else "No entries yet — click “Generate”."
            tk.Label(inner, text=text, bg=PANEL, fg=MUTED, font=(UI, 9)).pack(pady=18)
            self.mt_hist.to_top()
            return
        for e in entries[:150]:
            card = RoundCard(inner, fill=CARD, border=BORDER_SOFT, radius=8, pad=10)
            card.pack(fill="x", pady=(0, 6), padx=(0, 6))
            b = card.body
            fav = bool(e.get("favorite"))
            star = tk.Label(b, text="★" if fav else "☆", bg=CARD, fg=YELLOW if fav else MUTED, font=(UI, 13),
                            cursor="hand2")
            star.pack(side="left", padx=(4, 12))
            star.bind("<Button-1>", lambda ev, x=e: self._mt_toggle_favorite(x))
            self._mt_link(b, "✕", lambda x=e: self.delete_entry(x.get("id")), bg=CARD).pack(side="right", padx=(10, 4))
            self._mt_link(b, "Edit", lambda x=e: self._mt_edit(x), bg=CARD).pack(side="right", padx=(12, 6))
            for text, value in (("Copy pass", e.get("password", "")), ("Copy user", e.get("username", ""))):
                RoundButton(b, text, command=lambda v=value: self._copy(v), height=28, padx=12, fill=CARD2,
                            border=CARD2, font=(UI, 9)).pack(side="right", padx=(6, 0))
            info = tk.Frame(b, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            title = e.get("username", "—")
            tk.Label(info, text=title, bg=CARD, fg=TEXT, font=(MONO, 10, "bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=e.get("password", ""), bg=CARD, fg=MUTED, font=(MONO, 9), anchor="w").pack(fill="x")
            extra = " · ".join(x for x in (e.get("label", ""), " ".join(f"#{t}" for t in e.get("tags") or [])) if x)
            if extra:
                tk.Label(info, text=extra, bg=CARD, fg=MUTED, font=(UI, 8), anchor="w").pack(fill="x")
        if len(entries) > 150:
            tk.Label(inner, text=f"… and {len(entries) - 150} more – use search.", bg=PANEL, fg=MUTED,
                     font=(UI, 9)).pack(pady=6)
        self.mt_hist.to_top()

    def _mt_toggle_favorite(self, entry):
        entry["favorite"] = not entry.get("favorite")
        self._persist_credentials()

    def _mt_edit(self, entry):
        dlg = tk.Toplevel(self)
        dlg.title("Edit entry")
        dlg.configure(bg=PANEL)
        dlg.transient(self)
        dlg.resizable(False, False)
        frame = tk.Frame(dlg, bg=PANEL)
        frame.pack(padx=22, pady=18)
        tk.Label(frame, text="Edit entry", bg=PANEL, fg=TEXT, font=(UI, 14, "bold")).pack(anchor="w", pady=(0, 8))
        fields = [("LABEL", "label", entry.get("label", "")),
                  ("TAGS (comma separated)", "tags", ", ".join(entry.get("tags") or [])),
                  ("USERNAME", "username", entry.get("username", "")),
                  ("PASSWORD", "password", entry.get("password", ""))]
        variables = {}
        for title, key, value in fields:
            tk.Label(frame, text=title, bg=PANEL, fg=MUTED, font=(UI, 8)).pack(anchor="w", pady=(8, 3))
            var = tk.StringVar(value=value)
            make_entry(frame, var, width=42).pack(fill="x", ipady=4)
            variables[key] = var

        def save():
            entry["label"] = variables["label"].get().strip()[:60]
            entry["tags"] = [t.strip() for t in variables["tags"].get().replace(";", ",").split(",") if t.strip()][:8]
            for key in ("username", "password"):
                value = variables[key].get().strip()
                if value:
                    entry[key] = value
            for key in ("label", "tags"):
                if not entry[key]:
                    entry.pop(key)
            dlg.destroy()
            if self._persist_credentials():
                self.set_status("Entry updated")

        buttons = tk.Frame(frame, bg=PANEL)
        buttons.pack(fill="x", pady=(18, 0))
        RoundButton(buttons, "Save", command=save, height=36, padx=22, fill=ACCENT, fg=ACCENT_DARK,
                    hover=ACCENT_2, font=(UI, 10, "bold")).pack(side="right")
        RoundButton(buttons, "Cancel", command=dlg.destroy, height=36, padx=18, fill=CARD2, border=CARD2).pack(
            side="right", padx=(0, 8))
        dlg.bind("<Return>", lambda e: save())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 3
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")
        dlg.grab_set()

    # ------------------------------------------------------------ Mini-Modus
    def enter_mini_mode(self):
        if getattr(self, "_mini", None) is not None:
            return
        mini = tk.Toplevel(self)
        self._mini = mini
        mini.title("Multitool · Mini")
        mini.configure(bg=PANEL)
        mini.resizable(False, False)
        try:
            mini.attributes("-topmost", True)
            mini.attributes("-alpha", 1 - self._transparency_value() / 100)
        except tk.TclError:
            pass
        mini.protocol("WM_DELETE_WINDOW", self.exit_mini_mode)
        body = tk.Frame(mini, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=14)
        head = tk.Frame(body, bg=PANEL)
        head.pack(fill="x", pady=(0, 6))
        tk.Label(head, text="Multitool", bg=PANEL, fg=TEXT, font=(UI, 12, "bold")).pack(side="left")
        self._mt_link(head, "⤢  Full window", self.exit_mini_mode, bg=PANEL).pack(side="right")
        for label, show_var, copy_var in (("EMAIL", self.email_var, self.email_var),
                                          ("USERNAME", self.username_var, self.username_var),
                                          ("PASSWORD", self.password_display_var, self.password_var)):
            tk.Label(body, text=label, bg=PANEL, fg=MUTED, font=(UI, 7)).pack(anchor="w", pady=(6, 0))
            row = tk.Frame(body, bg=PANEL)
            row.pack(fill="x")
            RoundButton(row, "Copy", command=lambda v=copy_var: self._copy_var(v), height=26, padx=12, fill=CARD2,
                        border=CARD2, font=(UI, 8)).pack(side="right")
            tk.Label(row, textvariable=show_var, bg=PANEL, fg=TEXT, font=(MONO, 10), anchor="w").pack(
                side="left", fill="x", expand=True)
        RoundButton(body, "Generate", command=lambda: self.generate(), height=38, radius=9, fill=ACCENT,
                    fg=ACCENT_DARK, hover=ACCENT_2, font=(UI, 10, "bold")).pack(fill="x", pady=(12, 0))
        mini.bind("<Control-g>", lambda e: self.generate())
        self.withdraw()
        mini.update_idletasks()
        sw = mini.winfo_screenwidth()
        mini.geometry(f"360x{mini.winfo_reqheight()}+{sw - 400}+60")
        self.set_status("Mini mode")

    def exit_mini_mode(self):
        mini = getattr(self, "_mini", None)
        if mini is None:
            return
        self._mini = None
        try:
            mini.destroy()
        except tk.TclError:
            pass
        try:
            self.deiconify()
            self.lift()
        except tk.TclError:
            pass



# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App(MultitoolMixin, ToolsMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG)
        self._fit_window()

        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.credentials = load_json(SAVE_FILE, [])
        self._normalize_credentials()
        self.layout = "multitool" if self.settings.get("layout") == "multitool" else "classic"

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.render_history())
        self.email_var = tk.StringVar(value=self.settings["email"])
        self.username_var = tk.StringVar(value="—")
        self.password_var = tk.StringVar(value="—")
        self.password_display_var = tk.StringVar(value="—")
        self.test_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self._status_job = None
        self._save_job = None
        self._hibp_token = 0

        s = self.settings
        self.show_password_var = tk.BooleanVar(value=s.get("show_password", True))
        self.save_on_generate_var = tk.BooleanVar(value=s.get("save_on_generate", True))
        s["use_symbols"] = False   # Steam-kompatibel: keine Sonderzeichen
        try:
            self.length_value = max(PW_MIN, min(PW_MAX, int(s.get("password_length", 16))))
        except (TypeError, ValueError):
            self.length_value = 16
        s["password_length"] = self.length_value
        self.use_upper_var = tk.BooleanVar(value=s["use_uppercase"])
        self.use_lower_var = tk.BooleanVar(value=s["use_lowercase"])
        self.use_digits_var = tk.BooleanVar(value=s["use_digits"])
        self.use_symbols_var = tk.BooleanVar(value=False)
        self.first_letter_var = tk.BooleanVar(value=s.get("first_letter", False))
        self.no_ambiguous_var = tk.BooleanVar(value=s.get("no_ambiguous", False))
        self.unique_chars_var = tk.BooleanVar(value=s.get("unique_chars", False))

        self._load_tools()
        self.backdrop = Backdrop(self)
        self._build_styles()
        self._build_ui()
        self._sync_backdrop(reload_image=True)
        self._bind_shortcuts()
        self.restart_requested = False
        self._apply_transparency()

        self.test_var.trace_add("write", lambda *_: self._refresh_analysis())
        self.preview_only(silent=True)
        self.render_history()
        self._update_counts()
        self._update_bg_source_label()
        self._reset_status()
        self.after(60, self.backdrop.refresh)
        if LOAD_WARNINGS:
            self.after(400, lambda: messagebox.showwarning("Hinweis", "\n\n".join(LOAD_WARNINGS), parent=self))

    # ----------------------------------------------------------- Grundlagen
    def _fit_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(980, sw - 40), min(840, sh - 80)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(880, 640)

    def _normalize_credentials(self):
        for entry in self.credentials:
            entry.setdefault("id", uuid.uuid4().hex)
            entry.setdefault("email", self.settings.get("email", DEFAULT_SETTINGS["email"]))

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        layout = [("Vertical.Scrollbar.trough", {
            "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})],
            "sticky": "ns",
        })]
        for name, trough in (("Panel", PANEL), ("Card", CARD)):
            sname = f"{name}.Slim.Vertical.TScrollbar"
            style.layout(sname, layout)
            style.configure(sname, troughcolor=trough, background="#30323a", bordercolor=trough,
                            lightcolor="#30323a", darkcolor="#30323a", gripcount=0, arrowsize=8)
            style.map(sname, background=[("active", "#3c3f48")])
        style.configure("Dark.TCombobox", fieldbackground=FIELD, background=CARD2, foreground=TEXT,
                        arrowcolor=TEXT, bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD,
                        selectbackground=FIELD, selectforeground=TEXT, padding=5)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)],
                  bordercolor=[("focus", ACCENT)])
        self.option_add("*TCombobox*Listbox.background", CARD2)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", SELECT_BG)
        self.option_add("*TCombobox*Listbox.selectForeground", ACCENT)
        self.option_add("*TCombobox*Listbox.font", (UI, 10))

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        if self.layout == "multitool":
            return self._mt_build_ui()
        self.shell = Shell(self, self.backdrop)
        self.shell.pack(fill="both", expand=True)
        panel = self.shell.panel

        # Kopfzeile
        header = tk.Frame(panel, bg=PANEL)
        header.pack(fill="x", padx=14, pady=(8, 8))
        title_box = tk.Frame(header, bg=PANEL)
        title_box.pack(side="left")
        tk.Label(title_box, text=APP_NAME, bg=PANEL, fg=TEXT, font=(UI, 15, "bold")).pack(anchor="w")
        tk.Label(
            title_box, text=f"Account & Credential Generator  ·  {CURRENT_VERSION}",
            bg=PANEL, fg=MUTED, font=(UI, 9),
        ).pack(anchor="w")

        nav = tk.Frame(header, bg=PANEL)
        nav.pack(side="right")
        self._tab_buttons = []
        for i, title in enumerate(["Generator", "Tools", "Einstellungen"]):
            btn = RoundButton(nav, title, command=lambda i=i: self.select_tab(i), height=34, padx=14)
            btn.pack(side="left", padx=(6, 0))
            self._tab_buttons.append(btn)

        tk.Frame(panel, bg=BORDER_SOFT, height=1).pack(fill="x")

        # Fußzeile
        footer = tk.Frame(panel, bg=PANEL)
        footer.pack(side="bottom", fill="x", padx=14, pady=(6, 6))
        self.footer = footer
        tk.Label(footer, text="made with ❤ by Lean", bg=PANEL, fg=MUTED, font=(UI, 9)).pack(side="left")
        tk.Label(footer, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=(UI, 9)).pack(side="right")
        tk.Frame(panel, bg=BORDER_SOFT, height=1).pack(side="bottom", fill="x")

        self.content = tk.Frame(panel, bg=PANEL)
        self.content.pack(fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self._tab_frames = []
        for _ in range(3):
            frame = tk.Frame(self.content, bg=PANEL)
            frame.grid(row=0, column=0, sticky="nsew")
            self._tab_frames.append(frame)
        self.tab_generator, self.tab_tools, self.tab_settings = self._tab_frames

        self._build_generator_tab()
        self._build_tools_tab()
        self._build_settings_tab()
        self.select_tab(0)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            self._flush_note()
        except Exception:
            pass
        for job in (self._status_job, getattr(self, "_save_job", None)):   # offene Timer abbrechen
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self.exit_mini_mode()
        self.destroy()

    def select_tab(self, index):
        if self.layout == "multitool":
            return self._mt_select_tab(index)
        self.current_tab = index
        for i, (frame, button) in enumerate(zip(self._tab_frames, self._tab_buttons)):
            if i == index:
                frame.grid()
                button.restyle(fill=SELECT_BG, fg=ACCENT, border=SELECT_BORDER)
            else:
                frame.grid_remove()
                button.restyle(fill=CARD, fg=MUTED, border=BORDER)
        if index == 1 and getattr(self, "current_tool", None):
            self.show_tool(self.current_tool)

    @staticmethod
    def _caption(parent, text, bg=CARD):
        return tk.Label(parent, text=text, bg=bg, fg=MUTED, font=(UI, 9))

    def _field_row(self, parent, label, widget_factory, buttons, last=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 0 if last else 8))
        tk.Label(row, text=label, bg=CARD, fg=MUTED, font=(UI, 8, "bold"), width=14, anchor="w").pack(side="left")
        for text, command in reversed(buttons):
            RoundButton(row, text, command=command, height=32, padx=10, font=(UI, 9)).pack(
                side="right", padx=(6, 0))
        widget = widget_factory(row)
        widget.pack(side="left", fill="x", expand=True, ipady=4)
        return widget

    # ------------------------------------------------------------ Generator
    def _build_generator_tab(self):
        tab = self.tab_generator
        tab.grid_columnconfigure(0, weight=1, uniform="cols")
        tab.grid_columnconfigure(1, weight=1, uniform="cols")
        tab.grid_rowconfigure(0, weight=1)

        left_scroll = ScrollFrame(tab, bg=PANEL)
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(14, 6), pady=10)
        self.left_scroll = left_scroll
        left = left_scroll.inner
        gap = 8

        # Account-Felder
        card = RoundCard(left, pad=12)
        card.pack(fill="x", pady=(0, gap))
        body = card.body
        self._field_row(
            body, "PASSWORT",
            lambda p: tk.Label(p, textvariable=self.password_display_var, bg=FIELD, fg=TEXT,
                               font=(MONO, 11, "bold"), anchor="w", padx=8,
                               highlightthickness=1, highlightbackground=BORDER),
            [("Kopieren", lambda: self._copy_var(self.password_var))],
        )
        self.eye_button = None
        self._field_row(
            body, "BENUTZERNAME",
            lambda p: tk.Label(p, textvariable=self.username_var, bg=FIELD, fg=TEXT, font=(MONO, 10),
                               anchor="w", padx=8, highlightthickness=1, highlightbackground=BORDER),
            [("Neu", self.regenerate_username), ("Kopieren", lambda: self._copy_var(self.username_var))],
        )

        def email_entry(p):
            entry = make_entry(p, self.email_var, font=(MONO, 10))
            entry.configure(bd=3)
            entry.bind("<FocusOut>", lambda e: self.save_email(silent=True))
            entry.bind("<Return>", lambda e: self.save_email())
            return entry

        self._field_row(body, "E-MAIL", email_entry,
                        [("Kopieren", lambda: self._copy_var(self.email_var))], last=True)

        # Länge, Stärke, Modus
        card = RoundCard(left, pad=12)
        card.pack(fill="x", pady=(0, gap))
        body = card.body
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        self._caption(top, "Länge").pack(side="left")
        self.length_label = tk.Label(top, text=str(self.length_value), bg=CARD, fg=TEXT,
                                     font=(MONO, 10, "bold"))
        self.length_label.pack(side="right")

        slider_row = tk.Frame(body, bg=CARD)
        slider_row.pack(fill="x", pady=(2, 6))
        RoundButton(slider_row, "Neu", command=self.regenerate_password, height=30, width=46,
                    font=(UI, 9, "bold")).pack(side="right", padx=(10, 0))
        self.length_slider = Slider(slider_row, PW_MIN, PW_MAX, self.length_value, command=self._on_length,
                                    on_release=self._save_settings_file)
        self.length_slider.pack(side="left", fill="x", expand=True)

        strength_row = tk.Frame(body, bg=CARD)
        strength_row.pack(fill="x")
        self._caption(strength_row, "Stärke").pack(side="left")
        self.left_rating_label = tk.Label(strength_row, text="—", bg=CARD, fg=TEXT, font=(MONO, 9, "bold"))
        self.left_rating_label.pack(side="right")
        self.left_segments = Segments(body)
        self.left_segments.pack(fill="x", pady=(6, 10))

        tk.Frame(body, bg=BORDER_SOFT, height=1).pack(fill="x", pady=(0, 10))
        mode = tk.Frame(body, bg=CARD)
        mode.pack(fill="x")
        Toggle(mode, self.save_on_generate_var, command=self._on_mode_toggle).pack(side="right")
        self._caption(mode, "Modus:").pack(side="left")
        self.mode_label = tk.Label(mode, text="", bg=CARD, fg=TEXT, font=(UI, 9, "bold"))
        self.mode_label.pack(side="left", padx=(6, 0))
        self._update_mode_label()

        # Optionen (Steam-kompatibel: nur Buchstaben und Zahlen)
        grid = tk.Frame(left, bg=PANEL)
        grid.pack(fill="x", pady=(0, gap - 6))
        grid.grid_columnconfigure(0, weight=1, uniform="opt")
        grid.grid_columnconfigure(1, weight=1, uniform="opt")
        options = [
            ("A-Z", self.use_upper_var), ("a-z", self.use_lower_var),
            ("0-9", self.use_digits_var), ("Beginnt mit Buchstabe", self.first_letter_var),
            ("Keine mehrdeutigen", self.no_ambiguous_var), ("Keine Wiederholungen", self.unique_chars_var),
        ]
        for i, (text, var) in enumerate(options):
            tile = CheckTile(grid, text, var, command=self._on_option_change)
            tile.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 4, 0 if i % 2 else 4),
                      pady=(0, 6))

        # Aktionen
        actions = tk.Frame(left, bg=PANEL)
        actions.pack(fill="x", pady=(2, gap))
        actions.grid_columnconfigure(0, weight=3)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)
        RoundButton(actions, "Generieren", command=self.generate, height=42, radius=11,
                    font=(UI, 11, "bold"), fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2)).grid(
            row=0, column=0, sticky="ew")
        RoundButton(actions, "Alles kopieren", command=self.copy_all, height=42, radius=11, fill=CARD,
                    border=BORDER).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.eye_button = RoundButton(actions, "", command=self._toggle_show_password, height=42, radius=11,
                                      fill=CARD, border=BORDER, width=96)
        self.eye_button.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        # Hinweis-Akkordeon
        acc = RoundCard(left, pad=11)
        acc.pack(fill="x")
        head = tk.Frame(acc.body, bg=CARD, cursor="hand2")
        head.pack(fill="x")
        head_label = tk.Label(head, text="⛨  Was ein Generator nicht schützen kann", bg=CARD, fg=TEXT,
                              font=(UI, 9, "bold"), cursor="hand2")
        head_label.pack(side="left")
        arrow = tk.Label(head, text="▾", bg=CARD, fg=MUTED, font=(UI, 9), cursor="hand2")
        arrow.pack(side="right")
        details = tk.Label(
            acc.body,
            text=(
                "•  Phishing: Ein starkes Passwort hilft nicht auf einer Fake-Seite.\n"
                "•  Malware/Keylogger auf dem PC können alles mitlesen.\n"
                "•  Für jeden Account ein eigenes Passwort nutzen.\n"
                "•  Steam Guard / 2FA überall aktivieren.\n"
                "•  credentials.json liegt unverschlüsselt neben der EXE – Datei schützen."
            ),
            bg=CARD, fg=MUTED, font=(UI, 9), justify="left", anchor="w",
        )

        def toggle_details(_=None):
            if details.winfo_ismapped():
                details.pack_forget()
                arrow.config(text="▾")
            else:
                details.pack(fill="x", pady=(8, 0))
                arrow.config(text="▴")

        for widget in (head, head_label, arrow):
            widget.bind("<Button-1>", toggle_details)

        # Rechte Spalte: Analyse
        right = RoundCard(tab, pad=10, fixed=True, radius=14)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 14), pady=10)
        self._build_analysis(right.body)

    def _build_analysis(self, parent):
        self.analysis_scroll = ScrollFrame(parent, bg=CARD, style="Card.Slim.Vertical.TScrollbar")
        self.analysis_scroll.pack(fill="both", expand=True)
        root = self.analysis_scroll.inner
        pad = dict(padx=(4, 4))
        gap = 8

        title = tk.Frame(root, bg=CARD)
        title.pack(fill="x", pady=(2, gap), **pad)
        dot = tk.Canvas(title, width=10, height=10, bg=CARD, highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=ACCENT, outline="")
        dot.pack(side="left", padx=(2, 8))
        tk.Label(title, text="STÄRKE-ANALYSE", bg=CARD, fg=TEXT, font=(UI, 10, "bold")).pack(side="left")

        # Eigenes Passwort testen
        test = RoundCard(root, fill=CARD2, pad=10, radius=10)
        test.pack(fill="x", pady=(0, gap), **pad)
        tk.Label(test.body, text="Eigenes Passwort testen:", bg=CARD2, fg=TEXT, font=(UI, 9)).pack(anchor="w")
        self.test_entry = make_entry(test.body, self.test_var, show="•")
        self.test_entry.configure(bd=3)
        self.test_entry.pack(fill="x", ipady=3, pady=(5, 6))
        btns = tk.Frame(test.body, bg=CARD2)
        btns.pack(fill="x")
        for i in range(3):
            btns.grid_columnconfigure(i, weight=1, uniform="tb")
        RoundButton(btns, "Analysieren", command=self._refresh_analysis, height=30, fill=ACCENT,
                    fg=ACCENT_DARK).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        RoundButton(btns, "Leeren", command=lambda: self.test_var.set(""), height=30, fill=FIELD,
                    border=BORDER).grid(row=0, column=1, sticky="ew", padx=4)
        RoundButton(btns, "Leak-Check", command=self.check_hibp, height=30, fill=FIELD,
                    border=BORDER).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Gesamtbewertung
        row = tk.Frame(root, bg=CARD)
        row.pack(fill="x", **pad)
        tk.Label(row, text="Gesamtbewertung", bg=CARD, fg=TEXT, font=(UI, 9)).pack(side="left")
        self.an_rating = tk.Label(row, text="—", bg=CARD, fg=TEXT, font=(MONO, 10, "bold"))
        self.an_rating.pack(side="right")
        self.an_bar = Bar(root, height=7)
        self.an_bar.pack(fill="x", pady=(3, gap), **pad)

        # Entropie + Leak-Check nebeneinander
        pair = tk.Frame(root, bg=CARD)
        pair.pack(fill="x", pady=(0, gap), **pad)
        pair.grid_columnconfigure(0, weight=1, uniform="pair")
        pair.grid_columnconfigure(1, weight=1, uniform="pair")

        def value_card(col, label, color):
            card = RoundCard(pair, fill=CARD2, pad=9, radius=10)
            card.grid(row=0, column=col, sticky="ew", padx=(0, 4) if col == 0 else (4, 0))
            tk.Label(card.body, text=label, bg=CARD2, fg=MUTED, font=(UI, 8)).pack(anchor="w")
            value = tk.Label(card.body, text="—", bg=CARD2, fg=color, font=(MONO, 11, "bold"))
            value.pack(anchor="w")
            return value

        self.an_entropy = value_card(0, "Entropie", GREEN)
        self.an_hibp = value_card(1, "Datenlecks (HIBP)", MUTED)
        self.an_hibp.config(text="nicht geprüft", font=(MONO, 10, "bold"))

        # Knackzeit
        crack = RoundCard(root, fill=CARD2, pad=10, radius=10)
        crack.pack(fill="x", pady=(0, gap), **pad)
        head = tk.Frame(crack.body, bg=CARD2)
        head.pack(fill="x")
        tk.Label(head, text="KNACKZEIT (SCHÄTZUNG)", bg=CARD2, fg=TEXT, font=(UI, 8, "bold")).pack(side="left")
        self.an_crack = tk.Label(crack.body, text="—", bg=FIELD, fg=ACCENT, font=(MONO, 13, "bold"))
        self.an_crack.pack(fill="x", pady=(5, 3), ipady=3)
        self.an_times = {}
        for key, label in (("online", "Online (100/s)"), ("fast", "Offline schnell (10 Mrd./s)"),
                           ("slow", "Offline langsam (bcrypt)")):
            line = tk.Frame(crack.body, bg=CARD2)
            line.pack(fill="x", pady=1)
            tk.Label(line, text=label, bg=CARD2, fg=MUTED, font=(UI, 8)).pack(side="left")
            value = tk.Label(line, text="—", bg=CARD2, fg=TEXT, font=(MONO, 9, "bold"))
            value.pack(side="right")
            self.an_times[key] = value

        # Kennzahlen
        tiles = tk.Frame(root, bg=CARD)
        tiles.pack(fill="x", pady=(0, gap), **pad)
        self.an_tiles = {}
        for i, (key, label) in enumerate((("length", "LÄNGE"), ("unique", "EINZIGARTIG"),
                                           ("complexity", "KOMPLEXITÄT"))):
            tiles.grid_columnconfigure(i, weight=1, uniform="tiles")
            tile = RoundCard(tiles, fill=CARD2, pad=7, radius=10)
            tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 3, 0 if i == 2 else 3))
            value = tk.Label(tile.body, text="—", bg=CARD2, fg=TEXT, font=(MONO, 12, "bold"))
            value.pack()
            tk.Label(tile.body, text=label, bg=CARD2, fg=MUTED, font=(UI, 7, "bold")).pack()
            self.an_tiles[key] = value

        # Verteilung
        dist = tk.Frame(root, bg=CARD)
        dist.pack(fill="x", pady=(0, gap), **pad)
        dist.grid_columnconfigure(1, weight=1)
        self.an_dist = {}
        for i, (key, label, color) in enumerate((("upper", "A-Z", ACCENT), ("lower", "a-z", GREEN),
                                                  ("digits", "0-9", YELLOW))):
            tk.Label(dist, text=label, bg=CARD, fg=TEXT, font=(UI, 8), width=5, anchor="w").grid(
                row=i, column=0, sticky="w", pady=1)
            bar = Bar(dist, color=color, height=6)
            bar.grid(row=i, column=1, sticky="ew", padx=6)
            count = tk.Label(dist, text="0", bg=CARD, fg=TEXT, font=(MONO, 8, "bold"), width=3, anchor="e")
            count.grid(row=i, column=2, sticky="e")
            self.an_dist[key] = (bar, count)

        # Checkliste
        chips = tk.Frame(root, bg=CARD)
        chips.pack(fill="x", **pad)
        chips.grid_columnconfigure(0, weight=1, uniform="chips")
        chips.grid_columnconfigure(1, weight=1, uniform="chips")
        self.an_chips = []
        for i in range(6):
            chip = RoundCard(chips, fill=CARD2, pad=6, radius=8)
            chip.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 3, 0 if i % 2 else 3),
                      pady=(0, 5))
            icon = tk.Label(chip.body, text="", bg=CARD2, font=(UI, 9, "bold"), width=2)
            icon.pack(side="left")
            text = tk.Label(chip.body, text="", bg=CARD2, fg=TEXT, font=(UI, 8))
            text.pack(side="left")
            self.an_chips.append((icon, text))

    def _refresh_analysis(self):
        if self.layout == "multitool":
            return self._mt_refresh_strength()
        custom = self.test_var.get()
        pw = custom if custom else self.password_var.get()
        if pw == "—":
            pw = ""
        if pw != getattr(self, "_analysed_pw", None):
            self._hibp_token += 1
            self.an_hibp.config(text="nicht geprüft", fg=MUTED)
        self._analysed_pw = pw
        result = analyze_password(pw)

        self.an_rating.config(text=result["label"], fg=result["color"] if result["level"] else TEXT)
        self.an_bar.set(result["level"] / 5, result["color"])
        self.an_entropy.config(text=f"{round(result['bits'])} bits" if pw else "—")
        self.an_crack.config(text=result["times"]["fast"])
        for key, label in self.an_times.items():
            label.config(text=result["times"][key])
        self.an_tiles["length"].config(text=str(result["length"]) if pw else "—")
        self.an_tiles["unique"].config(text=str(result["unique"]) if pw else "—")
        self.an_tiles["complexity"].config(text=f"{result['complexity']}%" if pw else "—")
        n = max(1, result["length"])
        for key, (bar, count) in self.an_dist.items():
            bar.set(result[key] / n)
            count.config(text=str(result[key]))
        for (icon, text), (label, ok) in zip(self.an_chips, result["checks"]):
            icon.config(text="✓" if ok else "✕", fg=GREEN if ok else DANGER)
            text.config(text=label)

        # Stärke-Anzeige links bezieht sich immer auf das generierte Passwort
        gen = analyze_password("" if self.password_var.get() == "—" else self.password_var.get())
        self.left_rating_label.config(text=gen["label"])
        self.left_segments.set(gen["level"], ACCENT if gen["level"] >= 4 else gen["color"])

    def check_hibp(self):
        pw = self._analysed_pw
        if not pw:
            self.set_status("Kein Passwort zum Prüfen")
            return
        self._hibp_token += 1
        token = self._hibp_token
        self.an_hibp.config(text="prüfe…", fg=MUTED)

        def worker():
            try:
                count = hibp_count(pw)
                result = (f"{count:,}× geleakt!".replace(",", ".") if count else "nicht gefunden",
                          DANGER if count else GREEN)
            except Exception:
                result = ("keine Verbindung", ORANGE)

            def apply():
                if token == self._hibp_token:
                    self.an_hibp.config(text=result[0], fg=result[1])
            self.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------- Verlauf
    def _build_history_tab(self):
        tab = self.tab_history
        toolbar = tk.Frame(tab, bg=PANEL)
        toolbar.pack(fill="x", padx=14, pady=(12, 10))
        actions = tk.Frame(toolbar, bg=PANEL)
        actions.pack(side="right", padx=(8, 0))
        for text, cmd, fg in (("Export", self.export_credentials, TEXT), ("Import", self.import_credentials, TEXT),
                              ("JSON öffnen", self.open_json, TEXT), ("Alles löschen", self.clear_history, DANGER)):
            RoundButton(actions, text, command=cmd, height=36, fill=CARD, border=BORDER, fg=fg,
                        font=(UI, 9)).pack(side="left", padx=(6, 0))
        search = make_entry(toolbar, self._search_var, font=(UI, 10))
        search.pack(side="left", fill="x", expand=True, ipady=7)
        self._search_placeholder(search)

        self.history_scroll = ScrollFrame(tab, bg=PANEL)
        self.history_scroll.pack(fill="both", expand=True, padx=(14, 10), pady=(0, 10))

    def _search_placeholder(self, entry):
        hint = "Suchen …"

        def show(_=None):
            if not self._search_var.get():
                entry.config(fg=MUTED)
                entry.insert(0, hint)
                self._placeholder_active = True

        def hide(_=None):
            if getattr(self, "_placeholder_active", False):
                self._placeholder_active = False
                entry.delete(0, "end")
                entry.config(fg=TEXT)

        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", show)
        self._placeholder_active = False
        show()

    def _search_query(self):
        if getattr(self, "_placeholder_active", False):
            return ""
        return self._search_var.get().strip().lower()

    def _filtered_credentials(self):
        query = self._search_query()
        if not query:
            return self.credentials
        return [
            e for e in self.credentials
            if query in " ".join(str(e.get(k, "")) for k in ("username", "password", "email",
                                                         "generated_at")).lower()
        ]

    def render_history(self):
        if getattr(self, "layout", "classic") == "multitool":
            return self._mt_render_history()
        if not hasattr(self, "history_scroll"):
            return
        inner = self.history_scroll.inner
        for child in inner.winfo_children():
            child.destroy()
        entries = self._filtered_credentials()

        if not entries:
            text = "Keine Treffer." if self._search_query() else "Noch keine Einträge — auf „Generieren“ klicken."
            card = RoundCard(inner, pad=18)
            card.pack(fill="x")
            tk.Label(card.body, text=text, bg=CARD, fg=MUTED, font=(UI, 10)).pack()
            self.history_scroll.to_top()
            return

        limit = 150
        for entry in entries[:limit]:
            card = RoundCard(inner, pad=12, radius=10)
            card.pack(fill="x", pady=(0, 8))
            body = card.body
            actions = tk.Frame(body, bg=CARD)
            actions.pack(side="right")
            for text, cmd, fg in (
                ("Alles", lambda e=entry: self._copy_entry(e), TEXT),
                ("User", lambda u=entry.get("username", ""): self._copy(u), TEXT),
                ("Pass", lambda p=entry.get("password", ""): self._copy(p), TEXT),
                ("Löschen", lambda i=entry.get("id"): self.delete_entry(i), DANGER),
            ):
                RoundButton(actions, text, command=cmd, height=30, padx=10, fill=CARD2, fg=fg,
                            font=(UI, 8, "bold")).pack(side="left", padx=(6, 0))
            info = tk.Frame(body, bg=CARD)
            info.pack(side="left", fill="x", expand=True)
            tk.Label(info, text=entry.get("username", "—"), bg=CARD, fg=TEXT, font=(MONO, 11, "bold"),
                     anchor="w").pack(fill="x")
            tk.Label(info, text=entry.get("password", "—"), bg=CARD, fg=ACCENT, font=(MONO, 10),
                     anchor="w").pack(fill="x")
            tk.Label(info, text=f"{entry.get('email', '—')}  ·  {format_datetime(entry.get('generated_at', ''))}",
                     bg=CARD, fg=MUTED, font=(UI, 8), anchor="w").pack(fill="x", pady=(2, 0))
        if len(entries) > limit:
            tk.Label(inner, text=f"… und {len(entries) - limit} weitere – Suche benutzen.", bg=PANEL, fg=MUTED,
                     font=(UI, 9)).pack(pady=6)
        self.history_scroll.to_top()

    # --------------------------------------------------------------- E-Mail
    def _build_email_tab(self):
        tab = self.tab_email
        wrap = tk.Frame(tab, bg=PANEL)
        wrap.pack(fill="both", expand=True, padx=14, pady=12)

        hero = RoundCard(wrap, pad=22, radius=14)
        hero.pack(fill="x", pady=(0, 12))
        tk.Label(hero.body, text="ProtonMail", bg=CARD, fg=TEXT, font=(UI, 20, "bold")).pack(anchor="w")
        tk.Label(hero.body, text="Deine feste E-Mail-Adresse für alle generierten Accounts.", bg=CARD, fg=MUTED,
                 font=(UI, 10)).pack(anchor="w", pady=(4, 16))
        tk.Label(hero.body, textvariable=self.email_var, bg=CARD, fg=ACCENT, font=(MONO, 16, "bold"),
                 anchor="w").pack(anchor="w", fill="x")
        self.email_count_label = tk.Label(hero.body, text="", bg=CARD, fg=MUTED, font=(UI, 9))
        self.email_count_label.pack(anchor="w", pady=(10, 0))

        edit = RoundCard(wrap, pad=16)
        edit.pack(fill="x", pady=(0, 12))
        tk.Label(edit.body, text="E-MAIL BEARBEITEN", bg=CARD, fg=MUTED, font=(UI, 8, "bold")).pack(anchor="w")
        make_entry(edit.body, self.email_var, font=(MONO, 12)).pack(fill="x", ipady=8, pady=(6, 12))
        row = tk.Frame(edit.body, bg=CARD)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)
        RoundButton(row, "Speichern", command=self.save_email, height=40, fg=ACCENT_DARK,
                    gradient=(ACCENT, ACCENT_2)).grid(row=0, column=0, sticky="ew")
        RoundButton(row, "Kopieren", command=lambda: self._copy_var(self.email_var), height=40, fill=CARD2,
                    border=BORDER).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        RoundButton(row, "ProtonMail öffnen", command=self.open_protonmail, height=40, fill=CARD2,
                    border=BORDER).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        info = RoundCard(wrap, pad=16)
        info.pack(fill="x")
        tk.Label(info.body, text=(
            "Diese Adresse wird bei jedem „Generieren“ automatisch mitgespeichert.\n"
            "Änderungen gelten für alle neuen Einträge im Verlauf.\n"
            "Tipp: Strg+E kopiert die E-Mail direkt."),
            bg=CARD, fg=MUTED, font=(UI, 9), justify="left").pack(anchor="w")

    # -------------------------------------------------------- Einstellungen
    def _settings_card(self, parent, title):
        card = RoundCard(parent, pad=16)
        card.pack(fill="x", pady=(0, 12))
        tk.Label(card.body, text=title, bg=CARD, fg=TEXT, font=(UI, 12, "bold")).pack(anchor="w", pady=(0, 10))
        return card.body

    def _settings_check(self, parent, text, var, command=None):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=4)
        box = CheckBox(row, var, command)
        box.pack(side="left")
        label = tk.Label(row, text=text, bg=CARD, fg=TEXT, font=(UI, 10), cursor="hand2")
        label.pack(side="left", padx=(10, 0))
        label.bind("<Button-1>", box.toggle)

    def _build_settings_tab(self):
        self.settings_scroll = ScrollFrame(self.tab_settings, bg=PANEL)
        self.settings_scroll.pack(fill="both", expand=True, padx=(14, 10), pady=12)
        root = self.settings_scroll.inner

        body = self._settings_card(root, "Design & Fenster")
        self._caption(body, "Oberfläche").pack(anchor="w", pady=(0, 6))
        self.layout_var = tk.StringVar(value=self.layout)
        Segmented(body, self.layout_var, [("classic", "Klassisch"), ("multitool", "Multitool (Seitenleiste)")],
                  command=self._on_layout_change).pack(anchor="w", pady=(0, 14))
        self._caption(body, "Design (angelehnt an Qt Fluent, Dear ImGui, NiceGUI, Flet/Material 3, Textual)").pack(
            anchor="w", pady=(0, 6))
        self.theme_var = tk.StringVar(value=CURRENT_THEME)
        Segmented(body, self.theme_var, [(k, t["label"]) for k, t in THEMES.items()],
                  command=self._on_theme_change).pack(anchor="w")
        swatches = tk.Frame(body, bg=CARD)
        swatches.pack(anchor="w", pady=(8, 14))
        for key in THEMES:
            t = THEMES[key]
            sw = tk.Canvas(swatches, width=58, height=16, bg=CARD, highlightthickness=0, bd=0)
            round_rect(sw, 1, 1, 57, 15, 6, fill=t["CARD"], outline=t["BORDER"])
            sw.create_oval(6, 4, 14, 12, fill=t["ACCENT"], outline="")
            sw.create_rectangle(19, 6, 50, 10, fill=t["MUTED"], outline="")
            sw.pack(side="left", padx=(0, 8))
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        self._caption(top, "Fenster-Transparenz").pack(side="left")
        self.transparency_label = tk.Label(top, text=f"{self._transparency_value()} %", bg=CARD, fg=TEXT,
                                           font=(MONO, 10, "bold"))
        self.transparency_label.pack(side="right")
        self.transparency_slider = Slider(body, 0, 100, self._transparency_value(), command=self._on_transparency,
                                          on_release=self._save_settings_file)
        self.transparency_slider.pack(fill="x", pady=(6, 4))
        tk.Label(body, text="0 % = undurchsichtig · 100 % = komplett durchsichtig  ·  Strg+0 setzt auf 0 % zurück",
                 bg=CARD, fg=MUTED, font=(UI, 8)).pack(anchor="w")

        body = self._settings_card(root, "Benutzername")
        self._caption(body, "Trennzeichen").pack(anchor="w", pady=(0, 6))
        self.separator_var = tk.StringVar(value=self.settings["username_separator"])
        Segmented(body, self.separator_var, [("_", "Unterstrich  _"), (".", "Punkt  ."), ("", "Keins")]).pack(
            anchor="w", pady=(0, 12))
        rng = tk.Frame(body, bg=CARD)
        rng.pack(anchor="w")
        self.num_min_var = tk.StringVar(value=str(self.settings["username_number_min"]))
        self.num_max_var = tk.StringVar(value=str(self.settings["username_number_max"]))
        self._caption(rng, "Zahl von").pack(side="left")
        make_entry(rng, self.num_min_var, width=8).pack(side="left", padx=8, ipady=4)
        self._caption(rng, "bis").pack(side="left")
        make_entry(rng, self.num_max_var, width=8).pack(side="left", padx=8, ipady=4)

        body = self._settings_card(root, "Verhalten")
        self.auto_copy_var = tk.BooleanVar(value=self.settings.get("auto_copy", False))
        self.confirm_delete_var = tk.BooleanVar(value=self.settings.get("confirm_delete", True))
        self._settings_check(body, "Nach Generieren automatisch kopieren", self.auto_copy_var)
        self._settings_check(body, "Löschen bestätigen", self.confirm_delete_var)
        self._caption(body, "Auto-Kopie kopiert:").pack(anchor="w", pady=(10, 6))
        self.auto_copy_field_var = tk.StringVar(value=self.settings.get("auto_copy_field", "all"))
        Segmented(body, self.auto_copy_field_var, [("all", "Alles"), ("username", "Benutzername"),
                                                   ("password", "Passwort"), ("email", "E-Mail")]).pack(anchor="w")

        body = self._settings_card(root, "Hintergrund")
        self.bg_enabled_var = tk.BooleanVar(value=self.settings.get("bg_enabled", True))
        row = tk.Frame(body, bg=CARD)
        row.pack(fill="x")
        tk.Label(row, text="Hintergrundbild um das Fenster anzeigen", bg=CARD, fg=TEXT, font=(UI, 10)).pack(side="left")
        Toggle(row, self.bg_enabled_var, command=self._on_bg_toggle).pack(side="right")
        self.bg_source_label = tk.Label(body, text="", bg=CARD, fg=MUTED, font=(UI, 9), anchor="w")
        self.bg_source_label.pack(fill="x", pady=(4, 10))
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        self._caption(top, "Helligkeit").pack(side="left")
        self.bg_brightness_label = tk.Label(top, text=f"{self._bg_brightness_value()}%", bg=CARD, fg=TEXT,
                                            font=(MONO, 10, "bold"))
        self.bg_brightness_label.pack(side="right")
        self.bg_brightness_slider = Slider(body, 10, 100, self._bg_brightness_value(),
                                           command=self._on_bg_brightness, on_release=self._save_settings_file)
        self.bg_brightness_slider.pack(fill="x", pady=(6, 12))
        row = tk.Frame(body, bg=CARD)
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        RoundButton(row, "Eigenes Bild auswählen…", command=self.choose_background, height=38,
                    fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2)).grid(row=0, column=0, sticky="ew")
        RoundButton(row, "Standardbild", command=self.reset_background, height=38, fill=CARD2,
                    border=BORDER).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        if not PIL_OK:
            tk.Label(body, text="Pillow ist nicht installiert – Hintergrundbilder sind deaktiviert.",
                     bg=CARD, fg=ORANGE, font=(UI, 9)).pack(anchor="w", pady=(10, 0))

        body = self._settings_card(root, "Speicherort")
        tk.Label(body, text=f"Credentials:\n{SAVE_FILE}\n\nEinstellungen:\n{SETTINGS_FILE}", bg=CARD, fg=MUTED,
                 font=(MONO, 9), justify="left").pack(anchor="w")

        row = tk.Frame(root, bg=PANEL)
        row.pack(fill="x", pady=(0, 8))
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        RoundButton(row, "Einstellungen speichern", command=self._save_settings_from_ui, height=44, radius=12,
                    font=(UI, 10, "bold"), fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2)).grid(
            row=0, column=0, sticky="ew")
        RoundButton(row, "Zurücksetzen", command=self.reset_settings, height=44, radius=12, fill=CARD,
                    border=BORDER).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    # ------------------------------------------------------ Shortcuts/Scroll
    def _bind_shortcuts(self):
        for key in ("<Control-g>", "<Control-G>"):
            self.bind(key, lambda e: self.generate() if self.current_tab == 0 else None)
        for key in ("<Control-c>", "<Control-C>"):
            self.bind(key, self._ctrl_c)
        for key in ("<Control-e>", "<Control-E>"):
            self.bind(key, lambda e: self._copy_var(self.email_var))
        self.bind("<Control-Key-0>", lambda e: self._set_transparency(0))
        self.bind("<Control-KP_0>", lambda e: self._set_transparency(0))
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", lambda e: self._scroll_at(e, -1))
        self.bind_all("<Button-5>", lambda e: self._scroll_at(e, 1))

    def _ctrl_c(self, _event):
        if isinstance(self.focus_get(), (tk.Entry, tk.Text)):
            return None   # normales Kopieren im Eingabefeld
        self.copy_all()
        return "break"

    def _scroll_at(self, event, units):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, ScrollFrame):
                widget.scroll(units)
                return
            widget = widget.master

    def _on_mousewheel(self, event):
        units = int(-event.delta / 120) or (-1 if event.delta > 0 else 1)
        self._scroll_at(event, units)

    # --------------------------------------------------------------- Status
    def _copy_var(self, var):
        text = var.get()
        if text and text != "—":
            self._copy(text)

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("In Zwischenablage kopiert")

    def _reset_status(self):
        self._status_job = None
        self.status_var.set(f"{len(self.credentials)} Einträge gespeichert  ·  Steam-kompatibel  ·  secrets + HIBP")

    def set_status(self, text):
        self.status_var.set(text)
        if self._status_job:
            self.after_cancel(self._status_job)
        self._status_job = self.after(1800, self._reset_status)

    def _update_counts(self):
        self._update_email_stats()
        if hasattr(self, "_tool_pages"):
            self.refresh_stats()
        if self._status_job is None:
            self._reset_status()

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
        self.bg_source_label.config(text="Aktuell: eigenes Bild" if custom else "Aktuell: Standardbild")

    def _on_bg_toggle(self):
        self.settings["bg_enabled"] = self.bg_enabled_var.get()
        self._save_settings_file()
        self._sync_backdrop()

    def _on_bg_brightness(self, value):
        self.bg_brightness_label.config(text=f"{value}%")
        self.settings["bg_brightness"] = value
        self.backdrop.brightness = value / 100
        self.backdrop.schedule()

    def choose_background(self):
        if not PIL_OK:
            messagebox.showerror("Pillow fehlt", "Für Hintergrundbilder wird Pillow benötigt.\n\npip install pillow")
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

    # ------------------------------------------------------- Generator-Logik
    def _update_mode_label(self):
        if not hasattr(self, "mode_label"):
            return
        self.mode_label.config(
            text="Im Verlauf speichern" if self.save_on_generate_var.get() else "Nur Vorschau (nicht speichern)")

    def _on_mode_toggle(self):
        self.settings["save_on_generate"] = self.save_on_generate_var.get()
        self._update_mode_label()
        self._save_settings_file()

    def _on_length(self, value):
        self.length_value = value
        self.length_label.config(text=str(value))
        self.settings["password_length"] = value
        self.regenerate_password(silent=True)

    def _on_option_change(self):
        s = self.settings
        s["use_uppercase"] = self.use_upper_var.get()
        s["use_lowercase"] = self.use_lower_var.get()
        s["use_digits"] = self.use_digits_var.get()
        s["use_symbols"] = False
        s["first_letter"] = self.first_letter_var.get()
        s["no_ambiguous"] = self.no_ambiguous_var.get()
        s["unique_chars"] = self.unique_chars_var.get()
        self._save_settings_file()
        self.regenerate_password(silent=True)

    def _toggle_show_password(self):
        self.show_password_var.set(not self.show_password_var.get())
        self.settings["show_password"] = self.show_password_var.get()
        self._save_settings_file()
        self._update_password_display()

    def _update_password_display(self):
        password = self.password_var.get()
        if self.show_password_var.get() or password == "—":
            self.password_display_var.set(password)
        else:
            self.password_display_var.set("•" * len(password))
        if self.eye_button is not None:
            self.eye_button.restyle(text="Verbergen" if self.show_password_var.get() else "Anzeigen")
        self._refresh_analysis()

    def _build_passphrase(self):
        """4 Wörter + 2 Ziffern, ohne Sonderzeichen (Steam-kompatibel), z. B. GlacierRavenPixelComet47."""
        rng = secrets.SystemRandom()
        words = [rng.choice(PASSPHRASE_WORDS).capitalize() for _ in range(4)]
        return "".join(words) + f"{secrets.randbelow(100):02d}"

    def _build_password(self):
        s = self.settings
        if s.get("password_mode") == "passphrase":
            return self._build_passphrase()
        classes = []
        if s.get("use_uppercase", True):
            classes.append(string.ascii_uppercase)
        if s.get("use_lowercase", True):
            classes.append(string.ascii_lowercase)
        if s.get("use_digits", True):
            classes.append(string.digits)
        if not classes:
            classes = [string.ascii_letters, string.digits]
        if s.get("no_ambiguous"):
            classes = ["".join(c for c in cls if c not in AMBIGUOUS) for cls in classes]
        pool = "".join(dict.fromkeys("".join(classes)))
        letters = [c for c in pool if c.isalpha()]

        length = max(PW_MIN, min(PW_MAX, int(s.get("password_length", 16))))
        unique = bool(s.get("unique_chars"))
        if unique:
            length = min(length, len(pool))
        rng = secrets.SystemRandom()

        chars = []
        for _ in range(500):
            if unique:
                chars = rng.sample(pool, length)
            else:
                chars = [rng.choice(cls) for cls in classes][:length]
                chars += [rng.choice(pool) for _ in range(length - len(chars))]
                rng.shuffle(chars)
            if s.get("first_letter") and letters and not chars[0].isalpha():
                idx = next((i for i, c in enumerate(chars) if c.isalpha()), None)
                if idx is None:
                    continue
                chars[0], chars[idx] = chars[idx], chars[0]
            if len(classes) > length or all(any(c in cls for c in chars) for cls in classes):
                break
        return "".join(chars)

    def _build_username(self):
        sep = self.settings.get("username_separator", "_")
        try:
            num_min = int(self.settings.get("username_number_min", 10))
            num_max = int(self.settings.get("username_number_max", 9999))
        except (TypeError, ValueError):
            num_min, num_max = 10, 9999
        if num_min > num_max:
            num_min, num_max = num_max, num_min
        num = num_min + secrets.randbelow(num_max - num_min + 1)
        return f"{secrets.choice(ADJECTIVES)}{sep}{secrets.choice(NOUNS)}{num}"

    def regenerate_username(self):
        self.username_var.set(self._build_username())
        self.set_status("Neuer Benutzername")

    def regenerate_password(self, silent=False):
        self.password_var.set(self._build_password())
        self._update_password_display()
        if not silent:
            self.set_status("Neues Passwort")

    def preview_only(self, silent=False):
        self.username_var.set(self._build_username())
        self.password_var.set(self._build_password())
        self._update_password_display()
        if not silent:
            self.set_status("Vorschau erstellt (nicht gespeichert)")

    def generate(self):
        self.settings["email"] = self.email_var.get().strip() or DEFAULT_SETTINGS["email"]
        username = self._build_username()
        password = self._build_password()
        self.username_var.set(username)
        self.password_var.set(password)
        self._update_password_display()

        if self.save_on_generate_var.get():
            entry = {
                "id": uuid.uuid4().hex,
                "email": self.settings["email"],
                "username": username,
                "password": password,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                **self._entry_meta(),
            }
            self.credentials.insert(0, entry)
            try:
                save_json_atomic(SAVE_FILE, self.credentials)
            except OSError as e:
                messagebox.showerror("Speichern fehlgeschlagen", f"credentials.json konnte nicht gespeichert werden:\n{e}")
                self.credentials.pop(0)
                return
            self.render_history()
            self._update_counts()
            self.set_status("Credentials generiert & gespeichert")
        else:
            self.set_status("Vorschau erstellt (nicht gespeichert)")

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
        username, password = self.username_var.get(), self.password_var.get()
        if username == "—" or password == "—":
            if not silent:
                messagebox.showinfo("Info", "Noch nichts generiert.")
            return
        self._copy(f"E-Mail: {self.email_var.get()}\nBenutzername: {username}\nPasswort: {password}")
        if not silent:
            self.set_status("Alle Felder kopiert")

    # ---------------------------------------------------------- Credentials
    def _update_email_stats(self):
        email = self.email_var.get().strip()
        if not email:
            self.email_count_label.config(text="Keine E-Mail hinterlegt")
            return
        count = sum(1 for e in self.credentials if e.get("email", "").lower() == email.lower())
        domain = email.split("@")[-1] if "@" in email else "—"
        self.email_count_label.config(text=f"Domain: {domain}  ·  {count} Einträge im Verlauf mit dieser Adresse")

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

    def _copy_entry(self, entry):
        self._copy(
            f"E-Mail: {entry.get('email', '—')}\n"
            f"Benutzername: {entry.get('username', '—')}\n"
            f"Passwort: {entry.get('password', '—')}"
        )

    def _persist_credentials(self):
        try:
            save_json_atomic(SAVE_FILE, self.credentials)
        except OSError as e:
            messagebox.showerror("Speichern fehlgeschlagen", str(e))
            return False
        self.render_history()
        self._update_counts()
        return True

    def delete_entry(self, entry_id):
        if self.settings.get("confirm_delete", True):
            if not messagebox.askyesno("Eintrag löschen", "Diesen Eintrag wirklich löschen?"):
                return
        self.credentials = [e for e in self.credentials if e.get("id") != entry_id]
        if self._persist_credentials():
            self.set_status("Eintrag gelöscht")

    def clear_history(self):
        if not self.credentials:
            return
        if self.settings.get("confirm_delete", True):
            if not messagebox.askyesno("Verlauf leeren", "Alle gespeicherten Credentials löschen?"):
                return
        self.credentials = []
        if self._persist_credentials():
            self.set_status("Verlauf geleert")

    def export_credentials(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")],
                                            initialfile="credentials_export.json")
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
        imported = load_json(path, [])
        if not isinstance(imported, list):
            messagebox.showerror("Import fehlgeschlagen", "Die Datei enthält keine Liste.")
            return
        added = 0
        existing_ids = {e.get("id") for e in self.credentials}
        for entry in imported:
            if not isinstance(entry, dict):
                continue
            if "id" not in entry or entry["id"] in existing_ids:
                entry = dict(entry, id=uuid.uuid4().hex)
            existing_ids.add(entry["id"])
            self.credentials.append(entry)
            added += 1
        if self._persist_credentials():
            self.set_status(f"{added} Einträge importiert")

    def open_json(self):
        if os.path.exists(SAVE_FILE):
            try:
                os.startfile(SAVE_FILE)
            except AttributeError:
                messagebox.showinfo("Info", f"Datei liegt hier:\n{SAVE_FILE}")
        else:
            messagebox.showinfo("Info", "Noch keine Credentials gespeichert.")

    # ------------------------------------------------------------ Settings
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
            "username_separator": self.separator_var.get(),
            "username_number_min": num_min,
            "username_number_max": num_max,
            "auto_copy": self.auto_copy_var.get(),
            "auto_copy_field": self.auto_copy_field_var.get(),
            "confirm_delete": self.confirm_delete_var.get(),
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

    # ------------------------------------------------------ Design / Fenster
    def _transparency_value(self):
        try:
            value = int(self.settings.get("window_transparency", 0))
        except (TypeError, ValueError):
            value = 0
        return max(0, min(100, value))

    def _apply_transparency(self):
        value = self._transparency_value()
        try:
            self.attributes("-alpha", 1 - value / 100)
        except tk.TclError:
            pass

    def _on_transparency(self, value):
        self.settings["window_transparency"] = int(value)
        self.transparency_label.config(text=f"{int(value)} %")
        self._apply_transparency()

    def _set_transparency(self, value):
        self.transparency_slider.set(value)
        self._on_transparency(value)
        self._save_settings_file()
        self.set_status("Transparenz zurückgesetzt" if value == 0 else f"Transparenz {value} %")

    def _on_theme_change(self):
        name = self.theme_var.get()
        if name == CURRENT_THEME:
            return
        self.settings["theme"] = name
        self._save_settings_file()
        self.request_restart()

    def _on_layout_change(self):
        layout = self.layout_var.get()
        if layout == self.layout:
            return
        self.settings["layout"] = layout
        # passendes Farbdesign mitwählen (kann danach frei geändert werden)
        if layout == "multitool" and self.settings.get("theme", "original") == "original":
            self.settings["theme"] = "multitool"
        elif layout == "classic" and self.settings.get("theme") == "multitool":
            self.settings["theme"] = "original"
        if layout == "classic":
            self.settings["password_mode"] = "random"     # Passphrase-Schalter gibt es nur im Multitool-Layout
        self._save_settings_file()
        self.request_restart()

    def request_restart(self):
        """Fenster mit neuem Design neu aufbauen (Lizenz bleibt aktiv, kein erneutes Anmelden)."""
        self.restart_requested = True
        self.restart_geometry = self.geometry()
        self.restart_tab = getattr(self, "current_tab", 0)
        self._on_close()

    def reset_settings(self):
        if not messagebox.askyesno("Zurücksetzen", "Alle Einstellungen auf Standard zurücksetzen?"):
            return
        self.settings = DEFAULT_SETTINGS.copy()
        s = self.settings
        self._remove_custom_background()
        self.email_var.set(s["email"])
        self.length_value = s["password_length"]
        self.length_slider.set(s["password_length"])
        self.length_label.config(text=str(s["password_length"]))
        for var, key in ((self.use_upper_var, "use_uppercase"), (self.use_lower_var, "use_lowercase"),
                         (self.use_digits_var, "use_digits"), (self.use_symbols_var, "use_symbols"),
                         (self.first_letter_var, "first_letter"), (self.no_ambiguous_var, "no_ambiguous"),
                         (self.unique_chars_var, "unique_chars"), (self.save_on_generate_var, "save_on_generate"),
                         (self.show_password_var, "show_password"), (self.auto_copy_var, "auto_copy"),
                         (self.confirm_delete_var, "confirm_delete"), (self.bg_enabled_var, "bg_enabled")):
            var.set(s[key])
        self.separator_var.set(s["username_separator"])
        self.num_min_var.set(str(s["username_number_min"]))
        self.num_max_var.set(str(s["username_number_max"]))
        self.auto_copy_field_var.set(s["auto_copy_field"])
        self.bg_brightness_slider.set(s["bg_brightness"])
        self.bg_brightness_label.config(text=f"{s['bg_brightness']}%")
        self._update_mode_label()
        self._sync_backdrop(reload_image=True)
        self._update_bg_source_label()
        self._save_settings_file()
        self._update_email_stats()
        self.regenerate_password(silent=True)
        self.transparency_slider.set(0)
        self.transparency_label.config(text="0 %")
        self._apply_transparency()
        self.set_status("Einstellungen zurückgesetzt")
        if CURRENT_THEME != "original":
            self.request_restart()



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
    "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"
)


# ---------------------------------------------------------------------------
# Auto-Update über GitHub-Releases
# ---------------------------------------------------------------------------
def _version_tuple(version):
    return tuple(int(x) for x in version.split(".") if x.isdigit())


def check_for_updates():
    # Nur die gebaute EXE aktualisieren, nicht den Python-Testlauf.
    if not getattr(sys, "frozen", False):
        return

    new_file = None
    root = None
    try:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            headers={"User-Agent": "ACC-Generator-Updater"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            release = json.loads(response.read().decode("utf-8"))

        latest = release["tag_name"].lstrip("v")
        if _version_tuple(latest) <= _version_tuple(CURRENT_VERSION):
            return

        # Unsichtbares Hauptfenster, damit keine leere "tk"-Box erscheint
        root = tk.Tk()
        root.withdraw()

        asset = next((a for a in release.get("assets", []) if a["name"] == RELEASE_ASSET), None)
        if not asset:
            messagebox.showerror("Update-Fehler", f"Die Datei {RELEASE_ASSET} fehlt im neuesten Release.",
                                 parent=root)
            return

        if not messagebox.askyesno(
            "Update verfügbar",
            f"Neue Version: {latest}\nAktuelle Version: {CURRENT_VERSION}\n\n"
            "Möchtest du das Update jetzt installieren?",
            parent=root,
        ):
            return

        target = os.path.abspath(sys.executable)
        new_file = os.path.join(tempfile.gettempdir(), f"acc_generator_update_{os.getpid()}.exe")

        download_request = urllib.request.Request(
            asset["browser_download_url"], headers={"User-Agent": "ACC-Generator-Updater"},
        )
        with urllib.request.urlopen(download_request, timeout=60) as response:
            with open(new_file, "wb") as file:
                file.write(response.read())

        if os.path.getsize(new_file) == 0:
            raise RuntimeError("Die heruntergeladene Datei ist leer.")

        # Hilfs-BAT wartet auf das Ende der laufenden EXE, ersetzt sie und startet sie neu.
        helper = os.path.join(tempfile.gettempdir(), f"acc_generator_update_{os.getpid()}.bat")
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
            ["cmd.exe", "/c", helper, target, new_file, str(os.getpid())],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        root.destroy()
        root = None
        # Hauptprogramm beenden, damit die EXE ersetzt werden kann.
        sys.exit(0)

    except Exception:
        # Bei Netzwerkproblemen soll das Programm normal starten.
        try:
            if new_file and os.path.exists(new_file):
                os.remove(new_file)
        except OSError:
            pass
    finally:
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass



# ---------------------------------------------------------------------------
# Lizenz-Aktivierung (lokaler Lizenzserver, siehe license_server.py)
# ---------------------------------------------------------------------------
import queue
import urllib.error
from datetime import timezone

LICENSE_API = "http://127.0.0.1:8765/api/validate"
_LICENSE_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _license_config_dir():
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(root, "AccGenerator")
    os.makedirs(path, exist_ok=True)
    return path


def _license_key_file():
    return os.path.join(_license_config_dir(), "license.json")


def _load_saved_key():
    try:
        with open(_license_key_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("key", "")).strip() if isinstance(data, dict) else ""
    except (OSError, ValueError):
        return ""


def _save_key(key):
    try:
        save_json_atomic(_license_key_file(), {"key": key})
    except OSError:
        pass


def _forget_key():
    try:
        os.remove(_license_key_file())
    except OSError:
        pass


def _validate_license(key):
    """Fragt den Lizenzserver. Wirft ConnectionError, wenn er nicht erreichbar ist."""
    request = urllib.request.Request(
        LICENSE_API, data=json.dumps({"key": key}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # localhost nie über Proxy
    try:
        with opener.open(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            data = {}
        return {"valid": False, "message": data.get("error") or data.get("message") or f"Serverfehler ({e.code})."}
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ConnectionError(str(e)) from None


def _format_remaining(seconds):
    s = max(0, int(seconds or 0))
    units = [(31536000, "Jahr", "Jahre"), (86400, "Tag", "Tage"), (3600, "Stunde", "Stunden"),
             (60, "Minute", "Minuten"), (1, "Sekunde", "Sekunden")]
    parts = []
    for size, one, many in units:
        if s >= size or (size == 1 and not parts):
            value, s = divmod(s, size)
            parts.append(f"{value:,}".replace(",", ".") + " " + (one if value == 1 else many))
        elif parts:
            break
        if len(parts) == 2:
            break
    return " ".join(parts)


def _format_license_info(result):
    if result.get("lifetime"):
        return "Unbegrenzt gültig – läuft nie ab."
    exp = result.get("expires_at")
    if exp is None:
        return ""
    dt = _LICENSE_EPOCH + timedelta(seconds=int(exp))
    try:
        dt = dt.astimezone()
    except (OSError, OverflowError, ValueError):
        pass
    return f"Gültig bis {dt:%d.%m.%Y, %H:%M} Uhr · noch {_format_remaining(result.get('remaining_seconds'))}"


def _show_license_error(title, message):
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror(title, message, parent=root)
    finally:
        root.destroy()


class LicenseDialog(tk.Tk):
    """Aktivierungsfenster im Look der App."""

    W, H = 520, 540

    def __init__(self, initial_key="", message="", message_color=None):
        super().__init__()
        self.result = False
        self.result_key = None
        self.result_data = None
        self._busy = False
        self._queue = queue.Queue()
        self._formatting = False

        self.title(f"{APP_NAME} – Lizenz aktivieren")
        self.configure(bg=BG)
        self.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{max(0, (sw - self.W) // 2)}+{max(0, (sh - self.H) // 3)}")
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.bind("<Return>", lambda e: self._submit())

        self.key_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar()

        self.backdrop = Backdrop(self)
        if PIL_OK:
            try:
                with Image.open(io.BytesIO(base64.b64decode(DEFAULT_BG_B64))) as img:
                    self.backdrop.set_source(img.convert("RGB"))
            except Exception:
                pass
        self._build()

        self.key_var.trace_add("write", self._on_key_change)
        if initial_key:
            self.key_var.set(initial_key)
        if message:
            self._set_status(message, message_color or DANGER)
            self._set_entry_state("error" if (message_color or DANGER) == DANGER else "normal")
        self.after(60, self.backdrop.refresh)
        self.after(80, self._bring_to_front)

    # ------------------------------------------------------------------ UI
    def _build(self):
        shell = Shell(self, self.backdrop)
        shell.pack(fill="both", expand=True)
        panel = shell.panel
        body = tk.Frame(panel, bg=PANEL)
        body.pack(fill="both", expand=True, padx=22, pady=18)

        # Kopf mit Schlüssel-Symbol
        head = tk.Frame(body, bg=PANEL)
        head.pack(fill="x")
        icon = tk.Canvas(head, width=56, height=56, bg=PANEL, highlightthickness=0, bd=0)
        round_rect(icon, 2, 2, 54, 54, 16, fill=SELECT_BG, outline=SELECT_BORDER)
        icon.create_oval(13, 21, 29, 37, outline=ACCENT, width=3)
        icon.create_line(29, 29, 44, 29, fill=ACCENT, width=3, capstyle="round")
        icon.create_line(40, 29, 40, 35, fill=ACCENT, width=3, capstyle="round")
        icon.create_line(44, 29, 44, 34, fill=ACCENT, width=3, capstyle="round")
        icon.pack(side="left")
        titles = tk.Frame(head, bg=PANEL)
        titles.pack(side="left", padx=(14, 0))
        tk.Label(titles, text="Lizenz aktivieren", bg=PANEL, fg=TEXT, font=(UI, 17, "bold")).pack(anchor="w")
        tk.Label(titles, text=f"{APP_NAME}  ·  Version {CURRENT_VERSION}", bg=PANEL, fg=MUTED,
                 font=(UI, 9)).pack(anchor="w")

        tk.Label(body, text="Gib deinen Lizenzschlüssel ein, um den Generator freizuschalten. "
                            "Der Schlüssel wird danach auf diesem PC gespeichert.",
                 bg=PANEL, fg=MUTED, font=(UI, 9), wraplength=440, justify="left").pack(anchor="w", pady=(16, 12))

        # Eingabe-Karte
        card = RoundCard(body, pad=16, radius=14)
        card.pack(fill="x")
        cb = card.body
        top = tk.Frame(cb, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text="LIZENZSCHLÜSSEL", bg=CARD, fg=MUTED, font=(UI, 8, "bold")).pack(side="left")
        RoundButton(top, "Einfügen", command=self._paste, height=26, padx=10, fill=CARD2, border=BORDER,
                    font=(UI, 8, "bold")).pack(side="right")

        self.entry = tk.Entry(
            cb, textvariable=self.key_var, bg=FIELD, fg=TEXT, insertbackground=ACCENT, relief="flat",
            font=(MONO, 14, "bold"), justify="center", bd=8, highlightthickness=2,
            highlightbackground=BORDER, highlightcolor=ACCENT, disabledbackground=FIELD,
            disabledforeground=MUTED,
        )
        self.entry.pack(fill="x", pady=(8, 6), ipady=4)
        tk.Label(cb, text="Format: ACC-XXXXX-XXXXX-XXXXX-XXXXX", bg=CARD, fg="#5d616b",
                 font=(MONO, 8)).pack(anchor="center")

        remember = tk.Frame(cb, bg=CARD)
        remember.pack(fill="x", pady=(12, 0))
        box = CheckBox(remember, self.remember_var)
        box.pack(side="left")
        label = tk.Label(remember, text="Schlüssel auf diesem PC merken", bg=CARD, fg=TEXT, font=(UI, 9),
                         cursor="hand2")
        label.pack(side="left", padx=(9, 0))
        label.bind("<Button-1>", box.toggle)

        # Statuszeile
        status = tk.Frame(body, bg=PANEL, height=46)
        status.pack(fill="x", pady=(12, 4))
        status.pack_propagate(False)
        self.status_icon = tk.Label(status, text="", bg=PANEL, fg=MUTED, font=(UI, 11, "bold"), width=2)
        self.status_icon.pack(side="left", anchor="n")
        self.status_label = tk.Label(status, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=(UI, 9),
                                     wraplength=420, justify="left", anchor="nw")
        self.status_label.pack(side="left", fill="both", expand=True)

        # Buttons
        buttons = tk.Frame(body, bg=PANEL)
        buttons.pack(fill="x")
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=2)
        RoundButton(buttons, "Beenden", command=self._cancel, height=44, radius=11, fill=CARD, border=BORDER,
                    font=(UI, 10, "bold")).grid(row=0, column=0, sticky="ew")
        self.activate_btn = RoundButton(buttons, "Aktivieren  →", command=self._submit, height=44, radius=11,
                                        font=(UI, 10, "bold"), fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2))
        self.activate_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        tk.Label(body, text="Enter = Aktivieren  ·  Esc = Beenden",
                 bg=PANEL, fg="#5d616b", font=(UI, 8)).pack(side="bottom", pady=(10, 0))

    def _bring_to_front(self):
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after(400, lambda: self.attributes("-topmost", False))
            self.focus_force()
            self.entry.focus_set()
            self.entry.icursor("end")
        except tk.TclError:
            pass

    # ------------------------------------------------------------- Zustände
    def _set_status(self, text, color=MUTED):
        icons = {DANGER: "✕", GREEN: "✓", ORANGE: "!", MUTED: "•"}
        self.status_var.set(text)
        self.status_label.config(fg=color)
        self.status_icon.config(text=icons.get(color, "•") if text else "", fg=color)

    def _set_entry_state(self, state):
        colors = {"normal": (BORDER, ACCENT), "error": (DANGER, DANGER), "ok": (GREEN, GREEN)}
        bg, focus = colors[state]
        self.entry.config(highlightbackground=bg, highlightcolor=focus)

    def _set_busy(self, busy):
        self._busy = busy
        self.entry.config(state="disabled" if busy else "normal")
        self.activate_btn.restyle(text="Prüfe Lizenz …" if busy else "Aktivieren  →")
        self.configure(cursor="watch" if busy else "")

    def _shake(self):
        x, y = self.winfo_x(), self.winfo_y()
        offsets = [12, -12, 9, -9, 5, -5, 2, 0]
        for i, dx in enumerate(offsets):
            self.after(28 * i, lambda dx=dx: self.winfo_exists() and self.geometry(f"+{x + dx}+{y}"))

    def _on_key_change(self, *_):
        if self._formatting:
            return
        raw = self.key_var.get()
        clean = "".join(raw.split()).upper()
        if clean != raw:
            self._formatting = True
            self.key_var.set(clean)
            self.entry.icursor("end")
            self._formatting = False
        if not self._busy and self.status_var.get():
            self._set_status("")
            self._set_entry_state("normal")

    def _paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            self._set_status("Die Zwischenablage ist leer.", ORANGE)
            return
        self.key_var.set(text.strip())
        self.entry.focus_set()
        self.entry.icursor("end")

    # --------------------------------------------------------------- Ablauf
    def _submit(self):
        if self._busy or self.result:
            return
        key = self.key_var.get().strip()
        if not key:
            self._set_status("Bitte gib zuerst einen Lizenzschlüssel ein.", DANGER)
            self._set_entry_state("error")
            self._shake()
            return
        self._set_busy(True)
        self._set_status("Lizenz wird geprüft …", MUTED)
        threading.Thread(target=self._worker, args=(key,), daemon=True).start()
        self.after(60, self._poll)

    def _worker(self, key):
        try:
            self._queue.put(("ok", key, _validate_license(key)))
        except Exception as e:
            self._queue.put(("offline", key, str(e)))

    def _poll(self):
        try:
            kind, key, data = self._queue.get_nowait()
        except queue.Empty:
            self.after(60, self._poll)
            return
        self._set_busy(False)
        if kind == "offline":
            self._set_status("Der Lizenzserver ist nicht erreichbar. Bitte versuche es gleich noch einmal.", ORANGE)
            self._set_entry_state("error")
            return
        if data.get("valid"):
            if self.remember_var.get():
                _save_key(key)
            else:
                _forget_key()
            self.result = True
            self.result_key, self.result_data = key, data
            self._set_entry_state("ok")
            info = _format_license_info(data)
            self._set_status("Lizenz aktiviert!" + (f"  {info}" if info else ""), GREEN)
            self.activate_btn.restyle(text="Freigeschaltet ✓", gradient=(GREEN, "#22b866"))
            self.entry.config(state="disabled")
            self.after(1400, self.destroy)
        else:
            self._set_status(data.get("message") or "Der Lizenzschlüssel ist ungültig.", DANGER)
            self._set_entry_state("error")
            self._shake()
            self.entry.focus_set()
            self.entry.select_range(0, "end")

    def _cancel(self):
        if self.result:
            return
        self.result = False
        self.destroy()

    def run(self):
        self.mainloop()
        return (self.result_key, self.result_data) if self.result else None


def _require_local_license(logout_message=""):
    try:
        import license_server
        license_server.start_server()
    except Exception as exc:
        _show_license_error("Lizenzsystem",
                            f"Das lokale Lizenzsystem konnte nicht gestartet werden.\n\n{exc}")
        return None

    if logout_message:                           # nach einem Logout: direkt zur Anmeldung
        return LicenseDialog(message=logout_message, message_color=DANGER).run()

    saved = _load_saved_key()
    prefill, message, color = "", "", None
    if saved:
        try:
            result = _validate_license(saved)
            if result.get("valid"):
                return saved, result             # gespeicherte Lizenz gültig → direkt starten
            _forget_key()
            message = "Deine gespeicherte Lizenz funktioniert nicht mehr: " + (result.get("message") or "ungültig.")
        except ConnectionError:
            prefill = saved
            message, color = "Der Lizenzserver ist gerade nicht erreichbar. Versuche es erneut.", ORANGE

    return LicenseDialog(initial_key=prefill, message=message, message_color=color).run()


# ---------------------------------------------------------------------------
# Live-Lizenzwächter: hält eine Dauerverbindung zum Lizenzserver und sperrt /
# entsperrt die App sofort, wenn im Dashboard etwas geändert wird.
# ---------------------------------------------------------------------------
LICENSE_BASE = "http://127.0.0.1:8765"

LOCK_TEXTS = {
    "suspended": ("Lizenz pausiert",
                  "Dein Lizenzschlüssel wurde vorübergehend pausiert. Der Generator wird automatisch "
                  "wieder freigeschaltet, sobald die Lizenz reaktiviert wird.", YELLOW),
    "revoked": ("Lizenz gesperrt",
                "Dein Lizenzschlüssel wurde gesperrt. Sobald er entsperrt wird, geht es hier automatisch weiter.",
                DANGER),
    "banned": ("Lizenz gebannt", "Dein Lizenzschlüssel wurde dauerhaft gebannt.", DANGER),
    "expired": ("Lizenz abgelaufen",
                "Deine Lizenz ist abgelaufen. Wird sie verlängert, schaltet sich der Generator sofort wieder frei.",
                ORANGE),
    "unknown": ("Lizenz gelöscht", "Dein Lizenzschlüssel existiert nicht mehr.", DANGER),
}

# Bei diesen Zuständen wird man sofort abgemeldet: gespeicherter Key wird gelöscht,
# die App schließt sich und das Anmeldefenster erscheint.
# Pausiert / abgelaufen sperren nur vorübergehend (Sperrbild, automatisch wieder frei).
LOGOUT_STATUSES = {"revoked", "banned", "unknown"}
LOGOUT_SECONDS = 3
LOGOUT_MESSAGES = {
    "revoked": "Dein Lizenzschlüssel wurde gesperrt – du wurdest abgemeldet.",
    "banned": "Dein Lizenzschlüssel wurde dauerhaft gebannt – du wurdest abgemeldet.",
    "unknown": "Dein Lizenzschlüssel wurde gelöscht – du wurdest abgemeldet.",
}


def _watch_license(key, rev, sid):
    query = _urlparse.urlencode({"key": key, "rev": "" if rev is None else rev, "sid": sid or ""})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"{LICENSE_BASE}/api/watch?{query}", timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ConnectionError(str(e)) from None


class LicenseGuard:
    GUARDED = ("generate", "copy_all", "_copy", "regenerate_password", "regenerate_username", "preview_only",
               "_mt_generate_batch")

    def __init__(self, app, key, data):
        self.app = app
        self.key = key
        self.data = dict(data or {})
        self.rev = self.sid = None
        self.locked = False
        self.offline = False
        self.overlay = None
        self.logging_out = False
        self._activating = False
        self._pulse_on = False
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._jobs = set()

        self._wrap_app()
        self.badge = tk.Label(app.footer, text="", bg=PANEL, fg=MUTED, font=(UI, 9, "bold"))
        self.badge.pack(side="left", padx=(16, 0))
        app.bind("<Destroy>", self._on_destroy, add="+")

        threading.Thread(target=self._watch_loop, daemon=True, name="license-watch").start()
        self._apply(self.data)
        self._poll()
        self._tick()

    # ------------------------------------------------------------ Grundlagen
    def _wrap_app(self):
        """Sperrt Generieren/Kopieren auch per Tastenkürzel, solange die Lizenz ungültig ist."""
        for name in self.GUARDED:
            original = getattr(self.app, name, None)
            if original is None:
                continue

            def guarded(*args, _orig=original, **kwargs):
                if self.locked:
                    return None
                return _orig(*args, **kwargs)

            setattr(self.app, name, guarded)

    def _on_destroy(self, event):
        if event.widget is self.app:
            self._stop.set()
            for job in list(self._jobs):           # geplante Timer sauber abbrechen
                try:
                    self.app.after_cancel(job)
                except tk.TclError:
                    pass
            self._jobs.clear()

    def _after(self, ms, func):
        if self._stop.is_set():
            return
        job = None

        def run():
            self._jobs.discard(job)
            if not self._stop.is_set():
                func()
        try:
            job = self.app.after(ms, run)
            self._jobs.add(job)
        except tk.TclError:
            pass

    # ----------------------------------------------- Hintergrund-Verbindung
    def _watch_loop(self):
        while not self._stop.is_set():
            key = self.key
            try:
                data = _watch_license(key, self.rev, self.sid)
            except ConnectionError:
                self._queue.put(("offline", key, None))
                self.rev = self.sid = None
                try:                                   # Server weg? Dann übernimmt die App ihn selbst.
                    import license_server
                    license_server.start_server()
                except Exception:
                    pass
                self._stop.wait(2)
                continue
            if key != self.key:                        # inzwischen wurde ein anderer Key aktiviert
                self.rev = self.sid = None
                continue
            self.rev, self.sid = data.get("rev"), data.get("sid")
            self._queue.put(("state", key, data))

    def _poll(self):
        try:
            while True:
                kind, key, data = self._queue.get_nowait()
                if kind == "activate":
                    self._activation_result(key, data)
                elif key != self.key:
                    continue
                elif kind == "offline":
                    self._set_offline(True)
                else:
                    self._set_offline(False)
                    self._apply(data)
        except queue.Empty:
            pass
        self._after(100, self._poll)

    def _tick(self):
        exp = self.data.get("expires_at")
        if not self.locked and self.data.get("valid") and exp is not None and _time.time() >= exp:
            self._apply(dict(self.data, valid=False, effective_status="expired",
                             message="Deine Lizenz ist abgelaufen."))
        self._update_badge()
        self._after(1000, self._tick)

    # ----------------------------------------------------------- Zustände
    def _apply(self, data):
        if self.logging_out:
            return
        self.data = dict(data)
        status = data.get("effective_status") or data.get("status")
        if not data.get("valid") and status in LOGOUT_STATUSES:
            self._logout(status)
            return
        if data.get("valid"):
            if self.locked:
                self._unlock()
                self.app.set_status("Lizenz wieder aktiv ✓")
        else:
            if data.get("effective_status") == "unknown" and _load_saved_key() == self.key:
                _forget_key()
            self._lock(data)
        self._update_badge()

    def _set_offline(self, offline):
        if offline != self.offline:
            self.offline = offline
            self._update_badge()
            if self.overlay is not None and not self.logging_out:
                self._update_live_line()

    def _update_badge(self):
        if self.logging_out:
            return
        d = self.data
        if self.offline:
            text, color = "● Lizenzserver getrennt – verbinde neu …", ORANGE
        elif self.locked:
            text, color = "● " + LOCK_TEXTS.get(d.get("effective_status"), ("Lizenz ungültig",))[0], DANGER
        elif d.get("lifetime"):
            text, color = "● Lizenz aktiv · Lifetime", GREEN
        elif d.get("expires_at") is not None:
            left = int(d["expires_at"] - _time.time())
            text = "● Lizenz aktiv · noch " + _format_remaining(left)
            color = YELLOW if left < 86400 else GREEN
        else:
            text, color = "● Lizenz aktiv", GREEN
        try:
            self.badge.config(text=text, fg=color)
        except tk.TclError:
            pass

    # ------------------------------------------------------------ Sperrbild
    def _build_overlay(self):
        ov = tk.Frame(self.app, bg="#07080a")
        self.overlay = ov
        card = RoundCard(ov, pad=26, radius=18, fill=CARD, border=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        body = card.body

        self.ov_icon = tk.Canvas(body, width=68, height=68, bg=CARD, highlightthickness=0, bd=0)
        self.ov_icon.pack(pady=(0, 12))
        self.ov_title = tk.Label(body, text="", bg=CARD, fg=TEXT, font=(UI, 18, "bold"))
        self.ov_title.pack()
        self.ov_text = tk.Label(body, text="", bg=CARD, fg=MUTED, font=(UI, 10), wraplength=420, justify="center")
        self.ov_text.pack(pady=(6, 0))

        live = tk.Frame(body, bg=CARD)
        live.pack(pady=(14, 0))
        self.ov_dot = tk.Canvas(live, width=10, height=10, bg=CARD, highlightthickness=0, bd=0)
        self.ov_dot.pack(side="left", padx=(0, 7))
        self.ov_live = tk.Label(live, text="", bg=CARD, fg=MUTED, font=(UI, 8))
        self.ov_live.pack(side="left")

        self.ov_form = form = tk.Frame(body, bg=CARD)
        form.pack(fill="x")
        tk.Frame(form, bg=BORDER_SOFT, height=1, width=420).pack(fill="x", pady=18)

        tk.Label(form, text="ANDEREN SCHLÜSSEL VERWENDEN", bg=CARD, fg=MUTED, font=(UI, 8, "bold")).pack(anchor="w")
        self.ov_key = tk.StringVar()
        self.ov_key.trace_add("write", self._on_ov_key)
        self.ov_entry = tk.Entry(
            form, textvariable=self.ov_key, bg=FIELD, fg=TEXT, insertbackground=ACCENT, relief="flat",
            font=(MONO, 12, "bold"), justify="center", bd=7, highlightthickness=2,
            highlightbackground=BORDER, highlightcolor=ACCENT, width=34,
        )
        self.ov_entry.pack(fill="x", pady=(6, 4), ipady=3)
        self.ov_entry.bind("<Return>", lambda e: self._activate())
        self.ov_error = tk.Label(form, text="", bg=CARD, fg=DANGER, font=(UI, 9), wraplength=420)
        self.ov_error.pack(fill="x")

        buttons = tk.Frame(form, bg=CARD)
        buttons.pack(fill="x", pady=(8, 0))
        buttons.grid_columnconfigure(0, weight=1)
        buttons.grid_columnconfigure(1, weight=2)
        RoundButton(buttons, "Beenden", command=self.app._on_close, height=42, radius=11, fill=CARD2,
                    border=BORDER, font=(UI, 10, "bold")).grid(row=0, column=0, sticky="ew")
        self.ov_btn = RoundButton(buttons, "Aktivieren  →", command=self._activate, height=42, radius=11,
                                  font=(UI, 10, "bold"), fg=ACCENT_DARK, gradient=(ACCENT, ACCENT_2))
        self.ov_btn.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.ov_current = tk.Label(body, text="", bg=CARD, fg="#5d616b", font=(MONO, 8))
        self.ov_current.pack(pady=(14, 0))

    def _draw_lock(self, color):
        c = self.ov_icon
        c.delete("all")
        round_rect(c, 2, 2, 66, 66, 20, fill=mix(color, CARD, 0.82), outline=mix(color, CARD, 0.55))
        c.create_arc(22, 14, 46, 40, start=0, extent=180, style="arc", outline=color, width=4)
        c.create_line(22, 27, 22, 32, fill=color, width=4)
        c.create_line(46, 27, 46, 32, fill=color, width=4)
        round_rect(c, 17, 31, 51, 54, 6, fill=color, outline=color)
        c.create_oval(31, 38, 37, 44, fill=mix(color, CARD, 0.82), outline="")

    def _update_live_line(self):
        if self.offline:
            self.ov_live.config(text="Verbindung zum Lizenzserver unterbrochen – verbinde neu …", fg=ORANGE)
        else:
            self.ov_live.config(text="Live verbunden – Änderungen im Dashboard werden sofort übernommen.",
                                fg=MUTED)

    def _pulse(self):
        if not self.locked or self.overlay is None or self.logging_out:
            return
        self._pulse_on = not self._pulse_on
        base = ORANGE if self.offline else GREEN
        color = base if self._pulse_on else mix(base, CARD, 0.65)
        self.ov_dot.delete("all")
        self.ov_dot.create_oval(1, 1, 9, 9, fill=color, outline="")
        self._after(650, self._pulse)

    def _lock(self, data):
        exit_mini = getattr(self.app, "exit_mini_mode", None)
        if exit_mini:
            exit_mini()
        if self.overlay is None:
            self._build_overlay()
        status = data.get("effective_status") or data.get("status")
        title, text, color = LOCK_TEXTS.get(status, ("Lizenz ungültig", data.get("message") or "", DANGER))
        self.ov_title.config(text=title)
        self.ov_text.config(text=text)
        self._draw_lock(color)
        self._update_live_line()
        self.ov_current.config(text=f"Aktueller Key: {self.key}")
        was_locked = self.locked
        self.locked = True
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.overlay.lift()
        if not was_locked:
            self.ov_error.config(text="")
            self.ov_entry.focus_set()
            self._pulse()

    def _unlock(self):
        self.locked = False
        if self.overlay is not None:
            self.overlay.place_forget()

    # -------------------------------------------------------------- Logout
    def _logout(self, status):
        """Abmelden: Key vergessen, kurz Hinweis zeigen, App schließen -> Anmeldefenster."""
        self.logging_out = True
        self.locked = True
        exit_mini = getattr(self.app, "exit_mini_mode", None)
        if exit_mini:
            exit_mini()
        if _load_saved_key() == self.key:
            _forget_key()
        message = LOGOUT_MESSAGES.get(status, "Deine Lizenz ist nicht mehr gültig – du wurdest abgemeldet.")
        self.app.logout_message = message
        if self.overlay is None:
            self._build_overlay()
        self.ov_title.config(text="Du wurdest abgemeldet")
        self.ov_text.config(text=message.split(" – ")[0] + ". Der gespeicherte Schlüssel wurde von diesem PC entfernt.")
        self._draw_lock(DANGER)
        self.ov_form.pack_forget()
        self.ov_current.config(text=f"Key: {self.key}")
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.overlay.lift()
        try:
            self.badge.config(text="● Abgemeldet", fg=DANGER)
        except tk.TclError:
            pass
        self._logout_countdown(LOGOUT_SECONDS)

    def _logout_countdown(self, left):
        if left <= 0:
            try:
                self.app._on_close()
            except tk.TclError:
                pass
            return
        self.ov_dot.delete("all")
        self.ov_dot.create_oval(1, 1, 9, 9, fill=DANGER, outline="")
        self.ov_live.config(text=f"Zurück zur Anmeldung in {left} …", fg=MUTED)
        self._after(1000, lambda: self._logout_countdown(left - 1))

    # ------------------------------------------------ neuer Schlüssel im Sperrbild
    def _on_ov_key(self, *_):
        raw = self.ov_key.get()
        clean = "".join(raw.split()).upper()
        if clean != raw:
            self.ov_key.set(clean)
            self.ov_entry.icursor("end")
        self.ov_error.config(text="")
        self.ov_entry.config(highlightbackground=BORDER, highlightcolor=ACCENT)

    def _activate(self):
        if self._activating:
            return
        key = self.ov_key.get().strip()
        if not key:
            self._ov_fail("Bitte gib einen Lizenzschlüssel ein.")
            return
        self._activating = True
        self.ov_btn.restyle(text="Prüfe …")

        def worker():
            try:
                result = _validate_license(key)
            except ConnectionError:
                result = None
            self._queue.put(("activate", key, result))

        threading.Thread(target=worker, daemon=True).start()

    def _ov_fail(self, message):
        self.ov_error.config(text=message)
        self.ov_entry.config(highlightbackground=DANGER, highlightcolor=DANGER)

    def _activation_result(self, key, data):
        self._activating = False
        self.ov_btn.restyle(text="Aktivieren  →")
        if data is None:
            self._ov_fail("Der Lizenzserver ist nicht erreichbar. Bitte versuche es gleich noch einmal.")
        elif not data.get("valid"):
            self._ov_fail(data.get("message") or "Der Lizenzschlüssel ist ungültig.")
        else:
            _save_key(key)
            self.key = key
            self.rev = self.sid = None
            self.ov_key.set("")
            self._apply(data)
            self.app.set_status("Neue Lizenz aktiviert ✓")


def _settings_on_disk():
    return load_json(SETTINGS_FILE, DEFAULT_SETTINGS)


def run_app(on_app_created=None):
    start_settings = _settings_on_disk()
    apply_theme(start_settings.get("theme", "original"))
    if int(start_settings.get("window_transparency", 0) or 0) >= 95:   # nie unsichtbar starten
        start_settings["window_transparency"] = 0
        try:
            save_json_atomic(SETTINGS_FILE, start_settings)
        except OSError:
            pass

    logout_message = ""
    license_info = None
    restart = None
    first_start = True
    while True:
        if restart is None:
            license_info = _require_local_license(logout_message)
            if not license_info:
                break
            if first_start:
                check_for_updates()
                first_start = False
        app = App()
        if restart:
            app.geometry(restart["geometry"])
            app.select_tab(restart["tab"])
            app.set_status(f"Design: {THEMES[CURRENT_THEME]['label']}")
        app.logout_message = ""
        app.license_guard = LicenseGuard(app, *license_info)
        if on_app_created:
            on_app_created(app)
        app.mainloop()

        logout_message = getattr(app, "logout_message", "")
        restart = None
        if logout_message:
            continue
        if getattr(app, "restart_requested", False):          # Designwechsel
            guard = app.license_guard
            license_info = (guard.key, guard.data)
            restart = {"geometry": getattr(app, "restart_geometry", ""), "tab": getattr(app, "restart_tab", 2)}
            apply_theme(_settings_on_disk().get("theme", "original"))
            continue
        break


if __name__ == "__main__":
    run_app()
