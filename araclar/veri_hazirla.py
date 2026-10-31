"""D-Fire görüntülerini eğitim (%80) ve doğrulama (%20) olarak veri/ klasörüne yerleştirir.

D-Fire'da sınıflar 0 = duman, 1 = yangın şeklindedir. Bizim yangin.yaml dosyamızda
0 = yangin, 1 = duman olduğu için etiketlerdeki sınıf numaraları yer değiştirilir.

Kullanım (proje klasöründen):
    .venv/bin/python araclar/veri_hazirla.py <kaynak_klasor>

<kaynak_klasor> içinde images/ (jpg) ve labels/ (txt) klasörleri olmalı.
"""
import random
import shutil
import sys
from pathlib import Path

DOGRULAMA_ORANI = 0.2
TOHUM = 42  # aynı bölünmeyi tekrar elde etmek için sabit rastgelelik
SINIF_DONUSUMU = {"0": "1", "1": "0"}  # D-Fire -> bizim sıralamamız

PROJE = Path(__file__).resolve().parent.parent
VERI = PROJE / "veri"


def hedef_klasorler_bos_mu():
    for tur in ("images", "labels"):
        for bolum in ("train", "val"):
            dosyalar = [f for f in (VERI / tur / bolum).iterdir() if f.name != ".gitkeep"]
            if dosyalar:
                return False
    return True


def etiketi_donustur(metin):
    satirlar = []
    for satir in metin.strip().splitlines():
        parcalar = satir.split()
        if len(parcalar) != 5:
            raise ValueError(f"Hatalı etiket satırı: {satir!r}")
        parcalar[0] = SINIF_DONUSUMU[parcalar[0]]
        satirlar.append(" ".join(parcalar))
    return "\n".join(satirlar) + ("\n" if satirlar else "")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    kaynak = Path(sys.argv[1])
    if not hedef_klasorler_bos_mu():
        raise SystemExit("veri/images veya veri/labels boş değil. Önce içlerini temizle.")

    goruntuler = sorted((kaynak / "images").glob("*.jpg"))
    random.Random(TOHUM).shuffle(goruntuler)
    dogrulama_sayisi = int(len(goruntuler) * DOGRULAMA_ORANI)
    bolumler = {"val": goruntuler[:dogrulama_sayisi], "train": goruntuler[dogrulama_sayisi:]}

    for bolum, liste in bolumler.items():
        for goruntu in liste:
            etiket = kaynak / "labels" / (goruntu.stem + ".txt")
            metin = etiket.read_text() if etiket.exists() else ""
            shutil.copy2(goruntu, VERI / "images" / bolum / goruntu.name)
            (VERI / "labels" / bolum / etiket.name).write_text(etiketi_donustur(metin))
        print(f"{bolum}: {len(liste)} görüntü")


if __name__ == "__main__":
    main()
