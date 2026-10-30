"""Hafta 1 - Webcam ile hazır YOLOv8 modelini test et.

Çalıştırma (proje klasöründen):
    .venv/bin/python testler/kamera_testi.py

Çıkmak için pencere seçiliyken 'q' tuşuna bas.
"""
import time

import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # ilk çalışmada otomatik indirir
kamera = cv2.VideoCapture(0)

if not kamera.isOpened():
    raise SystemExit(
        "Kamera açılamadı. macOS'ta: Sistem Ayarları > Gizlilik ve Güvenlik > Kamera "
        "bölümünden Terminal'e (veya VS Code'a) izin ver."
    )

onceki_zaman = time.time()
while True:
    basarili, kare = kamera.read()
    if not basarili:
        print("Kameradan görüntü alınamadı.")
        break

    sonuclar = model(kare, verbose=False)
    cizilmis_kare = sonuclar[0].plot()

    # Saniyedeki kare sayısını (FPS) hesapla ve ekrana yaz
    simdiki_zaman = time.time()
    fps = 1 / (simdiki_zaman - onceki_zaman)
    onceki_zaman = simdiki_zaman
    cv2.putText(cizilmis_kare, f"FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Kamera Testi", cizilmis_kare)
    if cv2.waitKey(1) == ord("q"):
        break

kamera.release()
cv2.destroyAllWindows()
