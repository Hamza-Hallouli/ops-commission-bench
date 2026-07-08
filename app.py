import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Calculateur de Commissions", page_icon="💶", layout="centered")

# --- MOTEURS DE CALCUL (LOGIQUE MÉTIER REVISITÉE) ---
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
    elif tr < 1.40: return tr * 1.40 # Correction mineure par rapport à la borne 1.50
    elif tr < 1.72: return tr * 1.50
    else: return 2.50

# --- INTERFACE FRONTIÈRE ---
st.title("💶 Calculateur de Paie Variable")
st.write("Saisissez l'objectif, le réalisé et le montant cible pour obtenir le montant de la prime.")

st.divider()

# Section 1 : Configuration du profil
courbe_selectionnee = st.selectbox(
    "📊 Choix du profil de courbe",
    ["Standard", "Manager", "Manager IS", "Inside Sales"]
)

st.subheader("🔢 Données de Performance")
col1, col2, col3 = st.columns(3)

with col1:
    objectif = st.number_input("Objectif (Chiffre)", min_value=1.0, value=10000.0, step=100.0)
with col2:
    realise = st.number_input("Réalisation (Chiffre)", min_value=0.0, value=9500.0, step=100.0)
with col3:
    prime_target = st.number_input("Prime Target à 100% (€)", min_value=0.0, value=2000.0, step=50.0)

# --- CALCULS INTERNES ---
# 1. Calcul du TR automatique
tr_decimal = realise / objectif

# 2. Application de la courbe pour trouver le taux d'atteinte
if courbe_selectionnee == "Standard":
    taux_atteinte = calcul_standard(tr_decimal)
elif courbe_selectionnee == "Manager":
    taux_atteinte = calcul_manager(tr_decimal)
elif courbe_selectionnee == "Manager IS":
    taux_atteinte = calcul_manager_is(tr_decimal)
elif courbe_selectionnee == "Inside Sales":
    taux_atteinte = calcul_inside_sales(tr_decimal)

# 3. Calcul du variable final
variable_final = prime_target * taux_atteinte

st.divider()

# --- PANNEAU DES RÉSULTATS (KPIs) ---
st.subheader("🎯 Résultats du Calcul")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric(label="Taux de Performance (TR)", value=f"{tr_decimal:.2%}")
with c2:
    st.metric(label="Taux d'Atteinte Final", value=f"{taux_atteinte:.2%}")
with c3:
    st.metric(label="Variable à Verser", value=f"{variable_final:,.2f} €")

# Messages d'alerte et de contexte RH
if tr_decimal < 1.0:
    st.warning(f"Performance en dessous de l'objectif ({tr_decimal:.1%}). Prime partiellement débloquée.")
elif tr_decimal == 1.0:
    st.success("Objectif exactement atteint. 100% de la prime versée.")
else:
    st.balloons()
    st.success(f"Surperformance ({tr_decimal:.1%}) ! Application des accélérateurs.")
