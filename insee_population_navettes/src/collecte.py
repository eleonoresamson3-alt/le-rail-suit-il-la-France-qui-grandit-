"""Lire les paramètres du projet et récupérer les données SNCF."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yaml


def lire_config():
    """Lire config.yaml, le fichier qui rassemble les paramètres du projet."""
    with Path("config.yaml").open(encoding="utf-8") as fichier:
        return yaml.safe_load(fichier)


def get_json(url, chemin, params=None, hors_ligne=False):
    """Lire une réponse JSON en cache ou la télécharger une première fois.

    L'adresse et l'empreinte du fichier sont gardées à côté des données. On peut
    ainsi vérifier plus tard que le fichier utilisé n'a pas été modifié.
    """
    chemin = Path(chemin)
    trace_path = chemin.with_suffix(".provenance.json")
    if not chemin.exists():
        if hors_ligne:
            raise FileNotFoundError(f"Archive SNCF manquante : {chemin}")
        # Télécharger la réponse et arrêter si le serveur renvoie une erreur.
        reponse = requests.get(url, params=params, timeout=90)
        reponse.raise_for_status()
        reponse.json()

        # Écrire d'abord dans un fichier temporaire : une interruption du
        # téléchargement ne laissera pas un faux fichier complet dans le cache.
        chemin.parent.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(".part")
        temporaire.write_bytes(reponse.content)
        temporaire.replace(chemin)
        # Garder l'adresse, la date et l'empreinte du fichier reçu.
        trace = {
            "url": reponse.url,
            "collecte_utc": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(reponse.content).hexdigest(),
        }
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    # Que le fichier vienne du cache ou d'un téléchargement, vérifier son
    # empreinte avant de le relire.
    contenu = chemin.read_bytes()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if hashlib.sha256(contenu).hexdigest() != trace["sha256"]:
        raise ValueError(f"L'empreinte de l'archive SNCF est différente : {chemin}")
    return json.loads(contenu)


def get_sncf(nom_jeu, config, tri):
    """Télécharger les pages d'un jeu SNCF et les réunir en un tableau."""
    dossier = Path(config["dossier_brut"]) / nom_jeu
    url = f"{config['sncf']['api']}/{nom_jeu}"
    limite = config["sncf"]["page"]
    hors_ligne = config.get("hors_ligne", False)
    # La page de description est conservée elle aussi : elle documente le jeu.
    get_json(url, dossier / "metadata.json", hors_ligne=hors_ligne)

    lignes = []
    total = None
    # L'API envoie les résultats par petits groupes. Le tri fixe et l'offset
    # permettent de demander la page suivante sans recommencer au début.
    while total is None or len(lignes) < total:
        debut = len(lignes)
        page = get_json(
            f"{url}/records", dossier / f"page_{debut:05d}.json",
            {"limit": limite, "offset": debut, "order_by": tri},
            hors_ligne=hors_ligne,
        )
        if total is not None and page["total_count"] != total:
            raise ValueError(f"Le total annoncé a changé pendant la collecte de {nom_jeu}.")
        total = page["total_count"]
        lignes.extend(page["results"])
        # Une page vide avant la fin signale une collecte incomplète.
        if not page["results"] and len(lignes) < total:
            raise ValueError(f"Page vide avant la fin de la collecte de {nom_jeu}.")
    assert len(lignes) == total > 0, nom_jeu
    return pd.DataFrame(lignes)


def get_frequentation(config):
    """Récupérer l'historique SNCF des comptages par gare."""
    return get_sncf(config["sncf"]["frequentation"], config, "code_uic_complet")


def get_gares(config):
    """Récupérer le référentiel SNCF des noms et coordonnées de gares."""
    return get_sncf(config["sncf"]["gares"], config, "id")
