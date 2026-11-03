"""Modeli D-Fire test görüntülerinde ölçer; sonuçlar egitimler/test_degerlendirme/sonuclar.json.

    .venv/bin/python araclar/test_degerlendir.py <test_klasoru> "40. tur=modeller/best.pt"
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import cv2
import yaml
from ultralytics import YOLO

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE))
import ayarlar  # noqa: E402

SINIF_DONUSUMU = {"0": "1", "1": "0"}  # D-Fire (0 duman, 1 yangın) -> bizim (0 yangin, 1 duman)
CIKTI = PROJE / "egitimler" / "test_degerlendirme"


def veri_seti_hazirla(kaynak):
    """D-Fire biçimindeki klasörü, sınıfları çevirerek YOLO'nun okuyacağı yapıya kopyalar."""
    hedef = CIKTI / "veri"
    if hedef.exists():
        shutil.rmtree(hedef)
    (hedef / "images" / "val").mkdir(parents=True)
    (hedef / "labels" / "val").mkdir(parents=True)
    for goruntu in sorted((Path(kaynak) / "images").glob("*.jpg")):
        shutil.copy2(goruntu, hedef / "images" / "val" / goruntu.name)
        etiket = Path(kaynak) / "labels" / f"{goruntu.stem}.txt"
        satirlar = []
        for satir in (etiket.read_text().strip().splitlines() if etiket.exists() else []):
            parca = satir.split()
            parca[0] = SINIF_DONUSUMU[parca[0]]
            satirlar.append(" ".join(parca))
        (hedef / "labels" / "val" / f"{goruntu.stem}.txt").write_text("\n".join(satirlar))
    ayar = {"path": str(hedef), "train": "images/val", "val": "images/val",
            "names": {0: "yangin", 1: "duman"}}
    yaml_yolu = hedef / "test.yaml"
    yaml_yolu.write_text(yaml.safe_dump(ayar, allow_unicode=True))
    return hedef, yaml_yolu


def alarm_olcumu(model, veri):
    """Görüntü bazında: eşiklerle tespit var mı? Pozitif/boş görüntülere göre oranlar."""
    esikler = ayarlar.GUVEN_ESIKLERI
    sayac = {"yangin_var": [0, 0], "duman_var": [0, 0], "herhangi": [0, 0], "bos": [0, 0]}
    for goruntu in sorted((veri / "images" / "val").glob("*.jpg")):
        etiket = (veri / "labels" / "val" / f"{goruntu.stem}.txt").read_text().split()
        gercek = {"yangin": "0" in etiket[0::5], "duman": "1" in etiket[0::5]}
        sonuc = model(cv2.imread(str(goruntu)), conf=min(esikler.values()), imgsz=ayarlar.GORUNTU_BOYUTU,
                      verbose=False)[0]
        bulunan = {"yangin": False, "duman": False}
        for k, g in zip(sonuc.boxes.cls.tolist(), sonuc.boxes.conf.tolist()):
            ad = sonuc.names[int(k)]
            if g >= esikler[ad]:
                bulunan[ad] = True
        if gercek["yangin"]:
            sayac["yangin_var"][0] += bulunan["yangin"]; sayac["yangin_var"][1] += 1
        if gercek["duman"]:
            sayac["duman_var"][0] += bulunan["duman"]; sayac["duman_var"][1] += 1
        if gercek["yangin"] or gercek["duman"]:
            sayac["herhangi"][0] += bulunan["yangin"] or bulunan["duman"]; sayac["herhangi"][1] += 1
        else:
            sayac["bos"][0] += bulunan["yangin"] or bulunan["duman"]; sayac["bos"][1] += 1
    return {k: (a / n if n else 0.0, a, n) for k, (a, n) in sayac.items()}


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    veri, yaml_yolu = veri_seti_hazirla(sys.argv[1])
    goruntu = len(list((veri / "images" / "val").glob("*.jpg")))
    bos = sum(1 for p in (veri / "labels" / "val").glob("*.txt") if not p.read_text().strip())
    print(f"Test seti: {goruntu} görüntü ({bos} boş)")

    kayit_yolu = CIKTI / "sonuclar.json"
    kayitlar = json.loads(kayit_yolu.read_text()) if kayit_yolu.exists() else {}
    for arguman in sys.argv[2:]:
        etiket, _, model_yolu = arguman.rpartition("=")  # "40. tur=modeller/best.pt" ya da sadece yol
        etiket = etiket or Path(model_yolu).stem
        model = YOLO(model_yolu)
        m = model.val(data=str(yaml_yolu), split="val", imgsz=ayarlar.GORUNTU_BOYUTU, batch=16,
                      plots=False, verbose=False, project=str(CIKTI), name="val", exist_ok=True)
        a = alarm_olcumu(model, veri)
        sonuc = {"tarih": f"{datetime.now():%Y-%m-%d %H:%M}", "goruntu": goruntu, "bos": bos,
                 "esikler": ayarlar.GUVEN_ESIKLERI,
                 "genel": {"precision": m.box.mp, "recall": m.box.mr, "mAP50": m.box.map50, "mAP50-95": m.box.map},
                 "siniflar": {}, "alarm": {k: v[0] for k, v in a.items()}}
        for i, sinif_no in enumerate(m.box.ap_class_index):
            p, r, ap50, ap = m.class_result(i)
            sonuc["siniflar"][m.names[int(sinif_no)]] = {"precision": p, "recall": r, "mAP50": ap50, "mAP50-95": ap}
        kayitlar[etiket] = sonuc
        print(f"{etiket}: mAP50 {m.box.map50:.3f} | yangın bulundu %{100*a['yangin_var'][0]:.0f} | "
              f"duman bulundu %{100*a['duman_var'][0]:.0f} | boşta yanlış %{100*a['bos'][0]:.0f}")
    shutil.rmtree(veri)
    kayit_yolu.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1, default=float))
    print(f"Kaydedildi: {kayit_yolu.relative_to(PROJE)}")


if __name__ == "__main__":
    main()
