"""
Lokaler Lizenzserver für den ACC Generator.

Dashboard starten:   python license_server.py   -> öffnet http://127.0.0.1:8765
Die App startet den Server automatisch im Hintergrund (start_server()).

Endpunkte
  GET  /                               Dashboard (license_dashboard.html)
  GET  /api/health                     Lebenszeichen
  GET  /api/licenses                   alle Keys
  POST /api/licenses                   {"amount": "3", "unit": "months", "note": "..."}
                                       unit: seconds|minutes|hours|days|weeks|months|years|lifetime
  POST /api/licenses/<key>/action      {"action": "suspend|revoke|ban|reinstate|delete|extend|note", ...}
  POST /api/validate                   {"key": "ACC-..."}
  GET  /api/watch?key=..&rev=..&sid=.. Live-Verbindung der App (Long-Poll)
  GET  /api/events?rev=..&sid=..       Live-Aktualisierung des Dashboards (Long-Poll)
"""
import calendar
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

HOST = "127.0.0.1"
PORT = 8765
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _resource(name):
    for folder in (getattr(sys, "_MEIPASS", None), _base_dir()):
        if folder:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                return path
    return os.path.join(_base_dir(), name)


def _data_dir():
    # Fester Ort, damit Dashboard (license_server.py) und App (EXE) dieselbe Datenbank nutzen –
    # egal aus welchem Ordner sie gestartet werden.
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(root, "AccGenerator")
    os.makedirs(path, exist_ok=True)
    return path


DB_FILE = os.path.join(_data_dir(), "licenses.sqlite3")
LEGACY_DB_FILE = os.path.join(_base_dir(), "licenses.sqlite3")
DASHBOARD_FILE = "license_dashboard.html"
LONG_POLL_SECONDS = 25
SERVER_ID = secrets.token_hex(6)

KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # ohne I, O, 0, 1
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
MAX_TS = 253402300799                                # 31.12.9999 – alles darüber gilt als unbegrenzt
UNIT_SECONDS = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 604800}
UNIT_LABELS = {
    "seconds": ("Sekunde", "Sekunden"), "minutes": ("Minute", "Minuten"), "hours": ("Stunde", "Stunden"),
    "days": ("Tag", "Tage"), "weeks": ("Woche", "Wochen"), "months": ("Monat", "Monate"),
    "years": ("Jahr", "Jahre"),
}
STATUS_ACTIONS = {"suspend": "suspended", "revoke": "revoked", "ban": "banned", "reinstate": "active"}
STATUS_MESSAGES = {
    "expired": "Dieser Lizenzschlüssel ist abgelaufen.",
    "suspended": "Dieser Lizenzschlüssel ist vorübergehend pausiert.",
    "revoked": "Dieser Lizenzschlüssel wurde gesperrt.",
    "banned": "Dieser Lizenzschlüssel wurde dauerhaft gebannt.",
}


# --------------------------------------------------------------------------- Datenbank
_db_lock = threading.Lock()


class _DB:
    def __enter__(self):
        _db_lock.acquire()
        try:
            self.con = sqlite3.connect(DB_FILE, timeout=10)
            self.con.row_factory = sqlite3.Row
        except Exception:
            _db_lock.release()
            raise
        return self.con

    def __exit__(self, exc_type, *_):
        try:
            if exc_type is None:
                self.con.commit()
            else:
                self.con.rollback()
        finally:
            self.con.close()
            _db_lock.release()


