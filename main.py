"""Orman Yangını Erken Tespit Sistemi.

    .venv/bin/python main.py                          # kamera
    .venv/bin/python main.py --kaynak videolar/x.mp4  # video dosyası

Çıkmak için pencerede 'q'.
"""
import argparse
import time
from pathlib import Path

import cv2

import ayarlar
from kaynak.alarm import AlarmKaydedici, SesliUyari
from kaynak.hareket import HareketKontrolu
from kaynak.kamera import Kamera
from kaynak.tespit import AlarmKarari, YanginDedektoru


def serit_yuksekligi(kare):
    return max(32, kare.shape[1] // 25)


def ust_bilgi_ciz(kare, alarm, fps, tespit_sayisi):
    genislik, h = kare.shape[1], serit_yuksekligi(kare)
    renk, yazi, yazi_rengi = ((0, 0, 220), "YANGIN ALARMI", (255, 255, 255)) if alarm else \
        ((40, 40, 40), "Normal", (120, 220, 120))
    cv2.rectangle(kare, (0, 0), (genislik, h), renk, -1)
    cv2.putText(kare, yazi, (10, int(h * 0.72)), cv2.FONT_HERSHEY_SIMPLEX, h / 45, yazi_rengi, 2,
                cv2.LINE_AA)
    bilgi = f"FPS {fps:.0f} | tespit {tespit_sayisi}"
    (g, _), _ = cv2.getTextSize(bilgi, cv2.FONT_HERSHEY_SIMPLEX, h / 70, 1)
    cv2.putText(kare, bilgi, (genislik - g - 10, int(h * 0.68)), cv2.FONT_HERSHEY_SIMPLEX, h / 70,
                (255, 255, 255), 1, cv2.LINE_AA)


def main():
    ayrac = argparse.ArgumentParser(description="Yangın/duman tespiti")
    ayrac.add_argument("--kaynak", default=ayarlar.KAMERA_KAYNAGI, help="0 = kamera, ya da video yolu")
    ayrac.add_argument("--sessiz", action="store_true", help="sesli uyarıyı kapat")
    arguman = ayrac.parse_args()
    kaynak = int(arguman.kaynak) if str(arguman.kaynak).isdigit() else arguman.kaynak
    kaynak_adi = f"kamera {kaynak}" if isinstance(kaynak, int) else Path(kaynak).name

    dedektor = YanginDedektoru(ayarlar.MODEL_YOLU, ayarlar.GUVEN_ESIKLERI, ayarlar.GORUNTU_BOYUTU)
    hareket = HareketKontrolu(ayarlar.HAREKET_ARALIGI_SN, ayarlar.HAREKET_PIKSEL_ESIGI,
                              ayarlar.HAREKET_ORANLARI) if ayarlar.HAREKET_KONTROLU else None
    karar = AlarmKarari(ayarlar.ALARM_SURESI_SN, ayarlar.ALARM_ORANI)
    ses = SesliUyari(ayarlar.SES_DOSYASI, ayarlar.SES_ARALIGI_SN)
    kaydedici = AlarmKaydedici(ayarlar.ALARM_KLASORU, ayarlar.LOG_DOSYASI, ayarlar.ALARM_BEKLEME_SN,
                               kaynak_adi)

    fps, onceki = 0.0, time.time()
    with Kamera(kaynak) as kamera:
        for kare in kamera.kareler():
            tespitler = dedektor.tespit_et(kare)
            if hareket:
                tespitler = hareket.suz(kare, tespitler, time.time())
            alarm = karar.guncelle(bool(tespitler))
            if alarm and not arguman.sessiz:
                ses.cal()

            simdi = time.time()
            anlik = 1 / max(simdi - onceki, 1e-6)
            fps, onceki = (anlik if fps == 0 else 0.9 * fps + 0.1 * anlik), simdi

            YanginDedektoru.ciz(kare, tespitler, serit_yuksekligi(kare))
            ust_bilgi_ciz(kare, alarm, fps, len(tespitler))

            olay = kaydedici.guncelle(alarm, kare, tespitler)
            if olay:
                saat = time.strftime("%H:%M:%S")
                ozet = ", ".join(f"{t.sinif} {t.guven:.2f}" for t in tespitler)
                if olay[0] == "basladi":
                    print(f"YANGIN TESPİT EDİLDİ ({saat}) [{ozet}] -> {olay[1].name}")
                elif olay[0] == "kayit":
                    print(f"  yangın sürüyor ({saat}) [{ozet}] -> {olay[1].name}")
                else:
                    print(f"Alarm bitti ({saat})")

            cv2.imshow("Yangin Tespit Sistemi", kare)
            if cv2.waitKey(1) == ord("q"):
                break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
