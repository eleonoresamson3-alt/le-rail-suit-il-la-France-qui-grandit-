"""Étape 4 : statistiques descriptives et ACP (notebook 05_analyse_mobilites).

Lit la table data/clean/base_finale/base_finale_communes_variables.parquet.
Les fonctions analyse_ (fin du fichier) font le calcul de chaque cellule du notebook ;
elles s'appuient sur les fonctions d'indices et d'ACP du début du fichier.
"""

from IPython.display import display
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


# ---------- 05_analyse_mobilites : 5.1 Données et contrôles ----------

def arrondir_tableau(tableau, decimales=2, lignes=None):
    """Arrondit les mesures et garde les comptes entiers lisibles."""
    resultat = tableau.head(lignes).copy() if lignes is not None else tableau.copy()
    colonnes_numeriques = resultat.select_dtypes(include="number").columns

    for colonne in colonnes_numeriques:
        valeurs = resultat[colonne].dropna().astype(float)
        if valeurs.empty:
            continue
        arrondies = valeurs.round(decimales)
        if np.allclose(arrondies, np.round(arrondies), atol=1e-9):
            resultat[colonne] = resultat[colonne].round().astype("Int64")
        else:
            # Les colonnes mélangées (totaux et taux) gardent des chiffres lisibles.
            resultat[colonne] = resultat[colonne].map(
                lambda valeur: (
                    f"{valeur:,.0f}"
                    if pd.notna(valeur) and np.isclose(valeur, round(valeur))
                    else f"{valeur:,.{decimales}f}" if pd.notna(valeur) else valeur
                )
            )
    return resultat


# ---------- 05_analyse_mobilites : 5.2 Où va la population ? ----------

def synthese_croissance_par(groupe):
    """Résume la croissance annuelle des communes d'un groupe."""
    return groupe.agg(
        communes=("code_commune", "size"),
        population_2023=("pop_2023", "sum"),
        croissance_annuelle_mediane_pct=("croissance_pop_an_%", "median"),
        croissance_annuelle_moyenne_pct=("croissance_pop_an_%", "mean"),
    ).round(2)


# ---------- 05_analyse_mobilites : 5.3 Comment évolue la fréquentation des gares ? ----------

def indice_gini(valeurs):
    """Calcule le Gini d'une série de volumes non négatifs."""
    valeurs = np.sort(pd.Series(valeurs).dropna().to_numpy(dtype=float))
    if valeurs.size == 0 or np.any(valeurs < 0) or valeurs.sum() == 0:
        return np.nan
    rangs = np.arange(1, valeurs.size + 1)
    return float(
        2 * np.sum(rangs * valeurs) / (valeurs.size * valeurs.sum())
        - (valeurs.size + 1) / valeurs.size
    )


# ---------- 05_analyse_mobilites : 5.5 Qui dépend de la voiture, et qui vit loin d'une gare ? ----------

def resume_part_voiture(groupe):
    """Résume les parts voiture communales et leur évolution."""
    return groupe.agg(
        communes=("code_commune", "size"),
        mediane_2017_pct=("part_voiture_2017", "median"),
        Q1_2017_pct=("part_voiture_2017", lambda valeurs: valeurs.quantile(0.25)),
        Q3_2017_pct=("part_voiture_2017", lambda valeurs: valeurs.quantile(0.75)),
        mediane_2023_pct=("part_voiture_2023", "median"),
        Q1_2023_pct=("part_voiture_2023", lambda valeurs: valeurs.quantile(0.25)),
        Q3_2023_pct=("part_voiture_2023", lambda valeurs: valeurs.quantile(0.75)),
        evolution_mediane_pp=("evolution_part_voiture_pp", "median"),
    ).round(2)


# ---------- 05_analyse_mobilites : 5.6 Enrichissements statistiques descriptifs ----------

def contribution_demographique(frame, hausse_nationale):
    """Calcule la contribution positive d'une strate à la hausse nationale."""
    hausse_strate = frame["variation_population"].clip(lower=0).sum()
    population_2017 = frame["pop_2017"].sum()
    population_2023 = frame["pop_2023"].sum()
    return pd.Series(
        {
            "communes": len(frame),
            "population_2023": population_2023,
            "hausse_contribuee": hausse_strate,
            "part_croissance_nationale_%": (
                100 * hausse_strate / hausse_nationale if hausse_nationale else np.nan
            ),
            "variation_agregee_pct": (
                100 * (population_2023 / population_2017 - 1)
                if population_2017
                else np.nan
            ),
        }
    )


def resume_par_strate(groupe, hausse_nationale):
    """Applique la contribution démographique à chaque strate."""
    return pd.DataFrame(
        {
            str(cle): contribution_demographique(sous_groupe, hausse_nationale)
            for cle, sous_groupe in groupe
        }
    ).T


def indice_hoover(frame, annee):
    """Compare la répartition de la population à celle de la superficie."""
    surface = frame["superficie_km2"].fillna(0).clip(lower=0)
    population = frame[f"pop_{annee}"].fillna(0).clip(lower=0)
    part_surface = surface / surface.sum()
    part_population = population / population.sum()
    return float(0.5 * (part_population - part_surface).abs().sum())


def indice_theil(frame, annee):
    """Mesure l'inégalité de répartition de la population entre communes."""
    population = frame[f"pop_{annee}"].to_numpy(dtype=float)
    population = population[population > 0]
    if population.size == 0:
        return np.nan
    parts = population / population.sum()
    return float(np.sum(parts * np.log(parts * len(parts))))


def intensite_ternaire(serie):
    """Classe un solde en valeur nulle, faible ou forte selon sa médiane."""
    result = pd.Series("nul", index=serie.index, dtype="object")
    positifs = serie > 0
    negatifs = serie < 0

    if positifs.any():
        seuil_positif = serie.loc[positifs].median()
        result.loc[positifs & (serie <= seuil_positif)] = "faible"
        result.loc[positifs & (serie > seuil_positif)] = "fort"

    if negatifs.any():
        seuil_negatif = (-serie.loc[negatifs]).median()
        result.loc[negatifs & (-serie <= seuil_negatif)] = "faible"
        result.loc[negatifs & (-serie > seuil_negatif)] = "fort"
    return result


# ---------- 05_analyse_mobilites : 5.7 ACP : comment la lire ----------

