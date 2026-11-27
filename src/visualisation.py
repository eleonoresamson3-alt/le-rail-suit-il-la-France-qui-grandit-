from matplotlib.lines import Line2D
"""Fonctions plot_ et map_ : graphiques et cartes."""

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from folium.plugins import TimestampedGeoJson
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


from matplotlib.patches import Patch

# déclin en rouge, stable en gris, croissance en bleu (même palette pour toutes les cartes)
COULEURS_TRAJECTOIRE = ListedColormap(["#f19d9b", "#efefef", "#84b9f3"])
# distance à la gare : du plus clair (proche) au plus foncé (loin), en orangé puis rouge
COULEURS_DISTANCE = ListedColormap(["#fde0c5", "#f6a15c", "#e4572e", "#a8201a"])
# les 6 variables de la heatmap, dans l'ordre du plan, avec leur nom lisible
NOMS_VARIABLES = {"tcam_pop_2017_2023": "Croissance population", "tcam_voyageurs_2017_2023": "Croissance voyageurs",
                  "densite": "Densité", "part_voiture_2023": "Part voiture",
                  "dist_gare_km": "Distance à la gare", "voyageurs_hab_2023": "Voyageurs par habitant"}
# ordre et couleurs des trajectoires, pour les graphiques (mêmes couleurs que sur les cartes)
ORDRE_TRAJECTOIRE = ["déclin", "stable", "croissance"]
COULEURS_TRAJECTOIRE_LISTE = ["#f19d9b", "#efefef", "#84b9f3"]
# 4 profils : l'orangé signale les communes qui grandissent sans gare proche (le cas qui nous intéresse)
COULEURS_PROFIL = {"croissance – desservie": "#84b9f3", "croissance – non desservie": "#f47230",
                   "déclin ou stable – desservie": "#d9d9d9", "déclin ou stable – non desservie": "#a6a6a6"}

COULEURS_TRAJECTOIRE_LONG = ListedColormap([
    "#f19d9b",  # Déclin fort : rouge clair
    "#f6c5c3",  # Déclin modéré : rouge très clair
    "#efefef",  # Stabilité : gris
    "#b3d3f5",  # Croissance modérée : bleu clair
    "#84b9f3"   # Croissance forte : bleu
])

# carte des gares sur la trajectoire démographique des communes


# carte des gares (taille = voyageurs) sur la trajectoire démographique des communes
def map_gares(communes, gares, gares_annees, annee, titre, chemin):
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


def map_croissance_demographique() : 

    # Chargement de la table
    communes = gpd.read_parquet(CLEAN_DATA_DIR / "base_finale/base_finale_communes.parquet")
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
    communes = gpd.read_parquet(CLEAN_DATA_DIR / "base_finale/base_finale_communes.parquet")
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

