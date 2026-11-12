import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
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


@asynccontextmanager
async def lifespan(_app):
    # Banner dicetak saat server benar-benar siap menerima koneksi.
    port = os.getenv("PORT", "5000")
    lan_ip = get_lan_ip()
    print("=" * 64)
    print("  OptiPulse NOC siap dijalankan")
    print(f"  Di laptop ini      : http://localhost:{port}")
    print(f"  Dari HP / laptop   : http://{lan_ip}:{port}")
    print("  Pastikan izin firewall Windows aktif untuk jaringan Private.")
    print("  Hentikan server    : Ctrl + C")
    print("=" * 64, flush=True)
    yield


app = FastAPI(title="OptiPulse NOC", version="1.2.0", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

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
    allow_methods=["GET", "OPTIONS"],
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
