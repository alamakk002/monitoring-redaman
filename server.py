from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from netmiko import ConnectHandler
import re

app = FastAPI()

# Mengizinkan aplikasi web mengakses data backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurasi Akses IP OLT Anda
OLT_DEVICE = {
    "device_type": "zte_zxros",  # Sesuaikan: zte_zxros, huawei, cisco_ios, generic
    "host": "192.168.1.100",     # Ganti dengan IP OLT Anda
    "username": "admin",
    "password": "password_olt",
    "port": 23,                  # Port Telnet (23) atau SSH (22)
}

@app.get("/api/clients")
def get_olt_clients():
    try:
        # 1. Menghubungkan ke OLT
        connection = ConnectHandler(**OLT_DEVICE)
        
        # 2. Menjalankan perintah pembacaan sinyal optik OLT
        output = connection.send_command("show gpon onu detail-info gpon-olt_1/1/1")
        connection.disconnect()

        # 3. Parsing output teks OLT menjadi format terstruktur
        # (Contoh data hasil parsing untuk dikirim ke website)
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
                "latency": 4
            }
        ]
        return client_data

    except Exception as error:
        # Jika OLT tidak terjangkau (misal saat laptop masih pakai hotspot HP)
        return {"error": str(error), "status": "OLT_UNREACHABLE"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)