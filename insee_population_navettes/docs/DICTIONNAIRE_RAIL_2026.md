# Dictionnaire des données — version rail 2017–2023

Ce dictionnaire décrit la version définie par la feuille de route du 24 novembre 2026 : **France métropolitaine, communes entières au 1er janvier 2026**, comparaison principale **2017–2023**, historique ferroviaire **2015–2024**. Les paramètres opérationnels et seuils sont dans `config.yaml`.

Les fichiers de travail communs sont `data/processed/rail2026/communes.parquet`, `gares.parquet` et `gares_annees.parquet`. Les noms de colonnes ci-dessous correspondent aux fichiers livrés et aux fonctions de `src/insee.py`, `src/nettoyage.py`, `src/geographie.py` et `src/variables.py`.

## 1. Les cinq bases

| Base | Données retenues | Accès et référence | Clé |
|---|---|---|---|
| SNCF, fréquentation des gares | Comptages annuels par UIC, 2015–2024 | API Opendatasoft, jeu [`frequentation-gares-archive`](https://ressources.data.sncf.com/explore/dataset/frequentation-gares-archive/) | `code_uic` |
| SNCF, gares de voyageurs | Nom de référence, code communal, longitude et latitude | API Opendatasoft, jeu [`gares-de-voyageurs`](https://ressources.data.sncf.com/explore/dataset/gares-de-voyageurs/) | `code_uic` après séparation des listes |
| INSEE, séries historiques du RP 2023 | Populations 2017 et 2023, superficie, naissances et décès de 2017 à 2022 | Fichier `DS_RP_SERIE_HISTORIQUE_2023_CSV_FR.zip`, [publication 9003931](https://www.insee.fr/fr/statistiques/9003931) | `code_commune` |
| INSEE, navettes du RP 2023 en exploitation principale | Actifs occupés et modes domicile-travail, 2017 et 2023 | Fichier `DS_RP_NAVETTES_PRINC_2023_CSV_FR.zip`, [publication 8992172](https://www.insee.fr/fr/statistiques/8992172) | `code_commune` |
| Cartiflette, contours COG 2026 | Communes, départements et régions de métropole | [Cartiflette / InseeFrLab](https://github.com/InseeFrLab/cartiflette), contours IGN enrichis de l'appartenance INSEE, fichiers GeoParquet | Codes communal, départemental ou régional |

Les trois niveaux de contours appartiennent à la même cinquième base. Les populations contenues dans les attributs Cartiflette sont écartées : les populations d'analyse proviennent uniquement du fichier historique INSEE.

## 2. Règles de lecture

- `code_commune` est une chaîne de cinq caractères ; les zéros initiaux et lettres corses sont conservés. `code_departement` est une chaîne de deux caractères, y compris `2A` et `2B`. `code_region` est une chaîne. `code_uic` est une chaîne de huit chiffres.
- Un **zéro publié reste zéro**. Une absence reste une valeur manquante ; aucun nombre de voyageurs, d'actifs ou d'habitants n'est imputé.
- Les effectifs de recensement des actifs peuvent être pondérés et décimaux. On les agrège avant de calculer une part ; la moyenne de parts communales n'est pas une part régionale.
- Un comptage de gare n'est pas un voyage unique, ni un voyage effectué par un résident de la commune. Une gare dessert généralement un territoire plus large que sa commune d'implantation.
- `geometry` est stockée en WGS84, EPSG:4326. Les distances et centroïdes sont calculés en Lambert 93, EPSG:2154. Les degrés de longitude et latitude ne sont pas des kilomètres.
- Paris, Lyon et Marseille sont des communes entières. Les arrondissements municipaux ne constituent pas des observations communales supplémentaires.

## 3. Les trois tables finales

| Table | Une ligne représente | Clé unique | Effectif de l'instantané |
|---|---|---|---:|
| `communes.parquet` | Une commune métropolitaine entière en COG 2026 | `code_commune` | 34 746 |
| `gares.parquet` | Un UIC présent dans l'historique de fréquentation SNCF, y compris les échecs de localisation | `code_uic` | 3 021 |
| `gares_annees.parquet` | Un UIC de fréquentation × une année de 2015 à 2024 | `code_uic`, `annee` | 30 210 |

Les analyses ferroviaires métropolitaines sélectionnent les gares ayant `code_commune` renseigné. Les gares non rattachées restent dans les fichiers pour mesurer la couverture et préserver les observations sources. Elles ne doivent pas être interprétées comme des gares métropolitaines localisées.

## 4. Identification et géométrie

| Colonne | Tables | Définition, unité et usage |
|---|---|---|
| `code_commune` | Les trois tables | Code communal harmonisé au COG 2026. Dans les tables ferroviaires, manquant si aucun rattachement sûr n'est obtenu. |
| `code_departement`, `code_region` | Communes | Codes d'appartenance issus de Cartiflette 2026. Identifiants, pas quantités. |
| `nom_commune`, `nom_departement`, `nom_region` | Communes | Libellés géographiques officiels fournis avec les contours. Les jointures n'utilisent pas un rapprochement approximatif sur ces noms. |
| `geometry` | Communes | Polygone ou multipolygone communal, WGS84. Les contours complets Cartiflette sont demandés avec `simplification=0`. |
| `geometry` | Gares | Point construit à partir de la longitude et latitude du référentiel SNCF. Manquant si la localisation manque ou a été rejetée. |
| `code_uic` | Gares et panel | Identifiant UIC SNCF à huit chiffres, conservé en chaîne. L'unité statistique est l'UIC publié. |
| `nom_gare` | Gares et panel | Libellé du fichier de fréquentation. |
| `nom_gare_ref` | Gares | Libellé du référentiel des gares, distinct du nom dans la fréquentation. |
| `code_commune_source` | Gares | Code INSEE du référentiel SNCF avant validation au millésime 2026. Peut être ancien ou désigner un arrondissement. |
| `longitude`, `latitude` | Gares | Coordonnées WGS84, en degrés. Les points proviennent du dictionnaire `position_geographique` de la source SNCF. |
| `coordonnees_valides` | Gares | Vrai si les coordonnées du référentiel se trouvent dans l'emprise rectangulaire métropolitaine configurée ; faux si elles ont été rejetées ; manquant si le référentiel est absent. Ce contrôle n'est pas à lui seul une preuve d'appartenance à un polygone français. |
| `methode_commune` | Gares | `Code INSEE` si le code source appartient aux communes des contours ; sinon `Point dans la commune` si un unique polygone contient le point ; sinon `Non rattachée`. Un point sur une limite peut rester non rattaché. |

Le référentiel SNCF est mis à une ligne par UIC : les listes de codes séparés par `;` sont éclatées, les espaces retirés et l'unicité contrôlée. Une ambiguïté d'UIC provoque un contrôle, pas un choix aléatoire d'emplacement. Le rattachement spatial ne remplace pas un échec par le polygone le plus proche.

## 5. Population, superficie et état civil

Ces colonnes figurent dans `communes.parquet` et dans la table intermédiaire de population nettoyée.

| Colonne | Définition ou formule | Unité / champ source |
|---|---|---|
| `pop_2017`, `pop_2023` | Populations publiées pour les deux dates, dans la géographie de diffusion 2026 | Habitants ; `RP_MEASURE=POP`, `TIME_PERIOD=2017` ou `2023` |
| `superficie_km2` | Superficie publiée au millésime final | km² ; `RP_MEASURE=SUP` |
| `naissances_2017_2022` | Naissances cumulées du 1er janvier 2017 au 31 décembre 2022 | Personnes / événements ; `RP_MEASURE=BRTH`, ligne de période 2023 |
| `deces_2017_2022` | Décès cumulés sur le même intervalle | Personnes / événements ; `RP_MEASURE=DEATH`, ligne de période 2023 |
| `statut_pop_2017`, `statut_pop_2023` | Statut de diffusion INSEE de la population | Code de statut `OBS_STATUS` |
| `alerte_population_2017`, `alerte_population_2023` | Vrai si la population manque ou si son statut n'est pas `A` | Booléen ; aucune alerte sur les populations 2017 ou 2023 dans l'instantané livré |
| `variation_pop` | `pop_2023 − pop_2017`, neutralisée en cas d'alerte sur la population de départ | Habitants ; variation totale en six ans |
| `tcam_pop` | `100 × [(pop_2023 / pop_2017)^(1/6) − 1]`, seulement si `pop_2017 > 0`, et neutralisé en cas d'alerte au départ | % par an |
| `solde_naturel` | `naissances_2017_2022 − deces_2017_2022` | Personnes sur l'intervalle 2017–2023 |
| `solde_migratoire_apparent` | `variation_pop − solde_naturel` | Personnes ; résidu incluant aussi les ajustements de mesure, pas comptage direct des migrations |
| `densite` | `pop_2023 / superficie_km2`, superficie strictement positive | Habitants/km² ; moyenne communale, pas grille officielle urbain/rural |
| `classe_taille` | Classe de population 2023 selon `seuils.bornes_taille_commune` | Catégorie ordonnée : moins de 2 000 ; 2 000 à 9 999 ; 10 000 à 49 999 ; 50 000 et plus |
| `trajectoire` | `Déclin` si TCAM < −0,2 ; `Stable` entre −0,2 et +0,2 inclus ; `Croissance` si TCAM > +0,2 ; manquant si le taux est indéfini | Catégorie ; seuil descriptif, pas test de significativité |

Le filtre `GEO_OBJECT=COM` retient les communes entières ; les valeurs `ARM` sont exclues. Le contrôle réalisé ne détecte **aucun statut K ou W sur les populations 2017 et 2023**. Les difficultés de diffusion décrites ci-dessous concernent les navettes 2017, et ne doivent pas être attribuées à la population.

Pour les soldes régionaux, le graphique agrège d'abord les deux populations et le solde naturel, puis calcule le solde migratoire apparent régional par différence. Les contributions s'expriment en personnes, ou en milliers de personnes après division par 1 000 dans le graphique.

## 6. Actifs occupés et cinq modes harmonisés

Le champ du fichier des navettes est : communes entières, fréquence annuelle, **actifs occupés de 15 ans ou plus**, toutes zones de travail, exploitation principale du recensement. Les filtres exacts sont dans `config.yaml` : `GEO_OBJECT=COM`, `FREQ=A`, `AGE=Y_GE15`, `EMPSTA_ENQ=1`, `WORK_AREA=_T`, `RP_MEASURE=POP`.

Pour chaque année `a ∈ {2017, 2023}`, les colonnes suivantes sont conservées :

| Colonnes | Modalité `TRANS` | Définition et unité |
|---|---|---|
| `actifs_2017`, `actifs_2023` | `_T` | Tous les actifs occupés de 15 ans ou plus résidant dans la commune ; personnes, effectif pondéré possible |
| `actifs_sans_deplacement_a` | `1` | Actifs occupés n'effectuant pas de déplacement domicile-travail |
| `actifs_marche_a` | `2` | Actifs occupés utilisant principalement la marche |
| `actifs_deux_roues_a` | `3` + `4` | Somme des effectifs vélo et deux-roues motorisés, regroupés pour comparer les deux dates |
| `actifs_voiture_a` | `5` | Actifs occupés utilisant principalement la voiture |
| `actifs_transports_commun_a` | `6` | Actifs occupés utilisant principalement les transports collectifs ; cette catégorie n'isole pas le train |
| `statut_navettes_a` | Statut du total `_T` | Code `OBS_STATUS` du total d'actifs de la commune et de l'année |
| `alerte_navettes_a` | Contrôle de tous les modes et du total | Vrai si un statut est différent de `A` ou si un effectif manque |

Le suffixe `a` désigne une famille de deux colonnes réelles, par exemple `actifs_voiture_2017` et `actifs_voiture_2023`. Les cinq modes sont mutuellement exclusifs et leur somme doit retrouver le total publié, à la tolérance numérique indiquée dans la configuration.

**Statuts de diffusion :** `A` désigne une observation normale ; `K` signale une donnée comprise dans une autre observation et non publiée isolément ; `W` signale une observation comprenant des données d'autres unités. On ne ventile pas une valeur W entre communes et on ne remplace pas une valeur K absente par zéro. Dans l'instantané, **12 communes portent une alerte sur les navettes 2017**, avec des effectifs manquants pour huit d'entre elles. Les valeurs W publiées restent stockées, avec leur drapeau ; les parts 2017 des communes signalées sont neutralisées. Le millésime 2023 ne présente pas ces alertes dans les données retenues.

### Parts modales

Pour chaque mode et chaque année :

`part_mode_a = 100 × actifs_mode_a / actifs_a`.

Le dénominateur comprend **tous les actifs occupés**, y compris les actifs sans déplacement. Ce n'est ni la population totale, ni les seuls actifs se déplaçant hors de leur commune, ni les seuls utilisateurs de véhicules.

Les colonnes réelles sont `part_sans_deplacement_2017`, `part_marche_2017`, `part_deux_roues_2017`, `part_voiture_2017`, `part_transports_commun_2017` et leurs équivalents 2023. Leur unité est le **pourcentage des actifs occupés de 15 ans ou plus**.

Une part reste manquante si la commune compte **moins de 1 000 actifs occupés**, si le dénominateur manque ou si le numérateur manque. **1 000 exactement est admissible.** Les communes signalées en 2017 ont leurs parts neutralisées même si l'effectif publié dépasse ce seuil. Ce choix réduit la fragilité de lecture des petites communes ; il ne constitue pas un test statistique.

Les boîtes à moustaches représentent la distribution des parts communales non pondérées. Une part agrégée par classe se calcule au contraire par `100 × somme(actifs_voiture) / somme(actifs)`, sur le même ensemble de communes ayant une part définie. Ces deux résumés répondent à des questions différentes.

## 7. Fréquentation ferroviaire

| Colonne | Tables | Définition et unité |
|---|---|---|
| `annee` | Panel | Année civile entière de 2015 à 2024 |
| `voyageurs` | Panel | Comptages annuels « Total Voyageurs » de l'UIC et de l'année ; entier nullable |
| `voyageurs_2015` à `voyageurs_2024` | Gares | Même donnée annuelle, présentée en colonnes pour chaque UIC |
| `voyageurs_2017`, `voyageurs_2023` | Communes | Sommes sur la **même cohorte d'UIC** : code communal connu, comptage 2017 strictement positif et comptage 2023 renseigné |
| `nb_gares_cohorte` | Communes | Nombre d'UIC distincts de cette cohorte dans la commune ; nombre de gares observées, pas nombre de départs |
| `tcam_voyageurs` | Gares | `100 × [(voyageurs_2023 / voyageurs_2017)^(1/6) − 1]` pour un UIC de base 2017 positive et deux valeurs connues |
| `tcam_voyageurs` | Communes | Même formule appliquée aux **sommes communales de la cohorte**, sans moyenner les taux des gares |
| `taille_gare` | Gares et panel | Classe de comptage **fixée en 2019**, puis répétée sur les années : moins de 100 000 ; 100 000 à 999 999 ; 1 million ou plus |
| `gare_distance` | Gares | Vrai si le comptage 2023 est strictement positif, le code communal est rattaché et le point est disponible |

La colonne source 2017 se nomme `totalvoyageurs2017`, contrairement au motif des autres années `total_voyageurs_aaaa`. Le nettoyage traite explicitement cette exception et vérifie l'unicité UIC × année. Les zéros restent observés ; ils sont inclus dans les distributions, la courbe de Lorenz et le Gini. Ils n'autorisent pas un taux de croissance dont le dénominateur serait nul.

La somme d'un indicateur de fréquentation est appelée **somme de comptages publiés**, pas nombre national de voyages uniques. Une entrée/sortie, une correspondance, le mode de calcul du producteur et les révisions de la source limitent cette interprétation.

Une commune sans cohorte comparable garde `voyageurs_2017`, `voyageurs_2023`, `nb_gares_cohorte` et `tcam_voyageurs` manquants. Cela ne signifie pas nécessairement qu'elle n'a aucune gare ou aucun voyageur. L'indicateur `desservie`, fondé sur les distances, répond à une autre question.

## 8. Distance et profils territoriaux

| Colonne | Définition ou formule | Unité et limites |
|---|---|---|
| `dist_gare_km` | Distance minimale entre le **centroïde géométrique communal calculé en Lambert 93** et un point de gare ayant `gare_distance=True`, puis division de la distance en mètres par 1 000 | km à vol d'oiseau ; ni temps d'accès, ni distance routière, ni distance de chaque habitant |
| `uic_gare_proche` | UIC associé à cette distance minimale | Identifiant ; en cas d'ex æquo, l'UIC le plus petit est retenu, sans modifier la distance |
| `desservie` | `dist_gare_km ≤ 10` | Booléen nullable ; manquant si la distance est inconnue. « Desservie » est un **proxy de proximité**, pas une mesure de fréquence ou de qualité du service |
| `classe_dist_gare` | Classes `≤ 5`, `]5–10]`, `]10–15]`, `> 15` selon les seuils configurés | km ; les seuils sont inclus dans la classe inférieure, distance inconnue → classe manquante |
| `profil` | Croisement de `Croissance` / `Stable ou déclin` avec `desservie` vrai/faux | Quatre catégories. La croissance utilise le seuil démographique +0,2 %/an ; une composante indéfinie laisse le profil manquant |

La Corse reste dans les tables démographiques et les contours métropolitains, mais **les distances, la desserte et les profils d'accès y restent manquants** : les bases SNCF retenues ne couvrent pas le réseau des Chemins de fer de la Corse. On ne calcule pas une proximité artificielle vers une gare continentale à travers la mer.

La part de population « à plus de 10 km » est calculée comme :

`100 × population_2023 des communes dont le centroïde est à plus de 10 km / population_2023 des communes ayant une distance valide`.

La population entière de chaque commune est affectée à la classe de son centroïde. Ce n'est pas une mesure de population géolocalisée dans ou hors d'un tampon de gare. Les tampons 5 et 10 km dessinés sur la carte sont des objets géométriques illustratifs distincts de ce calcul.

## 9. Statuts de jointure et contrôles

| Colonne | Table | Sens |
|---|---|---|
| `jointure_population` | Communes | `both` si le code du contour a une ligne dans la population nettoyée ; `left_only` sinon |
| `jointure_navettes` | Communes | Même indicateur pour les navettes |
| `jointure_uic` | Gares | `both` si l'UIC de fréquentation existe dans le référentiel actuel des gares ; `left_only` sinon |

Une jointure réussie confirme l'existence de la clé ; elle n'efface ni un statut INSEE défavorable, ni une valeur manquante. Le bilan des jointures donne à la fois les proportions d'UIC appariés et la proportion des comptages couverts, année par année. Les deux taux ne sont pas interchangeables.

Les fichiers intermédiaires `source_population`, `source_navettes`, `source_frequentation`, `source_gares` et `source_contours_*` correspondent aux cinq bases nettoyées avant assemblage. Ils reprennent les mêmes variables élémentaires définies ci-dessus. Les tables de travail qui les doublent en CSV ne constituent pas de nouvelles bases.

## 10. Lecture des tableaux statistiques

| Résultat | Calcul et unité |
|---|---|
| Croissance démographique agrégée | `100 × (somme pop_2023 / somme pop_2017 − 1)` ; % sur six ans, distinct d'une moyenne de TCAM |
| Indice ferroviaire base 100 | `100 × somme des comptages de l'année / somme des comptages 2019`, sur les UIC rattachés ; 2019 = 100 |
| Concentration des grandes gares | Part des comptages 2024 portée par les `ceil(0,10 × n)` plus gros UIC rattachés avec valeur 2024 renseignée |
| Gini | Indice compris entre 0 et 1 calculé sur les comptages 2024 non manquants, zéros compris ; pas un pourcentage de voyageurs |
| Quatre quadrants population × rail | Signes négatif / nul ou positif des deux TCAM, sur les communes où les deux taux sont connus ; distincts des quatre profils de proximité |
| Corrélations de Pearson et Spearman | Associations entre taux communaux ; calculées sur la cohorte valide, puis hors Île-de-France pour la sensibilité |
| Heatmap à six variables | Corrélations de Spearman calculées par paires avec leur effectif propre ; les échantillons peuvent différer d'une cellule à l'autre |

Les taux annuels écrêtés à ±10 % pour l'affichage du nuage restent inchangés dans les tables et statistiques. Les extrêmes masqués des boîtes à moustaches restent dans le calcul des quartiles. Les résultats sont descriptifs : ni un écart de croissance, ni une corrélation ne suffit à identifier un effet causal du rail sur la population ou sur l'usage de la voiture.
