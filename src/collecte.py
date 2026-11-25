"""Fonctions get_ : téléchargent les données brutes dans data/raw/."""
import os
import pandas as pd
from src.config import RAW_DATA_DIR

# get_frequentation permet de télécharger la base de données avec la freéquentations des gares


def get_frequentation():

    chemin = RAW_DATA_DIR / "frequentation-gares.csv"  # chemin du fichier que l'on cherche
    # déjà téléchargé : on relit le fichier au lieu de retélécharger
    if os.path.exists(chemin):
        return pd.read_csv(chemin)  # si le fichier existe déjà dans data/raw on le relit et on le renvoie sans le télécharger à nouveau
    url = 'https://tabular-api.data.gouv.fr/api/resources/d4cf16d5-dd91-453c-887e-6084639caac8/data/csv/'
    df = pd.read_csv(url, sep=',')  # ouvre le fichier comme dataframe pandas
    df = df.drop(columns=["__id"])  # supprime la première colonne
    df.to_csv(chemin, sep=',', index=False)  # enregistre le fichier au chemin à l'emplacement prévu
    return df

# get_gares permet de télécharger le jeu de données sur les gares


def get_gares():

    chemin = RAW_DATA_DIR / "gares-de-vaoyageurs.csv"  # chemin du fichier que l'on cherche
    # déjà téléchargé : on relit le fichier au lieu de retélécharger
    if os.path.exists(chemin):
        return pd.read_csv(chemin, sep=';')  # si le fichier existe déjà dans data/raw on le relit et on le renvoie sans le télécharger à nouveau
    url = 'https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/exports/csv?use_labels=true'
    df = pd.read_csv(url, sep=';')  # ouvre le fichier comme dataframe pandas
    df.to_csv(chemin, sep=';', index=False)  # enregistre le fichier au chemin à l'emplacement prévu
    return df