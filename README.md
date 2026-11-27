# Le rail suit-il la France qui grandit ?

Projet de Python pour la data science (ENSAE, 2e année) : Éléonore, Mathilde et Tamsir.

Entre 2017 et 2023, la population augmente dans certaines communes et baisse dans d'autres.
La fréquentation des gares suit-elle ces évolutions, et qui dépend de la voiture faute de gare proche ?
En bonus : le train face à l'avion sur les liaisons intérieures.

## Installation

Python 3.14. Depuis la racine du projet :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name rail --display-name "Python (rail)"
```

Puis ouvrir les notebooks avec le noyau « Python (rail) ».

## Les notebooks, dans l'ordre

| Notebook | Contenu |
|---|---|
| `01_donnees` | collecte et nettoyage de chaque source, tables propres dans `data/clean/` |
| `02_base_finale` | jointures et variables, tables finales dans `data/clean/base_finale/` |
| `03_graphiques` | les 15 graphiques du projet, enregistrés dans `figures/` |
| `04_bonus_train_avion` | bonus : trafic aérien et CO2 de l'avion comparé au TGV |
| `05_analyse_mobilites` | statistiques descriptives et ACP |

Chaque notebook relit les tables enregistrées par le précédent : on peut en relancer un seul.
Les fichiers bruts ne sont téléchargés qu'une fois, dans `data/raw/`.

## Organisation

```
config.yaml          paramètres : années, adresses des données, seuils
src/collecte.py      get_    : téléchargement des données brutes (et des régions)
src/nettoyage.py     clean_  : nettoyage de chaque base
src/jointure.py      join_, build_ : bases SNCF, gares rattachées aux communes, table des communes
src/variables.py     build_  : variables construites (croissance, parts, profils, CO2)
src/visualisation.py plot_, map_ : graphiques et cartes
src/analyse_mobilites.py       statistiques et ACP
```

Dans chaque fichier, les fonctions sont rangées dans l'ordre où les notebooks les utilisent.

## Sources

- Contours des communes au 1er janvier 2026 : cartiflette (IGN, INSEE).
- Population, naissances, décès et navettes domicile-travail : INSEE, recensement 2023.
- Gares et fréquentation : SNCF Open Data.
- Parc automobile par commune : SDES.
- Trafic aérien par paire d'aéroports : DGAC (bonus).
- Facteurs d'émission : ADEME, Base Carbone (bonus).
