import os
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from netmiko import ConnectHandler
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="OptiPulse NOC API", version="1.1.0")

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

    # host 0.0.0.0 agar bisa diakses dari HP di WiFi yang sama
    uvicorn.run(app, host="0.0.0.0", port=int(env("PORT", "5000")))