def init_db():
    if not os.path.exists(DB_FILE) and os.path.exists(LEGACY_DB_FILE) \
            and os.path.abspath(LEGACY_DB_FILE) != os.path.abspath(DB_FILE):
        try:
            import shutil
            shutil.copy2(LEGACY_DB_FILE, DB_FILE)      # alte Datenbank einmalig übernehmen
        except OSError:
            pass
    with _DB() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key            TEXT PRIMARY KEY,
                note           TEXT NOT NULL DEFAULT '',
                duration_label TEXT NOT NULL DEFAULT '',
                created_at     INTEGER NOT NULL,
                expires_at     INTEGER,
                status         TEXT NOT NULL DEFAULT 'active',
                last_check     INTEGER,
                check_count    INTEGER NOT NULL DEFAULT 0
            )""")


# --------------------------------------------------------------------------- Live-Änderungen
# Jede Änderung erhöht die Revision. App und Dashboard warten per Long-Polling darauf
# und bekommen Änderungen dadurch sofort mit.
_rev = 0
_rev_cond = threading.Condition()


def bump_revision():
    global _rev
    with _rev_cond:
        _rev += 1
        _rev_cond.notify_all()


def current_revision():
    with _rev_cond:
        return _rev


def wait_for_change(rev, timeout):
    with _rev_cond:
        _rev_cond.wait_for(lambda: _rev != rev, timeout=max(0.0, timeout))
        return _rev


# --------------------------------------------------------------------------- Zeit
def now():
    return int(time.time())


def ts_to_dt(ts):
    return EPOCH + timedelta(seconds=int(ts))   # funktioniert auch unter Windows bis Jahr 9999


def iso(ts):
    return None if ts is None else ts_to_dt(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_months(ts, months):
    dt = ts_to_dt(ts)
    total = dt.year * 12 + (dt.month - 1) + months
    year, month0 = divmod(total, 12)
    if year > 9999:
        return None
    day = min(dt.day, calendar.monthrange(year, month0 + 1)[1])
    return int((dt.replace(year=year, month=month0 + 1, day=day) - EPOCH).total_seconds())


def parse_amount(value):
    if isinstance(value, bool):
        raise ValueError("Ungültige Dauer.")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("Die Dauer muss eine ganze Zahl sein.")
        value = int(value)
    try:
        amount = int(str(value).strip())
    except ValueError:
        raise ValueError("Die Dauer muss eine ganze Zahl sein.") from None
    if amount < 1:
        raise ValueError("Die Dauer muss mindestens 1 sein.")
    return amount


def compute_expiry(start, amount, unit):
    """Gibt den Ablauf-Zeitstempel zurück – oder None (= unbegrenzt)."""
    if unit == "lifetime":
        return None
    if unit in UNIT_SECONDS:
        ts = start + amount * UNIT_SECONDS[unit]
    elif unit == "months":
        ts = add_months(start, amount)
    elif unit == "years":
        ts = add_months(start, amount * 12)
    else:
        raise ValueError("Unbekannte Zeiteinheit.")
    if ts is None or ts > MAX_TS:
        return None
    return ts


def duration_label(amount, unit):
    if unit == "lifetime":
        return "Lifetime"
    one, many = UNIT_LABELS[unit]
    return f"{amount:,}".replace(",", ".") + " " + (one if amount == 1 else many)


# --------------------------------------------------------------------------- Logik
def generate_key():
    return "ACC-" + "-".join("".join(secrets.choice(KEY_ALPHABET) for _ in range(5)) for _ in range(4))


def normalize_key(key):
    return "".join(str(key or "").split()).upper()


def effective_status(row, t):
    if row["status"] != "active":
        return row["status"]
    if row["expires_at"] is not None and row["expires_at"] <= t:
        return "expired"
    return "active"


def serialize(row, t=None):
    t = now() if t is None else t
    exp = row["expires_at"]
    return {
        "key": row["key"],
        "note": row["note"],
        "duration_label": row["duration_label"],
        "status": row["status"],
        "effective_status": effective_status(row, t),
        "created_at": row["created_at"],
        "expires_at": exp,
        "expires_at_iso": iso(exp),
        "lifetime": exp is None,
        "remaining_seconds": None if exp is None else max(0, exp - t),
        "last_check": row["last_check"],
        "check_count": row["check_count"],
    }


def _parse_duration(body):
    if "unit" not in body and "duration_seconds" in body:      # altes Format
        unit, amount = "seconds", body["duration_seconds"]
    else:
        unit, amount = str(body.get("unit") or "").lower(), body.get("amount")
    if unit == "lifetime":
        return None, "lifetime"
    if unit not in UNIT_LABELS:
        raise ValueError("Unbekannte Zeiteinheit.")
    return parse_amount(amount), unit


def _get(con, key):
    return con.execute("SELECT * FROM license_keys WHERE key = ?", (key,)).fetchone()


def list_licenses():
    with _DB() as con:
        rows = con.execute("SELECT * FROM license_keys ORDER BY created_at DESC, rowid DESC").fetchall()
    t = now()
    return [serialize(r, t) for r in rows]


def create_license(body):
    amount, unit = _parse_duration(body)
    t = now()
    expires = None if unit == "lifetime" else compute_expiry(t, amount, unit)
    label = duration_label(amount, unit)
    if unit != "lifetime" and expires is None:
        label += " (unbegrenzt)"
    note = str(body.get("note") or "").strip()[:160]
    with _DB() as con:
        for _ in range(20):
            key = generate_key()
            try:
                con.execute(
                    "INSERT INTO license_keys (key, note, duration_label, created_at, expires_at) VALUES (?,?,?,?,?)",
                    (key, note, label, t, expires))
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError("Konnte keinen eindeutigen Schlüssel erzeugen.")
        row = _get(con, key)
    bump_revision()
    return serialize(row, t)


def apply_action(key, action, body):
    result = _apply_action(key, action, body)
    if result is not None:
        bump_revision()
    return result


def _apply_action(key, action, body):
    key = normalize_key(key)
    with _DB() as con:
        row = _get(con, key)
        if row is None:
            return None
        if action == "delete":
            con.execute("DELETE FROM license_keys WHERE key = ?", (key,))
            return {"deleted": True, "key": key}
        if action in STATUS_ACTIONS:
            con.execute("UPDATE license_keys SET status = ? WHERE key = ?", (STATUS_ACTIONS[action], key))
        elif action == "extend":
            amount, unit = _parse_duration(body)
            if unit == "lifetime" or row["expires_at"] is None:
                new_exp = None
            else:
                new_exp = compute_expiry(max(now(), row["expires_at"]), amount, unit)
            con.execute("UPDATE license_keys SET expires_at = ? WHERE key = ?", (new_exp, key))
        elif action == "note":
            con.execute("UPDATE license_keys SET note = ? WHERE key = ?",
                        (str(body.get("note") or "").strip()[:160], key))
        else:
            raise ValueError("Unbekannte Aktion.")
        row = _get(con, key)
    return {"license": serialize(row)}


def validate(key):
    key = normalize_key(key)
    if not key:
        return {"valid": False, "status": "empty", "message": "Bitte gib einen Lizenzschlüssel ein."}
    t = now()
    with _DB() as con:
        if _get(con, key) is None:
            return {"valid": False, "status": "unknown", "message": "Dieser Lizenzschlüssel existiert nicht."}
        con.execute("UPDATE license_keys SET last_check = ?, check_count = check_count + 1 WHERE key = ?", (t, key))
        row = _get(con, key)
    bump_revision()
    data = serialize(row, t)
    state = data["effective_status"]
    data["valid"] = state == "active"
    data["message"] = "Lizenz gültig." if data["valid"] else STATUS_MESSAGES.get(state, "Lizenz ungültig.")
    return data


def license_state(key):
    """Aktueller Zustand eines Keys – ohne die Prüfstatistik zu verändern (für die Live-Verbindung)."""
    key = normalize_key(key)
    with _DB() as con:
        row = _get(con, key) if key else None
    if row is None:
        return {"valid": False, "status": "unknown", "effective_status": "unknown", "key": key,
                "message": "Dieser Lizenzschlüssel wurde gelöscht oder existiert nicht."}
    data = serialize(row)
    state = data["effective_status"]
    data["valid"] = state == "active"
    data["message"] = "Lizenz gültig." if data["valid"] else STATUS_MESSAGES.get(state, "Lizenz ungültig.")
    return data


def watch_license(key, rev, sid):
    """Long-Poll: kehrt zurück, sobald sich etwas ändert, der Key abläuft oder nach 25 s."""
    if sid == SERVER_ID and rev is not None:
        state = license_state(key)
        timeout = LONG_POLL_SECONDS
        if state["valid"] and state.get("expires_at") is not None:
            timeout = min(timeout, state["expires_at"] - time.time() + 0.3)
        wait_for_change(rev, timeout)
    rev_now = current_revision()                 # Revision VOR dem Lesen merken -> nichts geht verloren
    data = license_state(key)
    data.update(rev=rev_now, sid=SERVER_ID, server_time=now())
    return data


def wait_events(rev, sid):
    if sid == SERVER_ID and rev is not None:
        wait_for_change(rev, LONG_POLL_SECONDS)
    return {"rev": current_revision(), "sid": SERVER_ID}


# --------------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "ACCLicense/2.0"

    def log_message(self, *_):
        pass

    def _send(self, code, payload=None, body=None, ctype="application/json; charset=utf-8"):
        data = body if body is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, message):
        self._send(code, {"error": message})

    def _host_ok(self):
        # Schutz gegen DNS-Rebinding: nur echte localhost-Aufrufe zulassen
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def _json_body(self):
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise ValueError("Content-Type muss application/json sein.")
        length = int(self.headers.get("Content-Length") or 0)
        if length > 65536:
            raise ValueError("Anfrage zu groß.")
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            raise ValueError("Ungültiges JSON.") from None
        if not isinstance(data, dict):
            raise ValueError("Ungültige Anfrage.")
        return data

    def do_GET(self):
        if not self._host_ok():
            return self._error(403, "Zugriff verweigert.")
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(_resource(DASHBOARD_FILE), "rb") as f:
                    html = f.read()
            except OSError:
                return self._error(404, f"{DASHBOARD_FILE} wurde nicht gefunden.")
            return self._send(200, body=html, ctype="text/html; charset=utf-8")
        if path == "/api/health":
            return self._send(200, {"ok": True, "service": "acc-license"})
        if path == "/api/licenses":
            return self._send(200, {"licenses": list_licenses(), "server_time": now(), "db_file": DB_FILE})
        if path in ("/api/watch", "/api/events"):
            query = parse_qs(urlparse(self.path).query)
            arg = lambda name: (query.get(name) or [""])[0]
            try:
                rev = int(arg("rev")) if arg("rev") else None
            except ValueError:
                rev = None
            if path == "/api/watch":
                return self._send(200, watch_license(arg("key"), rev, arg("sid")))
            return self._send(200, wait_events(rev, arg("sid")))
        self._error(404, "Nicht gefunden.")

    def do_POST(self):
        if not self._host_ok():
            return self._error(403, "Zugriff verweigert.")
        path = urlparse(self.path).path
        try:
            body = self._json_body()
            if path == "/api/validate":
                return self._send(200, validate(body.get("key")))
            if path == "/api/licenses":
                return self._send(201, {"license": create_license(body)})
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "licenses" and parts[3] == "action":
                result = apply_action(unquote(parts[2]), str(body.get("action") or ""), body)
                if result is None:
                    return self._error(404, "Lizenzschlüssel nicht gefunden.")
                return self._send(200, result)
            self._error(404, "Nicht gefunden.")
        except ValueError as exc:
            self._error(400, str(exc) or "Ungültige Anfrage.")
        except Exception as exc:  # noqa: BLE001
            self._error(500, f"Serverfehler: {exc}")


class _Server(ThreadingHTTPServer):
    # Windows: SO_REUSEADDR würde doppelte Belegung erlauben -> exklusiv binden.
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True

    def server_bind(self):
        import socket
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


_server = None
_server_lock = threading.Lock()


def is_running(timeout=1.5):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://{HOST}:{PORT}/api/health", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8")).get("service") == "acc-license"
    except Exception:
        return False


def start_server():
    """Startet den Server im Hintergrund. Gibt None zurück, wenn schon ein anderer Prozess ihn betreibt."""
    global _server
    with _server_lock:
        if _server is not None:
            return _server
        init_db()
        try:
            server = _Server((HOST, PORT), Handler)
        except OSError:
            if is_running():
                return None
            raise RuntimeError(f"Port {PORT} ist von einem anderen Programm belegt.") from None
        threading.Thread(target=server.serve_forever, daemon=True, name="license-server").start()
        _server = server
        return server


if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}/"
    srv = start_server()
    if srv is None:
        print(f"Lizenzserver läuft bereits: {url}")
        webbrowser.open(url)
        sys.exit(0)
    print(f"Lizenzserver läuft: {url}\nDatenbank: {DB_FILE}\nBeenden mit Strg+C.")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()
