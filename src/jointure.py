"""Fonctions join_ : associe plusieurs bases et les enregistre dans data/clean."""
import pandas as pd
from src.config import CLEAN_DATA_DIR

# la fonction join_sncf associe les jeux de données frequentation-gares.csv et gares-et-voyageurs.csv en utilisant code_uic comme clé de jointure
def join_sncf() :

    # On récupère les jeux de données que l'on souhaite 
    frequentation = pd.read_parquet(CLEAN_DATA_DIR / "frequentation-gares.parquet")
    gares = pd.read_parquet(CLEAN_DATA_DIR / "gares-de-voyageurs.parquet")

    # On utilise merge pour fusionner les eux de données 
    df_final = pd.merge(gares, frequentation, on="code_uic", how="left")

    # On enregistre le nouveau jeu de données dans data/clean
    chemin = CLEAN_DATA_DIR / 'sncf-merged.parquet'
    df_final.to_parquet(chemin, index=False)

    # On harmoniste les types
    #df_final["annee"] = df_final["annee"].astype(int)  # annee : str
    "à compléter, il faut gérer les valeurs manquantes"
    
    return df_final