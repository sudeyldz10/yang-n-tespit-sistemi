"""Sesli uyarı ve alarm kaydı (fotoğraf + log)."""
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path

import cv2


class SesliUyari:
    def __init__(self, ses_dosyasi, aralik_sn=3):
        self.ses_dosyasi = str(ses_dosyasi)
        self.aralik_sn = aralik_sn
        self.son_calma = 0.0

    def cal(self):
        if time.time() - self.son_calma < self.aralik_sn:
            return
        self.son_calma = time.time()
        if platform.system() == "Darwin":
            subprocess.Popen(["afplay", self.ses_dosyasi])
        elif platform.system() == "Windows":
            import winsound
            winsound.Beep(1000, 500)
        else:
            print("\a", end="", flush=True)


class AlarmKaydedici:
    """Alarm anının fotoğrafını kaydeder, log.txt'ye satır yazar.
    İki kayıt arasında en az `bekleme_sn` saniye olur; bu süre boyunca alarm olmazsa olay biter."""

    def __init__(self, klasor, log_dosyasi, bekleme_sn, kaynak_adi):
        self.klasor = Path(klasor)
        self.log_dosyasi = Path(log_dosyasi)
        self.bekleme_sn = bekleme_sn
        self.kaynak_adi = kaynak_adi
        self.son_kayit = None
        self.son_alarm = None
        self.olay_suruyor = False
        self.olay_kaydedildi = False
        self.klasor.mkdir(parents=True, exist_ok=True)

    def guncelle(self, alarm, kare, tespitler):
        """Döndürür: ("basladi", foto), ("kayit", foto), ("bitti", None) ya da None."""
        zaman = time.time()
        if not alarm:
            if self.olay_suruyor and zaman - self.son_alarm >= self.bekleme_sn:
                self.olay_suruyor = self.olay_kaydedildi = False
                return ("bitti", None)
            return None
        self.son_alarm = zaman
        self.olay_suruyor = True
        if not tespitler or (self.son_kayit and zaman - self.son_kayit < self.bekleme_sn):
            return None
        yeni_olay = not self.olay_kaydedildi
        self.son_kayit = zaman
        self.olay_kaydedildi = True
        return ("basladi" if yeni_olay else "kayit", self._kaydet(kare, tespitler))

    def _kaydet(self, kare, tespitler):
        an = datetime.now()
        foto = self.klasor / f"{an:%Y%m%d_%H%M%S}_{an.microsecond // 1000:03d}.jpg"
        kare = kare.copy()
        damga = f"{an:%Y-%m-%d %H:%M:%S} | {self.kaynak_adi}"
        olcek = max(0.45, kare.shape[1] / 1600)
        (g, y), _ = cv2.getTextSize(damga, cv2.FONT_HERSHEY_SIMPLEX, olcek, 1)
        cv2.rectangle(kare, (0, kare.shape[0] - y - 14), (g + 16, kare.shape[0]), (0, 0, 0), -1)
        cv2.putText(kare, damga, (8, kare.shape[0] - 7), cv2.FONT_HERSHEY_SIMPLEX, olcek,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(foto), kare)

        turler = ", ".join(sorted({t.sinif for t in tespitler}))
        guven = max(t.guven for t in tespitler)
        with open(self.log_dosyasi, "a", encoding="utf-8") as dosya:
            dosya.write(f"{an:%Y-%m-%d %H:%M:%S} | {turler} | güven: {guven:.2f} | "
                        f"kaynak: {self.kaynak_adi} | alarmlar/goruntular/{foto.name}\n")
        return foto
