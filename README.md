# ⚡ OptiPulse NOC - Monitoring Klien & Kalkulator Redaman FTTH

Aplikasi sistem pemantauan kualitas jaringan FTTH (Fiber to the Home) dan kalkulator redaman optik (*Optical Power Budget*) berbasis standar ITU-T G.984 GPON.

🌐 **Demo Live Website:** [https://alamakk002.github.io/monitoring-redaman/](https://alamakk002.github.io/monitoring-redaman/)

---

## 📌 Fitur Utama

1. **Dashboard Monitoring Klien:**
   - Pemantauan status Rx Power ONT (Optimal, Normal, Waspada, Kritis, LOS).
   - Pengelompokan status sinyal, uji latency (ICMP ping), dan grafik tren 24 jam.
   - Pilihan mode: **"Menampilkan Contoh Tampilan (Simulasi)"** dan **"Lihat Jaringan yang Terhubung"**.

2. **Kalkulator Link Budget FTTH:**
   - Perhitungan redaman kumulatif dari OLT hingga ONT pelanggan.
   - Perhitungan rasio splitter bertingkat (ODC 1:4 dan ODP 1:8).
   - Preset standar GPON Class B+ (+2.5 dBm) dan Class C+ (+4.5 dBm).

3. **Hitung Cepat ODP ke ONT (Field Tool):**
   - Alat bantu teknisi lapangan untuk memprediksi redaman di modem berdasarkan hasil ukur OPM di port ODP dan panjang kabel drop core.

---

## 🚀 Panduan Penggunaan

### A. Penggunaan Website Langsung (Di HP / Laptop / Tablet)
Untuk sekadar menggunakan kalkulator atau melihat simulasi:
1. Buka browser di perangkat apa pun.
2. Akses tautan: `https://alamakk002.github.io/monitoring-redaman/`
3. Aplikasi siap digunakan secara instan tanpa perlu instalasi apa pun.

---

### B. Menghubungkan ke Perangkat Fisik OLT (Mode Jaringan Riil)

Jika ingin membaca data sinyal asli langsung dari perangkat OLT (ZTE/Huawei/VSOL) di kantor:

#### 1. Persyaratan Sistem
- Laptop/PC tercolok kabel LAN manajemen OLT.
- Terpasang Python 3.8 atau lebih baru.

#### 2. Instalasi Pustaka Pendukung
Buka Terminal/CMD, lalu jalankan:
```bash
pip install fastapi uvicorn netmiko

#### 3. Konfigurasi IP OLT
Buka file `server.py`, lalu sesuaikan konfigurasi IP, username, dan password OLT kantor Anda:
```python
OLT_DEVICE = {
    "device_type": "zte_zxros",  # zte_zxros, huawei, cisco_ios
    "host": "192.168.1.100",     # Ganti dengan IP OLT kantor Anda
    "username": "admin",
    "password": "password_asli_olt",
    "port": 23                   # 23 (Telnet) atau 22 (SSH)
}