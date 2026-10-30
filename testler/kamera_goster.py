"""Kameradan görüntüyü sadece gösterir (tespit yok). Kamera çalışıyor mu diye bakmak için.

Kullanım: .venv/bin/python testler/kamera_goster.py   (çıkmak için q)
"""
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()