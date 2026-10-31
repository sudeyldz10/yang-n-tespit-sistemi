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
| 2 | Veri seti (yangın/duman) | Tamamlandı |
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

## Hafta 2: Veri seti

Yangın/duman tespiti için [D-Fire](https://github.com/gaiasd/DFireDataset) veri seti kullanıldı.
D-Fire'da 21.000'den fazla görüntü var; orijinal indirme linkleri (OneDrive, Kaggle) giriş
istediği için Hugging Face'teki kopyası (`badsaarow/d-fire`) kullanıldı. Plandaki 1000-2000
görüntü hedefine göre içinden 2035 görüntü seçildi.

| | Eğitim (train) | Doğrulama (val) |
|---|---|---|
| Görüntü | 1628 | 407 |
| Boş görüntü (yangın/duman yok) | 153 | 28 |
| Yangın kutusu | 3043 | 946 |
| Duman kutusu | 1406 | 376 |

- Görüntüler güvenlik kameralarından (gece/gündüz, uzak duman) ve internetten (yakın yangınlar)
  karışık seçildi; yanlış alarmı azaltmak için bir miktar boş görüntü de eklendi.
- %80 eğitim / %20 doğrulama olarak rastgele bölündü (sabit tohum: aynı bölünme tekrar elde edilir).
- D-Fire'da sınıf sırası tersdir (0 = duman, 1 = yangın). Etiketler yerleştirilirken bu projenin
  sırasına (0 = yangin, 1 = duman) çevrildi. Sıra, görüntüler üzerine çizilerek doğrulandı.
- Görüntü ve etiket sayıları birebir eşleşiyor; tüm kutu koordinatları 0-1 aralığında.

Etiket kontrolü (rastgele 12 görüntü; kırmızı = yangın, gri = duman):

![Etiket kontrolü](ekran_goruntuleri/etiket_kontrol.jpg)

Veri setini oluşturmak için (görüntüler büyük olduğu için repoda yok):

```bash
.venv/bin/python araclar/dfire_indir.py etiketli /tmp/dfire   # ~173 MB indirir
.venv/bin/python araclar/veri_hazirla.py /tmp/dfire           # %80/%20 böler, sınıfları çevirir
.venv/bin/python araclar/etiket_kontrol.py                    # sayıları kontrol eder, örnek çizer
```

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
├── araclar/
│   ├── dfire_indir.py      # D-Fire görüntülerini indirir
│   ├── veri_hazirla.py     # %80/%20 böler, sınıfları çevirir
│   └── etiket_kontrol.py   # sayıları kontrol eder, örnek çizer
├── kaynak/                 # sistemin kodu (sonraki haftalarda)
├── modeller/               # eğitilmiş model (Hafta 3)
├── veri/
│   ├── images/train, val   # görüntüler (repoda yok, araclar/ ile indirilir)
│   ├── labels/train, val   # etiketler (repoda yok, araclar/ ile indirilir)
│   └── yangin.yaml         # veri seti ayarları
├── alarmlar/goruntular/    # alarm fotoğrafları (Hafta 5)
├── videolar/               # test videoları
├── ekran_goruntuleri/      # README görselleri
└── requirements.txt
```

Not: `images` ve `labels` klasör adları YOLO için zorunludur. Görüntüler, etiketler ve
model ağırlıkları (`*.pt`) büyük oldukları için repoya eklenmez (bkz. `.gitignore`).
