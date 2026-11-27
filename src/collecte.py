"""Étape 1 : collecte (notebook 01_donnees).

Fonctions get_ : téléchargent chaque source une seule fois dans data/raw/, puis la relisent.
Elles renvoient les données brutes, nettoyées ensuite par nettoyage.py.
Les régions (get_regions) servent au graphique 2 (notebook 03_graphiques).
"""

import os #  module de manipulation des fichiers et des données
import zipfile  #  permet d'ouvrir et lire des fichiers zip
import json
import pandas as pd
import requests   #  téléchargement des fichiers ou pages depuis internet
import geopandas as gpd #  module pandas mais pour cartographie et représentation visuelle
from cartiflette import carti_download #  carti_download nous permet de récupérer les contours nécessaires à la création de nos cartes
from src.config import RAW_DATA_DIR
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# ---------- 01_donnees : Exploration des contours (cartiflette) ----------

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


# ---------- 01_donnees : Population des communes (INSEE) ----------

def _get_base(nom, config):
    """Ouvrir une archive INSEE en la téléchargeant seulement si nécessaire."""
    source = config["insee"][nom]
    chemin = Path(config["dossiers"]["brut"]) / source["fichier"]
    chemin.parent.mkdir(parents=True, exist_ok=True)
    trace = chemin.with_suffix(".provenance.json")
    if not chemin.exists():
        if config.get("hors_ligne", False):
            raise FileNotFoundError(f"Archive INSEE manquante en mode hors ligne : {chemin}")
        # Télécharger le fichier demandé et arrêter si le serveur signale une erreur.
        reponse = requests.get(source["url"], timeout=180)
        reponse.raise_for_status()
        # Vérifier l'archive avant de conserver une réponse du serveur.
        # Le fichier temporaire évite de prendre un téléchargement interrompu
        # pour une archive complète.
        temporaire = chemin.with_suffix(".part")
        temporaire.write_bytes(reponse.content)
        with zipfile.ZipFile(temporaire) as archive:
            assert archive.testzip() is None, "Archive ZIP corrompue"
        temporaire.replace(chemin)
        provenance = {
            "url": reponse.url,
            "collecte_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(reponse.content).hexdigest(),
            "octets": len(reponse.content),
        }
        trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    # Vérifier le fichier avant de le lire : l'archive peut avoir été modifiée
    # depuis son dernier téléchargement.
    contenu = chemin.read_bytes()
    empreinte = hashlib.sha256(contenu).hexdigest()
    if trace.exists():
        provenance = json.loads(trace.read_text(encoding="utf-8"))
        assert provenance["sha256"] == empreinte, f"Archive brute modifiée : {chemin}"
    else:
        # Les premiers fichiers ont été acquis pendant la vérification documentaire.
        # On distingue leur date locale de modification d'une date HTTP inconnue.
        provenance = {
            "url": source["url"],
            "date_modification_cache_utc": datetime.fromtimestamp(
                chemin.stat().st_mtime, tz=timezone.utc).isoformat(),
            "sha256": empreinte,
            "octets": len(contenu),
        }
        trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    # Le ZIP contient un seul CSV de données. Le lire en texte garde intacts
    # les codes INSEE, notamment leurs zéros initiaux.
    with zipfile.ZipFile(chemin) as archive:
        membres = [m for m in archive.namelist() if m.endswith("_data.csv")]
        assert len(membres) == 1, membres
        with archive.open(membres[0]) as fichier:
            brut = pd.read_csv(fichier, sep=";", dtype="string", encoding="utf-8-sig")
    print(f"INSEE {nom} : {len(brut):,} lignes brutes lues ; archive et empreinte contrôlées.")
    return brut


def get_population(config):
    """Lire les séries de population INSEE, depuis le cache si possible."""
    return _get_base("population", config)


# ---------- 01_donnees : Modes de déplacement domicile–travail (INSEE) ----------

def get_navettes(config):
    """Lire les navettes INSEE en exploitation principale."""
    return _get_base("navettes", config)


# ---------- 01_donnees : Exploration des jeu de données SNCF ----------

# get_gares permet de télécharger le jeu de données sur les gares
def get_gares():

    chemin = RAW_DATA_DIR / "gares-de-voyageurs.parquet"  # chemin du fichier que l'on cherche
    # déjà téléchargé : on relit le fichier au lieu de retélécharger
    if os.path.exists(chemin):
        return pd.read_parquet(chemin)  # si le fichier existe déjà dans data/raw on le relit et on le renvoie sans le télécharger à nouveau
    url = 'https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/gares-de-voyageurs/exports/csv?use_labels=true'
    df = pd.read_csv(url, sep=';', dtype={"Code commune": str})  # ouvre le fichier comme dataframe pandas en convertissant Code commune comme str pour éviter de perdre le premier 0
    df.to_parquet(chemin, index=False)  # enregistre le fichier au chemin à l'emplacement prévu
    return df


# get_frequentation permet de télécharger la base de données avec la freéquentations des gares
def get_frequentation():

    chemin = RAW_DATA_DIR / "frequentation-gares.parquet"  # chemin du fichier que l'on cherche
    # déjà téléchargé : on relit le fichier au lieu de retélécharger
    if os.path.exists(chemin):
        return pd.read_parquet(chemin)  # si le fichier existe déjà dans data/raw on le relit et on le renvoie sans le télécharger à nouveau
    url = 'https://tabular-api.data.gouv.fr/api/resources/d4cf16d5-dd91-453c-887e-6084639caac8/data/csv/'
    df = pd.read_csv(url, sep=',')  # ouvre le fichier comme dataframe pandas
    df = df.drop(columns=["__id"])  # supprime la première colonne
    df.to_parquet(chemin, index=False)  # enregistre le fichier au chemin à l'emplacement prévu
    return df


# ---------- 01_donnees : Exploration du parc automobile (SDES) ----------

#téléchargement et stockage unique de la base de données, et notamment des variables qui nous intéressent
def get_parc_auto(url, annee_debut, annee_fin):
    chemin = f"data/raw/parc_auto_{annee_debut}_{annee_fin}.csv"
    # la base complète est très lourde : on demande à l'API seulement ce qui nous sert, on évacue les voitures de société
    if not os.path.exists(chemin):
        parametres = {
            "GROUPE": "eq:VP",
            "STATUT_UTILISATEUR": "eq:Particulier",
            "columns": f"COMMUNE_CODE,COMMUNE_NOM,CARBURANT,CRIT_AIR,PARC_{annee_debut},PARC_{annee_fin}",
        }
        reponse = requests.get(url, params=parametres, timeout=300)
        reponse.raise_for_status()
        with open(chemin, "wb") as fichier:
            fichier.write(reponse.content)
    return pd.read_csv(chemin, sep=";", dtype={"COMMUNE_CODE": str})


# ---------- 01_donnees : Exploration du trafic aérien (DGAC, série PAP) ----------

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


# ---------- 01_donnees : Exploration des facteurs d'émission (ADEME, Base Carbone) ----------

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


# ---------- 03_graphiques : Graphique 2 : soldes naturels et migratoires par région ----------

def get_regions():
    """Récupère les régions et leurs codes."""

    regions = carti_download(values="France", borders="REGION",
    filter_by="FRANCE_ENTIERE_DROM_RAPPROCHES",year=2025, simplification=50)

    regions = regions.rename(columns={"LIBELLE_REGION": "nom_region", "INSEE_REG": "code_region"})

    return regions
