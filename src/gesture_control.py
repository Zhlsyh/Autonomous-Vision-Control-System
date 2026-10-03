import cv2
import mediapipe as mp
import math
import serial
import time

# ==============================================================================
# 1. KONFIGURASI SERIAL HARDWARE (ESP32 / ARDUINO)
# ==============================================================================
# Set SERIAL_ENABLED = True jika sudah terhubung ke ESP32/Arduino fisik via USB.
# Set SERIAL_ENABLED = False jika ingin menjalankan simulasi tanpa hardware.
SERIAL_ENABLED = False
SERIAL_PORT = 'COM3'     # Sesuaikan dengan Port COM Windows Anda (misal: 'COM3', 'COM4')
BAUD_RATE = 115200

ser = None
if SERIAL_ENABLED:
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        time.sleep(2)  # Tunggu jeda stabilisasi koneksi serial
        print(f"[INFO] Terhubung ke Hardware pada Port {SERIAL_PORT}")
    except Exception as e:
        print(f"[ERROR] Gagal membuka port serial {SERIAL_PORT}: {e}")
        print("[INFO] Berjalan dalam mode simulasi (Tanpa Hardware Serial).")
        SERIAL_ENABLED = False

# ==============================================================================
# 2. INISIALISASI MEDIAPIPE HANDS & WEBCAM
# ==============================================================================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Buka Kamera (Index 0)
cap = cv2.VideoCapture(0)

print("\n=== Vision-Based Control System Active ===")
print(f"Status Serial Hardware: {'AKTIF (' + SERIAL_PORT + ')' if SERIAL_ENABLED else 'NON-AKTIF (Simulasi Mode)'}")
print("Tekan tombol 'q' pada window kamera untuk keluar.\n")

last_command = ""

# ==============================================================================
# 3. MAIN PROCESSING LOOP
# ==============================================================================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Gagal mengakses kamera webcam.")
        break

    # Flip horizontal agar tampilan kamera berfungsi seperti cermin
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape

    # Konversi BGR ke RGB untuk pemrosesan MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    current_state = "IDLE / NO HAND DETECTED"
    state_color = (128, 128, 128)  # Abu-abu
    command_to_send = "STOP\n"

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Gambarkan koneksi 21 titik landmark tangan pada frame
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Ambil titik Ujung Ibu Jari (Index 4) dan Ujung Telunjuk (Index 8)
            thumb_tip = hand_landmarks.landmark[4]
            index_tip = hand_landmarks.landmark[8]

            # Konversi koordinat ternormalisasi (0.0 - 1.0) ke Piksel Layar
            x1, y1 = int(thumb_tip.x * w), int(thumb_tip.y * h)
            x2, y2 = int(index_tip.x * w), int(index_tip.y * h)

            # Hitung Jarak Euclidean antara Ibu Jari dan Telunjuk
            distance = math.hypot(x2 - x1, y2 - y1)

            # Visualisasi Titik & Garis Kontrol
            cv2.circle(frame, (x1, y1), 8, (255, 0, 0), -1)
            cv2.circle(frame, (x2, y2), 8, (255, 0, 0), -1)
            cv2.line(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

            # Logika Keputusan & Pemicu Status
            if distance < 35:
                current_state = "EMERGENCY STOP / CLOSE"
                state_color = (0, 0, 255)  # Merah (BGR)
                command_to_send = "STOP\n"
            elif distance > 120:
                current_state = "MODE: FULL POWER / OPEN"
                state_color = (0, 255, 0)  # Hijau (BGR)
                command_to_send = "FULL\n"
            else:
                current_state = f"MODE: KONTROL PRESISI ({int(distance)} px)"
                state_color = (0, 255, 255)  # Kuning (BGR)
                command_to_send = f"PWM:{int(distance)}\n"

            # Kirim perintah ke Hardware via Serial hanya jika ada perubahan komando
            if SERIAL_ENABLED and command_to_send != last_command:
                try:
                    ser.write(command_to_send.encode('utf-8'))
                    last_command = command_to_send
                except Exception as err:
                    print(f"[ERROR] Gagal mengirim data serial: {err}")

    # ==============================================================================
    # 4. VIRTUAL HUD CANVAS OVERLAY
    # ==============================================================================
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (470, 90), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Indikator Teks Status Utama
    serial_status_str = f"SERIAL: {'COM ACTIVE' if SERIAL_ENABLED else 'DISABLED (SIMULATION)'}"
    cv2.putText(frame, serial_status_str, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    cv2.putText(frame, "SYSTEM STATUS:", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, current_state, (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)

    # Tampilkan Frame Video
    cv2.imshow("Autonomous Vision Control System", frame)

    # Exit program dengan menekan 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release Resource Kamera & Serial Port
cap.release()
cv2.destroyAllWindows()
if SERIAL_ENABLED and ser:
    ser.close()
    print("[INFO] Port Serial berhasil ditutup.")