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
| **Aplikasi .exe** (Windows) | Laptop NOC tanpa Python, instalasi cepat | ✅ Ya, satu origin |
| **GitHub Pages** | Demo/portofolio, tanpa backend | ❌ Tidak |
| **Aplikasi desktop** | Jendela native tanpa browser | Belum tersedia |

> Untuk pemakaian sehari-hari, jalankan lewat `server.py`. UI dan API disajikan dari alamat yang sama sehingga tidak ada masalah CORS, *mixed content*, atau izin Local Network Access.

---

## B. Server LAN (Disarankan untuk Operasional)

### 1. Persyaratan

- Laptop/PC yang terhubung ke jaringan manajemen OLT.
- Python 3.8 atau lebih baru.
- Port `5000` tidak dipakai aplikasi lain.

> Tidak perlu koneksi internet. Tailwind, Chart.js, dan font (Inter & JetBrains Mono) disajikan dari folder `vendor/`.

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

Data klien dan log sekarang **dibagi antarperangkat**:

- Server menyimpan data di `optipulse.db` (SQLite) melalui endpoint `/api/state`.
- Laptop, HP, atau komputer lain yang membuka alamat server yang sama akan melihat data yang sama.
- Perubahan dari perangkat lain otomatis diambil tiap 15 detik (muncul notifikasi "Data diperbarui dari perangkat lain").
- `localStorage` tetap dipakai sebagai cadangan saat server mati/terputus, sehingga tampilan tidak kosong.
- Data hanya diperbarui ke server saat mode **DEMO**, supaya hasil pembacaan OLT di mode **LIVE** tidak menimpa data operasional bersama.
- Menghapus data browser tidak lagi menghapus data bersama; data tetap ada di `optipulse.db`.
- Untuk mengosongkan data bersama, hentikan server lalu hapus `optipulse.db` dan `optipulse.db-wal` / `optipulse.db-shm` (dibuat ulang otomatis saat server dijalankan).

File database **tidak** ikut di-commit (lihat `.gitignore`). Mode demo di GitHub Pages tetap memakai `localStorage` masing-masing browser karena tidak ada backend.

---

## C. Aplikasi .exe (Windows)

Versi siap pakai dibangun ke `dist\OptiPulse-NOC.exe` (± 29 MB). File ini **tidak** di-commit; bangun ulang kapan saja dengan `build-exe.bat`.

### 1. Cara menjalankan

1. Salin `OptiPulse-NOC.exe` ke folder mana pun (mis. `D:\OptiPulse NOC`).
2. Klik dua kali file tersebut.
3. Browser terbuka otomatis ke `http://localhost:5000`. Alamat untuk HP/laptop lain tampil di jendela hitam.
4. **Jangan tutup jendela hitam** selama aplikasi dipakai — jendela itu adalah servernya. Tutup jendela (atau `Ctrl + C`) untuk menghentikan aplikasi.

Tidak perlu Python, pip, atau koneksi internet.

### 2. Konfigurasi OLT

Buat file `optipulse.env` di folder yang sama dengan `.exe` (contoh lengkap: `optipulse.env.example`):

```ini
OLT_HOST=192.168.1.100
OLT_USERNAME=admin
OLT_PASSWORD=password_asli
OLT_PORT=23
```

Tanpa file ini, aplikasi tetap berjalan dalam mode demo. Environment variable Windows juga tetap didahulukan.

### 3. Lokasi data

| Item | Lokasi |
|---|---|
| Database bersama | `%LOCALAPPDATA%\OptiPulse NOC\optipulse.db` |
| Konfigurasi (opsional) | `optipulse.env` di samping `.exe`, atau di folder data di atas |

Menghapus aplikasi = hapus file `.exe` dan folder `%LOCALAPPDATA%\OptiPulse NOC` bila datanya juga ingin dihapus.

### 4. Memasang di beberapa perangkat

- Menyalin `.exe` ke 5 laptop berarti ada **5 database terpisah** — data tidak otomatis sama.
- Untuk data yang sama, jalankan `.exe` hanya di **satu** PC (jadikan server), lalu perangkat lain membuka `http://IP-PC-ITU:5000` lewat browser. Ini cara yang disarankan.
- Jangan menaruh `optipulse.db` di folder jaringan (SMB); SQLite tidak dirancang untuk diakses beberapa proses sekaligus lewat share.

### 5. Membangun ulang .exe

```bat
build-exe.bat
```

PyInstaller dipasang otomatis bila belum ada (butuh internet sekali saat build). Hasilnya `dist\OptiPulse-NOC.exe`. Build harus dilakukan di Windows; untuk Linux/macOS perlu build terpisah di sistem masing-masing.

### 6. Catatan Windows

- File belum ditandatangani (unsigned), jadi SmartScreen bisa menampilkan peringatan: **More info → Run anyway**.
- Saat pertama dijalankan, Windows Firewall mungkin bertanya. Pilih **Allow** untuk jaringan **Private** agar bisa diakses dari HP/laptop lain.
- Agar jalan otomatis saat login: buat *shortcut* `.exe` lalu letakkan di `shell:startup`. Tambahkan `OPTIPULSE_OPEN_BROWSER=0` di `optipulse.env` bila tidak ingin browser terbuka setiap login.
- Port 5000 dipakai aplikasi lain? Ubah `PORT=5050` di `optipulse.env`.

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
| `OPTIPULSE_DB` | `optipulse.db` di folder data | Lokasi file SQLite penyimpan data bersama |
| `OPTIPULSE_DATA_DIR` | folder aplikasi / `%LOCALAPPDATA%\OptiPulse NOC` (.exe) | Folder data yang bisa ditulis |
| `OPTIPULSE_OPEN_BROWSER` | `1` (khusus .exe) | `0` untuk tidak membuka browser otomatis |

---

## 🩺 Troubleshooting

**`python` tidak dikenali** — pasang Python dari python.org dan centang *Add Python to PATH*.

**Port 5000 sudah dipakai** — jalankan dengan port lain:
```powershell
$env:PORT="5050"
python server.py
```
Lalu buka `http://localhost:5050`. Untuk `.exe`, ubah `PORT=5050` di `optipulse.env`.

**Windows SmartScreen memblokir .exe** — klik **More info → Run anyway**. File belum ditandatangani secara digital.

**.exe langsung tertutup** — biasanya port sudah dipakai instance lain. Tutup jendela OptiPulse sebelumnya lewat Task Manager, atau ganti `PORT` di `optipulse.env`.

**Data .exe tidak muncul di perangkat lain** — setiap `.exe` punya database sendiri. Jalankan `.exe` di satu PC saja, perangkat lain mengakses `http://IP-PC:5000`.

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
index.html             # UI aplikasi (Tailwind, Chart.js, font lokal di vendor/)
server.py              # FastAPI: menyajikan UI, API OLT, dan /api/state
start-optipulse.bat    # Menjalankan server Python dengan sekali klik (Windows)
build-exe.bat          # Membangun dist\OptiPulse-NOC.exe dengan PyInstaller
optipulse.env.example  # Contoh konfigurasi OLT untuk server / .exe
README.md              # Dokumentasi ini
vendor/                # Tailwind, Chart.js, dan font untuk pemakaian offline
optipulse.db           # Database SQLite data bersama (dibuat otomatis, tidak di-commit)
dist/                  # Hasil build .exe (tidak di-commit)
```
