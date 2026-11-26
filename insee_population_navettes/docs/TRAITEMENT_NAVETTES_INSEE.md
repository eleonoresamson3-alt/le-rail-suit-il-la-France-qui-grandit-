# Traitement de la base INSEE des navettes

Ce guide explique comment le fichier des déplacements domicile-travail est
transformé en une table simple à joindre aux communes. Le notebook
[`04_navettes.ipynb`](../notebooks/04_navettes.ipynb) appelle les fonctions de
[`src/insee.py`](../src/insee.py) : les étapes ne sont pas recodées une
deuxième fois dans le notebook.

## 1. Ce que l'on veut obtenir

La source contient plusieurs lignes par commune : une ligne par année et par
mode de déplacement. La table finale contient une ligne par commune et, pour
2017 et 2023, le nombre d'actifs occupés qui utilisent chaque mode retenu.

Elle décrit les actifs occupés d'au moins 15 ans qui résident dans la commune.
Ce n'est pas le nombre de trajets effectués, ni le nombre de personnes qui
travaillent dans cette commune.

## 2. Source et choix de périmètre

Le fichier utilisé est l'archive INSEE
[`DS_RP_NAVETTES_PRINC_2023_CSV_FR.zip`](https://www.insee.fr/fr/statistiques/8992172).
Les valeurs de filtrage sont regroupées dans `config.yaml` :

| Dimension de la source | Valeur gardée | Pourquoi |
|---|---|---|
| `GEO_OBJECT` | `COM` | Garder les communes entières, pas les arrondissements |
| `FREQ` | `A` | Garder les observations annuelles |
| `AGE` | `Y_GE15` | Garder les personnes de 15 ans ou plus |
| `EMPSTA_ENQ` | `1` | Garder les actifs occupés |
| `WORK_AREA` | `_T` | Ne pas limiter selon la zone de travail |
| `RP_MEASURE` | `POP` | Garder les effectifs de population publiés |
| `TIME_PERIOD` | 2017 et 2023 | Comparer les deux années de l'étude |

Les codes géographiques commençant par `97` ou `98` sont ensuite écartés pour
limiter la table à la France métropolitaine. La Corse reste incluse. Les codes
communaux restent du texte afin de conserver les zéros initiaux et les codes
`2A` et `2B`.

## 3. Étapes de préparation

### Étape 1 — Lire l'archive sans abîmer les codes

`get_navettes` télécharge l'archive si elle n'existe pas dans le cache local,
vérifie que le ZIP s'ouvre et garde une empreinte de contrôle. Les colonnes
sont d'abord lues comme du texte : un code géographique est un identifiant,
pas une quantité à additionner.

### Étape 2 — Sélectionner les observations utiles

`_selection` applique les filtres du tableau ci-dessus, puis vérifie la forme
du code communal, les valeurs numériques et les statuts de diffusion admis.
Une valeur négative ou un statut inconnu arrête le traitement pour qu'on
vérifie la source au lieu de corriger la valeur au hasard.

### Étape 3 — Vérifier l'unicité

Après les filtres, une ligne doit être unique pour la combinaison :

`commune × année × mode`

Le code vérifie cette règle. En cas de doublon, il s'arrête au lieu de choisir
arbitrairement une ligne.

### Étape 4 — Réunir les modes qui nous intéressent

La source utilise un code `TRANS` par mode. La configuration les traduit ainsi :

| Colonne finale | Modalité source | Sens |
|---|---|---|
| `actifs_a` | `_T` | Total officiel des actifs occupés |
| `actifs_sans_deplacement_a` | `1` | Pas de déplacement domicile-travail |
| `actifs_marche_a` | `2` | Marche |
| `actifs_deux_roues_a` | `3` et `4` | Vélo et deux-roues motorisés réunis |
| `actifs_voiture_a` | `5` | Voiture |
| `actifs_transports_commun_a` | `6` | Transports en commun, sans isoler le train |

Ici, `a` vaut `2017` ou `2023`. Le vélo et les deux-roues motorisés sont
réunis pour garder des catégories comparables. L'addition utilise une règle
qui laisse le résultat manquant si l'une des deux modalités manque : une
absence de donnée ne devient pas un zéro.

### Étape 5 — Garder les problèmes visibles

La table conserve le statut du total, sous `statut_navettes_a`. Elle crée
également `alerte_navettes_a` : l'alerte est vraie si l'un des modes ou le total
est manquant, ou si son statut n'est pas `A`.

Une valeur publiée avec un statut particulier reste dans la table avec son
alerte. Une valeur manquante reste manquante ; le code ne l'invente pas et ne
la remplace pas par zéro. Dans les fichiers livrés, 12 communes sont signalées
en 2017 et aucune en 2023.

### Étape 6 — Vérifier que les modes retrouvent le total

Le code additionne les cinq catégories de déplacement et compare la somme au
total officiel. L'écart doit rester inférieur ou égal à `0.001`, la tolérance
définie dans `config.yaml`. Ce contrôle repère une modalité oubliée ou un
changement inattendu dans la source.

### Étape 7 — Enregistrer la table

Le notebook enregistre le résultat sous
`data/processed/rail2026/source_navettes.parquet`. La table livrée a 34 746
lignes : une par commune métropolitaine entière.

## 4. Lire correctement le résultat

- Les effectifs peuvent être décimaux : ils proviennent d'estimations pondérées
  du recensement. Il ne faut pas les arrondir pendant le nettoyage.
- Une commune avec zéro actif dans une modalité n'est pas la même chose qu'une
  valeur manquante.
- Le total inclut les actifs sans déplacement ; les parts modales ultérieures
  utilisent le total comme dénominateur.
- `actifs_transports_commun_a` réunit les transports collectifs. Cette colonne
  ne permet pas de compter les usagers du train séparément.
- Les données décrivent le mode principal déclaré au recensement, pas le
  nombre de trajets ou la fréquentation d'une gare.
