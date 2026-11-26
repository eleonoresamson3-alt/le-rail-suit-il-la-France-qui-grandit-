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




#  on nettoie la base de données pour qu'elle ne garde que les données essentielles à l'analyse, avec une ligne = un mode
def clean_base_carbone(bc, modes):
    #  on commence par renommer les variables
    propre = bc[["Identifiant_de_l'élément", "Total_poste_non_décomposé", "Unité_français"]].rename(
        columns={
            "Identifiant_de_l'élément": "code_ademe",
            "Total_poste_non_décomposé": "co2_kg_km",
            "Unité_français": "unite",
        }
    )
    #  nom court du mode à partir de l'identifiant ADEME (map permet de remplacer les noms parce ceux qui étaient dans le dictionnaire)
    propre.insert(0, "mode", propre["code_ademe"].map(modes)) 
    #  on vérifie qu'il ne manque pas de valeurs, que les modes sont uniques et on réinitialise la numération
    assert len(propre) == len(modes)
    assert propre["mode"].is_unique
    assert propre["co2_kg_km"].notna().all()
    return propre.sort_values("mode").reset_index(drop=True)


def clean_parc_auto(parc, annee_debut, annee_fin):
    # on retire les lignes avec des codes inconnus
    connus = parc[~parc["COMMUNE_CODE"].str.endswith("000")].copy()
    # arrondissements de Paris, Lyon et Marseille ramenés à leur ville
    codes = connus["COMMUNE_CODE"].copy()
    codes[codes.str.startswith("751")] = "75056"
    codes[codes.str.startswith("6938")] = "69123"
    codes[codes.str.startswith("132")] = "13055"
    connus["code_commune"] = codes
    # métropole seulement : les DOM ont un code qui commence par 97
    connus = connus[~connus["code_commune"].str.startswith("97")]
    # une ligne par commune : somme de tous les carburants et vignettes
    colonnes = {f"PARC_{annee_debut}": f"voitures_{annee_debut}", f"PARC_{annee_fin}": f"voitures_{annee_fin}"}
    propre = connus.groupby("code_commune")[list(colonnes)].sum().reset_index().rename(columns=colonnes)
    # la clé des jointures doit être unique et sur 5 caractères
    assert propre["code_commune"].is_unique
    assert (propre["code_commune"].str.len() == 5).all()
    return propre


from src.config import CLEAN_DATA_DIR
from src.collecte import get_frequentation
from src.collecte import get_gares

# la fonction clean_frequentation renvoie et enregistre un dataframe passé au format long en conservant seulement les observation du périmètre et harmonise les noms et les types des variables
def clean_frequentation():

    # 1. Récupération et copie des données brutes
    df_wide = get_frequentation()
    df_wide = df_wide.copy()

    # 2. Suppression des colonnes non désirées
    columns_drop = [col for col in df_wide.columns if "+ Non" in col]
    df_wide = df_wide.drop(columns_drop, axis=1)  # supprime les colonnes Voyageurs  + Non Voyageurs
    years_drop = ["Total Voyageurs 2016", "Total Voyageurs 2015"]
    df_wide = df_wide.drop(years_drop, axis=1)  # supprime les années hors périmètre

    # 3. Passage au format long
    id_vars = [df_wide.columns[i] for i in range(4)]  # colonnes à conserver
    value_vars = [df_wide.columns[i] for i in range(4,11)]  # colonnes à basculer
    df_long = df_wide.melt(id_vars=id_vars, value_vars=value_vars, var_name="indicateur annee", value_name="frequentation")  # passage au format long

    # 4. Ajout de la colonne année et supression de la colonne indicateur année
    df_long["annee"] = df_long["indicateur annee"].str[-4:]  # Ajoute la colonne annee défini en fonction de la colonne indicateur année
    df_long = df_long.drop("indicateur annee", axis=1)  # Supprime la colonne indicateur annee
    cols = list(df_long.columns)
    col = cols.pop(-1)
    cols.insert(-1, col)
    df_long = df_long[cols]  # Repositionne colonne année

    # 5. Nom des variables 
    df_long = df_long.rename(columns={"Code UIC": "code_uic", "Code postal": "code_postal", "Nom de la gare": "nom_gare", "Segmentation DRG": "segmentation_drg"})

    # 6. Harmonisation des types
    df_long["code_uic"] = df_long["code_uic"].astype(str)  # code_uic : str
    df_long["code_postal"] = df_long["code_postal"].astype(str)  # code_postal : str
    df_long["annee"] = df_long["annee"].astype(int)  # annee : str
    df_long["frequentation"] = df_long["frequentation"].astype(int)  # frequentation : integer

    # 7. Vérification de l'unicité
    # Une seule observation par gare et par année
    assert not df_long.duplicated(subset=["code_uic", "annee"]).any(), "Erreur : des doublons gare-année sont présents"

    # 8. Enregistrement du fichier nettoye dans data/clean
    chemin = CLEAN_DATA_DIR / 'frequentation-gares.parquet'
    df_long.to_parquet(chemin, index = False)

    return df_long


# la fonction clean_gares renvoie et enregistre un dataframe conservant seulement les colonnes qui nous intéresse et en harmonisant les noms et les types
def clean_gares():

    # 1. Récupération et copie des données brutes
    df_gares = get_gares()
    df_gares = df_gares.copy()

    # 2. Suppression des colonnes non utilisees
    columns_drop = ['Trigramme', 'Segment(s) DRG', 'Nom_Gare', 'Id_Gare']
    df_gares = df_gares.drop(columns_drop, axis=1) 

    # 3.Nom des variables
    df_gares = df_gares.rename(columns={"Code_UIC": "code_uic", "Code commune": "code_commune", "Position géographique": "position_geographique"})

    # 4. Harmonisation des types
    # Conversion de code_commune au type str faite dans la fonction get_gares

    # 5. Vérification de l'unicité
    assert df_gares["code_uic"].is_unique, "Erreur : plusieurs lignes possèdent le même code_uic"

    # 6. Vérification gares hors métropole
    departements = df_gares["code_commune"].str[:2]
    departements_metropole = [f"{i:02d}" for i in range(1, 96)] + ["2A", "2B"]  # Défini la liste departements_métropole comme la liste des entiers de 1 a 96 au format str ainsi que 2A et 2B
    assert departements.isin(departements_metropole).all(), "Certaines gares ne sont pas situées en France métropolitaine"

    # 7. Enregistrement du fichier nettoye dans data/clean
    chemin = CLEAN_DATA_DIR / 'gares-de-voyageurs.parquet'
    df_gares.to_parquet(chemin, index = False)

    return df_gares