def calculer_acp(tableau):
    """Calcule l'ACP sur un tableau de variables quantitatives."""
    donnees = tableau.replace([np.inf, -np.inf], np.nan).dropna().astype(float)
    if donnees.empty:
        raise ValueError("Aucune ligne complète disponible pour calculer l'ACP.")

    ecarts_types = donnees.std(ddof=0)
    constantes = ecarts_types[ecarts_types.eq(0)].index.tolist()
    if constantes:
        raise ValueError(f"Variables constantes, à retirer de l'ACP : {constantes}")

    standardise = (donnees - donnees.mean()) / ecarts_types
    covariance = standardise.T @ standardise / len(standardise)
    valeurs_propres, vecteurs_propres = np.linalg.eigh(covariance)
    ordre = np.argsort(valeurs_propres)[::-1]
    valeurs_propres = valeurs_propres[ordre]
    vecteurs_propres = vecteurs_propres[:, ordre]

    noms_axes = [f"PC{i + 1}" for i in range(len(valeurs_propres))]
    scores = pd.DataFrame(
        standardise.to_numpy() @ vecteurs_propres,
        index=donnees.index,
        columns=noms_axes,
    )
    variance = valeurs_propres / valeurs_propres.sum()
    correlations = pd.DataFrame(index=donnees.columns)
    for axe in noms_axes:
        correlations[axe] = standardise.corrwith(scores[axe])

    contributions = pd.DataFrame(index=donnees.index)
    for i, axe in enumerate(noms_axes):
        contributions[axe] = (
            100 * scores[axe].pow(2) / (len(scores) * valeurs_propres[i])
        )

    resume_axes = pd.DataFrame(
        {
            "Axe": noms_axes,
            "Valeur propre": valeurs_propres,
            "Variance expliquée (%)": 100 * variance,
            "Variance cumulée (%)": 100 * np.cumsum(variance),
        }
    )
    return {
        "donnees": donnees,
        "standardise": standardise,
        "valeurs_propres": valeurs_propres,
        "scores": scores,
        "correlations": correlations,
        "contributions": contributions,
        "resume_axes": resume_axes,
    }


def tracer_acp(resultats, titre, couleur="#4C78A8", taille_nuage=6000):
    """Trace l'éboulis, le plan factoriel et le cercle sans superposer les noms."""
    scores = resultats["scores"]
    correlations = resultats["correlations"]
    resume_axes = resultats["resume_axes"]
    variance = resume_axes["Variance expliquée (%)"].to_numpy()

    fig_eboulis, ax = plt.subplots(figsize=(8, 4.5))
    axes_visibles = min(10, len(variance))
    x_axes = np.arange(1, axes_visibles + 1)
    ax.bar(x_axes, variance[:axes_visibles], color=couleur, alpha=0.8)
    ax.set_xticks(x_axes, [f"PC{i}" for i in x_axes])
    ax.set_ylabel("Variance expliquée (%)")
    ax.set_title(f"{titre} — part expliquée par axe")
    ax.grid(axis="y", alpha=0.25)
    ax_cumul = ax.twinx()
    ax_cumul.plot(
        x_axes,
        np.cumsum(variance[:axes_visibles]),
        color="#E15759",
        marker="o",
        linewidth=2,
    )
    ax_cumul.set_ylabel("Variance cumulée (%)", color="#B33B3D")
    ax_cumul.set_ylim(0, 105)
    fig_eboulis.tight_layout()

    # L'hexbin montre la densité des communes, sans produire un nuage illisible.
    points = scores[["PC1", "PC2"]]
    if len(points) > taille_nuage:
        points = points.sample(taille_nuage, random_state=42)
    fig_plan, ax = plt.subplots(figsize=(7, 6))
    nuage = ax.hexbin(
        points["PC1"],
        points["PC2"],
        gridsize=55,
        mincnt=1,
        bins="log",
        cmap="Blues",
    )
    fig_plan.colorbar(nuage, ax=ax, label="Nombre de communes (échelle logarithmique)")
    ax.axhline(0, color="grey", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.7)
    ax.set_xlabel(f"PC1 ({variance[0]:.1f} %)")
    ax.set_ylabel(f"PC2 ({variance[1]:.1f} %)")
    ax.set_title(f"{titre} — profils communaux")
    fig_plan.tight_layout()

    # Les flèches restent sans texte ; la légende numérotée évite le chevauchement.
    fig_cercle, ax = plt.subplots(figsize=(9, 7))
    ax.add_patch(plt.Circle((0, 0), 1, fill=False, color="grey", linestyle="--"))
    ax.axhline(0, color="grey", linewidth=0.7)
    ax.axvline(0, color="grey", linewidth=0.7)
    palette = plt.get_cmap("tab10")
    legendes = []

    for numero, variable in enumerate(correlations.index, start=1):
        x = correlations.loc[variable, "PC1"]
        y = correlations.loc[variable, "PC2"]
        couleur_variable = palette((numero - 1) % 10)
        ax.annotate(
            "",
            xy=(x, y),
            xytext=(0, 0),
            arrowprops={
                "arrowstyle": "->",
                "color": couleur_variable,
                "linewidth": 1.7,
                "shrinkA": 0,
                "shrinkB": 0,
            },
        )
        ax.scatter([x], [y], color=[couleur_variable], s=28, zorder=3)

        # Numérotation avec léger décalage radial, sans noms longs sur les flèches.
        longueur = math.hypot(x, y)
        if longueur:
            ax.annotate(
                str(numero),
                (x, y),
                xytext=(4 * x / longueur, 4 * y / longueur),
                textcoords="offset points",
                fontsize=8,
                color=couleur_variable,
                weight="bold",
            )
        legendes.append(
            Line2D(
                [0],
                [0],
                color=couleur_variable,
                marker="o",
                linewidth=1.5,
                label=f"{numero}. {variable}",
            )
        )

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(f"Corrélation avec PC1 ({variance[0]:.1f} %)")
    ax.set_ylabel(f"Corrélation avec PC2 ({variance[1]:.1f} %)")
    ax.set_title(f"{titre} — cercle des corrélations")
    ax.grid(alpha=0.2)
    ax.legend(
        handles=legendes,
        title="Variables (numéro au bout de chaque flèche)",
        loc="center left",
        bbox_to_anchor=(1.03, 0.5),
        frameon=False,
        fontsize=8,
    )
    fig_cercle.tight_layout(rect=(0, 0, 0.68, 1))

    return fig_eboulis, fig_plan, fig_cercle


# ---------- 05_analyse_mobilites : une fonction par cellule de calcul ----------

# 5.1 aperçu de la base et valeurs manquantes
def analyse_apercu_base(FICHIER, communes):
    print(f"Base : {FICHIER.name}")
    print(f"{len(communes):,} communes, {len(communes.columns)} variables")
    display(arrondir_tableau(communes.head(5), decimales=2))

    description_colonnes = pd.DataFrame({
        "type": communes.dtypes.astype(str),
        "valeurs non manquantes": communes.notna().sum(),
        "valeurs manquantes": communes.isna().sum(),
        "part manquante (%)": (100 * communes.isna().mean()).round(2),
    })
    display(arrondir_tableau(description_colonnes, decimales=2))


