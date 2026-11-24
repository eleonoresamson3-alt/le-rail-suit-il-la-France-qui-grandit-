"""Fonctions get_ : téléchargent les données brutes dans data/raw/."""

import os #module de manipulation des données
import geopandas as gpd #module pandas mais pour cartographie et représentation visuelle
from cartiflette import carti_download #carti_download nous permet de récupérer les contours nécessaires à la création de nos cartes


#get_contours permet de télécharger la carte de la France avec ses contours et la répartition en commune
def get_contours(niveau, annee):
    chemin = f"data/raw/contours_{niveau.lower()}_{annee}.parquet" 
#Cette ligne construit le nom du fichier à partir du niveau et de l'année, par exemple data/raw/contours_commune_2026.parquet, pour savoir où enregistrer ou retrouver les contours.
    if os.path.exists(chemin):
        return gpd.read_parquet(chemin) #condition : si le fichier existe déjà dans data/raw/, on le relit et on le renvoie tout de suite, sans retélécharger, et la fonction s'arrête là.
    contours = carti_download(
        values="France",
        borders=niveau,
        filter_by="FRANCE_ENTIERE",
        year=annee,
        crs=4326,
    )
    #télécharge les contours de toute la France (DOM compris), au niveau et à l'année demandés, en coordonnées (longitude et latitude) et les range dans la variable contours.
    contours.to_parquet(chemin) #enregistre les contours dans un fichier parquet à l'adresse chemin pour ne pas avoir à les retélécharger. 
    return contours

