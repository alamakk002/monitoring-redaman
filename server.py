import json
import os
import re
import socket
import sqlite3
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from netmiko import ConnectHandler
from starlette.middleware.base import BaseHTTPMiddleware


def get_lan_ip() -> str:
    """Perkirakan IP LAN utama tanpa mengirim paket (UDP connect)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def resource_dir() -> Path:
    """Folder aset (index.html, vendor). Saat dibungkus PyInstaller, ada di _MEIPASS."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    """Folder data yang bisa ditulis.

    Saat dijalankan sebagai .exe, jangan simpan database di folder Program Files
    (biasanya tidak bisa ditulis). Gunakan folder data pengguna.
    """
    override = os.getenv("OPTIPULSE_DATA_DIR")
    if override:
        folder = Path(override)
    elif getattr(sys, "frozen", False):
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
        folder = Path(base) / "OptiPulse NOC"
    else:
        folder = Path(__file__).resolve().parent

    folder.mkdir(parents=True, exist_ok=True)
    return folder


BASE_DIR = resource_dir()
INDEX_FILE = BASE_DIR / "index.html"
DATA_DIR = data_dir()


def load_env_file() -> None:
    """Baca optipulse.env di samping .exe (atau folder aplikasi) bila ada.

    Memudahkan pemakaian .exe tanpa mengatur environment variable Windows.
    Nilai yang sudah ada di environment tidak ditimpa.
    """
    if getattr(sys, "frozen", False):
        primary = Path(sys.executable).resolve().parent / "optipulse.env"
    else:
        primary = Path(__file__).resolve().parent / "optipulse.env"

    for file in (primary, DATA_DIR / "optipulse.env"):
        if not file.is_file():
            continue
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file()
DB_FILE = Path(os.getenv("OPTIPULSE_DB", str(DATA_DIR / "optipulse.db")))


def open_browser_later(port: str) -> None:
    """Buka browser otomatis saat dijalankan sebagai .exe (kecuali dimatikan)."""
    if not getattr(sys, "frozen", False):
        return
    if os.getenv("OPTIPULSE_OPEN_BROWSER", "1") == "0":
        return

    import threading
    import time
    import webbrowser

    def _open():
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = db_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                clients TEXT,
                alerts TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@asynccontextmanager
async def lifespan(_app):
    # Banner dicetak saat server benar-benar siap menerima koneksi.
    port = os.getenv("PORT", "5000")
    lan_ip = get_lan_ip()
    init_db()
    print("=" * 64)
    print("  OptiPulse NOC siap dijalankan")
    print(f"  Di laptop ini      : http://localhost:{port}")
    print(f"  Dari HP / laptop   : http://{lan_ip}:{port}")
    print(f"  Penyimpanan data   : {DB_FILE}")
    print("  Pastikan izin firewall Windows aktif untuk jaringan Private.")
    if getattr(sys, "frozen", False):
        print("  Hentikan aplikasi  : tutup jendela ini")
    else:
        print("  Hentikan server    : Ctrl + C")
    print("=" * 64, flush=True)
    open_browser_later(port)
    yield


app = FastAPI(title="OptiPulse NOC", version="1.5.0", lifespan=lifespan)

# Aset offline (Tailwind & Chart.js) disajikan dari folder yang sama.
app.mount(
    "/vendor",
    StaticFiles(directory=BASE_DIR / "vendor", check_dir=False),
    name="vendor",
)

# Origin yang diizinkan. Default "*" agar bisa dibuka dari GitHub Pages / HP.
# Contoh: OPTIPULSE_ALLOWED_ORIGINS="https://alamakk002.github.io,http://localhost:8000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("OPTIPULSE_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
    # Wajib untuk Chrome Local Network Access (Private Network Access).
    # Tanpa ini, preflight dengan Access-Control-Request-Private-Network
    # ditolak 400 "Disallowed CORS private-network".
    allow_private_network=True,
)


class PrivateNetworkAccessMiddleware(BaseHTTPMiddleware):
    """Izinkan browser publik mengakses API di jaringan lokal (Chrome PNA).

    Chrome tetap dapat meminta izin pengguna untuk akses Local Network Access,
    namun header ini diperlukan agar preflight OPTIONS tidak ditolak.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(PrivateNetworkAccessMiddleware)


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