# 5.1 description des variables et bilan des rattachements
def analyse_description_base(communes):
    # Étape 1 — exclure les identifiants textuels et la géométrie des tableaux numériques.
    variables_numeriques = communes.select_dtypes(include='number').columns
    synthese_variables = communes[variables_numeriques].describe(
        percentiles=[0.25, 0.50, 0.75]
    ).T.rename(columns={
        'mean': 'moyenne', 'std': 'écart-type', 'min': 'minimum',
        '25%': 'Q1', '50%': 'médiane', '75%': 'Q3', 'max': 'maximum',
    })[['moyenne', 'médiane', 'écart-type', 'minimum', 'maximum', 'Q1', 'Q3']]
    display(arrondir_tableau(synthese_variables))

    # Le nombre de gares permet de calculer la desserte visible, mais pas la catégorie A/B/C.
    # Étape 2 — définir les exclusions visibles uniquement à partir des variables présentes.
    communes_avec_gare = communes['nb_gares'].gt(0)
    voyageurs_renseignes_2023 = communes['voyageurs_2023'].notna()
    bilan_visible = pd.DataFrame({
        'indicateur': [
            'Communes ayant au moins une gare',
            'Communes avec voyageurs renseignés en 2017',
            'Communes avec voyageurs renseignés en 2023',
            'Population 2023 dans les communes avec voyageurs renseignés',
            'Communes sans gare (aucune correspondance visible dans le parquet)',
            'Communes sous le seuil de 1 000 actifs en 2017 ou actifs manquants',
            'Gares à zéro voyageur en 2017 (communes desservies)',
            'Gares à zéro voyageur en 2023 (communes desservies)',
        ],
        'valeur': [
            int(communes_avec_gare.sum()),
            int(communes['voyageurs_2017'].notna().sum()),
            int(voyageurs_renseignes_2023.sum()),
            int(communes.loc[voyageurs_renseignes_2023, 'pop_2023'].sum()),
            int((~communes_avec_gare).sum()),
            int((communes['actifs_2017'].isna() | communes['actifs_2017'].lt(1000)).sum()),
            int((communes_avec_gare & communes['voyageurs_2017'].eq(0)).sum()),
            int((communes_avec_gare & communes['voyageurs_2023'].eq(0)).sum()),
        ],
    })
    display(bilan_visible)
    print('La part des voyageurs couverte par la jointure initiale et le bilan A/B/C ne figurent pas dans cette base.')

    # Le chiffre publié par l'INSEE n'est pas une variable de la base mais on considére celle recalculée
    population_insee_publiee_2023 = None
    population_recalculee = communes['pop_2023'].sum()
    print(f'Population 2017 recalculée : {communes["pop_2017"].sum():,.0f}')
    print(f'Population 2023 recalculée : {population_recalculee:,.0f}')
    if population_insee_publiee_2023 is None:
        print('Comparaison INSEE non chiffrée : la référence publiée doit être fournie pour éviter une valeur non vérifiée.')
    else:
        print(f'Écart au chiffre INSEE fourni : {population_recalculee - population_insee_publiee_2023:,.0f} habitants')
    print('La variable statut_pop indique la qualité des populations communales ; elle ne décrit pas une catégorie de gare.')


# 5.2 indicateurs démographiques et trajectoires
def analyse_population(communes):
    d = communes.copy()
    # Étape 1 — créer les variations absolues en habitants.
    d['variation_population'] = d['pop_2023'] - d['pop_2017']
    # Étape 2 — transformer l'écart 2017–2023 en taux annuel composé.
    d['croissance_pop_an_%'] = np.where(
        d['pop_2017'].gt(0) & d['pop_2023'].ge(0),
        ((d['pop_2023'] / d['pop_2017']) ** (1 / 6) - 1) * 100,
        np.nan,
    )
    # Étape 3 — classer chaque commune selon trois seuils explicités.
    d['trajectoire_population'] = pd.cut(
        d['croissance_pop_an_%'],
        bins=[-np.inf, -0.2, 0.2, np.inf],
        labels=['Déclin', 'Stable (±0,2 %/an)', 'Croissance'],
        right=True,
    ).astype('object')

    population_totaux = pd.DataFrame([
        {'année': '2017', 'population': d['pop_2017'].sum()},
        {'année': '2023', 'population': d['pop_2023'].sum()},
        {'année': 'Croissance agrégée (%)',
         'population': 100 * (d['pop_2023'].sum() / d['pop_2017'].sum() - 1)},
    ])
    display(arrondir_tableau(population_totaux))

    distribution_croissance = d['croissance_pop_an_%'].describe(percentiles=[0.05, 0.25, 0.75, 0.95])
    display(arrondir_tableau(distribution_croissance.rename({
        'mean': 'moyenne', 'std': 'écart-type', 'min': 'minimum', '5%': 'P5',
        '25%': 'P25', '50%': 'médiane', '75%': 'P75', '95%': 'P95', 'max': 'maximum',
    }).to_frame('croissance annuelle moyenne (%)')))

    # Étape 4 — agréger le nombre de communes, la population et le gain ou la perte.
    groupes_population = d.groupby('trajectoire_population', observed=False).agg(
        communes=('code_commune', 'size'),
        part_communes_pct=('code_commune', lambda s: 100 * len(s) / len(d)),
        population_2017=('pop_2017', 'sum'),
        population_2023=('pop_2023', 'sum'),
        variation_population=('variation_population', 'sum'),
    ).round(2)
    display(groupes_population)
    return d


# 5.2 croissance par région, taille et densité
def analyse_regions_classes(d):
    # Étape 1 — convertir les codes régionaux en libellés lisibles.
    noms_regions = {
        '11': 'Île-de-France', '24': 'Centre-Val de Loire', '27': 'Bourgogne-Franche-Comté',
        '28': 'Normandie', '32': 'Hauts-de-France', '44': 'Grand Est',
        '52': 'Pays de la Loire', '53': 'Bretagne', '75': 'Nouvelle-Aquitaine',
        '76': 'Occitanie', '84': 'Auvergne-Rhône-Alpes',
        '93': 'Provence-Alpes-Côte d’Azur', '94': 'Corse',
    }
    d['region'] = d['code_region'].astype(str).map(noms_regions).fillna(d['code_region'].astype(str))
    regions = d.groupby('region').agg(
        population_2017=('pop_2017', 'sum'),
        population_2023=('pop_2023', 'sum'),
        naissances_2017_2022=('naissances_2017_2022', 'sum'),
        deces_2017_2022=('deces_2017_2022', 'sum'),
    ).reset_index()
    regions['variation_population'] = regions['population_2023'] - regions['population_2017']
    regions['solde_naturel_2017_2022'] = regions['naissances_2017_2022'] - regions['deces_2017_2022']
    # Étape 2 — obtenir un résidu apparent entre la variation totale et le solde naturel.
    regions['solde_migratoire_apparent'] = regions['variation_population'] - regions['solde_naturel_2017_2022']
    regions['croissance_population_%'] = 100 * regions['variation_population'] / regions['population_2017']
    display(regions.sort_values('croissance_population_%', ascending=False).round(1))
    print('Le solde migratoire apparent est le résidu entre variation 2017–2023 et solde naturel fourni pour 2017–2022 ; les périodes ne coïncident pas exactement.')

    # Classes lisibles et stables : taille selon la population 2023, densité selon population/superficie.
    # Étape 3 — construire des strates de taille fixes et reproductibles.
    d['classe_taille'] = pd.cut(
        d['pop_2023'], bins=[0, 2000, 10000, 50000, np.inf],
        labels=['Moins de 2 000', '2 000–9 999', '10 000–49 999', '50 000 et plus'],
        right=False,
    )
    d['densite_2023'] = d['pop_2023'] / d['superficie_km2'].replace(0, np.nan)
    # Étape 4 — calculer la densité avant de créer les classes.
    d['classe_densite'] = pd.cut(
        d['densite_2023'], bins=[-np.inf, 30, 100, 300, np.inf],
        labels=['Moins de 30', '30–99', '100–299', '300 et plus'], right=False,
    )

    print('Croissance selon la taille de commune (classes établies sur 2023)')
    display(synthese_croissance_par(d.groupby('classe_taille', observed=False)))
    print('Croissance selon la densité de population 2023 (habitant/km²)')
    display(synthese_croissance_par(d.groupby('classe_densite', observed=False)))

    grandes_communes = d[d['pop_2023'].gt(10000)]
    colonnes_top = ['code_commune', 'nom_commune', 'region', 'pop_2017', 'pop_2023', 'variation_population']
    print('5 communes de plus de 10 000 habitants qui gagnent le plus d’habitants')
    display(arrondir_tableau(grandes_communes.nlargest(5, 'variation_population')[colonnes_top]))
    print('5 communes de plus de 10 000 habitants qui perdent le plus d’habitants')
    display(arrondir_tableau(grandes_communes.nsmallest(5, 'variation_population')[colonnes_top]))


