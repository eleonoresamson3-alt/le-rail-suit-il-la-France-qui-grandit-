"""Fonctions clean_ : nettoient chaque base"""
import pandas as pd

# cette fonction permet de renommer nos 5 colonnes pour standardiser nos variables entre les bases de données pour les jointures
def clean_contours(communes):
    # les DOM ont un code département qui commence par 97
    metropole = communes[~communes["INSEE_DEP"].str.startswith("97")] #on supprime les DOM (pas de sens pour analyser le train)
    # on renomme nos colonnes
    propre = metropole[["INSEE_COM", "NOM", "INSEE_DEP", "INSEE_REG", "geometry"]].rename(
        columns={
            "INSEE_COM": "code_commune",
            "NOM": "nom_commune",
            "INSEE_DEP": "code_departement",
            "INSEE_REG": "code_region",
        }
    )
    # la clé des jointures doit être unique et sur 5 caractères
    assert propre["code_commune"].is_unique
    assert (propre["code_commune"].str.len() == 5).all()
    return propre.reset_index(drop=True) #on renvoie notre base de données, chaque observation est numérotée de 0 à 34 745 

#création d'une table: chaque ligne correspond à une liaison et les colonnes synthètisent toutes les données sur cette liaison
def clean_dgac(pap, annee_debut, annee_fin):
    # liaisons intérieures : les deux codes OACI commencent par LF
    dom = pap[pap["PAP"].str.match(r"^LF.._LF..$")].copy()   #  on ne récupère que les liaisons intérieures
    dom["annee"] = dom["ANMOIS"].str[:4]   #  on récupère uniquement l'année
    dom["mois"] = dom["ANMOIS"].str[4:]    #    on récupère uniquement les mois
    debut, fin = str(annee_debut), str(annee_fin)

    # description de chaque liaison : noms des aéroports et distance: passage du format long en large
    liaisons = dom.groupby("PAP").agg(
        nom_aeroport_1=("PAP1_LABEL", "first"),
        nom_aeroport_2=("PAP2_LABEL", "first"),
        dist_km=("PAP_DIST", "first"),
    )

    # une ligne par liaison et par mois, une colonne par année (mois non publié = NaN)
    cote_a_cote = dom.pivot_table(index=["PAP", "mois"], columns="annee", values="PAP_PAX")

    # par année : mois publiés et passagers (total minimum à cause du secret statistique)
    for annee in [debut, fin]:
        liaisons[f"mois_publies_{annee}"] = cote_a_cote[annee].notna().groupby("PAP").sum()
        liaisons[f"passagers_{annee}"] = cote_a_cote[annee].groupby("PAP").sum(min_count=1)

    # mois publiés les deux années : la seule base de comparaison juste
    communs = cote_a_cote.dropna()
    liaisons["mois_communs"] = communs.groupby("PAP").size()
    liaisons["mois_communs"] = liaisons["mois_communs"].fillna(0).astype(int)
    for annee in [debut, fin]:
        liaisons[f"passagers_communs_{annee}"] = communs[annee].groupby("PAP").sum()

    # codes OACI des deux aéroports, puis clé de la table
    liaisons = liaisons.reset_index().rename(columns={"PAP": "code_liaison"})
    liaisons.insert(1, "code_oaci_1", liaisons["code_liaison"].str[:4])
    liaisons.insert(2, "code_oaci_2", liaisons["code_liaison"].str[5:])
    assert liaisons["code_liaison"].is_unique
    return liaisons