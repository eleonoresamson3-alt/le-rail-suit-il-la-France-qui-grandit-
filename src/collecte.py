"""Fonctions get_ : téléchargent les données brutes dans data/raw/."""
import os
import pandas as pd
from config import RAW_DATA_DIR

#get_frequentation permet de télécharger la base de données avec la freéquentations des gares
def get_frequentation():

    chemin = RAW_DATA_DIR / "frequentation-gares.csv"  #chemin du fichier que l'on cherche
    # déjà téléchargé : on relit le fichier au lieu de retélécharger
    if os.path.exists(chemin):
        return pd.read_csv(chemin)  #si le fichier existe déjà dans data/raw on le relit et on le renvoie sans le télécharger à nouveau
    url = 'https://tabular-api.data.gouv.fr/api/resources/d4cf16d5-dd91-453c-887e-6084639caac8/data/csv/'
    df = pd.read_csv(url, sep=';')  #ouvre le fichier comme dataframe pandas
    df.to_csv(chemin, sep = ',', index = False) #enregistre le fichier au chemin à l'emplacement prévu
    return df