# Konfigurasi akses OLT.
# Urutan prioritas: pengaturan yang disimpan dari dashboard > optipulse.env /
# environment variable Windows. Dengan begitu teknisi bisa mengisi kredensial
# lewat browser tanpa mengedit file.
OLT_SETTING_KEY = "olt_config"
OLT_DEFAULT_COMMAND = "show gpon onu detail-info gpon-olt_1/1/1"


def olt_env_config() -> dict:
    """Nilai awal dari optipulse.env / environment variable."""
    return {
        "host": env("OLT_HOST", "").strip(),
        "port": int(env("OLT_PORT", "23") or 23),
        "username": env("OLT_USERNAME", "").strip(),
        "password": env("OLT_PASSWORD", ""),
        "device_type": env("OLT_DEVICE_TYPE", "zte_zxros").strip() or "zte_zxros",
        "command": env("OLT_COMMAND", OLT_DEFAULT_COMMAND).strip() or OLT_DEFAULT_COMMAND,
        "timeout": int(env("OLT_TIMEOUT", "10") or 10),
    }


def get_setting(key: str):
    conn = db_connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def set_setting(key: str, value) -> None:
    conn = db_connect()
    try:
        if value is None:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        else:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def saved_olt_config():
    """Konfigurasi OLT yang terakhir disimpan dari dashboard (bila ada)."""
    data = parse_json_or_none(get_setting(OLT_SETTING_KEY))
    return data if isinstance(data, dict) else None


def current_olt_config() -> dict:
    """Gabungan nilai tersimpan dan nilai dari file .env."""
    cfg = olt_env_config()
    saved = saved_olt_config()
    if not saved:
        return cfg

    for key in ("host", "username", "device_type", "command"):
        value = saved.get(key)
        if isinstance(value, str) and value.strip():
            cfg[key] = value.strip()

    if isinstance(saved.get("password"), str) and saved["password"]:
        cfg["password"] = saved["password"]

    for key in ("port", "timeout"):
        try:
            if saved.get(key):
                cfg[key] = int(saved[key])
        except (TypeError, ValueError):
            pass

    return cfg


def public_olt_config() -> dict:
    """Konfigurasi aman untuk dikirim ke browser (tanpa password)."""
    cfg = current_olt_config()
    saved = saved_olt_config()
    if saved:
        source = "dashboard"
    elif cfg["host"]:
        source = "optipulse.env"
    else:
        source = "belum diatur"
    return {
        "host": cfg["host"],
        "port": cfg["port"],
        "username": cfg["username"],
        "device_type": cfg["device_type"],
        "command": cfg["command"],
        "timeout": cfg["timeout"],
        "passwordSet": bool(cfg["password"]),
        "configured": bool(cfg["host"] and cfg["username"]),
        "source": source,
        "defaultCommand": OLT_DEFAULT_COMMAND,
    }


def build_olt_device(cfg: dict) -> dict:
    return {
        "device_type": cfg["device_type"],
        "host": cfg["host"],
        "username": cfg["username"],
        "password": cfg["password"],
        "port": int(cfg["port"]),
        "timeout": int(cfg["timeout"]),
        "conn_timeout": int(cfg["timeout"]),
        "fast_cli": False,
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def serve_app():
    """Sajikan UI dan API dari origin yang sama.

    Dengan begitu browser tidak perlu CORS/PNA dan aplikasi bisa dibuka
    dari HP/laptop lain lewat alamat IP server.
    """
    try:
        html = INDEX_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>index.html tidak ditemukan</h1>"
            "<p>Letakkan server.py dan index.html di folder yang sama.</p>",
            status_code=500,
        )

    # Beri tahu frontend bahwa API berada di origin yang sama.
    marker = "  <script>window.OPTIPULSE_SAME_ORIGIN = true;</script>\n</head>"
    if "</head>" in html:
        html = html.replace("</head>", marker, 1)

    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
        },
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Favicon utama memakai SVG inline di index.html.
    return Response(status_code=204)


@app.get("/health")
def health():
    """Endpoint ringan untuk mengecek backend hidup tanpa menyentuh OLT."""
    return {"status": "ok", "service": "optipulse-noc-api"}


# ---------------------------------------------------------------------------
# Pengaturan OLT dari dashboard (tanpa mengedit optipulse.env)
# ---------------------------------------------------------------------------


