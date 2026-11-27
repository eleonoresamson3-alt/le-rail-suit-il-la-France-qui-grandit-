"""Étape 2 : variables construites (notebooks 02_base_finale et 03_graphiques).

Fonctions build_ : à partir de la table des communes (jointure.py), calculent les variables
de l'analyse (croissance, parts, classes, profils, CO2), puis celles qui servent aux titres
et aux graphiques.
"""

import pandas as pd


# ---------- 02_base_finale : 2.3 Les variables communales ----------

# taux de croissance annuel moyen entre deux dates, en % par an
def build_tcam(debut, fin, nb_annees):
    # une valeur de départ nulle rend le taux impossible à calculer : NaN
    return ((fin / debut.where(debut > 0)) ** (1 / nb_annees) - 1) * 100


# trajectoire de la commune selon son taux : déclin, stable ou croissance
def build_trajectoire(tcam, seuil):
    return pd.cut(tcam, bins=[-float("inf"), -seuil, seuil, float("inf")],
                  labels=["déclin", "stable", "croissance"])


# part en %, laissée vide quand le dénominateur est sous le minimum
def build_part(numerateur, denominateur, minimum):
    return (numerateur / denominateur * 100).where(denominateur >= minimum)


def build_classe_taille(population, bornes, noms):
    """Classe de taille de chaque commune selon sa population (la dernière classe n'a pas de limite haute)."""
    return pd.cut(population, bins=bornes + [float("inf")], labels=noms, right=False)


# profil de la commune : en croissance ou non × gare à seuil_km ou moins ; renvoie aussi desservie
def build_profil(tcam, dist_gare_km, seuil_km):
    desservie = (dist_gare_km <= seuil_km).where(dist_gare_km.notna())
    croissance = (tcam > 0).map({True: "croissance", False: "déclin ou stable"})
    gare = desservie.map({True: "desservie", False: "non desservie"})
    return (croissance + " – " + gare).where(tcam.notna() & desservie.notna()), desservie


# ---------- 02_base_finale : 2.4 Les liaisons aériennes et leur CO2 (bonus) ----------

# CO2 des passagers de chaque liaison, en avion et en TGV (pas de TGV vers la Corse)
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


# ---------- 03_graphiques : Graphique 2 : soldes naturels et migratoires par région ----------

# solde naturel : naissances moins décès
def build_solde_naturel(naissances, deces):
    return naissances - deces


# solde migratoire apparent : variation de la population moins le solde naturel
def build_solde_migratoire(pop_debut, pop_fin, solde_naturel):
    return (pop_fin - pop_debut) - solde_naturel


# population, soldes naturel et migratoire et croissance de chaque région
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


# ---------- 03_graphiques : Carte 7 : les gares et la croissance de la population ----------

# parts de la population et des voyageurs dans les communes en croissance (titre de la carte 7)
def build_parts_croissance(communes, gares_annees, annee):
    en_croissance = communes["tcam_pop_2017_2023"] > 0
    part_pop = communes.loc[en_croissance, "pop_2023"].sum() / communes["pop_2023"].sum() * 100
    # voyageurs de chaque gare, avec la croissance de sa commune
    voyageurs = gares_annees[gares_annees["annee"] == annee].merge(communes[["code_commune", "tcam_pop_2017_2023"]], on="code_commune")
    part_voy = voyageurs.loc[voyageurs["tcam_pop_2017_2023"] > 0, "voyageurs"].sum() / voyageurs["voyageurs"].sum() * 100
    return part_pop, part_voy
