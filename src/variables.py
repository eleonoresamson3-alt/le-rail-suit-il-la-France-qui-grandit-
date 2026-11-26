"""Fonctions build_ : jointures et variables construites."""

import geopandas as gpd
import pandas as pd

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

def build_gares(sncf, contours):
    # une ligne par gare, on met ça en format large
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