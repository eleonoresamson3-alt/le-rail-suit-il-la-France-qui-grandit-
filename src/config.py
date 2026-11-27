from pathlib import Path

# Racine du projet
ROOT = Path(__file__).resolve().parents[1]

# Dossiers principaux
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"

FIGURES_DIR = ROOT / "figures"