# Autonomous Vision-Based Control System

Proyek ini berisi aplikasi visi komputer berbasis Python dan firmware ESP32
berbasis ESP-IDF. Aplikasi mendeteksi jarak antara ujung ibu jari dan telunjuk,
menampilkan status kontrol, dan dapat mengirim perintah serial. Firmware ESP32
saat ini merupakan contoh FreeRTOS dengan data sensor simulasi.

---

## Fitur

- Melacak satu tangan menggunakan MediaPipe dan webcam.
- Mengubah jarak ibu jari–telunjuk menjadi status `STOP`, `FULL`, atau `PWM`.
- Menampilkan status kontrol di jendela video.
- Menjalankan task safety, producer, dan consumer dengan FreeRTOS pada ESP32.

---

## Menjalankan aplikasi visi

Gunakan Python dan pasang dependensi proyek:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/gesture_control.py
```

Pastikan webcam tersedia. Tekan `q` pada jendela kamera untuk keluar. Secara
default, pengiriman serial dinonaktifkan (`SERIAL_ENABLED = False`) di
`src/gesture_control.py`.

## Build firmware ESP32

Firmware menggunakan ESP-IDF native, bukan PlatformIO atau Arduino. Buka
terminal yang sudah menyiapkan environment ESP-IDF, lalu jalankan dari root
proyek:

```powershell
idf.py -C firmware set-target esp32
idf.py -C firmware build
```

Target perlu disetel saat pertama kali build atau jika target board berubah.
Untuk flash dan membuka serial monitor, ganti `COM3` dengan port ESP32:

```powershell
idf.py -C firmware -p COM3 flash monitor
```

### Batasan saat ini

Firmware menggunakan nilai suhu, tegangan, dan arus simulasi. Pembacaan sensor
fisik, MQTT/HTTP, dan protokol serial dari aplikasi Python belum diterapkan;
karena itu aplikasi visi dan firmware belum saling mengendalikan.

## Struktur proyek

```text
.
├── firmware/
│   ├── main/
│   │   ├── main.cpp
│   │   └── CMakeLists.txt
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
├── src/
│   └── gesture_control.py
├── requirements.txt
├── README.md
```

Python dan ESP-IDF disiapkan secara terpisah. `requirements.txt` hanya berisi
dependensi aplikasi Python.
