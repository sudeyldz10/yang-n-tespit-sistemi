"""YOLOv8 modeliyle karede yangın/duman tespiti ve alarm kararı."""
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

RENKLER = {"yangin": (72, 73, 227), "duman": (214, 80, 98)}  # BGR


@dataclass
class Tespit:
    sinif: str
    guven: float
    kutu: tuple  # (x1, y1, x2, y2)


class YanginDedektoru:
    def __init__(self, model_yolu, guven_esikleri, goruntu_boyutu=640):
        if not Path(model_yolu).exists():
            raise SystemExit(f"Model dosyası bulunamadı: {model_yolu}")
        self.model = YOLO(str(model_yolu))
        self.guven_esikleri = guven_esikleri
        self.goruntu_boyutu = goruntu_boyutu
        if torch.backends.mps.is_available():
            self.cihaz = "mps"
        elif torch.cuda.is_available():
            self.cihaz = 0
        else:
            self.cihaz = "cpu"

    def tespit_et(self, kare):
        sonuc = self.model(kare, conf=min(self.guven_esikleri.values()), imgsz=self.goruntu_boyutu,
                           device=self.cihaz, verbose=False)[0]
        tespitler = []
        for kutu, guven, sinif_no in zip(sonuc.boxes.xyxy.tolist(), sonuc.boxes.conf.tolist(),
                                         sonuc.boxes.cls.tolist()):
            sinif = sonuc.names[int(sinif_no)]
            if guven >= self.guven_esikleri[sinif]:
                tespitler.append(Tespit(sinif, guven, tuple(int(v) for v in kutu)))
        return tespitler

    @staticmethod
    def ciz(kare, tespitler, ust_bosluk=0):
        """Kutuları çizer. Etiket üstteki şeridin altında kalacaksa kutunun içine yazılır."""
        olcek = max(0.45, kare.shape[1] / 1600)
        for t in tespitler:
            renk = RENKLER[t.sinif]
            x1, y1, x2, y2 = t.kutu
            cv2.rectangle(kare, (x1, y1), (x2, y2), renk, 2)
            yazi = f"{t.sinif} {t.guven:.2f}"
            (g, y), _ = cv2.getTextSize(yazi, cv2.FONT_HERSHEY_SIMPLEX, olcek, 1)
            ust = max(y1, ust_bosluk) if y1 - y - 8 < ust_bosluk else y1 - y - 8
            cv2.rectangle(kare, (x1, ust), (x1 + g + 6, ust + y + 8), renk, -1)
            cv2.putText(kare, yazi, (x1 + 3, ust + y + 3), cv2.FONT_HERSHEY_SIMPLEX, olcek,
                        (255, 255, 255), 1, cv2.LINE_AA)


class AlarmKarari:
    """Son `sure_sn` saniyedeki karelerin en az `oran` kadarında tespit varsa alarm verir."""

    def __init__(self, sure_sn=1.5, oran=0.7, en_az_kare=5):
        self.sure_sn = sure_sn
        self.oran = oran
        self.en_az_kare = en_az_kare
        self.gecmis = deque()

    def guncelle(self, tespit_var_mi, zaman=None):
        zaman = time.time() if zaman is None else zaman
        self.gecmis.append((zaman, bool(tespit_var_mi)))
        while self.gecmis[0][0] < zaman - self.sure_sn:
            self.gecmis.popleft()
        if len(self.gecmis) < self.en_az_kare:
            return False
        return sum(v for _, v in self.gecmis) / len(self.gecmis) >= self.oran