def normalize_olt_payload(payload: dict) -> dict:
    """Validasi isian form Pengaturan OLT."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload harus berupa objek JSON")

    host = str(payload.get("host") or "").strip()
    username = str(payload.get("username") or "").strip()
    if not host:
        raise HTTPException(status_code=400, detail="Host / IP OLT wajib diisi")
    if not username:
        raise HTTPException(status_code=400, detail="Username OLT wajib diisi")

    try:
        port = int(payload.get("port") or 23)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Port harus berupa angka")
    if not 1 <= port <= 65535:
        raise HTTPException(status_code=400, detail="Port harus di antara 1 dan 65535")

    try:
        timeout = int(payload.get("timeout") or 10)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Timeout harus berupa angka")
    if not 1 <= timeout <= 60:
        raise HTTPException(status_code=400, detail="Timeout harus di antara 1 dan 60 detik")

    password = payload.get("password")
    password = password if isinstance(password, str) else ""

    device_type = str(payload.get("device_type") or "zte_zxros").strip() or "zte_zxros"
    command = str(payload.get("command") or OLT_DEFAULT_COMMAND).strip() or OLT_DEFAULT_COMMAND

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "device_type": device_type,
        "command": command,
        "timeout": timeout,
    }


@app.get("/api/olt/config")
def get_olt_config():
    """Konfigurasi OLT aktif. Password tidak pernah dikirim ke browser."""
    return public_olt_config()


@app.put("/api/olt/config")
def put_olt_config(payload: dict = Body(...)):
    """Simpan konfigurasi OLT dari dashboard.

    Password kosong berarti mempertahankan password yang sudah tersimpan.
    """
    cfg = normalize_olt_payload(payload)
    previous = saved_olt_config() or {}
    password = cfg["password"] or previous.get("password") or current_olt_config()["password"]

    stored = {
        "host": cfg["host"],
        "port": cfg["port"],
        "username": cfg["username"],
        "device_type": cfg["device_type"],
        "command": cfg["command"],
        "timeout": cfg["timeout"],
    }
    if password:
        stored["password"] = password

    set_setting(OLT_SETTING_KEY, json.dumps(stored, ensure_ascii=False))
    return {"ok": True, "config": public_olt_config()}


@app.delete("/api/olt/config")
def delete_olt_config():
    """Hapus konfigurasi dari dashboard dan kembali ke optipulse.env."""
    set_setting(OLT_SETTING_KEY, None)
    return {"ok": True, "config": public_olt_config()}


def friendly_olt_error(error: Exception, timeout: int) -> str:
    """Ubah error netmiko menjadi pesan yang bisa ditindaklanjuti teknisi."""
    name = type(error).__name__
    detail = str(error).strip() or name
    if "Authentication" in name:
        return "Username atau password ditolak oleh OLT."
    if "Timeout" in name:
        return (
            f"OLT tidak merespons dalam {timeout} detik. "
            "Periksa IP, port (23 Telnet / 22 SSH), dan jaringan manajemen."
        )
    if "TCP connection" in detail:
        return (
            "Koneksi TCP ke OLT gagal. Periksa IP, port, dan firewall. "
            "Pastikan PC server berada di jaringan manajemen OLT."
        )
    return f"Gagal terhubung ke OLT: {detail[:220]}"


@app.post("/api/olt/config/test")
def test_olt_config(payload: dict = Body(default={})):
    """Coba hubungkan ke OLT memakai isian form (bisa sebelum disimpan)."""
    import time

    cfg = current_olt_config()
    if isinstance(payload, dict):
        for key in ("host", "username", "device_type", "command"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                cfg[key] = value.strip()
        password = payload.get("password")
        if isinstance(password, str) and password:
            cfg["password"] = password
        for key in ("port", "timeout"):
            try:
                if payload.get(key):
                    cfg[key] = int(payload[key])
            except (TypeError, ValueError):
                pass

    if not cfg["host"]:
        return {"ok": False, "message": "Host / IP OLT belum diisi."}
    if not cfg["username"]:
        return {"ok": False, "message": "Username OLT belum diisi."}
    if not cfg["password"]:
        return {"ok": False, "message": "Password OLT belum diisi."}

    started = time.monotonic()
    connection = None
    try:
        connection = ConnectHandler(**build_olt_device(cfg))
        prompt = connection.find_prompt()
        snippet = ""
        if payload.get("runCommand"):
            snippet = connection.send_command(cfg["command"], read_timeout=cfg["timeout"] + 5)
            snippet = snippet[:1200]
        duration = int((time.monotonic() - started) * 1000)
        return {
            "ok": True,
            "message": "OLT merespons dan kredensial diterima.",
            "prompt": prompt,
            "durationMs": duration,
            "output": snippet,
            "config": public_olt_config(),
        }
    except Exception as error:  # noqa: BLE001 - tampilkan pesan ramah ke pengguna
        duration = int((time.monotonic() - started) * 1000)
        return {
            "ok": False,
            "message": friendly_olt_error(error, cfg["timeout"]),
            "error": (str(error).strip() or type(error).__name__)[:400],
            "durationMs": duration,
        }
    finally:
        if connection is not None:
            try:
                connection.disconnect()
            except Exception:
                pass


def parse_json_or_none(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


@app.get("/api/state")
def get_state():
    """Ambil data klien & log yang tersimpan di server (dipakai semua perangkat)."""
    conn = db_connect()
    try:
        row = conn.execute(
            "SELECT clients, alerts, updated_at FROM app_state WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return {"clients": None, "alerts": None, "updatedAt": None}

    return {
        "clients": parse_json_or_none(row[0]),
        "alerts": parse_json_or_none(row[1]),
        "updatedAt": row[2],
    }


@app.put("/api/state")
def put_state(payload: dict = Body(...)):
    """Simpan data dari perangkat mana pun.

    Field yang tidak dikirim (mis. clients saat mode LIVE) dibiarkan apa adanya.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload harus berupa objek JSON")

    if "clients" in payload:
        clients = payload["clients"]
        if (
            not isinstance(clients, list)
            or len(clients) > 5000
            or any(not isinstance(item, dict) for item in clients)
        ):
            raise HTTPException(
                status_code=400,
                detail="clients harus berupa array objek (maksimal 5000)",
            )
        clients_json = json.dumps(clients, ensure_ascii=False)
    else:
        clients_json = None

    if "alerts" in payload:
        alerts = payload["alerts"]
        if (
            not isinstance(alerts, list)
            or len(alerts) > 500
            or any(not isinstance(item, dict) for item in alerts)
        ):
            raise HTTPException(
                status_code=400,
                detail="alerts harus berupa array objek (maksimal 500)",
            )
        alerts_json = json.dumps(alerts, ensure_ascii=False)
    else:
        alerts_json = None

    updated_at = now_iso()
    conn = db_connect()
    try:
        conn.execute(
            """
            INSERT INTO app_state (id, clients, alerts, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                clients = COALESCE(excluded.clients, app_state.clients),
                alerts = COALESCE(excluded.alerts, app_state.alerts),
                updated_at = excluded.updated_at
            """,
            (clients_json, alerts_json, updated_at),
        )
        conn.commit()
    finally:
        conn.close()

    return {"ok": True, "updatedAt": updated_at}


