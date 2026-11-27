"""Étape 4 : statistiques descriptives et ACP (notebook 05_analyse_mobilites).

Lit la table data/clean/base_finale/base_finale_communes_variables.parquet.
"""

import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


# ---------- 05_analyse_mobilites : 0. Données et contrôles ----------

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


# ---------- 05_analyse_mobilites : 1. Où va la population ? ----------

def synthese_croissance_par(groupe):
    """Résume la croissance annuelle des communes d'un groupe."""
    return groupe.agg(
        communes=("code_commune", "size"),
        population_2023=("pop_2023", "sum"),
        croissance_annuelle_mediane_pct=("croissance_pop_an_%", "median"),
        croissance_annuelle_moyenne_pct=("croissance_pop_an_%", "mean"),
    ).round(2)


# ---------- 05_analyse_mobilites : 2. Comment évolue la fréquentation des gares ? ----------

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


# ---------- 05_analyse_mobilites : 4. Qui dépend de la voiture, et qui vit loin d'une gare ? ----------

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


# ---------- 05_analyse_mobilites : 5. Enrichissements statistiques descriptifs ----------

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


# ---------- 05_analyse_mobilites : 6. ACP : comment la lire ----------

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
