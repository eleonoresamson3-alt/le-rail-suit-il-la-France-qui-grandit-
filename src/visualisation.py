"""Fonctions plot_ et map_ : graphiques et cartes."""

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import pandas as pd
import geopandas as gpd
import numpy as np

from pathlib import Path

from src.config import CLEAN_DATA_DIR, FIGURES_DIR
from src.variables import build_tcam
from src.variables import build_solde_naturel
from src.variables import build_solde_migratoire
from src.variables import build_soldes_regionaux
from src.variables import build_region


# déclin en rouge, stable en gris, croissance en bleu (même palette pour toutes les cartes)
COULEURS_TRAJECTOIRE = ListedColormap(["#f19d9b", "#efefef", "#84b9f3"])

COULEURS_TRAJECTOIRE_LONG = ListedColormap([
    "#f19d9b",  # Déclin fort : rouge clair
    "#f6c5c3",  # Déclin modéré : rouge très clair
    "#efefef",  # Stabilité : gris
    "#b3d3f5",  # Croissance modérée : bleu clair
    "#84b9f3"   # Croissance forte : bleu
])

# carte des gares sur la trajectoire démographique des communes
def map_gares(communes, gares, gares_annees, annee, titre, chemin):
    # on set up les bulles pour les gares, à partir du code_iuc
    bulles = gares.merge(gares_annees[gares_annees["annee"] == annee], on="code_uic")
    fig, ax = plt.subplots(figsize=(9, 9))

    # fond : communes coloriées selon leur trajectoire, en Lambert 93
    communes.to_crs(2154).plot(ax=ax, column="trajectoire", cmap=COULEURS_TRAJECTOIRE, linewidth=0, legend=True,
                               legend_kwds={"loc": "lower left", "title": "Population 2017-2023"})

    # bulles : surface proportionnelle aux voyageurs, avec une taille minimale pour les petites gares
    bulles.to_crs(2154).plot(ax=ax, markersize=(bulles["voyageurs"] / 1e6 * 4).clip(lower=2),
                             color="#191919", edgecolor="white", linewidth=0.3, alpha=0.7)

    # seconde légende pour la taille des bulles, sans effacer celle des communes
    ax.add_artist(ax.get_legend())
    exemples = [ax.scatter([], [], s=millions * 4, color="#191919", alpha=0.7, label=f"{millions} millions")
                for millions in [10, 50, 200]]
    ax.legend(handles=exemples, title=f"Voyageurs {annee}", loc="upper left", labelspacing=1.5, frameon=False)

    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


