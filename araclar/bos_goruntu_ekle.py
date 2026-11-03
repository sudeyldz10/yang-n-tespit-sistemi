"""Modelin yanlışlıkla yangın/duman gördüğü boş görüntüleri veri setine ekler (%80/%20).

    .venv/bin/python araclar/bos_goruntu_ekle.py <aday_klasoru> --adet 450
"""
import argparse
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE))
import ayarlar  # noqa: E402
from kaynak.tespit import YanginDedektoru  # noqa: E402

VERI = PROJE / "veri"
TOHUM = 42
DOGRULAMA_ORANI = 0.2
TARAMA_ESIGI = 0.25  # zor negatif ararken kullanılan düşük güven eşiği
BENZERLIK_ESIGI = 8.0  # küçük gri kopyalar arasındaki ortalama fark bundan azsa "aynı" sayılır


def parmak_izi(yol):
    """Görüntünün 32x18 gri küçük kopyası; benzer kareleri bulmak için."""
    im = cv2.cvtColor(cv2.imread(str(yol)), cv2.COLOR_BGR2GRAY)
    return cv2.resize(im, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32)


class BenzerlikSuzgeci:
    def __init__(self):
        self.izler = []

    def yeni_mi(self, yol):
        iz = parmak_izi(yol)
        if any(np.abs(iz - eski).mean() < BENZERLIK_ESIGI for eski in self.izler):
            return False
        self.izler.append(iz)
        return True


def kaynak_turu(ad):
    """Dosya adının önekinden kaynağı bulur: AoF, PublicDataset, WEB."""
    for onek in ("AoF", "PublicDataset", "WEB"):
        if ad.startswith(onek):
            return onek
    return "diger"


def kontrol_resmi(secilenler, puanlar, cikti, adet=24):
    """Modelin en çok yanıldığı görüntülerden bir tablo resmi yapar (gözle kontrol için)."""
    kareler = []
    for p in secilenler[:adet]:
        im = cv2.resize(cv2.imread(str(p)), (320, 200))
        sinif, guven = puanlar[p.name]
        cv2.rectangle(im, (0, 0), (320, 24), (0, 0, 0), -1)
        cv2.putText(im, f"{sinif} {guven:.2f}" if sinif else "-", (5, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        kareler.append(im)
    while len(kareler) % 6:
        kareler.append(np.zeros((200, 320, 3), np.uint8))
    satirlar = [np.hstack(kareler[i:i + 6]) for i in range(0, len(kareler), 6)]
    cv2.imwrite(str(cikti), np.vstack(satirlar))


def main():
    ayrac = argparse.ArgumentParser(description="Veri setine boş görüntü ekle")
    ayrac.add_argument("kaynak", help="aday boş görüntülerin klasörü (jpg)")
    ayrac.add_argument("--adet", type=int, default=450, help="eklenecek görüntü sayısı")
    ayrac.add_argument("--sadece_sec", action="store_true", help="kopyalama, sadece seç ve göster")
    arguman = ayrac.parse_args()

    mevcut = {p.name for p in (VERI / "images").rglob("*.jpg")}
    adaylar = sorted(p for p in Path(arguman.kaynak).glob("*.jpg") if p.name not in mevcut)
    print(f"Aday: {len(adaylar)} görüntü (veri setinde olmayanlar)")

    # 1) Modeli düşük eşikle çalıştır, her görüntüdeki en yüksek güveni kaydet
    dedektor = YanginDedektoru(ayarlar.MODEL_YOLU, {"yangin": TARAMA_ESIGI, "duman": TARAMA_ESIGI},
                               ayarlar.GORUNTU_BOYUTU)
    puanlar = {}
    for i, p in enumerate(adaylar, 1):
        tespitler = dedektor.tespit_et(cv2.imread(str(p)))
        en_iyi = max(tespitler, key=lambda t: t.guven, default=None)
        puanlar[p.name] = (en_iyi.sinif, en_iyi.guven) if en_iyi else (None, 0.0)
        if i % 200 == 0:
            print(f"  taranan: {i}/{len(adaylar)}")

    # 2) Zor negatifler: modelin yanıldıkları, en yüksek güvenden başlayarak
    suzgec = BenzerlikSuzgeci()
    zorlar = sorted((p for p in adaylar if puanlar[p.name][0]), key=lambda p: -puanlar[p.name][1])
    zorlar = [p for p in zorlar if suzgec.yeni_mi(p)]  # neredeyse aynı kareleri ele
    secilenler = zorlar[: arguman.adet]

    # 3) Kalanı kaynak türlerine eşit dağıtarak rastgele doldur
    rastgele = random.Random(TOHUM)
    gruplar = defaultdict(list)
    for p in adaylar:
        if p not in secilenler:
            gruplar[kaynak_turu(p.name)].append(p)
    for liste in gruplar.values():
        rastgele.shuffle(liste)
    while len(secilenler) < arguman.adet and any(gruplar.values()):
        for tur in sorted(gruplar):
            if gruplar[tur] and len(secilenler) < arguman.adet:
                aday = gruplar[tur].pop()
                if suzgec.yeni_mi(aday):
                    secilenler.append(aday)

    yanilma = Counter(puanlar[p.name][0] for p in zorlar)
    print(f"Modelin yanıldığı (benzerleri elenmiş) görüntü: {len(zorlar)} (duman sandığı {yanilma['duman']}, "
          f"yangın sandığı {yanilma['yangin']})")
    print(f"Seçilen: {len(secilenler)} | kaynaklara göre: "
          + ", ".join(f"{k}={v}" for k, v in Counter(kaynak_turu(p.name) for p in secilenler).items()))

    cikti = PROJE / "ekran_goruntuleri" / "bos_kontrol.jpg"
    kontrol_resmi(zorlar or secilenler, puanlar, cikti)
    print(f"Kontrol resmi (modelin en çok yanıldıkları): {cikti.relative_to(PROJE)}")
    if arguman.sadece_sec:
        return

    # 4) %80 eğitim / %20 doğrulama olarak kopyala (boş etiket dosyasıyla)
    rastgele.shuffle(secilenler)
    dogrulama_sayisi = int(len(secilenler) * DOGRULAMA_ORANI)
    eklenen = []
    for i, p in enumerate(secilenler):
        bolum = "val" if i < dogrulama_sayisi else "train"
        shutil.copy2(p, VERI / "images" / bolum / p.name)
        (VERI / "labels" / bolum / f"{p.stem}.txt").write_text("")
        eklenen.append({"dosya": p.name, "bolum": bolum, "model_sandigi": puanlar[p.name][0],
                        "guven": round(puanlar[p.name][1], 3)})
    kayit = VERI / "eklenen_bos_goruntuler.json"
    kayit.write_text(json.dumps(eklenen, ensure_ascii=False, indent=1))
    print(f"Eklendi: eğitim {len(secilenler) - dogrulama_sayisi}, doğrulama {dogrulama_sayisi}. "
          f"Liste: {kayit.relative_to(PROJE)}")


if __name__ == "__main__":
    main()
