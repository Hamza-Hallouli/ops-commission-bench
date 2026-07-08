import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Calculateur de Paie Variable", page_icon="💰", layout="centered")

# --- MOTEURS DE CALCUL (LOGIQUE MÉTIER) ---
def calcul_standard(tr):
    if tr < 0.50: return tr * 0.40
    elif tr < 0.90: return tr * tr * 0.80
    elif tr < 1.00: return tr * tr * 0.95
    elif tr == 1.00: return 1.00
    elif tr < 1.91: return tr * tr * 1.10
    else: return 4.00

def calcul_manager(tr):
    if tr < 0.30: return 0.0
    elif tr < 0.60: return tr * 0.40
    elif tr < 0.70: return tr * 0.45
    elif tr < 0.80: return tr * 0.55
    elif tr < 0.90: return tr * 0.65
    elif tr < 0.95: return tr * 0.80
    elif tr < 1.00: return tr * 0.90
    elif tr < 1.03: return tr * 1.10
    elif tr < 1.05: return tr * 1.20
    elif tr < 1.10: return tr * 1.30
    elif tr < 1.15: return tr * 1.35
    elif tr < 1.20: return tr * 1.40
    elif tr < 1.25: return tr * 1.45
    elif tr < 1.30: return tr * 1.50
    elif tr < 1.35: return tr * 1.60
    elif tr < 1.45: return tr * 1.70
    else: return 2.50

def calcul_manager_is(tr):
    if tr < 0.70: return tr * 0.40
    elif tr < 0.80: return tr * 0.40
    elif tr < 0.90: return tr * 0.50
    elif tr < 0.95: return tr * 0.90
    elif tr < 1.00: return tr * 0.95
    elif tr < 1.01: return tr * 1.00
    elif tr < 1.05: return tr * 1.10
    elif tr < 1.10: return tr * 1.20
    elif tr < 1.20: return tr * 1.25
    elif tr < 1.55: return tr * 1.30
    else: return 2.00

def calcul_inside_sales(tr):
    if tr < 0.70: return tr * 0.40
    elif tr < 0.90: return tr * 0.70
    elif tr < 1.00: return tr * 0.90
    elif tr < 1.01: return tr * 1.00
    elif tr < 1.10: return tr * 1.15
    elif tr < 1.30: return tr * 1.30
    elif tr < 1.39: return tr * 1.35
    elif tr < 1.50: return tr * 1.40
    elif tr < 1.72: return tr * 1.50
    else: return 2.50

# --- INTERFACE GRAPHIQUE (FRONT-END) ---
st.title("💰 Simulateur de Paie Variable")
st.write("Sélectionnez votre profil et saisissez votre performance pour simuler votre taux d'atteinte.")

st.divider()

# Création de deux colonnes pour le formulaire
col1, col2 = st.columns(2)

with col1:
    courbe_selectionnee = st.selectbox(
        "1. Type de Courbe / Profil",
        ["Standard", "Manager", "Manager IS", "Inside Sales"]
    )

with col2:
    # Saisie en pourcentage (ex: 95.5)
    tr_saisi = st.number_input(
        "2. Taux de Performance (TR en %)",
        min_value=0.0,
        max_value=500.0,
        value=100.0,
        step=1.0,
        help="Entrez votre performance. Exemple : 105 pour 105%"
    )

# Conversion du pourcentage saisi en valeur décimale pour le calcul
tr_decimal = tr_saisi / 100.0

# Calcul dynamique selon la courbe choisie
if courbe_selectionnee == "Standard":
    resultat = calcul_standard(tr_decimal)
elif courbe_selectionnee == "Manager":
    resultat = calcul_manager(tr_decimal)
elif courbe_selectionnee == "Manager IS":
    resultat = calcul_manager_is(tr_decimal)
elif courbe_selectionnee == "Inside Sales":
    resultat = calcul_inside_sales(tr_decimal)

st.divider()

# --- AFFICHAGE DU RÉSULTAT ---
st.subheader("🎯 Résultat du calcul")

# Affichage sous forme de "Card" métrique
st.metric(
    label=f"Taux d'Atteinte Final ({courbe_selectionnee})",
    value=f"{resultat:.2%}"
)

# Petit message d'explication contextuel
if resultat == 0.0:
    st.error("⚠️ Vous êtes en dessous du seuil minimum de déclenchement (0%).")
elif tr_decimal >= 1.0:
    st.success("🚀 Félicitations, les objectifs sont atteints ou dépassés !")
else:
    st.info("📉 Objectifs partiellement atteints.")
