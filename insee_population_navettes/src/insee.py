"""Deux fichiers du RP2023 : population historique et navettes, COG2026.

Les filtres et modalités proviennent du config.yaml commun. Les observations
incluant une autre commune restent signalées, sans inventer leur ventilation.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile

import pandas as pd
import requests


def _get_base(nom, config):
    """Ouvrir une archive INSEE en la téléchargeant seulement si nécessaire."""
    source = config["insee"][nom]
    chemin = Path(config["dossier_brut"]) / source["fichier"]
    chemin.parent.mkdir(parents=True, exist_ok=True)
    trace = chemin.with_suffix(".provenance.json")
    if not chemin.exists():
        if config.get("hors_ligne", False):
            raise FileNotFoundError(f"Archive INSEE manquante en mode hors ligne : {chemin}")
        # Télécharger le fichier demandé et arrêter si le serveur signale une erreur.
        reponse = requests.get(source["url"], timeout=180)
        reponse.raise_for_status()
        # Vérifier l'archive avant de conserver une réponse du serveur.
        # Le fichier temporaire évite de prendre un téléchargement interrompu
        # pour une archive complète.
        temporaire = chemin.with_suffix(".part")
        temporaire.write_bytes(reponse.content)
        with zipfile.ZipFile(temporaire) as archive:
            assert archive.testzip() is None, "Archive ZIP corrompue"
        temporaire.replace(chemin)
        provenance = {
            "url": reponse.url,
            "collecte_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(reponse.content).hexdigest(),
            "octets": len(reponse.content),
        }
        trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    # Vérifier le fichier avant de le lire : l'archive peut avoir été modifiée
    # depuis son dernier téléchargement.
    contenu = chemin.read_bytes()
    empreinte = hashlib.sha256(contenu).hexdigest()
    if trace.exists():
        provenance = json.loads(trace.read_text(encoding="utf-8"))
        assert provenance["sha256"] == empreinte, f"Archive brute modifiée : {chemin}"
    else:
        # Les premiers fichiers ont été acquis pendant la vérification documentaire.
        # On distingue leur date locale de modification d'une date HTTP inconnue.
        provenance = {
            "url": source["url"],
            "date_modification_cache_utc": datetime.fromtimestamp(
                chemin.stat().st_mtime, tz=timezone.utc).isoformat(),
            "sha256": empreinte,
            "octets": len(contenu),
        }
        trace.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    # Le ZIP contient un seul CSV de données. Le lire en texte garde intacts
    # les codes INSEE, notamment leurs zéros initiaux.
    with zipfile.ZipFile(chemin) as archive:
        membres = [m for m in archive.namelist() if m.endswith("_data.csv")]
        assert len(membres) == 1, membres
        with archive.open(membres[0]) as fichier:
            brut = pd.read_csv(fichier, sep=";", dtype="string", encoding="utf-8-sig")
    print(f"INSEE {nom} : {len(brut):,} lignes brutes lues ; archive et empreinte contrôlées.")
    return brut


def get_population(config):
    """Lire les séries de population INSEE, depuis le cache si possible."""
    return _get_base("population", config)


def get_navettes(config):
    """Lire les navettes INSEE en exploitation principale."""
    return _get_base("navettes", config)


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
