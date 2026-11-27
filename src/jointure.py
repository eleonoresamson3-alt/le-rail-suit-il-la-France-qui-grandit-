"""Étape 2 : jointures (notebook 02_base_finale).

Les tables propres de data/clean/ sont réunies :
- join_ : les deux bases SNCF (gares et fréquentation), en une table sncf-merged ;
- build_ : les gares rattachées aux communes, puis la table des communes,
  enregistrées dans data/clean/base_finale/.
"""

import pandas as pd
from src.config import CLEAN_DATA_DIR
import geopandas as gpd


# ---------- 02_base_finale : 2.1 Les deux bases SNCF ----------

# affiche, pour chaque base SNCF, le nombre de lignes avec plusieurs codes UIC dans une même case
def verif_code_uic(bases):
    for df in bases :
        print(df)
        multiples = df[df['code_uic'].astype(str).str.contains(r"[;, ]")]
        print(len(multiples))
        
    return


# la fonction join_sncf_audit associe les jeux de données frequentation-gares et gares-et-voyageurs en conservant toutes les gares mais n'enregistre pas la base obtenue
def join_sncf_audit() :

    # 1. On récupère les jeux de données que l'on souhaite 
    frequentation = pd.read_parquet(CLEAN_DATA_DIR / "frequentation-gares.parquet")
    frequentation = frequentation.copy()
    gares = pd.read_parquet(CLEAN_DATA_DIR / "gares-de-voyageurs.parquet")
    gares = gares.copy()

    # 2. On sépare les code_uic multiples pour créer une ligne par code uic
    gares["code_uic"] = gares["code_uic"].str.split(r"[;, ]")
    gares_explose = gares.explode("code_uic")
    gares_explose["code_uic"] = gares_explose["code_uic"].str.strip() # Supprime les éventuels espaces créés lors de la séparation
    gares = gares_explose

    # 3. On utilise merge pour fusionner les eux de données 
    df_audit = pd.merge(gares, frequentation, on="code_uic", how="outer", indicator=True)

    # 4. Pas d'harmonisation des types en raison des NaN qui empêchent de passer au type integer ou float
    
    return df_audit


# la fonction join_sncf associe les jeux de données frequentation-gares et gares-et-voyageurs en conservant uniquement les gares dont le code_uic est présent dans les deux bases
def join_sncf_inner() :

    # 1. On récupère les jeux de données que l'on souhaite 
    frequentation = pd.read_parquet(CLEAN_DATA_DIR / "frequentation-gares.parquet")
    frequentation = frequentation.copy()
    gares = pd.read_parquet(CLEAN_DATA_DIR / "gares-de-voyageurs.parquet")
    gares = gares.copy()

    # 2. On sépare les code_uic multiples pour créer une ligne par code uic
    gares["code_uic"] = gares["code_uic"].str.split(r"[;, ]")
    gares_explose = gares.explode("code_uic")
    gares_explose["code_uic"] = gares_explose["code_uic"].str.strip() # Supprime les éventuels espaces créés lors de la séparation
    gares = gares_explose

    # 3. On utilise merge pour fusionner les eux de données 
    df_inner = pd.merge(gares, frequentation, on="code_uic", how="inner")

    # 4. On harmonise les types
    df_inner["annee"] = df_inner["annee"].astype(int)  # annee : str
    df_inner["frequentation"] = df_inner["frequentation"].astype(int)  # annee : int
    "à compléter, il faut gérer les valeurs manquantes"
    
    return df_inner


# la fonction join_sncf associe les jeux de données frequentation-gares et gares-et-voyageurs en conservant uniquement les gares dont le code_uic est présent dans les deux bases
def join_sncf_final() :

    # 1. On récupère les jeux de données que l'on souhaite 
    frequentation = pd.read_parquet(CLEAN_DATA_DIR / "frequentation-gares.parquet")
    frequentation = frequentation.copy()
    gares = pd.read_parquet(CLEAN_DATA_DIR / "gares-de-voyageurs.parquet")
    gares = gares.copy()

    # 2. On sépare les code_uic multiples pour créer une ligne par code uic
    gares["code_uic"] = gares["code_uic"].str.split(r"[;, ]")
    gares_explose = gares.explode("code_uic")
    gares_explose["code_uic"] = gares_explose["code_uic"].str.strip() # Supprime les éventuels espaces créés lors de la séparation
    gares = gares_explose

    # 3. On utilise merge pour fusionner les eux de données 
    df_final = pd.merge(gares, frequentation, on="code_uic", how="inner")

    # 4. On harmonise les types
    df_final["annee"] = df_final["annee"].astype(int)  # annee : str
    df_final["frequentation"] = df_final["frequentation"].astype(int)  # annee : int
    
    # 5. On supprime les gares dont la frequentation est toujours égales à 0
    codes_a_supprimer = ["87472639", "87534339", "87725457", "87725465"]
    df_final = df_final[~df_final["code_uic"].isin(codes_a_supprimer)].copy()

    # 6. On enregistre le nouveau jeu de données dans data/clean
    chemin = CLEAN_DATA_DIR / 'sncf-merged.parquet'
    df_final.to_parquet(chemin, index=False)
    
    return df_final


# ---------- 02_base_finale : 2.2 La table des communes ----------

