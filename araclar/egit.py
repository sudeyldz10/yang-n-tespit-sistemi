"""Modeli eğitir. Her 10 turda Excel raporu yazar ve modeli weights/tur_NNN.pt olarak saklar.

    .venv/bin/python araclar/egit.py --tur 50 --ad asil
    .venv/bin/python araclar/egit.py --ad asil --devam --oturum_turu 10   # kaldığı yerden 10 tur
"""
import argparse
import sys
from pathlib import Path

import torch
from ultralytics import YOLO

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE / "araclar"))
from egitim_raporu import EgitimRaporu  # noqa: E402


def en_son_kayit(ad):
    """weights/tur_NNN.pt dosyalarından en büyük tur numaralısını döndürür."""
    kayitlar = sorted((PROJE / "egitimler" / ad / "weights").glob("tur_*.pt"))
    return kayitlar[-1] if kayitlar else None


def yollari_duzelt(kayit, ad):
    """Proje klasörü taşındıysa/yeniden adlandırıldıysa, kayıtlı eğitim dosyasındaki
    eski yolları (veri seti, çıktı klasörü, model) bu klasöre göre düzeltir.
    Ultralytics devam ederken bu yolları kullandığı için gerekli."""
    ckpt = torch.load(kayit, map_location="cpu", weights_only=False)
    ayarlar = ckpt["train_args"]
    dogru = {
        "data": str(PROJE / "veri" / "yangin.yaml"),
        "project": str(PROJE / "egitimler"),
        "save_dir": str(PROJE / "egitimler" / ad),
        "model": str(PROJE / "yolov8n.pt"),
    }
    degisen = {k: v for k, v in dogru.items() if ayarlar.get(k) not in (None, v)}
    if not degisen:
        return
    for k, v in degisen.items():
        print(f"Yol düzeltildi ({k}): {ayarlar[k]} -> {v}")
        ayarlar[k] = v
    torch.save(ckpt, kayit)


def main():
    ayrac = argparse.ArgumentParser(description="Yangın/duman modeli eğitimi")
    ayrac.add_argument("--tur", type=int, default=50, help="toplam eğitim turu (epoch) sayısı")
    ayrac.add_argument("--ad", default="asil", help="sonuç klasörünün adı")
    ayrac.add_argument("--grup", type=int, default=16, help="grup boyutu (batch)")
    ayrac.add_argument("--rapor_araligi", type=int, default=10,
                       help="kaç turda bir Excel raporu yazılıp model saklanacağı")
    ayrac.add_argument("--devam", action="store_true",
                       help="en son kaydedilen turdan (weights/tur_NNN.pt) devam et")
    ayrac.add_argument("--oturum_turu", type=int, default=0,
                       help="bu çalıştırmada en fazla kaç tur yapılacağı (0 = sınırsız)")
    arguman = ayrac.parse_args()

    # Mac'te Apple GPU'su (MPS), yoksa NVIDIA GPU, o da yoksa işlemci
    if torch.backends.mps.is_available():
        cihaz = "mps"
    elif torch.cuda.is_available():
        cihaz = 0
    else:
        cihaz = "cpu"
    print(f"Eğitim cihazı: {cihaz}")

    klasor = PROJE / "egitimler" / arguman.ad
    rapor = EgitimRaporu(aralik=arguman.rapor_araligi, oturum_turu=arguman.oturum_turu)

    if arguman.devam:
        kayit = en_son_kayit(arguman.ad)
        if kayit is None:
            raise SystemExit(f"{klasor}/weights içinde tur_NNN.pt bulunamadı, devam edilemiyor.")
        tamamlanan = torch.load(kayit, map_location="cpu", weights_only=False)["epoch"] + 1
        toplam = torch.load(kayit, map_location="cpu", weights_only=False)["train_args"]["epochs"]
        if tamamlanan >= toplam:
            print(f"EGITIM_TAMAMLANDI: {toplam} turun hepsi zaten bitmiş ({kayit.name}).")
            return
        print(f"Devam: {kayit.name} (tamamlanan tur {tamamlanan}/{toplam})")
        yollari_duzelt(kayit, arguman.ad)
        rapor.onceki_kaydi_yukle(klasor / "rapor" / "detaylar.json")
        model = YOLO(str(kayit))
        rapor.ekle(model)
        model.train(resume=True, device=cihaz, workers=4)
    else:
        model = YOLO(str(PROJE / "yolov8n.pt"))  # hazır modelden başlayarak eğit
        rapor.ekle(model)
        model.train(
            data=str(PROJE / "veri" / "yangin.yaml"),
            epochs=arguman.tur,
            imgsz=640,
            batch=arguman.grup,
            device=cihaz,
            project=str(PROJE / "egitimler"),
            name=arguman.ad,
            exist_ok=True,
            workers=4,
            seed=42,
        )

    son = rapor.gecmis[-1]["tur"] if rapor.gecmis else None
    print(f"OTURUM_BITTI: son tamamlanan tur = {son}")


if __name__ == "__main__":
    main()
