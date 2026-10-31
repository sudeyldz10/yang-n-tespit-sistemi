# Orman Yangını Erken Tespit Sistemi

Kamera görüntüsünde yangın ve dumanı gerçek zamanlı tespit edip alarm veren sistem.
YOLOv8 ve OpenCV ile geliştiriliyor.

## Ne yaptık

| Hafta | Yapılan |
|---|---|
| 1 | Python ortamı kuruldu, hazır YOLOv8 modeliyle webcam testi yapıldı |
| 2 | [D-Fire](https://github.com/gaiasd/DFireDataset) veri setinden 2035 görüntü seçildi, %80/%20 bölündü |

## Sonuçlar

**Hafta 1:** Hazır YOLOv8 modeli webcam'de insan, telefon, bardak gibi nesneleri tanıyor.

**Hafta 2:** Eğitime hazır veri seti. Sınıflar: `0 = yangin`, `1 = duman`.

| | Eğitim | Doğrulama |
|---|---|---|
| Görüntü | 1628 | 407 |
| Boş görüntü | 153 | 28 |
| Yangın kutusu | 3043 | 946 |
| Duman kutusu | 1406 | 376 |

![Etiket kontrolü](ekran_goruntuleri/etiket_kontrol.jpg)

## Nasıl çalıştırılır

Kurulum (Python 3.9+):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Webcam testi (çıkmak için `q`):

```bash
.venv/bin/python testler/kamera_testi.py
```

Veri setini oluşturma:

```bash
.venv/bin/python araclar/dfire_indir.py etiketli /tmp/dfire
.venv/bin/python araclar/veri_hazirla.py /tmp/dfire
.venv/bin/python araclar/etiket_kontrol.py
```