# une ligne par gare : sa position (point) et la commune des contours où elle se trouve
def build_gares(sncf, contours):
    # une ligne par gare
    gares = sncf.drop_duplicates("code_uic")[["code_uic", "nom_gare", "code_commune", "position_geographique"]].copy()
    # position "latitude, longitude" (texte) transformée en point
    coordonnees = gares["position_geographique"].str.split(",", expand=True).astype(float)
    gares = gpd.GeoDataFrame(gares, geometry=gpd.points_from_xy(coordonnees[1], coordonnees[0]), crs=4326)
    gares = gares.drop(columns="position_geographique")

    # 1. arrondissements de Paris, Lyon et Marseille ramenés à leur ville
    gares["methode"] = "code SNCF"
    for debut, ville in [("751", "75056"), ("6938", "69123"), ("132", "13055")]:
        arrondissement = gares["code_commune"].str.startswith(debut)
        gares.loc[arrondissement, "code_commune"] = ville
        gares.loc[arrondissement, "methode"] = "arrondissement"

    # 2. code absent des contours (ancienne commune fusionnée) : commune où se trouve la gare
    absent = ~gares["code_commune"].isin(contours["code_commune"])
    dans = gares[absent].sjoin(contours[["code_commune", "geometry"]], how="left", predicate="within")
    gares.loc[absent, "code_commune"] = dans["code_commune_right"]
    gares.loc[absent, "methode"] = "point dans le polygone"

    # contrôle : comment chaque gare a été rattachée
    print(gares["methode"].value_counts())
    print("gares sans commune :", gares["code_commune"].isna().sum())
    assert gares["code_uic"].is_unique
    return gares


# nombre de gares et voyageurs de chaque commune, l'année de début et l'année de fin
def build_voyageurs_communes(sncf, gares, annee_debut, annee_fin):
    # chaque ligne SNCF reçoit le code commune corrigé de sa gare (build_gares)
    sncf = sncf.drop(columns="code_commune").merge(gares[["code_uic", "code_commune"]], on="code_uic", validate="many_to_one")
    # nombre de gares de chaque commune
    nb_gares = gares.groupby("code_commune").size().rename("nb_gares")
    # voyageurs de toutes les gares d'une commune, une colonne par année
    deux_annees = sncf[sncf["annee"].isin([annee_debut, annee_fin])]
    voyageurs = deux_annees.pivot_table(index="code_commune", columns="annee", values="frequentation", aggfunc="sum")
    voyageurs.columns = [f"voyageurs_{int(annee)}" for annee in voyageurs.columns]
    return pd.concat([nb_gares, voyageurs], axis=1).reset_index()


# distance entre le centre de chaque commune et la gare la plus proche, en km (vide pour la Corse)
def build_distance_gare(contours, gares, crs):
    # calculs en Lambert 93 : les distances sont en mètres
    centres = contours[["code_commune", "code_departement", "geometry"]].to_crs(crs)
    centres["geometry"] = centres.centroid
    points_gares = gares[["code_uic", "geometry"]].to_crs(crs)
    # gare la plus proche de chaque centre de commune
    proches = centres.sjoin_nearest(points_gares, how="left", distance_col="distance_m")
    # en cas d'égalité, deux gares sont renvoyées : on n'en garde qu'une
    proches = proches.drop_duplicates("code_commune")
    proches["dist_gare_km"] = proches["distance_m"] / 1000
    # Corse : pas de gare SNCF sur l'île, la plus proche serait sur le continent
    corse = proches["code_departement"].isin(["2A", "2B"])
    proches.loc[corse, "dist_gare_km"] = float("nan")
    return proches[["code_commune", "dist_gare_km"]].reset_index(drop=True)


# une ligne par gare et par année, avec le code commune corrigé par build_gares
def build_gares_annees(sncf, gares):
    # chaque ligne SNCF reçoit le code commune corrigé de sa gare (build_gares)
    annees = sncf.drop(columns="code_commune").merge(gares[["code_uic", "code_commune"]], on="code_uic", validate="many_to_one")
    # codes UIC secondaires sans fréquentation : pas d'année, on les retire de cette table
    annees = annees.dropna(subset=["annee"])
    annees["annee"] = annees["annee"].astype(int)
    annees = annees.rename(columns={"frequentation": "voyageurs"})
    # une seule ligne par gare et par année
    assert not annees.duplicated(subset=["code_uic", "annee"]).any()
    return annees[["code_uic", "nom_gare", "code_commune", "segmentation_drg", "annee", "voyageurs"]].reset_index(drop=True)


# jointure à gauche sur code_commune : affiche les communes sans correspondance, vérifie qu'aucune n'est perdue
def build_jointure(gauche, droite, nom):
    # on fait un left join à partir de la clé code_commune
    table = gauche.merge(droite, on="code_commune", how="left", validate="one_to_one", indicator=True)
    # permet d'isoler les communes qui n'ont pas été ajouté dans notre jointure
    sans = (table["_merge"] == "left_only").sum()
    print(f"{nom} : {len(table)} communes, {sans} sans correspondance ({sans / len(table) * 100:.2f} %)")
    # on veut s'assurer qu'il ne manque pas des observations ni qu'il y en a en trop, pareil pour les variables
    assert len(table) == len(gauche)
    return table.drop(columns="_merge")


#à partir de la table issues de cartiflette et des contours, on construit une plus grosse table basée sur code_commune
def build_communes(contours, population, navettes, parc, voyageurs):
    communes = build_jointure(contours, population, "population")
    communes = build_jointure(communes, navettes, "navettes")
    communes = build_jointure(communes, parc, "parc automobile")
    communes = build_jointure(communes, voyageurs, "gares et voyageurs")
    # une commune absente de la liste des gares n'a aucune gare : 0, et non NaN
    communes["nb_gares"] = communes["nb_gares"].fillna(0).astype(int)
    assert communes["code_commune"].is_unique
    return communes
