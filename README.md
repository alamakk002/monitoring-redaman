# ⚡ OptiPulse NOC - Monitoring Klien & Kalkulator Redaman FTTH

Aplikasi pemantauan kualitas jaringan FTTH (Fiber to the Home) dan kalkulator redaman optik (*Optical Power Budget*) berbasis standar ITU-T G.984 GPON.

🌐 **Demo (data simulasi):** [https://alamakk002.github.io/monitoring-redaman/](https://alamakk002.github.io/monitoring-redaman/)

---

## 📌 Fitur Utama

1. **Dashboard Monitoring Klien**
   - Status Rx Power ONT: Optimal, Normal, Waspada, Kritis, LOS.
   - Filter ODP/status, uji latency (ICMP ping), grafik tren 24 jam.
   - Mode **Contoh Tampilan (Simulasi)** dan **Jaringan yang Terhubung**.

2. **Kalkulator Link Budget FTTH**
   - Redaman kumulatif dari OLT hingga ONT.
   - Splitter bertingkat (ODC dan ODP) dengan rasio otomatis.
   - Preset GPON Class B+ (+2.5 dBm) dan Class C+ (+4.5 dBm).

3. **Hitung Cepat ODP ke ONT (Field Tool)**
   - Prediksi redaman modem dari hasil ukur OPM di port ODP dan panjang drop core.

---

## 🚀 Pilihan Cara Menjalankan

| Cara | Cocok untuk | Mode live OLT |
|---|---|---|
| **Server LAN** (disarankan) | Operasional NOC, dipakai beberapa teknisi | ✅ Ya, satu origin |
| **GitHub Pages** | Demo/portofolio, tanpa backend | ❌ Tidak |
| **Aplikasi desktop** | Satu laptop, tanpa browser | Perlu pengemasan terpisah |

> Untuk pemakaian sehari-hari, jalankan lewat `server.py`. UI dan API disajikan dari alamat yang sama sehingga tidak ada masalah CORS, *mixed content*, atau izin Local Network Access.

---

## B. Server LAN (Disarankan untuk Operasional)

### 1. Persyaratan

- Laptop/PC yang terhubung ke jaringan manajemen OLT.
- Python 3.8 atau lebih baru.
- Port `5000` tidak dipakai aplikasi lain.

### 2. Instalasi

```bash
pip install fastapi uvicorn netmiko
```

### 3. Konfigurasi OLT

Atur lewat environment variable agar password tidak tersimpan di kode.

**Windows PowerShell:**
```powershell
$env:OLT_HOST="192.168.1.100"
$env:OLT_USERNAME="admin"
$env:OLT_PASSWORD="password_asli_olt"
$env:OLT_PORT="23"
$env:OLT_DEVICE_TYPE="zte_zxros"
$env:OLT_COMMAND="show gpon onu detail-info gpon-olt_1/1/1"
```

**Linux/macOS:**
```bash
export OLT_HOST=192.168.1.100
export OLT_USERNAME=admin
export OLT_PASSWORD=password_asli_olt
export OLT_PORT=23
export OLT_DEVICE_TYPE=zte_zxros
export OLT_COMMAND="show gpon onu detail-info gpon-olt_1/1/1"
```

### 4. Jalankan Aplikasi

```bash
python server.py
```

Server akan menampilkan alamat yang bisa dibuka:

```
================================================================
  OptiPulse NOC siap dijalankan
  Di laptop ini      : http://localhost:5000
  Dari HP / laptop   : http://192.168.1.25:5000
================================================================
```

Buka `http://localhost:5000` — UI dan API otomatis satu origin. Cek backend di `http://localhost:5000/health`.

### 5. Akses dari HP / Laptop Lain

1. Hubungkan perangkat ke WiFi/LAN kantor yang sama dengan laptop server.
2. Buka `http://IP-LAPTOP:5000` (IP tertera saat server dijalankan, atau cek dengan `ipconfig`).
3. Jika tidak bisa dibuka, izinkan port 5000 di Windows Firewall (PowerShell **as Administrator**, sekali saja):

```powershell
New-NetFirewallRule -DisplayName "OptiPulse NOC" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -Profile Private
```

> Jangan membuka port 5000 ke internet. Untuk akses dari luar kantor, gunakan VPN kantor atau Tailscale.

### 6. Menjalankan Otomatis (Opsional)

- Buat shortcut ke `start-optipulse.bat` di folder ini, lalu letakkan di `shell:startup`.
- Atau daftarkan lewat **Task Scheduler** dengan trigger *At log on* dan aksi menjalankan `start-optipulse.bat`.

### 7. Update Aplikasi

1. Hentikan server (`Ctrl + C`).
2. Ganti `index.html` / `server.py` dengan versi baru.
3. Jalankan `python server.py` kembali. Browser cukup di-refresh.

### 8. Catatan Penyimpanan Data

Saat ini data klien dan log disimpan di `localStorage` **masing-masing browser**. Artinya:

- Data di laptop A tidak otomatis muncul di HP B.
- Menghapus data browser akan menghapus data aplikasi.
- Reset Data mengembalikan data demo.

Untuk data yang sama di semua perangkat, langkah berikutnya adalah menyimpan data di backend (SQLite) — belum termasuk dalam versi ini.

---

## A. Demo via GitHub Pages

Halaman publik hanya untuk memperlihatkan tampilan dengan data simulasi.

1. Buka `https://alamakk002.github.io/monitoring-redaman/`.
2. Kalkulator dan dashboard demo langsung bisa dipakai.
3. Mode live OLT **tidak** bisa diandalkan dari GitHub Pages karena halaman HTTPS memanggil API HTTP di jaringan lokal (diblokir *mixed content* / perlu izin Local Network Access).

Jika tetap ingin mencoba demo + backend lokal, jalankan server lalu buka `index.html?api=http://IP-LAPTOP:5000`. Chrome akan meminta izin akses jaringan lokal; pilih **Allow**.

---

## 🔧 Variabel Environment

| Variabel | Default | Keterangan |
|---|---|---|
| `HOST` | `0.0.0.0` | Alamat bind server (agar bisa diakses LAN) |
| `PORT` | `5000` | Port aplikasi web |
| `OLT_DEVICE_TYPE` | `zte_zxros` | Tipe Netmiko (`zte_zxros`, `huawei`, `cisco_ios`, `generic`) |
| `OLT_HOST` | `192.168.1.100` | IP OLT |
| `OLT_USERNAME` | `admin` | Username OLT |
| `OLT_PASSWORD` | `password_olt` | Password OLT |
| `OLT_PORT` | `23` | Port Telnet (23) atau SSH (22) |
| `OLT_TIMEOUT` | `10` | Timeout koneksi (detik) |
| `OLT_COMMAND` | `show gpon onu detail-info gpon-olt_1/1/1` | Perintah pembacaan ONT |
| `OPTIPULSE_ALLOWED_ORIGINS` | `*` | Origin CORS yang diizinkan, pisahkan dengan koma |

---

## 🩺 Troubleshooting

**`python` tidak dikenali** — pasang Python dari python.org dan centang *Add Python to PATH*.

**Port 5000 sudah dipakai** — jalankan dengan port lain:
```powershell
$env:PORT="5050"
python server.py
```
Lalu buka `http://localhost:5050`.

**HP tidak bisa membuka halaman** — pastikan satu jaringan, firewall mengizinkan port 5000, dan IP yang dipakai benar.

**"Backend online, namun OLT belum terjangkau"** — server hidup, tetapi koneksi ke OLT gagal. Periksa `OLT_HOST`, kabel/VLAN manajemen, dan kredensial OLT.

**Ingin memastikan alamat API yang dipakai** — buka Console browser (`F12`):
```js
window.OPTIPULSE_SAME_ORIGIN === true ? location.origin
  : (localStorage.getItem('optipulse_api_base') || window.OPTIPULSE_API_BASE || 'http://localhost:5000')
```

---

## 📏 Ambang Redaman GPON

| Rentang Rx | Status |
|---|---|
| -15 s/d -22 dBm | Optimal |
| -22 s/d -25 dBm | Normal |
| -25 s/d -27 dBm | Waspada |
| < -27 dBm | Kritis / berisiko RTO |
| ≤ -31 dBm | LOS |

---

## 📂 Struktur File

```
index.html          # UI aplikasi (Tailwind + Chart.js via CDN)
server.py           # FastAPI: menyajikan UI + API OLT
start-optipulse.bat # Menjalankan server dengan sekali klik (Windows)
README.md           # Dokumentasi ini
```
