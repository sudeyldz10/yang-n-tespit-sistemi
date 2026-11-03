"""D-Fire görüntülerini Hugging Face kopyasından (badsaarow/d-fire) indirir.

    .venv/bin/python araclar/dfire_indir.py etiketli <klasor>   # eğitim görüntüleri
    .venv/bin/python araclar/dfire_indir.py bos <klasor>        # boş aday görüntüler
    .venv/bin/python araclar/dfire_indir.py test <klasor>       # test görüntüleri
    .venv/bin/python araclar/dfire_indir.py bilgi               # grupları listeler
"""
import io
import sys
import time
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

ADRES = "https://huggingface.co/datasets/badsaarow/d-fire/resolve/main/data/train-0000{}-of-00009.parquet"
TEST_ADRES = "https://huggingface.co/datasets/badsaarow/d-fire/resolve/main/data/test-0000{}-of-00003.parquet"

# (parça, alt grup) seçimleri: bu projede kullanılanlar
ETIKETLI = [(2, 0), (2, 1), (3, 3), (6, 3), (7, 0)]   # 2035 görüntü: kamera + internet yangınları
BOS = [(1, 2), (3, 4), (4, 0), (4, 2)]                # 1234 boş aday: bulut, gün batımı, gökyüzü
# D-Fire'ın ayrı test bölümü (eğitimde hiç kullanılmadı): kamera, kamuya açık ve internet
# görüntülerinden dengeli bir karışım. Modelin gerçek başarısını ölçmek için.
TEST = [(0, 2), (1, 0), (1, 1), (2, 0), (2, 2)]


class UzakDosya(io.RawIOBase):
    """HTTP Range istekleriyle uzak dosyanın sadece istenen kısmını okur."""

    def __init__(self, url):
        istek = urllib.request.Request(url, method="HEAD")
        cevap = urllib.request.urlopen(istek, timeout=60)
        self.boyut = int(cevap.headers["Content-Length"])
        self.url = cevap.url
        self.konum = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.konum

    def seek(self, kayma, nereden=0):
        self.konum = {0: kayma, 1: self.konum + kayma, 2: self.boyut + kayma}[nereden]
        return self.konum

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.boyut - self.konum
        if n == 0 or self.konum >= self.boyut:
            return b""
        son = min(self.konum + n, self.boyut) - 1
        for deneme in range(6):  # hız sınırına takılırsa bekleyip tekrar dene
            try:
                istek = urllib.request.Request(self.url, headers={"Range": f"bytes={self.konum}-{son}"})
                veri = urllib.request.urlopen(istek, timeout=120).read()
                break
            except Exception:
                time.sleep(10 * (deneme + 1))
        else:
            raise RuntimeError(f"İndirilemedi: {self.url}")
        self.konum += len(veri)
        return veri

    def readinto(self, tampon):
        veri = self.read(len(tampon))
        tampon[:len(veri)] = veri
        return len(veri)


def indir(secim, klasor, sadece_bos, adres=ADRES):
    klasor = Path(klasor)
    (klasor / "images").mkdir(parents=True, exist_ok=True)
    (klasor / "labels").mkdir(parents=True, exist_ok=True)
    for parca, grup in secim:
        tablo = pq.ParquetFile(UzakDosya(adres.format(parca))).read_row_group(grup)
        sayi = 0
        for goruntu, etiket, ad in zip(tablo.column("image").to_pylist(), tablo.column("label").to_pylist(),
                                       tablo.column("filename").to_pylist()):
            etiket = (etiket or "").strip()
            if sadece_bos and etiket:
                continue
            ad = Path(ad).name
            if not ad.endswith(".jpg"):
                continue
            (klasor / "images" / ad).write_bytes(goruntu["bytes"])
            (klasor / "labels" / f"{ad[:-4]}.txt").write_text(etiket + ("\n" if etiket else ""))
            sayi += 1
        print(f"parça {parca} grup {grup}: {sayi} görüntü", flush=True)


def bilgi():
    for parca in sorted({p for p, _ in ETIKETLI + BOS}):
        ust = pq.ParquetFile(UzakDosya(ADRES.format(parca))).metadata
        for g in range(ust.num_row_groups):
            isaret = "etiketli" if (parca, g) in ETIKETLI else ("bos" if (parca, g) in BOS else "")
            print(f"parça {parca} grup {g}: {ust.row_group(g).num_rows} görüntü, "
                  f"{ust.row_group(g).total_byte_size / 1e6:.0f} MB {isaret}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "bilgi":
        bilgi()
    elif len(sys.argv) == 3 and sys.argv[1] == "test":
        indir(TEST, sys.argv[2], False, TEST_ADRES)
    elif len(sys.argv) == 3 and sys.argv[1] in ("etiketli", "bos"):
        indir(ETIKETLI if sys.argv[1] == "etiketli" else BOS, sys.argv[2], sys.argv[1] == "bos")
    else:
        raise SystemExit(__doc__)
