import json
import os
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


app = FastAPI(title="OptiPulse NOC", version="1.4.1", lifespan=lifespan)

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
    allow_methods=["GET", "PUT", "OPTIONS"],
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


# Konfigurasi akses OLT. Semua nilai dapat diatur lewat environment variable
# sehingga password tidak perlu ditulis di dalam kode.
OLT_DEVICE = {
    "device_type": env("OLT_DEVICE_TYPE", "zte_zxros"),  # zte_zxros, huawei, cisco_ios, generic
    "host": env("OLT_HOST", "192.168.1.100"),
    "username": env("OLT_USERNAME", "admin"),
    "password": env("OLT_PASSWORD", "password_olt"),
    "port": int(env("OLT_PORT", "23")),                  # 23 (Telnet) atau 22 (SSH)
    "timeout": int(env("OLT_TIMEOUT", "10")),
    "fast_cli": False,
}

OLT_COMMAND = env("OLT_COMMAND", "show gpon onu detail-info gpon-olt_1/1/1")


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


@app.get("/api/clients")
def get_olt_clients():
    try:
        # 1. Menghubungkan ke OLT
        connection = ConnectHandler(**OLT_DEVICE)

        # 2. Menjalankan perintah pembacaan sinyal optik OLT
        output = connection.send_command(OLT_COMMAND)
        connection.disconnect()

        # 3. Parsing output teks OLT menjadi format terstruktur.
        #    Ganti contoh data di bawah dengan regex sesuai keluaran OLT Anda.
        #    Contoh: rx = re.search(r"Rx\s*:\s*(-?\d+\.\d+)", output)
        client_data = [
            {
                "id": "CLI-2001",
                "name": "Pelanggan Port 1",
                "package": "Home 50 Mbps",
                "odp": "ODP-KBR-01",
                "port": 1,
                "ip": "192.168.10.51",
                "sn": "ZTEG12345678",
                "rxPower": -19.45,  # Nilai redaman aktual hasil parsing regex
                "status": "OPTIMAL",
                "latency": 4,
            }
        ]
        return client_data

    except Exception as error:
        # Jika OLT tidak terjangkau (misal laptop masih memakai hotspot HP)
        return {"error": str(error), "status": "OLT_UNREACHABLE"}


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
