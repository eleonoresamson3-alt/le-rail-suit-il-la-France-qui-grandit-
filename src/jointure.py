"""Fonctions join_ : associe plusieurs bases et les enregistre dans data/clean."""
import pandas as pd
from src.config import CLEAN_DATA_DIR

# la fonction join_sncf associe les jeux de données frequentation-gares.csv et gares-et-voyageurs.csv en utilisant code_uic comme clé de jointure
def join_sncf() :

    # 1. On récupère les jeux de données que l'on souhaite 
    frequentation = pd.read_parquet(CLEAN_DATA_DIR / "frequentation-gares.parquet")
    frequentation =frequentation.copy()
    gares = pd.read_parquet(CLEAN_DATA_DIR / "gares-de-voyageurs.parquet")
    gares = gares.copy()

    # 2. On sépare les code_uic multiples pour créer une ligne par code uic
    gares["code_uic"] = gares["code_uic"].str.split(r"[;, ]")
    gares_explose = gares.explode("code_uic")
    gares_explose["code_uic"] = gares_explose["code_uic"].str.strip() # Supprime les éventuels espaces créés lors de la séparation
    gares = gares_explose

    # On utilise merge pour fusionner les eux de données 
    df_final = pd.merge(gares, frequentation, on="code_uic", how="left")

    # On enregistre le nouveau jeu de données dans data/clean
    chemin = CLEAN_DATA_DIR / 'sncf-merged.parquet'
    df_final.to_parquet(chemin, index=False)

    # On harmoniste les types
    #df_final["annee"] = df_final["annee"].astype(int)  # annee : str
    "à compléter, il faut gérer les valeurs manquantes"
    
    return df_final