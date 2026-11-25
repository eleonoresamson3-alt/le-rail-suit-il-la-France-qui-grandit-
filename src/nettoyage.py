"""Fonctions clean_ : nettoient chaque base et écrivent dans data/clean/."""

from src.config import CLEAN_DATA_DIR


def clean_frequentation(df_wide):

    # 1. Copie des données brutes
    df_wide = df_wide.copy()

    # 2. Suppression des colonnes non désirées
    columns_drop = [col for col in df_wide.columns if "+ Non" in col]
    df_wide = df_wide.drop(columns_drop, axis=1)  # supprime les colonnes Voyageurs  + Non Voyageurs
    years_drop = ["Total Voyageurs 2023", "Total Voyageurs 2016", "Total Voyageurs 2015"]
    df_wide = df_wide.drop(years_drop, axis=1)  # supprime les années hors périmètre

    # 3. Passage au format long
    id_vars = [df_wide.columns[i] for i in range(4)]  # colonnes à conserver
    value_vars = [df_wide.columns[i] for i in range(5,10)]  # colonnes à basculer
    df_long = df_wide.melt(id_vars=id_vars, value_vars=value_vars, var_name="indicateur annee", value_name="frequentation")  # passage au format long

    # 4. Ajout de la colonne année et Supression de la colonne indicateur année
    df_long["annee"] = df_long["indicateur annee"].str[-4:]  # Ajoute la colonne annee défini en fonction de la colonne indicateur année
    df_long = df_long.drop("indicateur annee", axis=1)  # Supprime la colonne indicateur annee
    cols = list(df_long.columns)
    col = cols.pop(-1)
    cols.insert(-1, col)
    df_long = df_long[cols]  # Repositionne colonne année

    # 4. Nom des variables 
    df_long = df_long.rename(columns={"Code UIC": "code_uic", "Code postal": "code_postal", "Nom de la gare": "nom_gare", "Segmentation DRG": "segmentation_drg"})

    # 5. Harmonisation des types
    df_long["code_uic"] = df_long["code_uic"].astype("string")  # code_uic : str
    df_long["code_postal"] = df_long["code_postal"].astype("string")  # code_postal : str
    df_long["annee"] = df_long["annee"].astype(int)  # annee : str
    df_long["frequentation"] = df_long["frequentation"].astype(float)  # frequentation : float

    # 5. Vérification de l'unicité
    # Une seule observation par gare et par année
    assert not df_long.duplicated(subset=["code_uic", "annee"]).any(), "Erreur : des doublons gare-année sont présents"

    # 7. Enregistrement du fichier nettoye dans data/clean
    chemin = CLEAN_DATA_DIR / 'gares.csv'
    df_long.to_csv(chemin, sep =',', index = False)

    return df_long


def clean_gares(df_gares):

    # 1. Copies des données brutes
    df_gares = df_gares.copy()

    # 2. Suppression des colonnes non utilisees
    columns_drop = ['Trigramme', 'Segment(s) DRG']
    df_gares = df_gares.drop(columns_drop, axis=1) 

    # 3.Nom des variables
    df_gares = df_gares.rename(columns={"Code_UIC": "code_uic", "Code commune": "code_commune", "Nom_Gare": "nom_gare", "Position géographique": "position_geographique", "Id_Gare": "id_gare"})

    # 4. Harmonisation des types
    df_gares["code_commune"] = df_gares["code_commune"].astype("string")  # code_commune : str

    # 5. Vérification de l'unicité
    assert df_gares["code_uic"].is_unique, "Erreur : plusieurs lignes possèdent le même code_uic"

    # 6. Enregistrement du fichier nettoye dans data/clean
    chemin = CLEAN_DATA_DIR / 'gares.csv'
    df_gares.to_csv(chemin, sep =',', index = False)

    return df_gares