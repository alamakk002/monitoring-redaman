# ⚡ OptiPulse NOC - Monitoring Klien & Kalkulator Redaman FTTH

Aplikasi pemantauan kualitas jaringan FTTH (Fiber to the Home) dan kalkulator redaman optik (*Optical Power Budget*) berbasis standar ITU-T G.984 GPON.

🌐 **Demo (data simulasi):** [https://alamakk002.github.io/monitoring-redaman/](https://alamakk002.github.io/monitoring-redaman/)

⬇️ **Unduh aplikasi Windows:** [Releases — OptiPulse-NOC-Setup.exe](https://github.com/alamakk002/monitoring-redaman/releases/latest) (± 30 MB, tanpa perlu Python)

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

Tersedia dua file di folder `dist\`:

| File | Fungsi |
|---|---|
| `OptiPulse-NOC-Setup.exe` (± 30 MB) | **Installer** — disarankan |
| `OptiPulse-NOC.exe` (± 29 MB) | Versi portable, tanpa instalasi |

File **tidak** di-commit; bangun ulang kapan saja dengan `build-exe.bat`.

### 1. Install dengan Setup (disarankan)

1. Klik dua kali `dist\OptiPulse-NOC-Setup.exe`.
2. Ikuti wizard (bahasa Indonesia). Folder default:
   `%LOCALAPPDATA%\Programs\OptiPulse NOC`
3. Opsional: centang **shortcut Desktop** dan/atau **jalankan otomatis saat login**.
4. Klik **Install**, lalu **Finish**. Aplikasi langsung terbuka di browser.
5. Jika SmartScreen muncul: **More info → Run anyway**.
6. Jika Windows Firewall bertanya: centang **Private networks → Allow access**.

Setelah terpasang, aplikasi ada di **Start Menu → OptiPulse NOC**. Tidak perlu hak administrator.

**Uninstall:** Settings → Apps → *OptiPulse NOC* → Uninstall, atau Start Menu → *Uninstall OptiPulse NOC*. Data klien **tidak** ikut terhapus.

### 2. Versi portable (tanpa install)

1. Salin `OptiPulse-NOC.exe` ke folder mana pun (mis. `D:\OptiPulse NOC`).
2. Klik dua kali file tersebut.
3. Browser terbuka otomatis ke `http://localhost:5000`.

**Jangan tutup jendela hitam** selama aplikasi dipakai — jendela itu adalah servernya. Tutup jendela untuk menghentikan aplikasi.

### 3. Konfigurasi OLT (dari dashboard)

Cara termudah: buka aplikasi → tab **Dashboard & Monitoring** → tombol **Pengaturan OLT**.

Isi:

| Kolom | Contoh | Keterangan |
|---|---|---|
| Host / IP OLT | `192.168.1.100` | IP perangkat OLT di jaringan manajemen |
| Port | `23` | 23 = Telnet, 22 = SSH |
| Username | `admin` | Akun OLT (disarankan akun read-only) |
| Password | `••••` | Disimpan di PC server, tidak dikirim ke browser lain |
| Merek / model OLT | `ZTE C320 / C300 / C600` | Pilihan cepat: ZTE, Huawei, atau manual |
| Posisi port PON | Frame `1`, Slot `1`, Port `1` | Perintah dibentuk otomatis dari posisi ini |
| Tipe perangkat | `zte_zxros` | Driver netmiko, terisi otomatis dari pilihan merek |
| Perintah baca redaman | `show gpon onu detail-info gpon-olt_1/1/1` | Rekomendasi otomatis; bisa diedit manual |

Pilih **Merek / model OLT**, lalu isi **Frame / Slot / Port PON**. Perintah rekomendasi langsung muncul di kotak hijau dan otomatis mengisi kolom perintah:

| Merek / model | Perintah rekomendasi |
|---|---|
| ZTE C320 / C300 / C600 (GPON) | `show gpon onu detail-info gpon-olt_<frame>/<slot>/<port>` |
| Huawei MA5600T / MA5800 (GPON) | `display ont optical-info <frame> <slot> all` |
| Lainnya | tulis manual, lalu uji dengan **Tes Koneksi** |

Untuk Huawei, kolom Port PON tidak dipakai karena perintah `all` membaca semua port pada slot tersebut. Tombol **Pakai** mengembalikan kolom perintah ke rekomendasi bila sudah diubah manual.

#### Memantau banyak port PON sekaligus

Di bagian **Port PON yang dipantau**:

- **+ Tambah port ini** — memasukkan port yang sedang dipilih ke daftar. Ulangi untuk port lain (maksimal 32).
- **Cari port otomatis** — aplikasi memeriksa port 1–16 pada slot terpilih (ZTE) atau slot 1–8 (Huawei), lalu menambahkan port yang berisi ONU. Proses ini bisa memakan 20–60 detik karena setiap port dijalankan satu per satu.
- Tombol **×** pada chip menghapus port dari daftar; **Kosongkan** menghapus semuanya.

Saat daftar berisi port, mode **Jaringan yang Terhubung** membaca semua port itu dan menggabungkan hasilnya, sehingga pelanggan di port berbeda tampil di satu dashboard. Nama ONU diberi awalan lokasi port, mis. `Frame 1 / Slot 1 / Port 3 · ONU Port 2`.

Klik **Tes Koneksi** untuk memastikan IP/port/kredensial benar sebelum menyimpan, lalu **Simpan**.
Setelah tersimpan, tombol **Cek Koneksi** dan mode **Jaringan yang Terhubung** langsung memakai pengaturan tersebut.

Alternatif tanpa membuka aplikasi: buat file `optipulse.env` di folder aplikasi (contoh: `optipulse.env.example` yang ikut terpasang).

```ini
OLT_HOST=192.168.1.100
OLT_USERNAME=admin
OLT_PASSWORD=password_asli
OLT_PORT=23
```

- Installer: `%LOCALAPPDATA%\Programs\OptiPulse NOC\optipulse.env`
- Portable: di samping `OptiPulse-NOC.exe`

**Urutan prioritas:** pengaturan yang disimpan dari dashboard → isi `optipulse.env` → environment variable Windows. Tombol **Hapus pengaturan tersimpan** mengembalikan aplikasi ke nilai `optipulse.env`.

Tanpa konfigurasi sama sekali, aplikasi tetap berjalan dalam mode demo.

### 4. Lokasi data

| Item | Lokasi |
|---|---|
| Database bersama | `%LOCALAPPDATA%\OptiPulse NOC\optipulse.db` |
| Pengaturan OLT dari dashboard | tabel `settings` di `optipulse.db` yang sama |
| Konfigurasi alternatif (opsional) | `optipulse.env` di folder aplikasi atau folder data di atas |

Menghapus data = hapus folder `%LOCALAPPDATA%\OptiPulse NOC`.

### 5. Memasang di beberapa perangkat

- Install di 5 laptop berarti ada **5 database terpisah** — data tidak otomatis sama.
- Untuk data yang sama, jalankan aplikasi hanya di **satu** PC (jadikan server), lalu perangkat lain membuka `http://IP-PC-ITU:5000` lewat browser. Ini cara yang disarankan.
- Jangan menaruh `optipulse.db` di folder jaringan (SMB); SQLite tidak dirancang diakses beberapa proses sekaligus lewat share.

### 6. Membangun ulang .exe dan installer

```bat
build-exe.bat
```

Script akan:

1. Memasang PyInstaller bila belum ada (butuh internet sekali).
2. Membuat `dist\OptiPulse-NOC.exe`.
3. Membuat `dist\OptiPulse-NOC-Setup.exe` bila **Inno Setup 6** terpasang (unduh dari <https://jrsoftware.org/isdl.php>).

Build harus dilakukan di Windows; Linux/macOS perlu build terpisah.

### 7. Catatan Windows

- File belum ditandatangani (unsigned), jadi SmartScreen bisa menampilkan peringatan: **More info → Run anyway**.
- Saat pertama dijalankan, Windows Firewall mungkin bertanya. Pilih **Allow** untuk jaringan **Private** agar bisa diakses dari HP/laptop lain.
- Autostart bisa dipilih saat install, atau letakkan shortcut di `shell:startup`. Tambahkan `OPTIPULSE_OPEN_BROWSER=0` di `optipulse.env` bila tidak ingin browser terbuka setiap login.
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

**Klik dua kali .exe padahal aplikasi sudah jalan** — jendela baru akan menampilkan `OptiPulse NOC sudah berjalan` dan langsung membuka browser, lalu menutup diri. Ini normal; aplikasi hanya boleh punya satu server. Untuk mematikan aplikasi, tutup jendela server yang lama.

**.exe langsung tertutup** — hanya terjadi bila port dipakai aplikasi **lain** (bukan OptiPulse). Jendela akan menampilkan pesan `Port 5000 sedang dipakai aplikasi lain` dan menunggu Enter. Tutup aplikasi tersebut, atau ubah `PORT=5050` di `optipulse.env`.

**Data .exe tidak muncul di perangkat lain** — setiap `.exe` punya database sendiri. Jalankan `.exe` di satu PC saja, perangkat lain mengakses `http://IP-PC:5000`.

**HP tidak bisa membuka halaman** — pastikan satu jaringan, firewall mengizinkan port 5000, dan IP yang dipakai benar.

**"OLT belum dikonfigurasi"** — buka **Pengaturan OLT** di dashboard, isi host/username/password, klik **Tes Koneksi**, lalu **Simpan**. Tidak perlu mengedit file apa pun.

**"Backend online, namun OLT belum terjangkau"** — server hidup, tetapi koneksi ke OLT gagal. Periksa `OLT_HOST`, kabel/VLAN manajemen, dan kredensial OLT.

**Ingin memastikan alamat API yang dipakai** — buka Console browser (`F12`):
```js
window.OPTIPULSE_SAME_ORIGIN === true ? location.origin
  : (localStorage.getItem('optipulse_api_base') || window.OPTIPULSE_API_BASE || 'http://localhost:5000')
```

---

## 📏 Ambang Redaman GPON

| Rentang Rx | Status | Tindakan |
|---|---|---|
| > -15 dBm | **Terlalu kuat** | Risiko saturasi receiver. Tambahkan atenuator 5–10 dB, periksa rasio splitter, dan pastikan ukur di 1490 nm |
| -15 s/d -22 dBm | Optimal | Tidak ada tindakan |
| -22 s/d -25 dBm | Normal | Tidak ada tindakan |
| -25 s/d -27 dBm | Waspada | Bersihkan konektor, cek tekukan kabel |
| < -27 dBm | Kritis / berisiko RTO | Perbaikan segera |
| ≤ -31 dBm | LOS | Cek putus fiber / ONT mati |

> Daya maksimum yang masih aman bagi receiver ONT kelas B+ sekitar **-8 dBm**. Angka -14 dBm masih bekerja, tetapi menandakan desain jaringan terlalu "kuat" (splitter kurang, jarak terlalu dekat, atau salah ukur).

---

## 📂 Struktur File

```
index.html             # UI aplikasi (Tailwind, Chart.js, font lokal di vendor/)
server.py              # FastAPI: menyajikan UI, API OLT, dan /api/state
start-optipulse.bat    # Menjalankan server Python dengan sekali klik (Windows)
build-exe.bat          # Membangun .exe dan installer dengan PyInstaller + Inno Setup
installer.iss          # Resep installer Inno Setup
installer/             # Panduan setelah install + terjemahan bahasa Indonesia
assets/optipulse.ico   # Ikon aplikasi dan installer
optipulse.env.example  # Contoh konfigurasi OLT untuk server / .exe
README.md              # Dokumentasi ini
vendor/                # Tailwind, Chart.js, dan font untuk pemakaian offline
optipulse.db           # Database SQLite data bersama (dibuat otomatis, tidak di-commit)
dist/                  # Hasil build .exe + Setup (tidak di-commit)
```