# 5.3 fréquentation communale du rail
def analyse_frequentation(d):
    annees_voyageurs = [2017, 2023]
    # Étape 1 — sommer les volumes communaux disponibles pour chaque année.
    totaux_voyageurs = pd.DataFrame({
        'année': annees_voyageurs,
        'voyageurs (somme des communes renseignées)': [d[f'voyageurs_{annee}'].sum() for annee in annees_voyageurs],
        'communes renseignées': [d[f'voyageurs_{annee}'].notna().sum() for annee in annees_voyageurs],
    })
    display(arrondir_tableau(totaux_voyageurs))
    print('Indice base 100 en 2019, choc Covid 2020 et reprise 2024 : non calculables, ces années sont absentes.')

    voyageurs_2023 = d.loc[d['voyageurs_2023'].notna(), 'voyageurs_2023']
    display(arrondir_tableau(voyageurs_2023.describe(percentiles=[0.05, 0.25, 0.5, 0.75, 0.95]).rename({
        'mean': 'moyenne', 'std': 'écart-type', 'min': 'minimum', '5%': 'P5',
        '25%': 'P25', '50%': 'médiane', '75%': 'P75', '95%': 'P95', 'max': 'maximum',
    }).to_frame('voyageurs par commune en 2023')))

    # Étape 2 — définir la concentration à partir des communes, pas des gares.
    volumes = voyageurs_2023
    volumes_tries = volumes.sort_values(ascending=False)
    total_volumes = volumes_tries.sum()
    # Étape 3 — calculer les parts du top 10 %, du top 1 % et le Gini.
    concentration = pd.DataFrame({
        'mesure': ['Part des 10 % de communes les plus fréquentées', 'Part des 1 % de communes les plus fréquentées', 'Indice de Gini entre communes'],
        'valeur': [
            volumes_tries.head(math.ceil(0.10 * len(volumes_tries))).sum() / total_volumes,
            volumes_tries.head(math.ceil(0.01 * len(volumes_tries))).sum() / total_volumes,
            indice_gini(volumes_tries),
        ],
    })
    concentration.loc[0:1, 'valeur'] *= 100
    concentration['unité'] = ['%', '%', 'indice (0–1)']
    display(arrondir_tableau(concentration, decimales=3))

    # Étape 4 — mesurer la variation relative communale sur six ans.
    d['evolution_voyageurs_2017_2023_%'] = np.where(
        d['voyageurs_2017'].gt(0) & d['voyageurs_2023'].notna(),
        100 * (d['voyageurs_2023'] / d['voyageurs_2017'] - 1), np.nan,
    )
    d['croissance_voyageurs_an_%'] = np.where(
        d['voyageurs_2017'].gt(0) & d['voyageurs_2023'].ge(0),
        ((d['voyageurs_2023'] / d['voyageurs_2017']) ** (1 / 6) - 1) * 100, np.nan,
    )
    top_communes_rail = d[d['voyageurs_2023'].notna()].nlargest(5, 'voyageurs_2023')
    display(arrondir_tableau(top_communes_rail[[
        'code_commune', 'nom_commune', 'region', 'nb_gares', 'voyageurs_2017',
        'voyageurs_2023', 'evolution_voyageurs_2017_2023_%',
    ]]))

    rail_regions = d.groupby('region').agg(
        voyageurs_2017=('voyageurs_2017', 'sum'), voyageurs_2023=('voyageurs_2023', 'sum')
    )
    rail_regions['evolution_2017_2023_%'] = 100 * (rail_regions['voyageurs_2023'] / rail_regions['voyageurs_2017'] - 1)
    display(rail_regions.sort_values('voyageurs_2023', ascending=False).round(1))
    print('Série annuelle 2015–2024, top 20 des gares, catégories A/B/C et évolution par catégorie : non disponibles dans communes.parquet.')


