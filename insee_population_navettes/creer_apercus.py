"""Créer des CSV courts pour consulter les tables INSEE directement sur GitHub."""

from pathlib import Path

import pandas as pd


# Le script se base sur son propre dossier : il fonctionne même si on le lance
# depuis un autre répertoire.
racine = Path(__file__).parent
dossier = racine / "data" / "processed" / "rail2026"

# Garder seulement les 20 premières lignes : les fichiers complets restent en
# Parquet, et les aperçus CSV sont faciles à ouvrir sur GitHub.
for nom in ("source_population", "source_navettes"):
    table = pd.read_parquet(dossier / f"{nom}.parquet")
    table.head(20).to_csv(dossier / f"apercu_{nom}.csv", index=False)
    print(f"Aperçu écrit : apercu_{nom}.csv (20 lignes maximum)")
