# Le rail suit-il la France qui grandit ?

_Auteurs : Mathilde DECOUCHON; Tamsir NDONG; Eléonore SAMSON_

Projet de Python pour la data science (ENSAE, 2e année 2026)

Entre 2017 et 2023, la population en France métropolitaine continuait de suivre une dynamique de croissance.
Cependant, cette dynamique n'est pas uniforme sur le territoire : certaines communes connaissent une augmentation et d'autres une baisse de leur population.
Sur la même période, les enjeux de développement durable et notamment de décarbonation des transports ont gagné en importance.
Le principal levier de cette transition dans le domaine des transports est le rail.
Aussi peut-on se demander si la fréquentation des gares suit une trajectoire similaire à celle de la population ? A l'inverse, qui dépend de la voiture faute de gare proche ?

Entre 2017 et 2023, la population de France métropolitaine a poursuivi sa croissance. Celle-ci est inégalement répartie sur le territoire : certaines communes ont gagné des habitants, tandis que d'autres en ont perdu.

Parallèlement, les enjeux de développement durable, et notamment la décarbonation des transports, ont pris une place croissante dans les politiques publiques. Dans cette transition, le transport ferroviaire constitue un levier essentiel.

Dès lors, une question se pose : la fréquentation des gares suit-elle les évolutions démographiques du territoire ? À l'inverse, quelles populations restent éloignées du réseau ferroviaire et dépendent ainsi davantage de la voiture pour leurs déplacements ?

Complément : le train face à l'avion sur les liaisons intérieures (complément d'analyse non abouti par manque de temps)


## Données et sources
Nous avons collecté et croisé plusieurs types de données :
- Données ferroviaires : fréquentation et localisation des gares entre 2015 et 2023 - **SNCF Open Data**
- Données démographiques : population des communes en 2017 et 2023 - **INSEE, recensement 2023**
- Données géographiques : contours des communes au 1er janvier 2026 - **cartiflette (IGN, INSEE)**
- Données automobiles : parc automobile par commune - **SDES**

Complément : 
- Transport aérien : données relatives au trafic aérien - **DGAC**
- Émissions carbone : données relatives aux émissions de gaz à effet de serre - **ADEME, Base Carbone**

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
src/collecte.py      get_    : téléchargement des données brutes
src/nettoyage.py     clean_  : nettoyage de chaque base
src/jointure.py      join_   : réunion des deux bases SNCF
src/variables.py     build_  : jointures communales et variables construites
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
