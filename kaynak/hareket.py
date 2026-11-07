"""Tespit kutusunun içinde hareket var mı kontrolü.
Alev titrer, duman dağılır; turuncu bir tabela ya da fotoğraf kıpırdamaz."""
from collections import deque

import cv2
import numpy as np

KUCUK_GENISLIK = 320


class HareketKontrolu:
    """Her kutuyu `aralik_sn` saniye önceki kareyle karşılaştırır. Kutudaki piksellerin
    en az `oranlar[sinif]` kadarı `piksel_esigi`nden fazla değişmediyse kutu atılır."""

    def __init__(self, aralik_sn=2.0, piksel_esigi=15, oranlar=None):
        self.aralik_sn = aralik_sn
        self.piksel_esigi = piksel_esigi
        self.oranlar = oranlar or {"yangin": 0.01, "duman": 0.005}
        self.gecmis = deque()  # (zaman, küçültülmüş gri kare)

    def suz(self, kare, tespitler, zaman):
        olcek = KUCUK_GENISLIK / kare.shape[1]
        gri = cv2.cvtColor(cv2.resize(kare, None, fx=olcek, fy=olcek), cv2.COLOR_BGR2GRAY)
        gri = cv2.GaussianBlur(gri, (5, 5), 0)
        self.gecmis.append((zaman, gri))
        while len(self.gecmis) > 1 and self.gecmis[1][0] <= zaman - self.aralik_sn:
            self.gecmis.popleft()
        if self.gecmis[0][0] > zaman - self.aralik_sn:
            return []  # henüz karşılaştırılacak eski kare yok
        degisen = cv2.absdiff(gri, self.gecmis[0][1]) > self.piksel_esigi
        kalanlar = []
        for t in tespitler:
            x1, y1, x2, y2 = (int(v * olcek) for v in t.kutu)
            bolge = degisen[y1:max(y2, y1 + 1), x1:max(x2, x1 + 1)]
            if bolge.size and np.mean(bolge) >= self.oranlar[t.sinif]:
                kalanlar.append(t)
        return kalanlar