# carte interactive des gares avec un curseur pour choisir l'année ; au clic : gare, voyageurs, croissance de la commune
def map_gares_curseur(communes, gares, gares_annees, chemin):
    # une ligne par gare et par année, avec la position de la gare et la croissance de sa commune
    points = gares[["code_uic", "geometry"]].merge(gares_annees, on="code_uic").to_crs(4326)
    points = points.merge(communes[["code_commune", "tcam_pop_2017_2023"]], on="code_commune", how="left")
    # un point par gare et par année, au format attendu par le curseur de folium
    elements = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [p.geometry.x, p.geometry.y]},
        "properties": {
            "time": f"{p['annee']}-01-01",
            "popup": (f"<b>{p['nom_gare']}</b><br>{p['voyageurs']:,.0f} voyageurs en {p['annee']}<br>"
                      f"Population de la commune : {p['tcam_pop_2017_2023']:+.1f} % par an (2017-2023)").replace(",", " "),
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


# heatmap triangulaire des corrélations de Spearman entre les 6 variables de NOMS_VARIABLES (partie basse)
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


# carte de la distance du centre de chaque commune à la gare la plus proche, en 4 classes
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


# boîtes à moustaches : croissance des voyageurs selon la trajectoire de la population (communes avec gare)
def plot_voyageurs_trajectoire(communes, titre, chemin):
    donnees = communes.dropna(subset=["tcam_voyageurs_2017_2023", "trajectoire"])
    fig, ax = plt.subplots(figsize=(8, 5))
    # showfliers=False : on masque les valeurs extrêmes (gares ouvertes en cours de période)
    sns.boxplot(data=donnees, x="trajectoire", y="tcam_voyageurs_2017_2023", order=ORDRE_TRAJECTOIRE,
                hue="trajectoire", palette=COULEURS_TRAJECTOIRE_LISTE, showfliers=False, legend=False, width=0.5, ax=ax)
    # nombre de communes sous chaque boîte
    effectifs = donnees["trajectoire"].value_counts()
    ax.set_xticks(range(3), [f"{t}\nn = {effectifs[t]:,}".replace(",", " ") for t in ORDRE_TRAJECTOIRE])
    ax.axhline(0, color="#666666", linewidth=0.8)
    ax.set_xlabel("Trajectoire de la population, 2017-2023")
    ax.set_ylabel("Croissance des voyageurs (% par an)")
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# nuage de points : part de la voiture selon la distance à la gare, avec la médiane par tranche de 2 km
def plot_voiture_distance(communes, titre, chemin):
    donnees = communes.dropna(subset=["dist_gare_km", "part_voiture_2023"])
    # médiane de la part de la voiture par tranche de 2 km (milieu de la tranche en abscisse)
    tranche = (donnees["dist_gare_km"] // 2) * 2 + 1
    par_tranche = donnees.groupby(tranche)["part_voiture_2023"].agg(["median", "count"])
    medianes = par_tranche.loc[par_tranche["count"] >= 20, "median"]   # tranches d'au moins 20 communes
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(donnees["dist_gare_km"], donnees["part_voiture_2023"], s=6, color="#9c9c9c", alpha=0.4, label="une commune")
    ax.plot(medianes.index, medianes.values, color="#e4572e", linewidth=2, marker="o", markersize=4, label="médiane par tranche de 2 km")
    ax.set_xlabel("Distance du centre de la commune à la gare la plus proche (km)")
    ax.set_ylabel("Actifs allant travailler en voiture (%)")
    ax.legend(frameon=False, loc="lower right")
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# boîtes à moustaches : part des actifs allant travailler en voiture, par classe de taille de commune
def plot_voiture_taille(communes, titre, chemin):
    donnees = communes.dropna(subset=["part_voiture_toutes_2023", "classe_taille"])
    fig, ax = plt.subplots(figsize=(10, 5))
    # showfliers=False : valeurs extrêmes masquées (très petites communes)
    sns.boxplot(data=donnees, x="classe_taille", y="part_voiture_toutes_2023", color="#e4572e",
                showfliers=False, width=0.5, ax=ax)
    # nombre de communes sous chaque boîte
    effectifs = donnees["classe_taille"].value_counts(sort=False)
    ax.set_xticks(range(len(effectifs)), [f"{classe}\nn = {n:,}".replace(",", " ") for classe, n in effectifs.items()])
    ax.set_ylim(0, 102)
    ax.set_xlabel("Taille de la commune (habitants en 2023)")
    ax.set_ylabel("Actifs allant travailler en voiture (%)")
    ax.set_title(titre, loc="left", fontweight="bold")
    # note sous le graphique : valeurs extrêmes signalées, champ et source
    fig.text(0, -0.04, "Valeurs extrêmes non affichées. Toutes les communes, sans seuil d'actifs.\n"
             "Source : INSEE, navettes domicile-travail 2023. Champ : France métropolitaine.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# carte des 4 profils de communes : croissance ou non, gare à 10 km ou moins (desservie) ou non
def map_profils(communes, titre, chemin):
    carte = communes[["profil", "geometry"]].to_crs(2154)
    fig, ax = plt.subplots(figsize=(9, 9))
    # chaque commune prend la couleur de son profil ; sans profil (Corse, communes sans taux) en blanc
    carte.plot(ax=ax, color=carte["profil"].map(COULEURS_PROFIL).fillna("white"), linewidth=0)
    cases = [Patch(facecolor=couleur, label=profil) for profil, couleur in COULEURS_PROFIL.items()]
    ax.legend(handles=cases, title="Profil de la commune", loc="lower left", frameon=False, alignment="left")
    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0.02, 0.06, "Croissance : population en hausse entre 2017 et 2023. Desservie : gare de voyageurs à 10 km ou moins.\n"
             "Sources : INSEE, recensements 2017 et 2023 ; SNCF. Champ : France métropolitaine hors Corse.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# nuage : croissance de la population × croissance des voyageurs, en 4 quadrants (communes avec gare)
def plot_quadrants(communes, titre, chemin):
    donnees = communes.dropna(subset=["tcam_pop_2017_2023", "tcam_voyageurs_2017_2023"])
    # écrêtage à ±10 % par an : les valeurs plus fortes sont ramenées au bord du graphique
    x = donnees["tcam_pop_2017_2023"].clip(-10, 10)
    y = donnees["tcam_voyageurs_2017_2023"].clip(-10, 10)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(x, y, s=8, color="#191919", alpha=0.3)
    ax.axhline(0, color="#666666", linewidth=0.8)
    ax.axvline(0, color="#666666", linewidth=0.8)
    # nombre de communes dans chaque quadrant, écrit dans son coin
    for signe_x, signe_y in [(1, 1), (-1, 1), (-1, -1), (1, -1)]:
        n = ((signe_x * x > 0) & (signe_y * y > 0)).sum()
        sens = f"population {'+' if signe_x > 0 else '−'}, voyageurs {'+' if signe_y > 0 else '−'}"
        ax.text(signe_x * 9.5, signe_y * 9, f"{n} communes\n{sens}", ha="right" if signe_x > 0 else "left",
                va="top" if signe_y > 0 else "bottom", fontweight="bold")
    ax.set_xlim(-10.5, 10.5)
    ax.set_ylim(-10.5, 10.5)
    ax.set_xlabel("Croissance de la population, 2017-2023 (% par an)")
    ax.set_ylabel("Croissance des voyageurs des gares, 2017-2023 (% par an)")
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0, -0.02, "Communes ayant au moins une gare. Valeurs écrêtées à ±10 % par an.\n"
             "Sources : INSEE, recensements 2017 et 2023 ; SNCF, fréquentation en gares. Champ : France métropolitaine.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# barres horizontales : CO2 de l'avion et des mêmes passagers en TGV, pour les liaisons qui émettent le plus
def plot_co2_avion_tgv(liaisons, annee, nb, titre, chemin):
    # hors Corse (pas de train possible) ; les nb liaisons qui émettent le plus, la plus grosse en haut
    haut = liaisons.dropna(subset=[f"co2_tgv_t_{annee}"]).nlargest(nb, f"co2_avion_t_{annee}").iloc[::-1]
    noms = (haut["nom_aeroport_1"].str.title() + " – " + haut["nom_aeroport_2"].str.title()
            + " (" + haut["dist_km"].astype(str) + " km)")
    y = np.arange(len(haut))
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(y + 0.2, haut[f"co2_avion_t_{annee}"] / 1000, height=0.4, color="#e4572e", label="avion")
    ax.barh(y - 0.2, haut[f"co2_tgv_t_{annee}"] / 1000, height=0.4, color="#257de0", label="mêmes passagers en TGV")
    ax.set_yticks(y, noms)
    ax.set_xlabel(f"CO2 émis en {annee} (milliers de tonnes équivalent CO2)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0, -0.02, "Passagers × distance à vol d'oiseau × facteur d'émission (avion : 101-220 sièges, 500-1 000 km, avec traînées ;\n"
             "TGV). Passagers publiés (minimum, secret statistique). Sources : DGAC ; ADEME, Base Carbone. Liaisons hors Corse.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")


# nuage : évolution des passagers aériens (mêmes mois publiés) selon la distance de la liaison
def plot_avion_distance(liaisons, annee_debut, annee_fin, titre, chemin):
    donnees = liaisons[liaisons["mois_communs"] > 0].copy()
    # évolution sur les mois publiés les deux années, en %
    donnees["evolution"] = (donnees[f"passagers_communs_{annee_fin}"] / donnees[f"passagers_communs_{annee_debut}"] - 1) * 100
    corse = donnees["code_oaci_1"].str.startswith("LFK") | donnees["code_oaci_2"].str.startswith("LFK")
    fig, ax = plt.subplots(figsize=(9, 5.5))
    # surface du point proportionnelle aux passagers de la première année
    for groupe, couleur, nom in [(~corse, "#e4572e", "continent"), (corse, "#a6a6a6", "vers la Corse (pas de train)")]:
        ax.scatter(donnees.loc[groupe, "dist_km"], donnees.loc[groupe, "evolution"],
                   s=donnees.loc[groupe, f"passagers_communs_{annee_debut}"] / 2000,
                   color=couleur, alpha=0.6, edgecolor="white", linewidth=0.5, label=nom)
    ax.axhline(0, color="#666666", linewidth=0.8)
    ax.set_xlabel("Distance entre les deux aéroports (km)")
    ax.set_ylabel(f"Évolution des passagers, {annee_debut}-{annee_fin} (%)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0, -0.02, f"Liaisons intérieures publiées les deux années, comparées sur les mêmes mois (secret statistique).\n"
             f"Taille du point : passagers {annee_debut} sur ces mois. Source : DGAC, trafic par paire d'aéroports.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")

# carte des liaisons aériennes : un trait entre les deux villes, épaisseur = passagers
def map_liaisons(communes, villes, liaisons, annee, titre, chemin):
    # position de chaque aéroport : le centre de la ville qu'il dessert (table du config), en Lambert 93
    centres = communes.to_crs(2154).set_index("code_commune").geometry.centroid
    position = villes.set_index("code_oaci")["code_commune"].map(centres)
    traits = liaisons.dropna(subset=[f"passagers_{annee}"]).sort_values(f"passagers_{annee}")
    fig, ax = plt.subplots(figsize=(9, 9))
    communes.to_crs(2154).plot(ax=ax, color="#eeeeee", linewidth=0)
    for _, l in traits.iterrows():
        depart, arrivee = position[l["code_oaci_1"]], position[l["code_oaci_2"]]
        # vers la Corse : en gris (pas de train possible)
        corse = l["code_oaci_1"].startswith("LFK") or l["code_oaci_2"].startswith("LFK")
        ax.plot([depart.x, arrivee.x], [depart.y, arrivee.y], color="#8c8c8c" if corse else "#e4572e",
                linewidth=max(l[f"passagers_{annee}"] / 2e5, 0.5), alpha=0.8, solid_capstyle="round")
    # nom des villes
    for _, v in villes.drop_duplicates("ville").iterrows():
        point = position[v["code_oaci"]]
        ax.text(point.x, point.y, v["ville"], fontsize=8, ha="center", va="bottom")
    legende = [Line2D([], [], color="#e4572e", linewidth=n / 2e5, label=texte)
               for n, texte in [(1e5, "100 000 passagers"), (5e5, "500 000 passagers"), (1e6, "1 million de passagers")]]
    legende.append(Line2D([], [], color="#8c8c8c", linewidth=3, label="vers la Corse (pas de train)"))
    ax.legend(handles=legende, loc="lower left", frameon=False, title=f"Passagers {annee}", alignment="left")
    ax.set_axis_off()
    ax.set_title(titre, loc="left", fontweight="bold")
    fig.text(0.02, 0.06, "Trait entre les villes desservies par les deux aéroports (Paris : Orly et Charles-de-Gaulle confondus sur la carte).\n"
             "Passagers publiés (minimum, secret statistique). Source : DGAC, trafic par paire d'aéroports.",
             fontsize=8, color="#666666", va="top")
    fig.savefig(chemin, dpi=200, bbox_inches="tight")
