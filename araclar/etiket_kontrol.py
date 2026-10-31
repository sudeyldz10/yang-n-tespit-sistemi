"""Veri setini kontrol eder ve rastgele görüntüleri etiketleriyle çizer.

- Görüntü ve etiket sayılarının eşleşip eşleşmediğini kontrol eder
- Sınıf başına kutu sayısını yazar
- Rastgele 12 görüntüyü kutularıyla bir tabloya çizip
  ekran_goruntuleri/etiket_kontrol.jpg olarak kaydeder

Kullanım (proje klasöründen):
    .venv/bin/python araclar/etiket_kontrol.py
"""
import random
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml

PROJE = Path(__file__).resolve().parent.parent
VERI = PROJE / "veri"
CIKTI = PROJE / "ekran_goruntuleri" / "etiket_kontrol.jpg"
RENKLER = {0: (0, 0, 255), 1: (200, 200, 200)}  # yangin: kırmızı, duman: gri (BGR)
KARE_BOYUTU = 400


def etiketleri_oku(dosya):
    kutular = []
    for satir in dosya.read_text().strip().splitlines():
        sinif, x, y, g, y_ = satir.split()
        kutular.append((int(sinif), float(x), float(y), float(g), float(y_)))
    return kutular


def kutulari_ciz(goruntu, kutular, isimler):
    yukseklik, genislik = goruntu.shape[:2]
    for sinif, xm, ym, g, y in kutular:
        x1, y1 = int((xm - g / 2) * genislik), int((ym - y / 2) * yukseklik)
        x2, y2 = int((xm + g / 2) * genislik), int((ym + y / 2) * yukseklik)
        renk = RENKLER.get(sinif, (0, 255, 0))
        kalinlik = max(2, genislik // 300)
        cv2.rectangle(goruntu, (x1, y1), (x2, y2), renk, kalinlik)
        cv2.putText(goruntu, isimler[sinif], (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, genislik / 800, renk, kalinlik)
    return goruntu


def main():
    isimler = yaml.safe_load((VERI / "yangin.yaml").read_text())["names"]
    ornekler = []

    for bolum in ("train", "val"):
        goruntuler = {f.stem for f in (VERI / "images" / bolum).glob("*.jpg")}
        etiketler = {f.stem for f in (VERI / "labels" / bolum).glob("*.txt")}
        sinif_sayaci, bos = Counter(), 0
        for ad in etiketler:
            kutular = etiketleri_oku(VERI / "labels" / bolum / f"{ad}.txt")
            bos += not kutular
            sinif_sayaci.update(k[0] for k in kutular)
            for k in kutular:
                assert all(0 <= v <= 1 for v in k[1:]), f"Koordinat 0-1 dışında: {ad}"

        print(f"[{bolum}] görüntü: {len(goruntuler)}, etiket: {len(etiketler)}, "
              f"eşleşiyor: {'EVET' if goruntuler == etiketler else 'HAYIR'}")
        print(f"   boş (yangın/duman yok): {bos}, kutular: "
              + ", ".join(f"{isimler[s]}={n}" for s, n in sorted(sinif_sayaci.items())))
        ornekler += [(bolum, ad) for ad in sorted(goruntuler & etiketler)]

    # Rastgele 12 etiketli görüntüyü 4x3 tabloya çiz
    secilenler = random.Random(1).sample(ornekler, 12)
    kareler = []
    for bolum, ad in secilenler:
        goruntu = cv2.imread(str(VERI / "images" / bolum / f"{ad}.jpg"))
        kutular = etiketleri_oku(VERI / "labels" / bolum / f"{ad}.txt")
        goruntu = kutulari_ciz(goruntu, kutular, isimler)
        kareler.append(cv2.resize(goruntu, (KARE_BOYUTU, KARE_BOYUTU)))
    satirlar = [np.hstack(kareler[i:i + 4]) for i in range(0, 12, 4)]
    cv2.imwrite(str(CIKTI), np.vstack(satirlar))
    print(f"Örnek çizim kaydedildi: {CIKTI.relative_to(PROJE)}")


if __name__ == "__main__":
    main()
