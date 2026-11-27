"""Fonctions plot_ et map_ : graphiques et cartes."""

import folium
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from folium.plugins import TimestampedGeoJson
import numpy as np
import seaborn as sns
import pandas as pd

# déclin en rouge, stable en gris, croissance en bleu (même palette pour toutes les cartes)
COULEURS_TRAJECTOIRE = ListedColormap(["#f19d9b", "#efefef", "#84b9f3"])
# distance à la gare : du plus clair (proche) au plus foncé (loin), en orangé puis rouge
COULEURS_DISTANCE = ListedColormap(["#fde0c5", "#f6a15c", "#e4572e", "#a8201a"])
# noms lisibles des variables communales, pour les graphiques
NOMS_VARIABLES = {"tcam_pop_2017_2023": "Croissance population", "tcam_voyageurs_2017_2023": "Croissance voyageurs",
                  "part_voiture_2023": "Part voiture", "voitures_1000_hab_2023": "Voitures / 1 000 hab.",
                  "dist_gare_km": "Distance à la gare", "densite": "Densité"}

def map_gares(communes, gares, gares_annees, annee, titre, chemin):
    """Carte des gares (taille = voyageurs) sur la trajectoire démographique des communes."""
    # une bulle par gare : sa position et ses voyageurs de l'année
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

# carte interactive des gares avec un curseur pour choisir l'année
def map_gares_curseur(gares, gares_annees, chemin):
    # une ligne par gare et par année, avec la position de la gare en latitude-longitude
    points = gares[["code_uic", "geometry"]].merge(gares_annees, on="code_uic").to_crs(4326)
    # un point par gare et par année, au format attendu par le curseur de folium
    elements = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [p.geometry.x, p.geometry.y]},
        "properties": {
            "time": f"{p['annee']}-01-01",
            "popup": f"{p['nom_gare']} : {p['voyageurs']:,.0f} voyageurs en {p['annee']}".replace(",", " "),
            "icon": "circle",
            "iconstyle": {"radius": max((p["voyageurs"] / 1e6) ** 0.5 * 2, 2), "color": "#191919",
                          "weight": 0.5, "fillColor": "#191919", "fillOpacity": 0.6},
        },
    } for _, p in points.iterrows()]
    carte = folium.Map(location=[46.6, 2.4], zoom_start=6)
    # duration="P1Y" : chaque point ne reste affiché que pendant son année
    TimestampedGeoJson({"type": "FeatureCollection", "features": elements}, period="P1Y", duration="P1Y",
                       auto_play=False, add_last_point=False, date_options="YYYY").add_to(carte)
    carte.save(chemin)
    return carte
#heatmap triangulaire matrice de corrélation (que partie basse)
def plot_correlations(communes, titre, chemin):
    correlations = communes[list(NOMS_VARIABLES)].corr(method="spearman").rename(index=NOMS_VARIABLES, columns=NOMS_VARIABLES)
    # on retire la 1re ligne et la dernière colonne, vides, puis on masque la moitié haute qui répète la basse
    bas = correlations.iloc[1:, :-1]
    masque = np.triu(np.ones(bas.shape, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(bas, mask=masque, annot=True, fmt=".2f", cmap="RdBu", vmin=-1, vmax=1,
                linewidths=2, cbar_kws={"label": "Corrélation de Spearman"}, ax=ax)
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")

#carte de la distance du centre de chaque commune à la gare la plus proche, 4 classes
def map_distance_gare(communes, titre, chemin):
    carte = communes[["dist_gare_km", "geometry"]].to_crs(2154)
    carte["classe"] = pd.cut(carte["dist_gare_km"], bins=[0, 5, 10, 15, float("inf")],
                             labels=["5 km ou moins", "5 à 10 km", "10 à 15 km", "plus de 15 km"])
    fig, ax = plt.subplots(figsize=(9, 9))
    # Corse sans distance (pas de gare SNCF) : en gris clair
    carte.plot(ax=ax, column="classe", cmap=COULEURS_DISTANCE, linewidth=0, legend=True,
               missing_kwds={"color": "#e0e0e0", "label": "pas de gare SNCF"},
               legend_kwds={"loc": "lower left", "title": "Distance à la gare la plus proche"})
    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")