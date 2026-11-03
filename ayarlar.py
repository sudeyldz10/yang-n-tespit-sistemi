"""Projenin ayarları."""
from pathlib import Path

PROJE = Path(__file__).resolve().parent

MODEL_YOLU = PROJE / "modeller" / "best.pt"

# Model bir kutudan en az bu kadar eminse tespit sayılır (0-1)
GUVEN_ESIKLERI = {"yangin": 0.40, "duman": 0.50}
GORUNTU_BOYUTU = 640
