"""Étape 1 : nettoyage (notebook 01_donnees).

Fonctions clean_ : reçoivent les données brutes de collecte.py et renvoient une table propre,
une ligne par commune (ou par gare, par liaison...), enregistrée dans data/clean/.
"""

import pandas as pd
from src.config import CLEAN_DATA_DIR
from src.collecte import get_frequentation
from src.collecte import get_gares


# ---------- 01_donnees : 1.1 Contours des communes (cartiflette) ----------

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


# ---------- 01_donnees : 1.2 Population des communes (INSEE) ----------

def _selection(brut, nom, config):
    """Garder le champ géographique demandé et vérifier les valeurs de base."""
    # Les dimensions INSEE sont filtrées par égalité exacte : on ne veut ni
    # mélanger plusieurs champs d'étude, ni transformer une absence en valeur.
    selection = pd.Series(True, index=brut.index)
    for colonne, valeur in config["insee"][nom]["filtres"].items():
        selection &= brut[colonne].eq(str(valeur))
    table = brut.loc[selection].copy()

    # COM désigne la commune entière ; ARM, présents dans le fichier, sont exclus.
    # Les chiffres 97/98 désignent l'outre-mer et ne sont pas des départements métro.
    prefixes = tuple(config["geographie"]["prefixes_hors_metropole"])
    table = table[~table["GEO"].str.startswith(prefixes)].copy()

    # Les identifiants restent des chaînes : les convertir en nombres ferait
    # perdre les zéros initiaux des codes communaux.
    assert table["GEO"].str.fullmatch(r"(?:\d{5}|2[AB]\d{3})").all()
    table["TIME_PERIOD"] = pd.to_numeric(table["TIME_PERIOD"], errors="raise").astype(int)
    table["OBS_VALUE"] = pd.to_numeric(table["OBS_VALUE"], errors="raise").astype(float)
    assert table["OBS_VALUE"].dropna().ge(0).all()

    # Les statuts sont une information de qualité : ils seront conservés pour
    # distinguer une observation normale d'une valeur regroupée ou manquante.
    statuts = set(table["OBS_STATUS"].dropna())
    assert statuts.issubset({"A", "K", "W"}), f"Statut INSEE à examiner : {statuts}"
    return table


def clean_population(brut, config):
    """Préparer une ligne par commune avec populations, surface et état civil.

    Les populations sont gardées pour les deux années étudiées. Les naissances
    et décès de la ligne 2023 sont les cumuls entre les recensements
    (du 1er janvier 2017 au 31 décembre 2022). Les statuts douteux restent
    visibles au lieu d'être remplacés par des valeurs inventées.
    """
    # Après la sélection, chaque ligne décrit une commune, une période et une
    # mesure. On garde seulement les mesures et les deux dates nécessaires.
    table = _selection(brut, "population", config)
    debut, fin = config["annee_debut"], config["annee_fin"]
    mesures = config["insee"]["population"]["mesures"]
    cles = ["GEO", "TIME_PERIOD", "RP_MEASURE"]
    utile = table[table["RP_MEASURE"].isin(mesures.values()) &
                  table["TIME_PERIOD"].isin([debut, fin])].copy()

    # Un doublon sur ces trois dimensions rendrait le pivot ambigu : on s'arrête
    # plutôt que de supprimer arbitrairement une ligne.
    assert not utile.duplicated(cles).any(), "Doublon commune × année × mesure INSEE"

    # L'index de sortie est la liste des codes observés. Reindexer chaque
    # mesure sur cette liste aligne les colonnes sans associer des communes
    # différentes, et laisse les observations absentes en valeur manquante.
    codes = pd.Index(sorted(utile["GEO"].unique()), name="code_commune")
    propre = pd.DataFrame(index=codes)
    for annee in (debut, fin):
        ligne = utile[(utile["TIME_PERIOD"] == annee) &
                      utile["RP_MEASURE"].eq(mesures["population"])].set_index("GEO")
        propre[f"pop_{annee}"] = ligne["OBS_VALUE"].reindex(codes)
        propre[f"statut_pop_{annee}"] = ligne["OBS_STATUS"].reindex(codes)

        # Une valeur n'est interprétable comme population communale comparable
        # que si elle existe et porte le statut normal A. On marque l'alerte,
        # sans effacer la valeur publiée ni la remplacer par zéro.
        propre[f"alerte_population_{annee}"] = (
            propre[f"statut_pop_{annee}"].ne("A") | propre[f"pop_{annee}"].isna()).fillna(True)

    # La superficie et les cumuls d'état civil sont publiés à la période finale.
    # BRTH/DEATH à 2023 décrivent ici les événements entre les deux recensements.
    colonnes = {
        "superficie": "superficie_km2",
        "naissances": f"naissances_{debut}_{fin - 1}",
        "deces": f"deces_{debut}_{fin - 1}",
    }
    for mesure, colonne in colonnes.items():
        ligne = utile[(utile["TIME_PERIOD"] == fin) &
                      utile["RP_MEASURE"].eq(mesures[mesure])].set_index("GEO")
        propre[colonne] = ligne["OBS_VALUE"].reindex(codes)
        # Les mesures auxiliaires doivent avoir été diffusées normalement :
        # un statut inattendu exige une vérification de la source.
        assert ligne["OBS_STATUS"].eq("A").all(), f"Statut inattendu pour {mesure} à examiner"

    # La sortie est une table large prête à être jointe aux contours, avec la
    # clé redevenue une colonne explicite.
    propre = propre.reset_index()
    assert propre["code_commune"].is_unique
    assert propre["superficie_km2"].dropna().gt(0).all()
    print(f"Population propre : {len(propre):,} communes métropolitaines, sans double compte des arrondissements.")
    for annee in (debut, fin):
        alerte = propre[f"alerte_population_{annee}"]
        print(f"  {annee} : {propre[f'pop_{annee}'].isna().sum()} valeurs absentes, "
              f"{alerte.sum()} alertes de périmètre ; somme publiée {propre[f'pop_{annee}'].sum():,.0f}.")
    return propre