RX_LINE_RE = re.compile(
    r"rx\s*(?:power)?[^-\d]{0,24}(?P<rx>-?\d{1,2}(?:\.\d{1,2})?)", re.IGNORECASE
)


def parse_olt_clients(output: str) -> list:
    """Ambil baris yang memuat nilai Rx dari keluaran OLT.

    Parser ini sengaja dibuat umum. Sesuaikan regex/OLT_COMMAND bila format
    OLT Anda berbeda (mis. Huawei, FiberHome, atau ZTE dengan nama kolom lain).
    """
    clients = []
    for line in (output or "").splitlines():
        match = RX_LINE_RE.search(line)
        if not match:
            continue
        try:
            rx = float(match.group("rx"))
        except (TypeError, ValueError):
            continue
        if not -60.0 < rx < 10.0:
            continue
        index = len(clients) + 1
        clients.append(
            {
                "id": f"CLI-OLT-{index:04d}",
                "name": f"ONU Port {index}",
                "package": "-",
                "odp": "-",
                "port": index,
                "ip": "-",
                "sn": "-",
                "rxPower": rx,
                "latency": 0,
            }
        )
    return clients


@app.get("/api/clients")
def get_olt_clients():
    cfg = current_olt_config()
    if not cfg["host"] or not cfg["username"]:
        return {
            "error": "OLT belum dikonfigurasi. Buka menu Pengaturan OLT di dashboard.",
            "status": "OLT_NOT_CONFIGURED",
        }
    if not cfg["password"]:
        return {
            "error": "Password OLT belum diisi. Lengkapi lewat menu Pengaturan OLT.",
            "status": "OLT_NOT_CONFIGURED",
        }

    connection = None
    try:
        connection = ConnectHandler(**build_olt_device(cfg))
        output = connection.send_command(cfg["command"], read_timeout=cfg["timeout"] + 5)
        clients = parse_olt_clients(output)
        if not clients:
            return {
                "error": (
                    "OLT terhubung, tetapi tidak ada nilai Rx yang terbaca. "
                    "Sesuaikan OLT_COMMAND / device type dengan merek OLT Anda."
                ),
                "status": "OLT_PARSE_EMPTY",
                "outputSample": (output or "")[:800],
            }
        return clients
    except Exception as error:  # noqa: BLE001 - status dikirim ke UI
        return {
            "error": friendly_olt_error(error, cfg["timeout"]),
            "status": "OLT_UNREACHABLE",
        }
    finally:
        if connection is not None:
            try:
                connection.disconnect()
            except Exception:
                pass


