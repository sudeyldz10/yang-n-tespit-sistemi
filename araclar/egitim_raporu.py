"""Eğitim sırasında her N turda egitimler/<ad>/rapor/ içine Excel raporu ve detaylar.json yazar.

    .venv/bin/python araclar/egitim_raporu.py egitimler/asil/rapor/detaylar.json   # raporu yeniden üret
"""
import json
import shutil
import platform
import time
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Renkler (sabit sırayla, renk körlüğü için doğrulanmış palet)
MAVI, TURUNCU, CAMGOBEGI, SARI = "2A78D6", "EB6834", "1BAF7A", "EDA100"
SINIF_RENKLERI = {"yangin": "E34948", "duman": "6250D6"}  # kırmızı, mor

YAZI_TIPI = "Arial"
BASLIK = Font(name=YAZI_TIPI, bold=True, color="FFFFFF")
BASLIK_ZEMIN = PatternFill("solid", fgColor="3A3936")
KALIN = Font(name=YAZI_TIPI, bold=True)
NORMAL = Font(name=YAZI_TIPI)
BUYUK = Font(name=YAZI_TIPI, bold=True, size=14)
VURGU_ZEMIN = PatternFill("solid", fgColor="F1F0EC")
INCE = Side(style="thin", color="D9D8D3")
KENAR = Border(bottom=INCE)

# Turlar sayfasının sütunları: (başlık, kaynak anahtar veya None=formül, sayı biçimi)
TUR_SUTUNLARI = [
    ("Tur", "tur", "0"),
    ("Tur süresi (sn)", "sure_sn", "0.0"),
    ("Geçen süre (dk)", "toplam_sure_dk", "0.0"),
    ("Precision", "metrics/precision(B)", "0.000"),
    ("Recall", "metrics/recall(B)", "0.000"),
    ("mAP50", "metrics/mAP50(B)", "0.000"),
    ("mAP50-95", "metrics/mAP50-95(B)", "0.000"),
    ("Eğitim box kaybı", "train/box_loss", "0.000"),
    ("Eğitim cls kaybı", "train/cls_loss", "0.000"),
    ("Eğitim dfl kaybı", "train/dfl_loss", "0.000"),
    ("Doğrulama box kaybı", "val/box_loss", "0.000"),
    ("Doğrulama cls kaybı", "val/cls_loss", "0.000"),
    ("Doğrulama dfl kaybı", "val/dfl_loss", "0.000"),
    ("Toplam eğitim kaybı", None, "0.000"),       # = H+I+J
    ("Toplam doğrulama kaybı", None, "0.000"),    # = K+L+M
    ("Öğrenme hızı", "lr/pg0", "0.000000"),
]
SINIF_ALANLARI = ["precision", "recall", "mAP50", "mAP50-95"]
# Sütun harfleri
S = {ad: get_column_letter(i + 1) for i, (ad, _, _) in enumerate(TUR_SUTUNLARI)}


def _toplam_kayip(g, onek):
    """box + cls + dfl kayıplarının toplamı (onek: 'train' veya 'val')."""
    return round(g[f"{onek}/box_loss"] + g[f"{onek}/cls_loss"] + g[f"{onek}/dfl_loss"], 5)


def _sinif_degeri(g, sinif, alan, sinif_gecmisi):
    deger = g.get(f"{sinif}/{alan}")
    if deger is None:
        deger = sinif_gecmisi.get(g["tur"], {}).get(sinif, {}).get(alan)
    return deger


def _baslik_satiri(sayfa, satir, basliklar):
    for i, metin in enumerate(basliklar, start=1):
        h = sayfa.cell(row=satir, column=i, value=metin)
        h.font, h.fill = BASLIK, BASLIK_ZEMIN
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    sayfa.row_dimensions[satir].height = 46


def _genislik(sayfa, genislikler):
    for i, g in enumerate(genislikler, start=1):
        sayfa.column_dimensions[get_column_letter(i)].width = g


