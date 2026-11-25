"""Fonctions join_ : associe plusieurs bases et les enregistre dans data/clean."""
import pandas as pd
from config import CLEAN_DATA_DIR

# la fonction join_sncf associe les jeux de données frequentation-gares.csv et gares-et-voyageurs.csv en utilisant code_uic comme clé de jointure
def join_sncf()

    # On récupère les jeux de données que l'on souhaite 
    frequentation = df.read_csv(CLEAN_DATA_DIR / "frequentation-gares.csv", sep=',')
    gares = df.read_csv(RAW_DATA_DIR / "gares-de-voyageurs.csv", sep=',')

   df_final = pd.merge(gares, frequentation, on="code_uic", how="left")