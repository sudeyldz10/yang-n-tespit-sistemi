# Orman Yangını Erken Tespit Sistemi

Kamera görüntüsünde yangın ve dumanı gerçek zamanlı tespit edip alarm veren bir sistem.
YOLOv8 (Ultralytics) ve OpenCV ile geliştiriliyor.

Hedef: 6 hafta sonunda webcam önünde ateş gösterildiğinde ekranda tespit çıkaran,
alarmı kaydeden ve ekibe gösterilebilecek bir demo. Backend, harita ve bildirim sistemi
sonraki aşamada ekiple yapılacak.

## Durum

| Hafta | Konu | Durum |
|---|---|---|
| 1 | Ortam kurulumu + YOLOv8 webcam testi | Tamamlandı |
| 2 | Veri seti (yangın/duman) | - |
| 3 | Model eğitimi | - |
| 4 | Webcam'e bağlama + alarm | - |
| 5 | Alarm kaydı + log | - |
| 6 | Demo + README | - |

## Hafta 1: Ortam kurulumu ve ilk tespit

Yapılanlar:

- Python sanal ortamı kuruldu, `ultralytics` ve `opencv-python` yüklendi.
- Hazır `yolov8n.pt` modeliyle webcam testi çalıştırıldı: model webcam'de insan, telefon,
  bardak gibi nesneleri tanıyor.
- Proje klasör yapısı oluşturuldu.
- Veri seti ayar dosyası hazırlandı: [veri/yangin.yaml](veri/yangin.yaml)
  (sınıflar: `0 = yangin`, `1 = duman`).

## Kurulum

Gereken: Python 3.9 veya üstü, bilgisayarda kamera.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Windows'ta `.venv/bin/...` yerine `.venv\Scripts\...` kullan.

## Webcam testi

```bash
.venv/bin/python testler/kamera_testi.py
```

- İlk çalıştırmada `yolov8n.pt` modeli (6 MB) otomatik indirilir.
- Pencerede algılanan nesneler kutularla gösterilir; sol üstte FPS (saniyedeki kare sayısı) yazar.
- Çıkmak için pencere seçiliyken `q` tuşuna bas.

Sadece kamera görüntüsünü (tespit olmadan) görmek için:

```bash
.venv/bin/python testler/kamera_goster.py
```

**macOS kamera izni:** Kamera açılmazsa Sistem Ayarları > Gizlilik ve Güvenlik > Kamera
bölümünden Terminal'e (veya kullandığın editöre) izin ver.

## Klasör yapısı

```
yangin-tespit-sistemi/
├── testler/
│   ├── kamera_testi.py     # YOLOv8 ile webcam testi
│   └── kamera_goster.py    # sadece kamera görüntüsü
├── kaynak/                 # sistemin kodu (sonraki haftalarda)
├── modeller/               # eğitilmiş model (Hafta 3)
├── veri/
│   ├── images/train, val   # görüntüler (Hafta 2)
│   ├── labels/train, val   # etiketler (Hafta 2)
│   └── yangin.yaml         # veri seti ayarları
├── alarmlar/goruntular/    # alarm fotoğrafları (Hafta 5)
├── videolar/               # test videoları
├── ekran_goruntuleri/      # README görselleri
└── requirements.txt
```

Not: `images` ve `labels` klasör adları YOLO için zorunludur. Görüntüler, etiketler ve
model ağırlıkları (`*.pt`) büyük oldukları için repoya eklenmez (bkz. `.gitignore`).