def _cizgi_grafigi(baslik, y_baslik, y_aralik=None):
    g = LineChart()
    g.title = baslik
    g.y_axis.title = y_baslik
    g.x_axis.title = "Tur (epoch)"
    g.height, g.width = 9, 17
    g.legend.position = "t"  # üstte: eksen yazılarıyla çakışmasın
    g.x_axis.delete = False
    g.y_axis.delete = False
    g.y_axis.number_format = "0.00"
    if y_aralik:
        g.y_axis.scaling.min, g.y_axis.scaling.max = y_aralik
    return g


def _seri_renkle(seri, renk, isaretci=False):
    seri.graphicalProperties.line.solidFill = renk
    seri.graphicalProperties.line.width = 25400  # 2 pt
    seri.smooth = False
    if isaretci:
        seri.marker.symbol = "circle"
        seri.marker.size = 8
        seri.marker.graphicalProperties.solidFill = renk
        seri.marker.graphicalProperties.line.solidFill = "FFFFFF"
    else:
        seri.marker.symbol = "none"


def excel_olustur(gecmis, sinif_gecmisi, bilgi, cikti, aralik, son_degerlendirme=None):
    """gecmis: her tur için değer sözlüğü; sinif_gecmisi: {tur: {sınıf: {...}}};
    bilgi: {'ad', 'toplam_tur', 'cihaz', 'ayarlar': {...}, ...}"""
    kitap = Workbook()
    ozet = kitap.active
    ozet.title = "Özet"
    turlar = kitap.create_sheet("Turlar")
    siniflar = kitap.create_sheet("Sınıflar")
    grafikler = kitap.create_sheet("Grafikler")
    ayarlar = kitap.create_sheet("Ayarlar")

    # ---- Turlar: her turun ham değerleri ----
    sinif_adlari = list(next(iter(sinif_gecmisi.values()))) if sinif_gecmisi else []
    _baslik_satiri(turlar, 1, [b for b, _, _ in TUR_SUTUNLARI]
                   + [f"{s} {a}" for s in sinif_adlari for a in SINIF_ALANLARI])
    son_satir = len(gecmis) + 1
    for r, g in enumerate(gecmis, start=2):
        for c, (ad, anahtar, bicim) in enumerate(TUR_SUTUNLARI, start=1):
            if anahtar is not None:
                deger = g.get(anahtar)
            elif ad == "Toplam eğitim kaybı":
                deger = _toplam_kayip(g, "train")
            else:
                deger = _toplam_kayip(g, "val")
            h = turlar.cell(row=r, column=c, value=deger)
            h.number_format, h.font, h.border = bicim, NORMAL, KENAR
        sutun = len(TUR_SUTUNLARI) + 1
        for sinif in sinif_adlari:
            for alan in SINIF_ALANLARI:
                h = turlar.cell(row=r, column=sutun, value=_sinif_degeri(g, sinif, alan, sinif_gecmisi))
                h.number_format, h.font, h.border = "0.000", NORMAL, KENAR
                sutun += 1
        if g["tur"] % aralik == 0:  # kontrol turlarını vurgula
            for c in range(1, sutun):
                turlar.cell(row=r, column=c).fill = VURGU_ZEMIN
                turlar.cell(row=r, column=c).font = KALIN
    turlar.freeze_panes = "B2"
    _genislik(turlar, [7, 10, 10] + [11] * 12 + [13] + [11] * (len(sinif_adlari) * len(SINIF_ALANLARI)))

    # ---- Sınıflar: kontrol turlarında sınıf bazında değerler ----
    _baslik_satiri(siniflar, 1, ["Tur", "Sınıf", "Precision", "Recall", "mAP50", "mAP50-95"])
    r = 2
    for tur in sorted(sinif_gecmisi):
        for sinif, d in sinif_gecmisi[tur].items():
            for c, v in enumerate([tur, sinif, d["precision"], d["recall"], d["mAP50"], d["mAP50-95"]], 1):
                h = siniflar.cell(row=r, column=c, value=v)
                h.font, h.border = NORMAL, KENAR
                if c > 2:
                    h.number_format = "0.000"
            r += 1
    # Grafik için geniş tablo: Tur | yangin mAP50 | duman mAP50
    genis_bas = 1
    siniflar.cell(row=genis_bas, column=8, value="Tur")
    for j, sinif in enumerate(sinif_adlari):
        siniflar.cell(row=genis_bas, column=9 + j, value=f"{sinif} mAP50")
    for c in range(8, 9 + len(sinif_adlari)):
        h = siniflar.cell(row=genis_bas, column=c)
        h.font, h.fill = BASLIK, BASLIK_ZEMIN
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    k_turlar = sorted(sinif_gecmisi)
    for i, tur in enumerate(k_turlar):
        rr = genis_bas + 1 + i
        siniflar.cell(row=rr, column=8, value=tur).font = NORMAL
        for j, sinif in enumerate(sinif_adlari):
            h = siniflar.cell(row=rr, column=9 + j, value=sinif_gecmisi[tur][sinif]["mAP50"])
            h.number_format, h.font = "0.000", NORMAL
    _genislik(siniflar, [7, 10, 11, 11, 11, 11, 3, 7, 14, 14])

    # ---- Özet ----
    ozet["A1"] = f"Eğitim raporu: {bilgi['ad']}"
    ozet["A1"].font = BUYUK
    en_iyi = max(gecmis, key=lambda g: g["metrics/mAP50(B)"])
    satirlar = [
        ("Son güncelleme", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Tamamlanan tur", gecmis[-1]["tur"]),
        ("Toplam tur", bilgi["toplam_tur"]),
        ("Geçen süre (dk)", gecmis[-1]["toplam_sure_dk"]),
        ("En iyi mAP50", en_iyi["metrics/mAP50(B)"]),
        ("En iyi mAP50 turu", en_iyi["tur"]),
        ("Cihaz", bilgi["cihaz"]),
        ("Görüntü boyutu / grup", f"{bilgi['ayarlar'].get('imgsz')} / {bilgi['ayarlar'].get('batch')}"),
    ]
    for i, (etiket, deger) in enumerate(satirlar, start=3):
        ozet.cell(row=i, column=1, value=etiket).font = KALIN
        h = ozet.cell(row=i, column=2, value=deger)
        h.font = NORMAL
        h.alignment = Alignment(horizontal="left")
        if etiket in ("En iyi mAP50",):
            h.number_format = "0.000"
        if etiket == "Geçen süre (dk)":
            h.number_format = "0.0"

    bas = 3 + len(satirlar) + 2
    ozet.cell(row=bas - 1, column=1, value=f"Her {aralik} turda genel değerler").font = KALIN
    _baslik_satiri(ozet, bas, ["Tur", "mAP50", "Değişim", "mAP50-95", "Precision", "Recall",
                               "Toplam eğitim kaybı", "Toplam doğrulama kaybı", "Geçen süre (dk)"])
    kontrol = [g for g in gecmis if g["tur"] % aralik == 0 or g["tur"] == gecmis[-1]["tur"]]
    onceki = None
    for i, g in enumerate(kontrol):
        rr = bas + 1 + i
        m = g["metrics/mAP50(B)"]
        degerler = [g["tur"], m,
                    "" if onceki is None else round(m - onceki, 5),
                    g["metrics/mAP50-95(B)"], g["metrics/precision(B)"], g["metrics/recall(B)"],
                    _toplam_kayip(g, "train"), _toplam_kayip(g, "val"), g["toplam_sure_dk"]]
        onceki = m
        for c, v in enumerate(degerler, start=1):
            h = ozet.cell(row=rr, column=c, value=v)
            h.font, h.border = NORMAL, KENAR
            h.number_format = "0" if c == 1 else ("0.000" if c == 3 else
                                                  ("0.0" if c == 9 else "0.000"))
    not_satiri = bas + len(kontrol) + 2
    ozet.cell(row=not_satiri, column=1, value=(
        "Not: Her turun tüm değerleri 'Turlar' sayfasında. Grafikler 'Grafikler' sayfasında. "
        f"Her {aralik} turdaki model weights/tur_NNN.pt olarak saklanır.")).font = Font(name=YAZI_TIPI, italic=True, color="52514E")

    # En iyi modelin (best.pt) eğitim sonundaki değerlendirmesi
    if son_degerlendirme:
        sb = not_satiri + 2
        ozet.cell(row=sb, column=1, value="En iyi model (best.pt) son değerlendirmesi").font = KALIN
        _baslik_satiri(ozet, sb + 1, ["Kapsam", "Precision", "Recall", "mAP50", "mAP50-95"])
        satirlar_sd = [("Genel", son_degerlendirme["genel"])] + list(son_degerlendirme["siniflar"].items())
        for i, (ad, d) in enumerate(satirlar_sd):
            rr = sb + 2 + i
            ozet.cell(row=rr, column=1, value=ad).font = KALIN if i == 0 else NORMAL
            for c, k in enumerate(["precision", "recall", "mAP50", "mAP50-95"], start=2):
                h = ozet.cell(row=rr, column=c, value=d[k])
                h.number_format, h.font, h.border = "0.000", NORMAL, KENAR
        her_tur_bas = sb + 2 + len(satirlar_sd) + 2
    else:
        her_tur_bas = not_satiri + 2

    # Her turun değerleri (kontrol turları kalın ve gri zeminli)
    ozet.cell(row=her_tur_bas, column=1, value="Her turun değerleri").font = KALIN
    basliklar = ["Tur", "mAP50", "Değişim", "mAP50-95", "Precision", "Recall",
                 "Toplam eğitim kaybı", "Toplam doğrulama kaybı", "Tur süresi (sn)"]
    basliklar += [f"{s} mAP50" for s in sinif_adlari]
    _baslik_satiri(ozet, her_tur_bas + 1, basliklar)
    onceki = None
    for i, g in enumerate(gecmis):
        rr = her_tur_bas + 2 + i
        m = g["metrics/mAP50(B)"]
        degerler = [g["tur"], m, "" if onceki is None else round(m - onceki, 5),
                    g["metrics/mAP50-95(B)"], g["metrics/precision(B)"], g["metrics/recall(B)"],
                    _toplam_kayip(g, "train"), _toplam_kayip(g, "val"), g.get("sure_sn")]
        degerler += [_sinif_degeri(g, s, "mAP50", sinif_gecmisi) for s in sinif_adlari]
        onceki = m
        for c, v in enumerate(degerler, start=1):
            h = ozet.cell(row=rr, column=c, value=v)
            h.border = KENAR
            h.number_format = "0" if c == 1 else ("0.0" if c == 9 else "0.000")
            kontrol_turu = g["tur"] % aralik == 0
            h.font = KALIN if kontrol_turu else NORMAL
            if kontrol_turu:
                h.fill = VURGU_ZEMIN
    _genislik(ozet, [24, 18, 10, 11, 11, 11, 13, 14, 11, 12, 12])

    # ---- Grafikler (Excel'in kendi grafikleri) ----
    x = Reference(turlar, min_col=1, min_row=2, max_row=son_satir)

    def sutun_ref(ad):
        c = [b for b, _, _ in TUR_SUTUNLARI].index(ad) + 1
        return Reference(turlar, min_col=c, min_row=1, max_row=son_satir)

    g1 = _cizgi_grafigi("Doğrulama başarısı (her tur)", "Değer (0–1)", (0, 1))
    for ad, renk in [("mAP50", MAVI), ("mAP50-95", TURUNCU), ("Precision", CAMGOBEGI), ("Recall", SARI)]:
        g1.add_data(sutun_ref(ad), titles_from_data=True)
        _seri_renkle(g1.series[-1], renk)
    g1.set_categories(x)
    grafikler.add_chart(g1, "A1")

    g2 = _cizgi_grafigi("Kayıp — düşük = iyi (doğrulama yükselirse ezber)", "Toplam kayıp")
    for ad, renk in [("Toplam eğitim kaybı", MAVI), ("Toplam doğrulama kaybı", TURUNCU)]:
        g2.add_data(sutun_ref(ad), titles_from_data=True)
        _seri_renkle(g2.series[-1], renk)
    g2.set_categories(x)
    grafikler.add_chart(g2, "L1")

    # Her N turda mAP50 (Özet tablosundan)
    g3 = _cizgi_grafigi(f"Her {aralik} turda mAP50", "mAP50", (0, 1))
    g3.add_data(Reference(ozet, min_col=2, min_row=bas, max_row=bas + len(kontrol)), titles_from_data=True)
    _seri_renkle(g3.series[-1], MAVI, isaretci=True)
    g3.set_categories(Reference(ozet, min_col=1, min_row=bas + 1, max_row=bas + len(kontrol)))
    grafikler.add_chart(g3, "A20")

    if sinif_adlari:
        g4 = _cizgi_grafigi(f"Sınıf bazında mAP50 (her {aralik} turda)", "mAP50", (0, 1))
        for j, sinif in enumerate(sinif_adlari):
            g4.add_data(Reference(siniflar, min_col=9 + j, min_row=genis_bas,
                                  max_row=genis_bas + len(k_turlar)), titles_from_data=True)
            _seri_renkle(g4.series[-1], SINIF_RENKLERI.get(sinif, SARI), isaretci=True)
        g4.set_categories(Reference(siniflar, min_col=8, min_row=genis_bas + 1,
                                    max_row=genis_bas + len(k_turlar)))
        grafikler.add_chart(g4, "L20")

    # ---- Ayarlar ----
    _baslik_satiri(ayarlar, 1, ["Ayar", "Değer"])
    sabitler = [("Cihaz", bilgi["cihaz"]), ("İşlemci", bilgi.get("islemci", "")),
                ("Sistem", bilgi.get("sistem", "")), ("Python", bilgi.get("python", ""))]
    sabitler += sorted(bilgi["ayarlar"].items())
    for i, (k, v) in enumerate(sabitler, start=2):
        ayarlar.cell(row=i, column=1, value=k).font = KALIN
        ayarlar.cell(row=i, column=2, value=str(v)).font = NORMAL
    _genislik(ayarlar, [22, 80])

    _testler_sayfasi(kitap, Path(cikti).parents[2] / "test_degerlendirme")
    kitap.save(cikti)


def _testler_sayfasi(kitap, klasor):
    """egitimler/test_degerlendirme/ içindeki test seti ve video sonuçlarını 'Testler' sayfasına yazar."""
    test_yolu, video_yolu = klasor / "sonuclar.json", klasor / "video_testleri.json"
    if not test_yolu.exists() and not video_yolu.exists():
        return
    sayfa = kitap.create_sheet("Testler", index=len(kitap.sheetnames) - 1)
    satir = 1
    if test_yolu.exists():
        testler = json.loads(test_yolu.read_text())
        ilk = next(iter(testler.values()))
        sayfa.cell(row=satir, column=1, value=(
            f"D-Fire test seti: {ilk['goruntu']} görüntü ({ilk['bos']} boş), eğitimde hiç kullanılmadı")).font = KALIN
        satir += 1
        _baslik_satiri(sayfa, satir, ["Model", "Precision", "Recall", "mAP50", "mAP50-95", "Yangın mAP50",
                                      "Duman mAP50", "Yangın bulundu", "Duman bulundu", "Boşta yanlış tespit"])
        for ad, t in testler.items():
            satir += 1
            g, sn, a = t["genel"], t["siniflar"], t["alarm"]
            degerler = [ad, g["precision"], g["recall"], g["mAP50"], g["mAP50-95"], sn["yangin"]["mAP50"],
                        sn["duman"]["mAP50"], a["yangin_var"], a["duman_var"], a["bos"]]
            for c, v in enumerate(degerler, start=1):
                h = sayfa.cell(row=satir, column=c, value=v)
                h.font, h.border = (KALIN if c == 1 else NORMAL), KENAR
                h.number_format = "0%" if c >= 8 else "0.000"
        satir += 3
    if video_yolu.exists():
        sayfa.cell(row=satir, column=1, value="Video testleri").font = KALIN
        satir += 1
        _baslik_satiri(sayfa, satir, ["Video", "Model", "İlk alarm (sn)", "Alarmlı süre", "Sonuç"])
        sayfa.merge_cells(start_row=satir, start_column=5, end_row=satir, end_column=10)
        for v in json.loads(video_yolu.read_text()):
            satir += 1
            degerler = [v["video"], v["model"], v["ilk_alarm_sn"] if v["ilk_alarm_sn"] is not None else "yok",
                        v["alarmli_sure"], v["sonuc"]]
            for c, d in enumerate(degerler, start=1):
                h = sayfa.cell(row=satir, column=c, value=d)
                h.font, h.border = NORMAL, KENAR
                if c == 3:
                    h.number_format = "0.0"
                if c == 4:
                    h.number_format = "0%"
            sayfa.merge_cells(start_row=satir, start_column=5, end_row=satir, end_column=10)  # sonuç metni geniş
    _genislik(sayfa, [44, 11, 13, 12, 11, 13, 13, 14, 14, 16])


class EgitimRaporu:
    """Ultralytics eğitimine eklenen geri çağırma (callback)."""

    def __init__(self, aralik=10, oturum_turu=0):
        self.aralik = aralik
        self.oturum_turu = oturum_turu  # bu çalıştırmada en fazla kaç tur (0 = sınırsız)
        self.oturum_sayaci = 0
        self.onceki_sure_dk = 0.0  # önceki günlerin toplam eğitim süresi
        self.gecmis = []          # her tur
        self.sinif_gecmisi = {}   # sadece kontrol turları
        self.son_degerlendirme = None  # eğitim sonunda best.pt değerlendirmesi
        self.tur_suruyor = False  # normal tur mu, son değerlendirme mi ayırt etmek için
        self.bilgi = None
        self.baslangic = time.time()
        self.tur_baslangic = time.time()

    def onceki_kaydi_yukle(self, yol):
        """Kaldığı yerden devam ederken önceki günlerin kayıtlarını yükler."""
        yol = Path(yol)
        if not yol.exists():
            print(f"[rapor] UYARI: {yol} bulunamadı, rapor bu turdan itibaren başlayacak.")
            return
        eski = json.loads(yol.read_text())
        self.gecmis = eski.get("turlar", [])
        self.sinif_gecmisi = {int(t): d for t, d in eski.get("sinif_bazinda", {}).items()}
        if self.gecmis:
            self.onceki_sure_dk = self.gecmis[-1]["toplam_sure_dk"]
        print(f"[rapor] önceki kayıt yüklendi: {len(self.gecmis)} tur")

    def tur_basi(self, egitici):
        self.tur_baslangic = time.time()
        self.tur_suruyor = True

    def tur_sonu(self, egitici):
        if not self.tur_suruyor:  # tur başlamadan gelen çağrı = eğitim sonu değerlendirmesi
            self._son_degerlendirme(egitici)
            return
        self.tur_suruyor = False
        tur = egitici.epoch + 1
        # Devam ederken, kaydedilen noktadan sonraki eski turlar varsa at (tekrar yapılıyorlar)
        self.gecmis = [g for g in self.gecmis if g["tur"] < tur]
        self.sinif_gecmisi = {t: d for t, d in self.sinif_gecmisi.items() if t < tur}
        kayit = {"tur": tur, "sure_sn": round(time.time() - self.tur_baslangic, 1),
                 "toplam_sure_dk": round(self.onceki_sure_dk + (time.time() - self.baslangic) / 60, 2)}
        kayit.update(egitici.label_loss_items(egitici.tloss, prefix="train"))
        kayit.update(egitici.metrics)
        kayit.update(egitici.lr)
        kayit = {k: (round(float(v), 5) if not isinstance(v, (int, str)) else v)
                 for k, v in kayit.items()}
        try:  # sınıf bazında değerler (yangin/duman) her turda
            for sinif, d in self._sinif_degerleri(egitici).items():
                for alan in ("precision", "recall", "mAP50", "mAP50-95"):
                    kayit[f"{sinif}/{alan}"] = d[alan]
        except Exception as hata:
            print(f"[rapor] UYARI: tur {tur} sınıf değerleri okunamadı: {hata!r}")
        self.gecmis.append(kayit)

        # Günlük sınır: bu çalıştırmada istenen tur sayısına ulaşıldı mı?
        self.oturum_sayaci += 1
        oturum_bitiyor = bool(self.oturum_turu) and self.oturum_sayaci >= self.oturum_turu

        # Kontrol turu: her N turda, son turda ve oturum biterken (devam edebilmek için şart)
        if tur % self.aralik == 0 or tur == egitici.epochs or oturum_bitiyor:
            try:
                self.sinif_gecmisi[tur] = self._sinif_degerleri(egitici)
                # O anki modeli (last.pt) tur numarasıyla sakla
                shutil.copy2(egitici.last, Path(egitici.wdir) / f"tur_{tur:03d}.pt")
                self._kaydet(egitici, tur)
            except Exception as hata:  # rapor hatası eğitimi durdurmasın
                print(f"[rapor] UYARI: tur {tur} raporu yazılamadı: {hata!r}")

        if oturum_bitiyor and tur < egitici.epochs:
            print(f"[rapor] bu oturumda {self.oturum_sayaci} tur yapıldı, eğitim duruyor (tur {tur}).")
            egitici.stop = True

    @staticmethod
    def _sinif_degerleri(egitici):
        metrikler = egitici.validator.metrics
        isimler = egitici.data["names"]
        sonuc = {}
        for i, sinif_no in enumerate(metrikler.box.ap_class_index):
            p, r, ap50, ap = metrikler.class_result(i)
            sonuc[isimler[int(sinif_no)]] = {
                "precision": round(float(p), 4), "recall": round(float(r), 4),
                "mAP50": round(float(ap50), 4), "mAP50-95": round(float(ap), 4)}
        return sonuc

    def _son_degerlendirme(self, egitici):
        try:
            m = egitici.metrics
            self.son_degerlendirme = {
                "genel": {"precision": round(float(m["metrics/precision(B)"]), 4),
                          "recall": round(float(m["metrics/recall(B)"]), 4),
                          "mAP50": round(float(m["metrics/mAP50(B)"]), 4),
                          "mAP50-95": round(float(m["metrics/mAP50-95(B)"]), 4)},
                "siniflar": self._sinif_degerleri(egitici)}
            self._kaydet(egitici, self.gecmis[-1]["tur"])
            print("[rapor] en iyi modelin son değerlendirmesi rapora eklendi")
        except Exception as hata:
            print(f"[rapor] UYARI: son değerlendirme yazılamadı: {hata!r}")

    def _kaydet(self, egitici, tur):
        klasor = Path(egitici.save_dir) / "rapor"
        klasor.mkdir(exist_ok=True)
        ayarlar = {k: (v if isinstance(v, (int, float, bool, type(None))) else str(v))
                   for k, v in vars(egitici.args).items()}
        bilgi = {"ad": Path(egitici.save_dir).name, "toplam_tur": egitici.epochs,
                 "cihaz": str(egitici.device), "islemci": platform.processor(),
                 "sistem": platform.platform(), "python": platform.python_version(),
                 "ayarlar": ayarlar}

        excel_olustur(self.gecmis, self.sinif_gecmisi, bilgi,
                      klasor / "egitim_raporu.xlsx", self.aralik, self.son_degerlendirme)
        detay = dict(bilgi, guncelleme=datetime.now().isoformat(timespec="seconds"),
                     tamamlanan_tur=tur, sinif_bazinda=self.sinif_gecmisi,
                     son_degerlendirme=self.son_degerlendirme, turlar=self.gecmis)
        (klasor / "detaylar.json").write_text(json.dumps(detay, ensure_ascii=False, indent=2))
        print(f"[rapor] tur {tur}: Excel raporu kaydedildi -> {klasor / 'egitim_raporu.xlsx'}")

    def ekle(self, model):
        model.add_callback("on_train_epoch_start", self.tur_basi)
        model.add_callback("on_fit_epoch_end", self.tur_sonu)


if __name__ == "__main__":
    # Kayıtlı detaylar.json dosyasından Excel raporunu yeniden üretir:
    #   .venv/bin/python araclar/egitim_raporu.py egitimler/asil/rapor/detaylar.json
    import sys
    yol = Path(sys.argv[1])
    d = json.loads(yol.read_text())
    sinif = {int(t): v for t, v in d.get("sinif_bazinda", {}).items()}
    aralik = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    excel_olustur(d["turlar"], sinif, d, yol.parent / "egitim_raporu.xlsx", aralik,
                  d.get("son_degerlendirme"))
    print(f"Yeniden oluşturuldu: {yol.parent / 'egitim_raporu.xlsx'}")
