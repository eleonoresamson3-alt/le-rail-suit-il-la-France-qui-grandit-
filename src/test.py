from config import CLEAN_DATA_DIR

import pandas as pd

gares_annees = pd.read_parquet(CLEAN_DATA_DIR / "base_finale/gares_annees.parquet")


# Nombre de catégories différentes par gare
stabilite = (
    gares_annees
    .dropna(subset=["segmentation_drg"])
    .groupby("code_uic")["segmentation_drg"]
    .nunique()
)

print("Gares avec une segmentation stable :", (stabilite == 1).sum())
print("Gares ayant changé de segmentation :", (stabilite > 1).sum())