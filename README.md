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

## B. Menghubungkan ke Perangkat Fisik OLT (Mode Jaringan Riil)

Jika ingin membaca data sinyal asli langsung dari perangkat OLT (ZTE/Huawei/VSOL) di kantor:

### 1. Persyaratan Sistem
- Laptop/PC tercolok kabel LAN manajemen OLT.
- Terpasang Python 3.8 atau lebih baru.

### 2. Instalasi Pustaka Pendukung
Buka Terminal/CMD, lalu jalankan perintah:
```bash
pip install fastapi uvicorn netmiko
```

### 3. Konfigurasi IP OLT

Cara paling aman: atur lewat environment variable sebelum menjalankan server (password tidak tersimpan di kode).

**Windows (PowerShell):**
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

Alternatif cepat untuk uji coba: edit nilai default di `server.py` pada bagian `OLT_DEVICE`. Jangan commit password asli ke Git.

### 4. Menjalankan Server Backend

Jalankan file backend melalui terminal/CMD:
```bash
python server.py
```

Server berjalan di `http://localhost:5000`. Cek dengan membuka `http://localhost:5000/health` — harus menampilkan `{"status":"ok",...}`.

### 5. Menghubungkan dari Perangkat Lain (HP / Laptop Teknisi)

Agar HP atau laptop teknisi lain di kantor bisa membaca data OLT secara nirkabel:

1. Hubungkan HP ke jaringan WiFi kantor yang sama dengan laptop server.
2. Cek IP lokal laptop server dengan perintah `ipconfig` (misalnya didapat `192.168.1.25`).
3. Arahkan aplikasi ke alamat tersebut **tanpa mengedit HTML**. Pilih salah satu cara:

   **Cara A — dari Console browser (sekali per sesi):**
   ```js
   localStorage.setItem('optipulse_api_base', 'http://192.168.1.25:5000');
   location.reload();
   ```

   **Cara B — sisipkan konfigurasi sebelum script aplikasi:**
   ```html
   <script>window.OPTIPULSE_API_BASE = 'http://192.168.1.25:5000';</script>
   ```

   **Cara C — query string:** buka `index.html?api=http://192.168.1.25:5000`
   (aplikasi membaca parameter `api` dan menyimpannya di localStorage).

4. Klik tombol **Cek Koneksi** di dashboard.

### 6. Catatan Chrome Local Network Access (PNA)

Saat website dibuka dari domain publik (GitHub Pages) lalu memanggil API di `localhost`/IP privat, Chrome memblokir request sampai pengguna memberi izin:

> *Permission was denied for this request to access the `loopback` address space.*

Yang perlu dilakukan:

- Jalankan server dengan header CORS + `Access-Control-Allow-Private-Network: true` (sudah disertakan di `server.py`).
- Saat Chrome menampilkan prompt izin akses jaringan lokal, pilih **Allow**.
- Jika tidak ada prompt: buka `chrome://settings/content/localNetworkAccess` lalu izinkan situs tersebut.
- Cara paling bebas masalah: akses aplikasi dari `http://localhost:8000/index.html` (bukan dari GitHub Pages) ketika memakai backend lokal.

### 7. Cara Mengecek Alamat Backend yang Sedang Digunakan

Buka Console browser (`F12`) lalu jalankan:
```js
localStorage.getItem('optipulse_api_base') || window.OPTIPULSE_API_BASE || 'http://localhost:5000'
```

Atau di tab **Network**, klik tombol **Cek Koneksi**, lalu lihat Request URL pada baris `clients`.

### 8. Variabel Environment Backend

| Variabel | Default | Keterangan |
|---|---|---|
| `OLT_DEVICE_TYPE` | `zte_zxros` | Tipe perangkat Netmiko (`zte_zxros`, `huawei`, `cisco_ios`, `generic`) |
| `OLT_HOST` | `192.168.1.100` | IP OLT |
| `OLT_USERNAME` | `admin` | Username OLT |
| `OLT_PASSWORD` | `password_olt` | Password OLT |
| `OLT_PORT` | `23` | Port Telnet/SSH |
| `OLT_TIMEOUT` | `10` | Timeout koneksi (detik) |
| `OLT_COMMAND` | `show gpon onu detail-info gpon-olt_1/1/1` | Perintah pembacaan ONT |
| `OPTIPULSE_ALLOWED_ORIGINS` | `*` | Origin yang diizinkan, pisahkan dengan koma |
| `PORT` | `5000` | Port server backend |