def is_our_server_running(port: str) -> bool:
    """Cek apakah instance OptiPulse NOC sudah melayani port ini."""
    import urllib.request

    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/health", timeout=1.5
        ) as response:
            if response.status != 200:
                return False
            data = json.loads(response.read().decode("utf-8"))
        return isinstance(data, dict) and data.get("service") == "optipulse-noc-api"
    except Exception:
        return False


def port_in_use(port: int) -> bool:
    """Cek apakah ada aplikasi yang menerima koneksi di port ini."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1.0)
    try:
        return probe.connect_ex(("127.0.0.1", port)) == 0
    finally:
        probe.close()


def pause_if_frozen() -> None:
    """Beri kesempatan membaca pesan error sebelum jendela .exe tertutup."""
    if not getattr(sys, "frozen", False):
        return
    try:
        input("Tekan Enter untuk menutup jendela ini...")
    except EOFError:
        pass


def run_from_cli() -> int:
    import time
    import webbrowser

    import uvicorn

    port = env("PORT", "5000")
    default_open = "1" if getattr(sys, "frozen", False) else "0"
    open_browser = os.getenv("OPTIPULSE_OPEN_BROWSER", default_open) != "0"

    # Klik ganda saat aplikasi sudah berjalan: jangan gagal bind, cukup buka browser.
    if is_our_server_running(port):
        print(f"OptiPulse NOC sudah berjalan di http://localhost:{port}")
        if open_browser:
            print("Membuka browser...")
            webbrowser.open(f"http://localhost:{port}")
        else:
            print("Tidak perlu dijalankan lagi.")
        time.sleep(1.2)
        return 0

    if port_in_use(int(port)):
        print()
        print("=" * 64)
        print("  OptiPulse NOC gagal dijalankan.")
        print(f"  Port {port} sedang dipakai aplikasi lain.")
        print("  Tutup aplikasi tersebut, atau ubah PORT di optipulse.env.")
        print("=" * 64)
        pause_if_frozen()
        return 1

    try:
        # host 0.0.0.0 agar bisa diakses dari perangkat lain di WiFi kantor
        uvicorn.run(app, host=env("HOST", "0.0.0.0"), port=int(port))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            return 0
        print()
        print("=" * 64)
        if is_our_server_running(port):
            print("  OptiPulse NOC sudah berjalan.")
            print(f"  Buka http://localhost:{port}")
            if open_browser:
                webbrowser.open(f"http://localhost:{port}")
        else:
            print("  OptiPulse NOC gagal dijalankan.")
            print(f"  Port {port} kemungkinan dipakai aplikasi lain.")
            print("  Tutup aplikasi tersebut, atau ubah PORT di optipulse.env.")
        print("=" * 64)
        pause_if_frozen()
        return code
    except Exception as exc:  # noqa: BLE001 - tampilkan pesan ramah ke pengguna
        print(f"OptiPulse NOC gagal dijalankan: {exc}")
        pause_if_frozen()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run_from_cli())
