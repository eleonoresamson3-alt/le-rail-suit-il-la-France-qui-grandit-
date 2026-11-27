"""Fonctions join_ : associe plusieurs bases et les enregistre dans data/clean."""

import pandas as pd
from src.config import CLEAN_DATA_DIR


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
