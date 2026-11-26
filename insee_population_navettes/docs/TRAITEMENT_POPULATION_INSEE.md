# Traitement détaillé de la base de population INSEE

Ce document explique, simplement et étape par étape, le traitement de la base
des **séries historiques du recensement INSEE 2023** utilisé dans ce projet.
Le code exécuté est celui du notebook
[`03_population.ipynb`](../notebooks/03_population.ipynb) et de
[`src/insee.py`](../src/insee.py). Le notebook appelle ces fonctions : il ne
réimplémente pas une deuxième version du nettoyage.

## 1. Objectif et résultat attendu

La source INSEE est une grande table dite **longue** : une ligne peut représenter
une commune, une année, une mesure et d'autres dimensions de diffusion. Nous
voulons une table plus facile à analyser, avec :

- une ligne par **commune entière** de France métropolitaine ;
- une clé communale stable, conservée en texte ;
- la population en 2017 et en 2023 ;
- la superficie ;
- les naissances et décès entre les deux dates de recensement ;
- le statut de diffusion et un indicateur d'alerte pour chaque population.

La sortie s'appelle `source_population.parquet` et est écrite dans
`data/processed/rail2026/`. Elle compte **34 746 communes** dans l'instantané du
projet.

### Champ et limites

L'analyse porte sur les communes entières de la géographie COG 2026. Paris,
Lyon et Marseille restent des communes entières : leurs arrondissements
municipaux ne sont pas des observations séparées. La Corse est incluse dans
la base démographique. Le recensement fournit des valeurs publiées ; ce
traitement n'est ni une estimation de population manquante, ni une correction
statistique.

## 2. Les données utiles et leur sens

La base source est le fichier
`DS_RP_SERIE_HISTORIQUE_2023_CSV_FR.zip`. Le code d'acquisition dans
[`src/insee.py`](../src/insee.py) conserve l'archive brute, vérifie le ZIP,
enregistre sa provenance et contrôle son empreinte SHA-256. Une collecte
ultérieure relit le cache : les données brutes ne sont pas réécrites pendant le
nettoyage.

Les principales colonnes utilisées sont :

| Colonne source | Signification dans le traitement |
|---|---|
| `GEO` | Code géographique INSEE ; utilisé comme identifiant communal |
| `GEO_OBJECT` | Niveau géographique ; `COM` signifie commune entière |
| `FREQ` | Fréquence ; `A` signifie annuelle |
| `RP_MEASURE` | Mesure publiée : population, superficie, naissances ou décès |
| `OCS` | Champ de diffusion ; `_T` signifie toutes les catégories retenues |
| `TIME_PERIOD` | Année ou période associée à l'observation |
| `OBS_VALUE` | Valeur numérique publiée |
| `OBS_STATUS` | Statut de diffusion de l'observation |

Dans le fichier livré, la source brute contient environ **3,05 millions de
lignes**, parce qu'elle décrit de nombreux territoires, mesures et millésimes.
Le nettoyage ne conserve que les dimensions nécessaires à la question posée.

## 3. Étapes de traitement

### Étape 1 — Lire les paramètres communs

Les années, mesures, filtres et chemins sont définis dans `config.yaml`. Le
notebook les lit au lieu de répéter des constantes dans plusieurs endroits.
Cela limite les erreurs et facilite une évolution cohérente du millésime.

```python
from pathlib import Path
import sys

# Exécuter le notebook depuis sa racine ou depuis le dossier notebooks.
if not Path("config.yaml").exists():
    import os
    os.chdir("..")
sys.path.insert(0, str(Path.cwd()))

# Charger les paramètres partagés par les notebooks et le pipeline.
from src.collecte import lire_config
config = lire_config()
```

**Pourquoi ?** La comparaison est définie par `annee_debut: 2017` et
`annee_fin: 2023`. Si les années changent, le code et les contrôles doivent
rester synchronisés.

### Étape 2 — Lire et préserver la source brute

```python
from src.insee import get_population

# Lire l'archive INSEE locale ou la télécharger si elle n'existe pas.
brut = get_population(config)

# Contrôler rapidement la taille et la forme des données reçues.
print(f"{len(brut):,} lignes et {len(brut.columns)} colonnes")
display(brut.head(3))
```

**Pourquoi ?** La première vérification confirme que le fichier s'est lu. Les
trois premières lignes ne sont pas encore les données finales : elles peuvent
concerner un autre territoire, une autre mesure ou une autre année. Il ne faut
donc pas en tirer de conclusion démographique.

L'archive est chargée avec des colonnes en texte au départ. C'est volontaire :
les codes communaux sont des identifiants, pas des nombres. Les convertir en
entiers ferait perdre d'éventuels zéros initiaux.

