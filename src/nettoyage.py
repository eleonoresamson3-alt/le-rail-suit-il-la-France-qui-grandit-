"""Fonctions clean_ : nettoient chaque base"""

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
