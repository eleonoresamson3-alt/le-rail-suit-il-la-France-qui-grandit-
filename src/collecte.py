"""Fonctions get_ : téléchargent les données brutes dans data/raw/."""

import os #  module de manipulation des fichiers et des données
import zipfile  #  permet d'ouvrir et lire des fichiers zip
import json

import pandas as pd
import requests   #  téléchargement des fichiers ou pages depuis internet

import geopandas as gpd #  module pandas mais pour cartographie et représentation visuelle
from cartiflette import carti_download #  carti_download nous permet de récupérer les contours nécessaires à la création de nos cartes


#  get_contours permet de télécharger la carte de la France avec ses contours et la répartition en commune
def get_contours(niveau, annee):
    chemin = f"data/raw/contours_{niveau.lower()}_{annee}.parquet" 
#  Cette ligne construit le nom du fichier à partir du niveau et de l'année, par exemple data/raw/contours_commune_2026.parquet, pour savoir où enregistrer ou retrouver les contours.
    if os.path.exists(chemin):
        return gpd.read_parquet(chemin) #  condition : si le fichier existe déjà dans data/raw/, on le relit et on le renvoie tout de suite, sans retélécharger, et la fonction s'arrête là.
    contours = carti_download(
        values="France",
        borders=niveau,
        filter_by="FRANCE_ENTIERE",
        year=annee,
        crs=4326,
    )
    #  télécharge les contours de toute la France (DOM compris), au niveau et à l'année demandés, en coordonnées (longitude et latitude) et les range dans la variable contours.
    contours.to_parquet(chemin) #  enregistre les contours dans un fichier parquet à l'adresse chemin pour ne pas avoir à les retélécharger. 
    return contours

#  récupérer le dossier raw des données dgac
def get_dgac(url, annees):
    chemin = "data/raw/dgac_pap_1990_2025.zip"
    # l'archive n'est téléchargée qu'une fois
    if not os.path.exists(chemin): 
        reponse = requests.get(url, timeout=60)    #  télécharge le document en ligne, la condition timeout permet d'arrêter la recheche si le lien ne fonctionne pas
        reponse.raise_for_status()     #  arrête le programme avec une erreur si le téléchargement a échoué (par exemple un lien cassé), pour ne pas enregistrer un mauvais fichier.
        with open(chemin, "wb") as fichier:  # enregistre l'archive téléchargée dans data/raw/ (mode binaire car c'est un .zip)
            fichier.write(reponse.content)   # copie le contenu téléchargé dans le fichier
    tables = []   # créer un tableau vide, pour le remplir avec nos données
    with zipfile.ZipFile(chemin) as archive:   # ouvre l'archive pour lire les CSV qu'elle contient
        for annee in annees:
            # un CSV par année ; codes lus en texte; nettoie la base (accents, caractères invisibles, séparation et décimal, fixe le type de certaines variables)
            with archive.open(f"ASP_PAP_{annee}.csv") as fichier:
                table = pd.read_csv(fichier, sep=";", decimal=",", encoding="utf-8-sig",
                                    dtype={"ANMOIS": str, "PAP": str})
            tables.append(table)
    return pd.concat(tables, ignore_index=True) # assemble les années en un seul tableau

#get_base_carbone permet de récupérer la base de données sur les émissions carbone une seule fois puis stockée. 
def get_base_carbone(url, identifiants):
    chemin = "data/raw/base_carbone.json"
    # l'API n'est interrogée qu'une fois, on récupère 100 lignes maximum, seulement les éléments choisis et le total, pas le détails
    if not os.path.exists(chemin):
        parametres = {
            "Identifiant_de_l'élément_in": ",".join(identifiants),
            "Type_Ligne_eq": "Elément",
            "size": 100,
        }
        reponse = requests.get(url, params=parametres, timeout=60)
        reponse.raise_for_status()
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write(reponse.text)
    # la réponse est un JSON : les facteurs sont dans la liste "results" "utf-8": garder les accents
    with open(chemin, encoding="utf-8") as fichier:
        resultats = json.load(fichier)["results"]
    return pd.DataFrame(resultats)