# 5.4 trajectoires rail et population, quadrants, profils
def analyse_rail_population(d):
    # Étape 1 — conserver uniquement les observations positives aux deux dimensions.
    comparables = d[d['voyageurs_2017'].notna() & d['voyageurs_2023'].notna()].copy()
    comparables = comparables[comparables['pop_2017'].gt(0) & comparables['voyageurs_2017'].gt(0)]
    comparables['croissance_voyageurs_an_%'] = (
        (comparables['voyageurs_2023'] / comparables['voyageurs_2017']) ** (1 / 6) - 1
    ) * 100
    comparables['croissance_pop_an_%'] = (
        (comparables['pop_2023'] / comparables['pop_2017']) ** (1 / 6) - 1
    ) * 100
    part_population_couverte = comparables['pop_2023'].sum() / d['pop_2023'].sum()
    print(f'Communes comparables : {len(comparables):,}')
    print(f'Part de la population 2023 représentée : {part_population_couverte:.1%}')
    display(comparables[['croissance_pop_an_%', 'croissance_voyageurs_an_%']].agg(['mean', 'median']).T.rename(
        index={'croissance_pop_an_%': 'Population', 'croissance_voyageurs_an_%': 'Voyageurs'},
        columns={'mean': 'moyenne (%)', 'median': 'médiane (%)'},
    ).round(2))

    # Hausse/baisse signifie ici strictement supérieur/inférieur à zéro, comme dans la définition des quadrants.
    # Étape 2 — croiser les signes des taux de croissance.
    comparables['quadrant'] = np.select(
        [
            comparables['croissance_pop_an_%'].le(0) & comparables['croissance_voyageurs_an_%'].le(0),
            comparables['croissance_pop_an_%'].le(0) & comparables['croissance_voyageurs_an_%'].gt(0),
            comparables['croissance_pop_an_%'].gt(0) & comparables['croissance_voyageurs_an_%'].le(0),
        ],
        ['Population ↓ / voyageurs ↓', 'Population ↓ / voyageurs ↑', 'Population ↑ / voyageurs ↓'],
        default='Population ↑ / voyageurs ↑',
    )
    quadrants = comparables.groupby('quadrant').agg(
        communes=('code_commune', 'size'), population_2023=('pop_2023', 'sum')
    )
    quadrants['part_communes_%'] = 100 * quadrants['communes'] / len(comparables)
    quadrants['part_population_%'] = 100 * quadrants['population_2023'] / comparables['pop_2023'].sum()
    display(quadrants.round(2))

    # Étape 3 — calculer une association linéaire (Pearson) et une association de rang (Spearman).
    correlations = comparables[['croissance_pop_an_%', 'croissance_voyageurs_an_%']].corr(method='pearson').iloc[0, 1], comparables[['croissance_pop_an_%', 'croissance_voyageurs_an_%']].corr(method='spearman').iloc[0, 1]
    print(f'Pearson : {correlations[0]:.3f} ; Spearman : {correlations[1]:.3f}')

    # Les deux exclusions ferroviaires sont des proxys communaux, pas des exclusions de gares individuelles.
    top_un_pct = max(1, math.ceil(0.01 * len(comparables)))
    sans_top_communes = comparables.drop(comparables.nlargest(top_un_pct, 'voyageurs_2017').index)
    # Étape 4 — répéter les corrélations dans des échantillons plus ciblés.
    scenarios = {
        'Champ comparable': comparables,
        'Sans Île-de-France (code 11)': comparables[comparables['code_region'].astype(str).ne('11')],
        'Sans le 1 % de communes les plus fréquentées en 2017': sans_top_communes,
        'Sans les communes sous 10 000 voyageurs en 2017': comparables[comparables['voyageurs_2017'].ge(10000)],
    }
    robustesse = []
    for nom, echantillon in scenarios.items():
        paire = echantillon[['croissance_pop_an_%', 'croissance_voyageurs_an_%']].dropna()
        robustesse.append({
            'scénario': nom,
            'communes': len(paire),
            'Pearson': paire.corr(method='pearson').iloc[0, 1] if len(paire) > 1 else np.nan,
            'Spearman': paire.corr(method='spearman').iloc[0, 1] if len(paire) > 1 else np.nan,
        })
    display(pd.DataFrame(robustesse).set_index('scénario').round(3))
    print('Le seuil de 10 000 voyageurs et le top 1 % s’appliquent aux agrégats communaux, faute de valeurs par gare.')

    mediane_voyageurs_par_trajectoire = comparables.groupby('trajectoire_population', observed=False).agg(
        communes=('code_commune', 'size'),
        croissance_mediane_voyageurs_an_pct=('croissance_voyageurs_an_%', 'median'),
    ).round(2)
    display(mediane_voyageurs_par_trajectoire)

    d['gare_a_10_km_ou_moins'] = d['dist_gare_km'].le(10)
    d['population_en_croissance'] = d['croissance_pop_an_%'].gt(0)
    d['profil_commune'] = np.select(
        [d['population_en_croissance'] & d['gare_a_10_km_ou_moins'],
         d['population_en_croissance'] & ~d['gare_a_10_km_ou_moins'],
         ~d['population_en_croissance'] & d['gare_a_10_km_ou_moins']],
        ['Croissance / gare ≤ 10 km', 'Croissance / gare > 10 km ou inconnue', 'Pas de croissance / gare ≤ 10 km'],
        default='Pas de croissance / gare > 10 km ou inconnue',
    )
    profils = d.groupby('profil_commune').agg(
        communes=('code_commune', 'size'), habitants_2023=('pop_2023', 'sum')
    )
    profils['part_communes_%'] = 100 * profils['communes'] / len(d)
    profils['part_population_%'] = 100 * profils['habitants_2023'] / d['pop_2023'].sum()
    display(profils.round(2))
    return comparables


