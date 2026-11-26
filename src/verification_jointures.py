" les fonctions veri_ permettent de vérifier dans quelles bases il y a des valeurs multiples sur une même ligne"

def verif_code_uic(bases):
    for df in bases :
        print(df)
        multiples = df[df['code_uic'].astype(str).str.contains(r"[;, ]")]
        print(len(multiples))
        
    return