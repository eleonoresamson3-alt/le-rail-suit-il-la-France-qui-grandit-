# le-rail-suit-il-la-France-qui-grandit-

## Traitement INSEE : population et navettes

Les notebooks, le code commenté, les guides et les tables préparées sont
regroupés dans [insee_population_navettes](./insee_population_navettes/).

## Analyse des mobilités

Le notebook [analyse_mobilites_population](./notebooks/analyse_mobilites_population.ipynb)
utilise la base `data/clean/base_finale/base_finale_communes_variables.parquet`.
Ses fonctions statistiques et les graphiques ACP sont dans
[`src/analyse_mobilites.py`](./src/analyse_mobilites.py). Installer les dépendances
de `requirements.txt`, puis ouvrir le notebook depuis la racine du dépôt.