# 5.5 modes de déplacement, taille et distance à la gare
def analyse_voiture(d):
    modes = {
        2017: [
            'actifs_sans_deplacement_2017',
            'actifs_marche_2017',
            'actifs_deux_roues_2017',
            'actifs_voiture_2017',
            'actifs_transports_commun_2017',
        ],
        2023: [
            'actifs_sans_deplacement_2023',
            'actifs_marche_2023',
            'actifs_deux_roues_2023',
            'actifs_voiture_2023',
            'actifs_transports_commun_2023',
        ],
    }
    noms_modes = ['Sans déplacement', 'Marche', 'Deux-roues', 'Voiture', 'Transports en commun']
    parts_modes = {}

    for annee, colonnes in modes.items():
        # Étape 1 — sélectionner les cinq postes du même millésime et retirer les lignes incomplètes.
        valeurs = d[colonnes].dropna()
        # Étape 2 — pondérer chaque part modale par l'effectif observé de toutes les communes complètes.
        totaux = valeurs.sum()
        parts_modes[annee] = 100 * totaux / totaux.sum()
        print(f'Effectif total classé par mode en {annee} : {totaux.sum():,.0f}')

    table_modes = pd.DataFrame({
        2017: parts_modes[2017].to_numpy(),
        2023: parts_modes[2023].to_numpy(),
    }, index=noms_modes)
    table_modes.index.name = 'mode de transport'
    display(arrondir_tableau(table_modes.rename_axis(columns='année')))
    print(f'Part voiture nationale 2017 : {table_modes.loc["Voiture", 2017]:.2f} %')
    print(f'Part voiture nationale 2023 : {table_modes.loc["Voiture", 2023]:.2f} %')

    for annee in [2017, 2023]:
        # Étape 3 — ramener les actifs voiture au nombre total d'actifs de leur propre commune.
        d[f'part_voiture_{annee}'] = (
            100 * d[f'actifs_voiture_{annee}']
            / d[f'actifs_{annee}'].replace(0, np.nan)
        )
    d['evolution_part_voiture_pp'] = d['part_voiture_2023'] - d['part_voiture_2017']

    print('Part voiture et évolution par classe de taille')
    display(resume_part_voiture(d.groupby('classe_taille', observed=False)))
    print('Part voiture par classe de densité')
    display(resume_part_voiture(d.groupby('classe_densite', observed=False)))
    print('Part voiture par trajectoire démographique')
    display(resume_part_voiture(d.groupby('trajectoire_population', observed=False)))
    print('Part voiture par profil de commune')
    display(resume_part_voiture(d.groupby('profil_commune', observed=False)))

    # Étape 5 — transformer la distance continue en classes lisibles et cumulables.
    d['tranche_distance_gare'] = pd.cut(
        d['dist_gare_km'],
        bins=[-np.inf, 5, 10, 15, np.inf],
        labels=['≤ 5 km', '> 5 à 10 km', '> 10 à 15 km', '> 15 km'],
        right=True,
    )
    distance_voiture = d.groupby('tranche_distance_gare', observed=False).agg(
        communes=('code_commune', 'size'),
        part_voiture_mediane_2017_pct=('part_voiture_2017', 'median'),
        part_voiture_mediane_2023_pct=('part_voiture_2023', 'median'),
    ).round(2)
    display(arrondir_tableau(distance_voiture))

    display(d['dist_gare_km'].describe(percentiles=[0.25, 0.5, 0.75]).rename({
        'mean': 'moyenne',
        'std': 'écart-type',
        'min': 'minimum',
        '25%': 'Q1',
        '50%': 'médiane',
        '75%': 'Q3',
        'max': 'maximum',
    }).to_frame('distance à la gare la plus proche (km)'))

    # Étape 6 — cumuler la population concernée au-delà de plusieurs seuils.
    seuils_distance = []
    for seuil in [5, 10, 15]:
        eloignees = d['dist_gare_km'].gt(seuil)
        seuils_distance.append({
            'seuil': f'> {seuil} km',
            'communes': int(eloignees.sum()),
            'part_communes_%': 100 * eloignees.mean(),
            'population_2023': d.loc[eloignees, 'pop_2023'].sum(),
            'part_population_%': 100 * d.loc[eloignees, 'pop_2023'].sum() / d['pop_2023'].sum(),
        })
    display(pd.DataFrame(seuils_distance).set_index('seuil').round(2))

    # Étape 7 — isoler les gains démographiques positifs avant la matrice finale.
    croissance_positive = d['variation_population'].clip(lower=0)
    hausse_loin = croissance_positive[d['dist_gare_km'].gt(10)].sum()
    hausse_totale = croissance_positive.sum()
    print(f'Part de la somme des hausses communales au-delà de 10 km : {hausse_loin / hausse_totale:.1%}')

    # Étape 8 — calculer les rangs de corrélation uniquement là où les deux variables existent.
    variables_heatmap = [
        'croissance_pop_an_%',
        'croissance_voyageurs_an_%',
        'part_voiture_2023',
        'densite_2023',
        'dist_gare_km',
        'pop_2023',
    ]
    heatmap_donnees = d[variables_heatmap]
    correlations_spearman = heatmap_donnees.corr(method='spearman')
    effectifs_par_paire = heatmap_donnees.notna().astype(int).T.dot(heatmap_donnees.notna().astype(int))
    display(correlations_spearman.round(3).rename_axis('variable').rename_axis('variable', axis=1))
    display(effectifs_par_paire.rename_axis('variable').rename_axis('variable', axis=1))
    print('La part voiture évolue en points de pourcentage ; les tableaux par taille donnent sa médiane par année.')


# 5.6.1 poids démographique et géographique des exclusions
def analyse_exclusions(communes, d):
    # Comparaison pondérée des principales exclusions disponibles.
    # Étape 1 — définir les exclusions sans modifier les données sources.
    sans_1000_actifs = communes['actifs_2017'].isna() | communes['actifs_2017'].lt(1000)
    sans_gare_visible = communes['nb_gares'].fillna(0).eq(0)
    # Étape 2 — prendre la population totale comme dénominateur des parts.
    population_totale = communes['pop_2023'].sum()
    superficie_totale = communes['superficie_km2'].sum()

    # Étape 3 — agréger communes, habitants et surface pour chaque règle.
    poids_exclusions = []
    for nom, masque in [
        ('Moins de 1 000 actifs en 2017 ou actif manquant', sans_1000_actifs),
        ('Aucune gare dans la correspondance visible', sans_gare_visible),
    ]:
        poids_exclusions.append({
            'exclusion': nom,
            'communes': int(masque.sum()),
            'population_2023': communes.loc[masque, 'pop_2023'].sum(),
            'part_population_%': 100 * communes.loc[masque, 'pop_2023'].sum() / population_totale,
            'superficie_km2': communes.loc[masque, 'superficie_km2'].sum(),
            'part_superficie_%': 100 * communes.loc[masque, 'superficie_km2'].sum() / superficie_totale,
        })
    display(pd.DataFrame(poids_exclusions).round(2))

    # Les deux dates disponibles permettent seulement une typologie historique limitée.
    zero_2017 = d[d['nb_gares'].gt(0) & d['voyageurs_2017'].eq(0)]
    zero_2023 = d[d['nb_gares'].gt(0) & d['voyageurs_2023'].eq(0)]
    zero_aux_deux_dates = d[d['nb_gares'].gt(0) & d['voyageurs_2017'].eq(0) & d['voyageurs_2023'].eq(0)]
    print(f'Zéro voyageur en 2017 : {len(zero_2017)} communes-agrégats')
    print(f'Zéro voyageur en 2023 : {len(zero_2023)} communes-agrégats')
    print(f'Zéro aux deux dates : {len(zero_aux_deux_dates)} communes-agrégats')
    print('Conclusion limitée : fermeture structurelle, fermeture temporaire, travaux, ouverture récente et statut individuel des gares ne sont pas observables.')


# 5.6.2 contribution démographique et concentration spatiale
def analyse_contributions(d):
    # Contribution positive totale par strate démographique.
    # Étape 1 — sommer les seules variations positives pour mesurer la croissance nationale.
    hausse_nationale = d['variation_population'].clip(lower=0).sum()

    # Étape 2 — calculer la part qu'une strate contribue à cette croissance.
    print('Contribution positive par classe de taille')
    display(resume_par_strate(d.groupby('classe_taille', observed=False), hausse_nationale).round(2))
    print('Contribution positive par classe de densité')
    display(resume_par_strate(d.groupby('classe_densite', observed=False), hausse_nationale).round(2))
    print('Contribution positive par région')
    display(resume_par_strate(d.groupby('region'), hausse_nationale).sort_values('part_croissance_nationale_%', ascending=False).round(2))

    # Étape 3 — comparer les parts de superficie et de population.
    # Étape 4 — mesurer la concentration relative entre communes.
    concentration = pd.DataFrame([
        {'année': 2017, 'Hoover': indice_hoover(d, 2017), 'Theil': indice_theil(d, 2017)},
        {'année': 2023, 'Hoover': indice_hoover(d, 2023), 'Theil': indice_theil(d, 2023)},
    ])
    display(concentration.round(4))
    print('Une hausse du Hoover indique une plus forte concentration sur une fraction plus petite de la superficie. Le Theil compare les communes entre elles.')


