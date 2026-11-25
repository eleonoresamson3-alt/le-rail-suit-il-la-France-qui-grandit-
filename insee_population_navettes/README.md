# Bases INSEE : population et navettes

Ce dossier rassemble les deux traitements INSEE du projet, leurs résultats et
les explications nécessaires pour les comprendre.

## Par où commencer ?

1. Lire les guides de traitement de la population et des navettes dans `docs/`
   pour suivre chaque nettoyage étape par étape.
2. Ouvrir [`notebooks/03_population.ipynb`](notebooks/03_population.ipynb)
   ou [`notebooks/04_navettes.ipynb`](notebooks/04_navettes.ipynb) dans Jupyter
   ou VS Code et exécuter les cellules dans l'ordre.
3. Consulter les aperçus CSV ci-dessous ou charger les Parquet complets avec
   pandas.

## Contenu

- `notebooks/` : les étapes de collecte, de nettoyage et de vérification.
- `notebooks/06_visualisation_bases.ipynb` : un aperçu interactif des tables
  propres, une par une.
- `src/insee.py` : les fonctions partagées par les deux notebooks.
- `src/collecte.py` : lecture du fichier de réglages.
- `config.yaml` : années, filtres INSEE, mesures et modes retenus.
- `data/processed/rail2026/` : tables complètes au format Parquet et
  échantillons de 20 lignes en CSV, lisibles directement sur GitHub.
- `docs/` : guides pas à pas et dictionnaire des données.
- `creer_apercus.py` : recrée les deux CSV de 20 lignes à partir des Parquet.

Les Parquet contiennent chacun 34 746 lignes dans l'instantané publié. Les CSV
ne sont que des aperçus : ils ne remplacent pas les tables complètes.

## Exécuter les notebooks

Il faut Python 3.13. Depuis ce dossier, installer les dépendances :

```bash
python -m pip install -r requirements.txt
```

Ouvrir ensuite un notebook dans `notebooks/` et exécuter les cellules de haut
en bas. Les fichiers sources ZIP ne sont pas inclus dans cette branche. À la
première exécution, le code les télécharge depuis les pages officielles de
l'INSEE indiquées dans `config.yaml`, puis garde une copie locale pour les
exécutions suivantes. Une connexion Internet est donc nécessaire pour refaire
la collecte depuis les archives d'origine.

Les Parquet et aperçus déjà préparés restent consultables sans exécuter les
notebooks.

## Sources

- Population : [INSEE, séries historiques du recensement 2023](https://www.insee.fr/fr/statistiques/9003931).
- Navettes : [INSEE, déplacements domicile-travail du recensement 2023](https://www.insee.fr/fr/statistiques/8992172).

Les règles, limites et choix de traitement sont détaillés dans le dictionnaire
et dans les guides du dossier `docs/`.
