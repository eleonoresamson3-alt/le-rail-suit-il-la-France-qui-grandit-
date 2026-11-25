"""Fonctions build_ : jointures et variables construites."""


def build_jointure(gauche, droite, nom):
    # on fait un left join à partir de la clé code_commune
    table = gauche.merge(droite, on="code_commune", how="left", validate="one_to_one", indicator=True)
    # permet d'isoler les communes qui n'ont pas été ajouté dans notre jointure
    sans = (table["_merge"] == "left_only").sum()
    print(f"{nom} : {len(table)} communes, {sans} sans correspondance ({sans / len(table) * 100:.2f} %)")
    # on veut s'assurer qu'il ne manque pas des observations ni qu'il y en a en trop, pareil pour les variables
    assert len(table) == len(gauche)
    return table.drop(columns="_merge")

#à partir de la table issues de cartiflette et des contours, on construit une plus grosse table basée sur code_commune
def build_communes(contours, population, navettes, parc):
    
    communes = build_jointure(contours, population, "population")
    communes = build_jointure(communes, navettes, "navettes")
    communes = build_jointure(communes, parc, "parc automobile")
    assert communes["code_commune"].is_unique   #  on vérifie bien qu'on a toujours l'unicité de la commune
    return communes