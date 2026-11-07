"""Webcam'den veya video dosyasından kare okuma."""
import time

import cv2


class Kamera:
    def __init__(self, kaynak=0):
        self.kaynak = kaynak
        self.video_mu = not isinstance(kaynak, int)
        self.yakalayici = None

    def __enter__(self):
        self.yakalayici = cv2.VideoCapture(self.kaynak if not self.video_mu else str(self.kaynak))
        if not self.yakalayici.isOpened():
            if self.video_mu:
                raise SystemExit(f"Video açılamadı: {self.kaynak}")
            raise SystemExit("Kamera açılamadı. Sistem Ayarları > Gizlilik ve Güvenlik > Kamera "
                             "bölümünden Terminal'e izin ver.")
        return self

    def __exit__(self, *hata):
        self.yakalayici.release()

    def kareler(self):
        """Kareleri sırayla verir. Video dosyası gerçek hızında oynatılır."""
        fps = self.yakalayici.get(cv2.CAP_PROP_FPS) or 30.0
        bekleme = 1.0 / fps if self.video_mu else 0
        while True:
            baslangic = time.time()
            basarili, kare = self.yakalayici.read()
            if not basarili:
                return
            yield kare
            kalan = bekleme - (time.time() - baslangic)
            if kalan > 0:
                time.sleep(kalan)
