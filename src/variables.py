"""Fonctions build_ : jointures et variables construites."""

import geopandas as gpd
import pandas as pd
from cartiflette import carti_download
from cartiflette import carti_download

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


def build_liaisons_co2(liaisons, facteurs, annee_debut, annee_fin):
    # facteur d'émission de chaque mode, en kgCO2e par passager.km
    facteur = dict(zip(facteurs["mode"], facteurs["co2_kg_km"]))
    table = liaisons.copy()
    # pas de train vers la Corse : les aéroports corses ont un code OACI qui commence par LFK
    corse = table["code_oaci_1"].str.startswith("LFK") | table["code_oaci_2"].str.startswith("LFK")
    for annee in [annee_debut, annee_fin]:
        passagers_km = table[f"passagers_{annee}"] * table["dist_km"]
        table[f"co2_avion_t_{annee}"] = passagers_km * facteur["avion"] / 1000
        table[f"co2_tgv_t_{annee}"] = (passagers_km * facteur["tgv"] / 1000).where(~corse)
    return table


def build_tcam(debut, fin, nb_annees):
    # une valeur de départ nulle rend le taux impossible à calculer : NaN
    return ((fin / debut.where(debut > 0)) ** (1 / nb_annees) - 1) * 100


def build_solde_naturel(naissances, deces):
    return naissances - deces


def build_solde_migratoire(pop_debut, pop_fin, solde_naturel):
    return (pop_fin - pop_debut) - solde_naturel



def build_solde_naturel(naissances, deces):
    return naissances - deces


def build_solde_migratoire(pop_debut, pop_fin, solde_naturel):
    return (pop_fin - pop_debut) - solde_naturel



def build_trajectoire(tcam, seuil):
    return pd.cut(tcam, bins=[-float("inf"), -seuil, seuil, float("inf")],
                  labels=["déclin", "stable", "croissance"])



def build_part(numerateur, denominateur, minimum):
    return (numerateur / denominateur * 100).where(denominateur >= minimum)


def build_classe_taille(population, bornes, noms):
    """Classe de taille de chaque commune selon sa population (la dernière classe n'a pas de limite haute)."""
    return pd.cut(population, bins=bornes + [float("inf")], labels=noms, right=False)


def build_profil(tcam, dist_gare_km, seuil_km):
    desservie = (dist_gare_km <= seuil_km).where(dist_gare_km.notna())
    croissance = (tcam > 0).map({True: "croissance", False: "déclin ou stable"})
    gare = desservie.map({True: "desservie", False: "non desservie"})
    return (croissance + " – " + gare).where(tcam.notna() & desservie.notna()), desservie


def build_parts_croissance(communes, gares_annees, annee):
    en_croissance = communes["tcam_pop_2017_2023"] > 0
    part_pop = communes.loc[en_croissance, "pop_2023"].sum() / communes["pop_2023"].sum() * 100
    # voyageurs de chaque gare, avec la croissance de sa commune
    voyageurs = gares_annees[gares_annees["annee"] == annee].merge(communes[["code_commune", "tcam_pop_2017_2023"]], on="code_commune")
    part_voy = voyageurs.loc[voyageurs["tcam_pop_2017_2023"] > 0, "voyageurs"].sum() / voyageurs["voyageurs"].sum() * 100
    return part_pop, part_voy


def build_soldes_regionaux(communes):
    # 1. Copie de la base
    communes = communes.copy()
    # 2. Ajout des soldes à partir des fonctions build_solde_
    communes["solde_naturel"] = build_solde_naturel(communes["naissances_2017_2022"],
             communes["deces_2017_2022"])
    communes["solde_migratoire"] = build_solde_migratoire(communes["pop_2017"], communes["pop_2023"],
             communes["solde_naturel"])
    communes["tcam_pop_2017_2023"] = build_tcam(communes["pop_2017"], communes["pop_2023"], 6)
    # 3. Agrégation des données communales par région
    regional = (communes.groupby("code_region", as_index=False).agg(pop_2017=("pop_2017", "sum"),
                 pop_2023=("pop_2023", "sum"),solde_naturel=("solde_naturel", "sum"),
                 solde_migratoire=("solde_migratoire", "sum")))
    # 5. Calcul de la croissance annuelle moyenne régionale
    regional["tcam_pop_2017_2023"] = ((regional["pop_2023"] / regional["pop_2017"]) ** (1/6) - 1) * 100
    # 6. Classement des régions par croissance
    regional = regional.sort_values("tcam_pop_2017_2023", ascending=False)
    return regional


def build_region():
    """Récupère les régions et leurs codes."""

    regions = carti_download(values="France", borders="REGION",
    filter_by="FRANCE_ENTIERE_DROM_RAPPROCHES",year=2025, simplification=50)

    regions = regions.rename(columns={"LIBELLE_REGION": "nom_region", "INSEE_REG": "code_region"})

    return regions



def build_soldes_regionaux(communes):
    # 1. Copie de la base
    communes = communes.copy()
    # 2. Ajout des soldes à partir des fonctions build_solde_
    communes["solde_naturel"] = build_solde_naturel(communes["naissances_2017_2022"],
             communes["deces_2017_2022"])
    communes["solde_migratoire"] = build_solde_migratoire(communes["pop_2017"], communes["pop_2023"],
             communes["solde_naturel"])
    communes["tcam_pop_2017_2023"] = build_tcam(communes["pop_2017"], communes["pop_2023"], 6)
    # 3. Agrégation des données communales par région
    regional = (communes.groupby("code_region", as_index=False).agg(pop_2017=("pop_2017", "sum"),
                 pop_2023=("pop_2023", "sum"),solde_naturel=("solde_naturel", "sum"),
                 solde_migratoire=("solde_migratoire", "sum")))
    # 5. Calcul de la croissance annuelle moyenne régionale
    regional["tcam_pop_2017_2023"] = ((regional["pop_2023"] / regional["pop_2017"]) ** (1/6) - 1) * 100
    # 6. Classement des régions par croissance
    regional = regional.sort_values("tcam_pop_2017_2023", ascending=False)
    return regional


def build_region():
    """Récupère les régions et leurs codes."""

    regions = carti_download(values="France", borders="REGION",
    filter_by="FRANCE_ENTIERE_DROM_RAPPROCHES",year=2025, simplification=50)

    regions = regions.rename(columns={"LIBELLE_REGION": "nom_region", "INSEE_REG": "code_region"})

    return regions
