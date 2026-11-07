"""Projenin ayarları."""
from pathlib import Path

PROJE = Path(__file__).resolve().parent

MODEL_YOLU = PROJE / "modeller" / "best.pt"
KAMERA_KAYNAGI = 0  # 0 = bilgisayarın kamerası

# Model bir kutudan en az bu kadar eminse tespit sayılır (0-1)
GUVEN_ESIKLERI = {"yangin": 0.40, "duman": 0.50}
GORUNTU_BOYUTU = 640

# Alarm: son 1.5 saniyedeki karelerin en az %70'inde tespit olmalı
ALARM_SURESI_SN = 1.5
ALARM_ORANI = 0.7

# Hareket kontrolü: kutu 2 saniye önceki kareye göre hiç değişmediyse (tabela, fotoğraf) sayılmaz
HAREKET_KONTROLU = True
HAREKET_ARALIGI_SN = 2.0
HAREKET_PIKSEL_ESIGI = 15  # bir pikselin "değişti" sayılması için gri tonda en az bu kadar fark
HAREKET_ORANLARI = {"yangin": 0.01, "duman": 0.005}  # kutudaki değişen piksel oranı en az

# Alarm kaydı: aynı yangın için iki kayıt arası en az 10 saniye
ALARM_KLASORU = PROJE / "alarmlar" / "goruntular"
LOG_DOSYASI = PROJE / "alarmlar" / "log.txt"
ALARM_BEKLEME_SN = 10

SES_DOSYASI = "/System/Library/Sounds/Sosumi.aiff"
SES_ARALIGI_SN = 3
