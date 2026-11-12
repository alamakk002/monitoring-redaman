import json
import os
import socket
import sqlite3
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


BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
DB_FILE = Path(os.getenv("OPTIPULSE_DB", str(BASE_DIR / "optipulse.db")))


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
    print("  Hentikan server    : Ctrl + C")
    print("=" * 64, flush=True)
    yield


app = FastAPI(title="OptiPulse NOC", version="1.3.0", lifespan=lifespan)

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


if __name__ == "__main__":
    import uvicorn

    # host 0.0.0.0 agar bisa diakses dari perangkat lain di WiFi kantor
    uvicorn.run(app, host=env("HOST", "0.0.0.0"), port=int(env("PORT", "5000")))