### Étape 3 — Filtrer le bon champ géographique

La fonction `_selection` dans `src/insee.py` applique les valeurs configurées :

- `GEO_OBJECT = COM` : communes entières, sans arrondissements municipaux ;
- `FREQ = A` : observations annuelles ;
- `OCS = _T` : champ total demandé pour cette source.

Elle retire ensuite les codes géographiques ultramarins commençant par `97` ou
`98`, afin de limiter cette table à la France métropolitaine. La Corse n'est
pas supprimée : ses codes `2A` et `2B` font partie de la métropole.

Enfin, un contrôle vérifie que les codes ont le format communal attendu :
cinq chiffres, ou `2A`/`2B` suivi de trois chiffres.

**Pourquoi filtrer tôt ?** Cela réduit le nombre de lignes examinées et évite
de mélanger des objets géographiques qui n'ont pas la même unité d'analyse.
On filtre sur les codes officiels, pas sur les noms de communes, qui peuvent
être ambigus ou changer d'écriture.

### Étape 4 — Vérifier les valeurs et les statuts

Après la sélection géographique :

- `TIME_PERIOD` est convertie en entier ;
- `OBS_VALUE` est convertie en nombre ;
- toute conversion impossible arrête le traitement (`errors="raise"`) ;
- les valeurs numériques négatives sont refusées ;
- les statuts observés doivent appartenir à `A`, `K` ou `W`.

Les statuts ne sont pas interchangeables :

| Statut | Lecture pratique |
|---|---|
| `A` | Observation diffusée normalement |
| `K` | Valeur non diffusée isolément, notamment parce qu'elle est incluse dans une autre observation |
| `W` | Valeur publiée qui peut inclure des données d'autres unités géographiques |

**Décision importante :** un zéro publié reste zéro ; une valeur absente reste
manquante. Le code ne remplace jamais l'une par l'autre. Le statut reste dans
la table pour que l'utilisateur puisse reconnaître une valeur qui demande de
la prudence.

### Étape 5 — Garder les mesures et années utiles

La configuration associe les noms compréhensibles aux codes source :

| Mesure finale | Code source | Périodes retenues |
|---|---|---|
| Population | `POP` | 2017 et 2023 |
| Superficie | `SUP` | 2023 |
| Naissances | `BRTH` | 2023 |
| Décès | `DEATH` | 2023 |

Les mesures `SUP`, `BRTH` et `DEATH` sont conservées sur la période finale
publiée. Pour ce fichier, les naissances et décès de la ligne 2023 sont des
cumulés correspondant à l'intervalle entre les deux recensements :
**du 1er janvier 2017 au 31 décembre 2022**. Ils ne représentent donc pas
uniquement l'année civile 2023.

### Étape 6 — Vérifier l'unicité avant de réorganiser

À ce stade, une observation doit être identifiée par le triplet :

`GEO × TIME_PERIOD × RP_MEASURE`

Le code vérifie qu'il n'existe aucun doublon sur ces dimensions.

**Pourquoi ne pas supprimer automatiquement les doublons ?** Deux lignes
concurrentes pourraient représenter des modalités ou des données distinctes.
Les supprimer « pour que ça passe » choisirait arbitrairement une observation
et masquerait un problème de source ou de filtre. Le traitement s'arrête donc
et demande une vérification.

### Étape 7 — Passer du format long au format large

Le tableau source contient des lignes séparées pour chaque mesure et chaque
année. La table finale met ces informations dans des colonnes :

| code_commune | pop_2017 | pop_2023 | superficie_km2 | naissances_2017_2022 | deces_2017_2022 |
|---|---:|---:|---:|---:|---:|
| `01001` | valeur publiée | valeur publiée | valeur publiée | valeur publiée | valeur publiée |

Dans `clean_population`, le code :

1. crée une liste triée des codes communaux retenus ;
2. utilise ce code comme index temporaire ;
3. sélectionne chaque mesure et sa période ;
4. aligne les mesures sur le même index avec `reindex` ;
5. remet `code_commune` en colonne pour faciliter les jointures.

`reindex` est essentiel : il aligne les valeurs par code communal et laisse une
valeur manquante lorsqu'une observation n'est pas disponible. Il n'invente pas
de zéro et ne décale pas une valeur d'une commune vers une autre.

### Étape 8 — Garder les statuts et fabriquer des alertes

Pour les populations 2017 et 2023, la sortie contient :

- `statut_pop_2017` et `statut_pop_2023` ;
- `alerte_population_2017` et `alerte_population_2023`.

Une alerte est vraie si la population est absente ou si son statut n'est pas
`A`. La valeur publiée et son statut sont néanmoins conservés.