def map_croissance_demographique() : 

    # Chargement de la table
    communes = gpd.read_parquet(CLEAN_DATA_DIR / "base_finale/communes.parquet")
    communes = communes.copy()

    # Ajout du tcam à partir de la fonction build_tcam()
    communes["tcam_pop_2017_2023"] = build_tcam(communes["pop_2017"], communes["pop_2023"], 6)


    # Création de la figure
    fig, ax = plt.subplots(figsize=(12, 10))

    # Tracé de la carte
    communes.plot(column="tcam_pop_2017_2023", cmap= COULEURS_TRAJECTOIRE_LONG, scheme="quantiles",
                  k=5, legend=True, edgecolor="white", linewidth=0.05,
                  ax=ax,legend_kwds={"title": "Croissance annuelle moyenne (%)","loc": "lower left"})

    # Titre
    ax.set_title("Une population en croissance autour des grandes villes", fontsize=14, pad=15)

    # Suppression des axes
    ax.set_axis_off()

    # Source
    #fig.text(1, 0.05, "Source : INSEE, Recensements de la population 2017 et 2023.")
    "a repositionner, pour l'instant rend la légende illisible"

    plt.tight_layout()

    # Enregistrer
    fig.savefig(FIGURES_DIR / "01_croissance_demographique.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_soldes_regionaux():

    # Récupération des variables
    communes = gpd.read_parquet(CLEAN_DATA_DIR / "base_finale/communes.parquet")
    regional = build_soldes_regionaux(communes)
    regional = regional.merge(build_region(), on="code_region", how="left")
    regional["evolution_population"] = (regional["pop_2023"] - regional["pop_2017"])
    regional = regional.sort_values(by="evolution_population", ascending=False)
    
    # Position des régions sur l'axe vertical
    positions = np.arange(len(regional))

    # Dimensions de la figure
    fig, ax = plt.subplots(figsize=(12, 8))

    # Barres horizontales
    hauteur = 0.35

    ax.barh(positions - hauteur/2,regional["solde_naturel"],height=hauteur,label="Solde naturel")

    ax.barh(positions + hauteur/2,regional["solde_migratoire"],height=hauteur,label="Solde migratoire apparent")

    # Noms des régions
    ax.set_yticks(positions)
    ax.set_yticklabels(regional["nom_region"])

    # Ordre des régions : croissance décroissante
    ax.invert_yaxis()

    # Ligne verticale à zéro
    ax.axvline(0, color="black", linewidth=0.8)

    # Titres et axes
    ax.set_title("Les soldes naturel et migratoire expliquent les dynamiques régionales",fontsize=14)

    ax.set_xlabel("Nombre d'habitants")
    ax.set_ylabel("Région")

    ax.legend()

    # Source
    fig.text(0.1, 0.02,"Source : INSEE, Recensements de la population 2017 et 2023.")

    plt.tight_layout()

    # Enregistrer
    fig.savefig(FIGURES_DIR / "02_soldes_regionaux.png", dpi=300, bbox_inches="tight")


    return fig, ax



def plot_hist_croissance():

    # Préparation des données
    communes = gpd.read_parquet(CLEAN_DATA_DIR / "base_finale/communes.parquet")
    communes["tcam_pop_2017_2023"] = build_tcam(communes["pop_2017"], communes["pop_2023"], 6)
    croissance = communes["tcam_pop_2017_2023"].dropna()

    # Calcul du nombre de communes en croissance
    nb_croissance = (croissance > 0).sum()

    nb_total = len(croissance)

    part_croissance = nb_croissance / nb_total * 100

    # Création de la figure
    fig, ax = plt.subplots(figsize=(11, 6))

    # Histogramme
    ax.hist(croissance, bins=40, edgecolor="white", alpha=0.8)

    # Ligne verticale à zéro
    ax.axvline(0, color="red", linestyle="--", linewidth=1.5, label="Absence de croissance")

    # Titre
    ax.set_title(
        f"{part_croissance:.1f} % des communes connaissent une croissance démographique",
        fontsize=14)

    # Axes
    ax.set_xlabel("Taux de croissance annuel moyen (%)")
    ax.set_ylabel("Nombre de communes")

    ax.legend()

    # Source
    #fig.text(0.1, 0.02,"Source : INSEE, Recensements de la population 2017 et 2023.")

    plt.tight_layout()

     # Enregistrer
    fig.savefig(FIGURES_DIR / "03_histogramme_croissance.png", dpi=300, bbox_inches="tight")

    return fig, ax



def plot_evolution_frequentation():

    # Copie et sélection des données
    gares_annees = pd.read_parquet(CLEAN_DATA_DIR / "base_finale/gares_annees.parquet")
    gares_annees = gares_annees.copy()

    gares_annees = gares_annees[gares_annees["segmentation_drg"].notna()]

    # Agrégation des voyageurs par année et segmentation
    evolution = (gares_annees.groupby(["annee", "segmentation_drg"])["voyageurs"].sum().unstack())

    # Passage en base 100 en 2019
    evolution = evolution.div(evolution.loc[2019]) * 100

    # Création du graphique
    fig, ax = plt.subplots(figsize=(11, 6))

    for categorie in ["A", "B", "C"]:
        if categorie in evolution.columns:
            ax.plot(evolution.index, evolution[categorie], marker="o", linewidth=2, 
                    label=f"Catégorie {categorie}")

    # Repère Covid
    ax.axvline(x=2020, color="grey", linestyle="--", alpha=0.8, label="Covid-19")

    # Mise en forme
    ax.axhline(100, color="black", linewidth=0.8, alpha=0.5)

    ax.set_title("Évolution de la fréquentation des gares par segmentation DRG")
    ax.set_xlabel("Année")
    ax.set_ylabel("Indice de fréquentation (base 100 en 2019)")

    ax.set_xticks(range(2017, 2024))
    ax.legend(title="Segmentation")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.show()

    fig.savefig(FIGURES_DIR / "04_voyageurs_base_100.png", dpi=300, bbox_inches="tight")

    return fig, ax