# ---------- 01_donnees : 1.3 Modes de déplacement domicile–travail (INSEE) ----------

def clean_navettes(brut, config):
    """Préparer les effectifs d'actifs et leurs modes de déplacement.

    Le vélo et les deux-roues motorisés sont réunis. Une valeur manquante reste
    manquante ; les parts en pourcentage seront calculées plus tard, une fois
    les tables réunies.
    """
    # Garder les communes entières, le champ d'étude demandé et les deux années.
    table = _selection(brut, "navettes", config)
    annees = [config["annee_debut"], config["annee_fin"]]
    table = table[table["TIME_PERIOD"].isin(annees)].copy()
    assert not table.duplicated(["GEO", "TIME_PERIOD", "TRANS"]).any(), "Modes non uniques après filtres"
    modes = config["insee"]["navettes"]["modes"]
    codes = pd.Index(sorted(table["GEO"].unique()), name="code_commune")
    propre = pd.DataFrame(index=codes)
    for annee in annees:
        # Chaque ligne source décrit un mode. Le pivot met un mode par colonne,
        # afin qu'on puisse additionner le total et les modes choisis.
        periode = table[table["TIME_PERIOD"] == annee]
        effectifs = periode.pivot(index="GEO", columns="TRANS", values="OBS_VALUE").reindex(codes)
        etats = periode.pivot(index="GEO", columns="TRANS", values="OBS_STATUS").reindex(codes)

        # Les codes de modes sont écrits comme du texte dans le fichier INSEE.
        codes_modes = [str(code) for modalites in modes.values() for code in modalites]
        for mode, modalites in modes.items():
            selection = [str(code) for code in modalites]
            assert set(selection).issubset(effectifs.columns), f"Modalité absente : {mode} / {selection}"
            colonne = f"actifs_{annee}" if mode == "total" else f"actifs_{mode}_{annee}"
            # min_count empêche de transformer une modalité manquante en zéro.
            propre[colonne] = effectifs[selection].sum(axis=1, min_count=len(selection))

        # Une commune est signalée si un mode manque ou si son statut n'est pas
        # normal. Le statut du total est gardé pour comprendre l'alerte.
        propre[f"alerte_navettes_{annee}"] = (
            etats[codes_modes].ne("A").fillna(True).any(axis=1) |
            effectifs[codes_modes].isna().any(axis=1))
        # Statut du total : utile pour distinguer une inclusion W d'une absence K.
        propre[f"statut_navettes_{annee}"] = etats[[str(x) for x in modes["total"]]].iloc[:, 0]
        # Vérifier que les cinq modes retombent bien sur le total officiel.
        colonnes = [f"actifs_{mode}_{annee}" for mode in modes if mode != "total"]
        ecart = propre[colonnes].sum(axis=1, min_count=len(colonnes)) - propre[f"actifs_{annee}"]
        tolerance = config["insee"]["tolerance_additivite"]
        assert ecart.abs().dropna().le(tolerance).all(), (
            "La somme des modes diffère du total officiel."
        )
        print(f"  Navettes {annee} : écart maximal somme des cinq modes / total = "
              f"{ecart.abs().max():.6g} ; {propre[f'alerte_navettes_{annee}'].sum()} alertes.")
    propre = propre.reset_index()
    assert propre["code_commune"].is_unique
    print(f"Navettes propres : {len(propre):,} communes métropolitaines ; zéro publié conservé, absence conservée.")
    return propre


# ---------- 01_donnees : 1.4 Gares et fréquentation (SNCF) ----------

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


# ---------- 01_donnees : 1.5 Parc automobile (SDES) ----------

# une ligne par commune : voitures des particuliers au début et à la fin de la période
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


# ---------- 01_donnees : 1.6 Trafic aérien (DGAC, série PAP), bonus ----------

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


# ---------- 01_donnees : 1.7 Facteurs d'émission (ADEME, Base Carbone), bonus ----------

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