# 5.6.3 typologie croisée des soldes naturel et migratoire
def analyse_soldes(d):
    # Typologie de solde naturel et solde migratoire apparent, avec intensité forte/faible.
    webb = d.copy()
    webb['solde_naturel'] = webb['naissances_2017_2022'] - webb['deces_2017_2022']
    webb['solde_migratoire_apparent'] = (
        webb['variation_population'] - webb['solde_naturel']
    )

    webb['naturel_intensite'] = np.select(
        [webb['solde_naturel'].gt(0), webb['solde_naturel'].lt(0)],
        ['positif', 'négatif'], default='nul'
    ) + ' ' + intensite_ternaire(webb['solde_naturel'])
    webb['migration_intensite'] = np.select(
        [webb['solde_migratoire_apparent'].gt(0), webb['solde_migratoire_apparent'].lt(0)],
        ['positif', 'négatif'], default='nul'
    ) + ' ' + intensite_ternaire(webb['solde_migratoire_apparent'])
    webb['profil_webb'] = webb['naturel_intensite'] + ' / ' + webb['migration_intensite']

    webb_resume = webb.groupby('profil_webb').agg(
        communes=('code_commune', 'size'),
        population_2023=('pop_2023', 'sum'),
        solde_naturel=('solde_naturel', 'sum'),
        solde_migratoire_apparent=('solde_migratoire_apparent', 'sum'),
    ).sort_values('communes', ascending=False)
    webb_resume['part_communes_%'] = 100 * webb_resume['communes'] / len(webb)
    display(webb_resume.round(2))
    print('Webb simplifiée : la médiane interne sépare les soldes positifs/faibles/forts et négatifs/faibles/forts. Le profil nul est ajouté aux cas exacts où le solde vaut zéro.')


# 5.6.4 élasticité et quadrants pondérés
def analyse_elasticite(comparables):
    # Élasticité apparente et quadrants pondérés.
    comparables['croissance_voyageurs_an_%'] = (
        (comparables['voyageurs_2023'] / comparables['voyageurs_2017']) ** (1 / 6) - 1
    ) * 100

    croissance_positive = comparables['croissance_pop_an_%'].gt(0)
    elasticites = comparables.loc[croissance_positive].copy()
    elasticites['elasticite_apparente'] = np.divide(
        elasticites['croissance_voyageurs_an_%'],
        elasticites['croissance_pop_an_%'],
        out=np.full(len(elasticites), np.nan),
        where=elasticites['croissance_pop_an_%'].to_numpy() != 0,
    )
    print('Élasticité apparente des voyageurs à la population')
    display(elasticites['elasticite_apparente'].describe(percentiles=[0.25, 0.5, 0.75]).to_frame('ratio annuel voyageurs / population').round(2))

    comparables['quadrant'] = np.select(
        [
            comparables['croissance_pop_an_%'].le(0) & comparables['croissance_voyageurs_an_%'].le(0),
            comparables['croissance_pop_an_%'].le(0) & comparables['croissance_voyageurs_an_%'].gt(0),
            comparables['croissance_pop_an_%'].gt(0) & comparables['croissance_voyageurs_an_%'].le(0),
        ],
        ['Population ↓ / voyageurs ↓', 'Population ↓ / voyageurs ↑', 'Population ↑ / voyageurs ↓'],
        default='Population ↑ / voyageurs ↑',
    )
    quadrants_enrichis = comparables.groupby('quadrant').agg(
        communes=('code_commune', 'size'),
        habitants=('pop_2023', 'sum'),
        voyageurs_2017=('voyageurs_2017', 'sum'),
        voyageurs_2023=('voyageurs_2023', 'sum'),
    )
    quadrants_enrichis['part_communes_%'] = 100 * quadrants_enrichis['communes'] / len(comparables)
    quadrants_enrichis['part_habitants_%'] = 100 * quadrants_enrichis['habitants'] / comparables['pop_2023'].sum()
    quadrants_enrichis['part_voyageurs_2023_%'] = 100 * quadrants_enrichis['voyageurs_2023'] / comparables['voyageurs_2023'].sum()
    display(quadrants_enrichis.round(2))


# 5.6.5 gradient de distance et accessibilité
def analyse_distance(d):
    # Gradient démographique et accessibilité pondérée par la population.
    tranches_distance = pd.IntervalIndex.from_tuples(
        [(-np.inf, 2), (2, 5), (5, 10), (10, 20), (20, np.inf)],
        closed='right',
    )
    labels_distance = ['≤ 2 km', '> 2 à 5 km', '> 5 à 10 km', '> 10 à 20 km', '> 20 km']
    d['tranche_distance_fine'] = pd.cut(d['dist_gare_km'], bins=[-np.inf, 2, 5, 10, 20, np.inf],
                                        labels=labels_distance, right=True)

    gradient = d.groupby('tranche_distance_fine', observed=False).agg(
        communes=('code_commune', 'size'),
        population_2023=('pop_2023', 'sum'),
        croissance_mediane_annuelle_pct=('croissance_pop_an_%', 'median'),
        croissance_cumulee_habitants=('variation_population', lambda s: s.clip(lower=0).sum()),
    ).round(2)
    display(gradient)

    # Courbe de Lorenz inverse : seuil de distance atteint pour 50, 80 et 90 % de la population.
    accessibilite = d[d['dist_gare_km'].notna() & d['pop_2023'].ge(0)].copy()
    accessibilite = accessibilite.sort_values('dist_gare_km')
    accessibilite['part_cumulative_population'] = accessibilite['pop_2023'].cumsum() / accessibilite['pop_2023'].sum()
    seuils_population = []
    for part in [0.50, 0.80, 0.90]:
        seuil = accessibilite.loc[accessibilite['part_cumulative_population'].ge(part), 'dist_gare_km'].iloc[0]
        seuils_population.append({'part_population_%': 100 * part, 'distance_maximale_km': seuil})
    display(pd.DataFrame(seuils_population).round(2))

    # Différence-en-différences descriptive : évolutions des parts voiture par distance.
    for colonne in ['evolution_part_voiture_pp']:
        pass
    did = pd.DataFrame({
        'groupe': ['À moins de 5 km', 'À plus de 10 km', 'Différence descriptive'],
        'evolution_mediane_pp': [
            d.loc[d['dist_gare_km'].lt(5), 'evolution_part_voiture_pp'].median(),
            d.loc[d['dist_gare_km'].gt(10), 'evolution_part_voiture_pp'].median(),
            d.loc[d['dist_gare_km'].lt(5), 'evolution_part_voiture_pp'].median()
            - d.loc[d['dist_gare_km'].gt(10), 'evolution_part_voiture_pp'].median(),
        ],
    })
    display(did.round(2))

    # Dispersion de la dépendance automobile parmi les communes très proches d'une gare.
    proximités = d[d['dist_gare_km'].lt(2)]['part_voiture_2023'].dropna()
    dispersion_proximite = pd.DataFrame({
        'mesure': ['Commune à moins de 2 km', 'Médiane part voiture 2023', 'Q1', 'Q3', 'Écart interquartile'],
        'valeur': [len(proximités),
                   proximités.median(),
                   proximités.quantile(0.25),
                   proximités.quantile(0.75),
                   proximités.quantile(0.75) - proximités.quantile(0.25)],
    })
    display(dispersion_proximite.round(2))