**Pourquoi ne pas retirer ces communes ?** On garde la couverture complète de
la source. Les analyses de croissance neutralisent ensuite les comparaisons
signalées au lieu de supprimer silencieusement les communes ou de prétendre
que leurs valeurs sont normales.

Pour la superficie, les naissances et les décès, le code exige le statut `A`.
Si un statut différent apparaît, le traitement échoue explicitement : le
contrat de données doit être réexaminé avant de poursuivre.

### Étape 9 — Contrôler la table finale et l'exporter

```python
from src.insee import clean_population

# Transformer les lignes de la source en une table communale.
table = clean_population(brut, config)

# Une commune ne doit apparaître qu'une seule fois.
assert table["code_commune"].is_unique

# Une superficie valide doit être strictement positive.
assert table["superficie_km2"].dropna().gt(0).all()

# Comparer les totaux nationaux à la référence stockée dans la configuration.
totaux = table[["pop_2017", "pop_2023"]].sum(min_count=1)
for annee in (config["annee_debut"], config["annee_fin"]):
    observe = int(totaux[f"pop_{annee}"])
    attendu = config["insee"]["population_metropole_reference"][annee]
    assert observe == attendu, f"Total {annee} inattendu : {observe} au lieu de {attendu}"

# Écrire le fichier propre dans le dossier prévu par la configuration.
propre = Path(config["dossier_propre"])
propre.mkdir(parents=True, exist_ok=True)
table.to_parquet(propre / "source_population.parquet", index=False)
```

Pour l'instantané fourni, les contrôles donnent :

- population 2017 : **64 639 133** ;
- population 2023 : **66 165 815** ;
- **aucune valeur de population manquante ou en alerte** ;
- une ligne par code communal retenu.

Les totaux sont un contrôle de cohérence global, pas une preuve suffisante à
eux seuls : la clé unique, les statuts, les formats et les dimensions doivent
également être contrôlés.

## 4. Variables calculées après le nettoyage

Le notebook source produit les variables élémentaires. Les indicateurs dérivés
sont calculés plus tard lors de l'assemblage dans
[`src/variables.py`](../src/variables.py), afin qu'ils soient construits une
seule fois pour l'ensemble du projet.

| Indicateur | Calcul | Précaution |
|---|---|---|
| Variation de population | `pop_2023 - pop_2017` | En habitants sur la période |
| TCAM démographique | `100 × ((pop_2023 / pop_2017) ** (1 / 6) - 1)` | Seulement si la base 2017 est strictement positive et sans alerte de statut |
| Densité | `pop_2023 / superficie_km2` | Habitants par km² ; superficie positive requise |
| Solde naturel | `naissances_2017_2022 - deces_2017_2022` | Événements cumulés sur l'intervalle indiqué |
| Solde migratoire apparent | `variation_pop - solde_naturel` | Résidu qui peut aussi inclure des ajustements statistiques |

Le TCAM convertit une variation sur six ans en rythme annuel moyen composé. Il
ne s'agit pas de la moyenne des variations annuelles réellement observées. Si
la population initiale vaut zéro, le taux n'est pas défini : on garde une
valeur manquante plutôt que de produire une division invalide.

Le solde migratoire **apparent** n'est pas un comptage direct des migrations.
Il est obtenu par différence entre la variation de population et le solde
naturel, et peut inclure d'autres ajustements de mesure.

## 5. Résumé du choix de traitement

| Choix | Justification |
|---|---|
| Utiliser `COM`, pas `ARM` | Une ligne doit représenter une commune entière |
| Garder 2017 et 2023 pour la population | Dates de comparaison retenues par le projet |
| Garder `SUP`, `BRTH`, `DEATH` en période finale | Besoin de densité et de décomposition démographique |
| Garder les codes en texte | Préserver les zéros initiaux et les codes corses |
| Tester les doublons au lieu de les supprimer | Éviter un choix arbitraire et rendre les anomalies visibles |
| Garder séparément zéro, manquant et statut | Ne pas transformer une absence ou un statut particulier en observation normale |
| Aligner les colonnes sur les codes communaux | Garantir une jointure et un pivot corrects |
| Vérifier les totaux de population | Détecter un filtre ou une extraction incohérente |
| Réserver les indicateurs dérivés à l'assemblage | Éviter plusieurs implémentations divergentes dans le projet |

## 6. Reproduire le traitement

Depuis la racine du projet, avec l'environnement Python installé :

```powershell
python -m pip install -r requirements.txt
python run.py --offline --sources
```

Le mode hors ligne requiert que l'archive brute soit déjà présente. Pour
exécuter seulement le notebook de population dans Jupyter, ouvrir
[`notebooks/03_population.ipynb`](../notebooks/03_population.ipynb) depuis la
racine du projet ou depuis le dossier `notebooks`.
