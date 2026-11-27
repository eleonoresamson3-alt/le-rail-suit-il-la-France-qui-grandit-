"""Chemins des dossiers du projet, calculés à partir de la racine du projet.

Utilisés par les fonctions SNCF (collecte.py, nettoyage.py, jointure.py) et par les graphiques 1 à 6
(visualisation.py). Les autres paramètres (années, seuils, adresses des données) sont dans config.yaml.
"""
from pathlib import Path

# Racine du projet
ROOT = Path(__file__).resolve().parents[1]

# Dossiers principaux
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"

FIGURES_DIR = ROOT / "figures"