# 5.7 ACP territoriale
def analyse_acp_territoriale(d):
    # Préparer les indicateurs qui décrivent la démographie, les déplacements et l'accès au rail.
    acp = d.copy()
    acp["densite_2023"] = acp["pop_2023"] / acp["superficie_km2"].replace(0, np.nan)
    acp["croissance_pop_6ans_pct"] = (
        100 * (acp["pop_2023"] / acp["pop_2017"].replace(0, np.nan) - 1)
    )
    acp["solde_naturel_pour_1000"] = (
        1000 * (acp["naissances_2017_2022"] - acp["deces_2017_2022"])
        / acp["pop_2017"].replace(0, np.nan)
    )
    acp["part_voiture_2023"] = (
        100 * acp["actifs_voiture_2023"] / acp["actifs_2023"].replace(0, np.nan)
    )
    acp["part_transports_2023"] = (
        100 * acp["actifs_transports_commun_2023"] / acp["actifs_2023"].replace(0, np.nan)
    )
    acp["part_marche_deux_roues_2023"] = (
        100 * (acp["actifs_marche_2023"] + acp["actifs_deux_roues_2023"])
        / acp["actifs_2023"].replace(0, np.nan)
    )

    # Le logarithme réduit l'effet des communes exceptionnellement grandes ou denses.
    X_acp = pd.DataFrame({
        "Croissance démographique (%)": acp["croissance_pop_6ans_pct"],
        "Log population 2023": np.log10(acp["pop_2023"].replace(0, np.nan)),
        "Log densité 2023": np.log10(acp["densite_2023"].replace(0, np.nan)),
        "Solde naturel / 1 000 habitants": acp["solde_naturel_pour_1000"],
        "Part voiture (%)": acp["part_voiture_2023"],
        "Part transports collectifs (%)": acp["part_transports_2023"],
        "Part marche + deux-roues (%)": acp["part_marche_deux_roues_2023"],
        "Distance gare (km)": acp["dist_gare_km"],
        "Présence ferroviaire (log 1+gares)": np.log1p(acp["nb_gares"]),
    })

    # Le module standardise les variables, calcule les axes et projette les communes.
    acp_territoriale = calculer_acp(X_acp)
    X_acp = acp_territoriale["donnees"]
    table_axes = acp_territoriale["resume_axes"]
    scores = acp_territoriale["scores"]
    corr_variables = acp_territoriale["correlations"]
    contributions = acp_territoriale["contributions"]
    print(f"Communes retenues : {len(X_acp):,} sur {len(acp):,}")
    display(arrondir_tableau(table_axes))
    display(arrondir_tableau(corr_variables.sort_values("PC1", ascending=False)))

    # Les 5 communes à chaque extrémité aident à donner un sens concret à chaque axe.
    communes_acp = acp.loc[X_acp.index, [
        "code_commune", "nom_commune", "code_region", "pop_2023",
        "densite_2023", "part_voiture_2023", "dist_gare_km",
    ]]
    for axe in ["PC1", "PC2", "PC3"]:
        indices = pd.concat([scores[axe].nlargest(5), scores[axe].nsmallest(5)])
        extremes = communes_acp.loc[indices.index].copy()
        extremes["score"] = indices
        extremes["contribution (%)"] = contributions.loc[indices.index, axe]
        print(f"Communes extrêmes — {axe}")
        display(arrondir_tableau(extremes.sort_values("score", ascending=False)))

    # L'hexbin montre où les communes se concentrent ; la légende numérotée clarifie les flèches.
    figures_acp = tracer_acp(acp_territoriale, "ACP territoriale")
    for figure in figures_acp:
        display(figure)


# 5.7 ACP ferroviaire
def analyse_acp_ferroviaire(d):
    # Garder les communes avec les deux observations de fréquentation et une population 2017 positive.
    rail_acp = d[
        d["voyageurs_2017"].notna()
        & d["voyageurs_2023"].notna()
        & d["pop_2017"].gt(0)
    ].copy()
    rail_acp["densite_2023"] = (
        rail_acp["pop_2023"] / rail_acp["superficie_km2"].replace(0, np.nan)
    )
    rail_acp["croissance_voyageurs_pct"] = (
        100 * (rail_acp["voyageurs_2023"] / rail_acp["voyageurs_2017"].replace(0, np.nan) - 1)
    )
    rail_acp["croissance_population_pct"] = (
        100 * (rail_acp["pop_2023"] / rail_acp["pop_2017"] - 1)
    )
    rail_acp["part_voiture_2023"] = (
        100 * rail_acp["actifs_voiture_2023"]
        / rail_acp["actifs_2023"].replace(0, np.nan)
    )
    rail_acp["part_transport_2023"] = (
        100 * rail_acp["actifs_transports_commun_2023"]
        / rail_acp["actifs_2023"].replace(0, np.nan)
    )

    # Les volumes sont logarithmés pour qu'une poignée de très grandes villes ne domine pas tout l'axe.
    X_rail = pd.DataFrame({
        "Log voyageurs 2023": np.log10(rail_acp["voyageurs_2023"].replace(0, np.nan)),
        "Croissance voyageurs (%)": rail_acp["croissance_voyageurs_pct"],
        "Croissance population (%)": rail_acp["croissance_population_pct"],
        "Log population 2023": np.log10(rail_acp["pop_2023"].replace(0, np.nan)),
        "Log densité 2023": np.log10(rail_acp["densite_2023"].replace(0, np.nan)),
        "Nombre de gares": rail_acp["nb_gares"],
        "Distance gare (km)": rail_acp["dist_gare_km"],
        "Part voiture (%)": rail_acp["part_voiture_2023"],
        "Part transports collectifs (%)": rail_acp["part_transport_2023"],
    })

    acp_ferroviaire = calculer_acp(X_rail)
    X_rail = acp_ferroviaire["donnees"]
    scores_rail = acp_ferroviaire["scores"]
    corr_rail = acp_ferroviaire["correlations"]
    print(f"Communes retenues : {len(X_rail):,}")
    display(arrondir_tableau(acp_ferroviaire["resume_axes"]))
    display(arrondir_tableau(corr_rail.sort_values("PC1", ascending=False)))

    figures_acp_rail = tracer_acp(acp_ferroviaire, "ACP ferroviaire", couleur="#59A14F")
    for figure in figures_acp_rail:
        display(figure)

    for axe in ["PC1", "PC2"]:
        indices = pd.concat([scores_rail[axe].nlargest(5), scores_rail[axe].nsmallest(5)])
        extremes = rail_acp.loc[indices.index, [
            "nom_commune", "code_region", "pop_2023", "nb_gares",
            "voyageurs_2017", "voyageurs_2023", "dist_gare_km",
        ]].copy()
        extremes["score"] = indices
        print(f"Communes extrêmes — {axe}")
        display(arrondir_tableau(extremes.sort_values("score", ascending=False)))
