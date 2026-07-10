import streamlit as st
import pandas as pd
from pyairtable import Api
import io
import requests  # Pour capturer proprement les refus d'Airtable
from datetime import datetime

# Config de l'application
st.set_page_config(page_title="Ops Variable Engine", page_icon="💎", layout="wide")

# Connexion sécurisée à Airtable via tes Secrets Streamlit
TOKEN_AIRTABLE = st.secrets["AIRTABLE_API_KEY"]
BASE_ID_AIRTABLE = st.secrets["AIRTABLE_BASE_ID"]

api = Api(TOKEN_AIRTABLE)
table_collaborateurs = api.table(BASE_ID_AIRTABLE, "Collaborateurs")
table_performances = api.table(BASE_ID_AIRTABLE, "Performances")

# Ordre d'affichage chronologique des mois et trimestres
ORDRE_PERIODES = ["1", "2", "3", "Q1", "4", "5", "6", "Q2", "7", "8", "9", "Q3", "10", "11", "12", "Q4"]

# --- MOTEURS DE CALCUL DE COURBE CORRIGÉS AU MM PRÈS SELON TES IMAGES ---
def calcul_standard(tr):
    if tr < 0.50: return tr * 0.40
    elif tr < 0.90: return tr * tr * 0.80
    elif tr < 1.00: return tr * tr * 0.95
    elif tr < 1.91: return tr * tr * 1.10
    else: return 4.00  # Cap à 400% au-delà de 191%

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
    else: return 2.50  # Cap à 250% au-delà de 145%

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
    else: return 2.00  # Cap à 200% au-delà de 155%

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
    else: return 2.50  # Cap à 250% au-delà de 172%

# --- MOTEUR DE PRORATISATION DES LIGNES ---
def calculer_ligne(row):
    try:
        obj = float(row.get('Objectif', 0))
        real = float(row.get('Réalisation', 0))
        target_annuelle = float(row.get('Prime Target 100%', 0))
        courbe = str(row.get('Courbe', '')).strip().lower()
        periode = str(row.get('Période', '')).strip()
        
        if obj <= 0 or pd.isna(row.get('Période')) or periode in ["", "None", "nan", "Non assigné"]: 
            return 0.0, 0.0, 0.0
            
        tr = real / obj
        
        # Dispatching intelligent selon la nomenclature Airtable
        if courbe in ["standard", "standard curve"]: atteinte = calcul_standard(tr)
        elif courbe in ["manager", "plan sales manager"]: atteinte = calcul_manager(tr)
        elif courbe in ["manager is"]: atteinte = calcul_manager_is(tr)
        elif courbe in ["is", "is curve", "inside sales", "standard is curve"]: atteinte = calcul_inside_sales(tr)
        else: atteinte = 0.0
        
        # Règle de proratisation Target Annuelle
        if "Q" in periode: target_proratisee = target_annuelle / 4.0
        else: target_proratisee = target_annuelle / 12.0
            
        return tr, atteinte, (target_proratisee * atteinte)
    except:
        return 0.0, 0.0, 0.0

# --- CHARGEMENT SÉCURISÉ DES DONNÉES ---
@st.cache_data(ttl=2)
def load_airtable_data():
    df_c = pd.DataFrame([r["fields"] for r in table_collaborateurs.all()])
    df_p = pd.DataFrame([r["fields"] for r in table_performances.all()])
    
    if df_c.empty: return pd.DataFrame(), pd.DataFrame()
    
    for col in ["Team", "Manager", "Courbe", "Périodicité", "Nom", "Prénom", "Matricule"]:
        if col not in df_c.columns: df_c[col] = "Non assigné"
        df_c[col] = df_c[col].fillna("Non assigné")
        
    if "Prime Target 100%" not in df_c.columns: df_c["Prime Target 100%"] = 0.0
    df_c["Prime Target 100%"] = df_c["Prime Target 100%"].fillna(0.0)
    
    if df_p.empty or "Nom" not in df_p.columns: return df_c, pd.DataFrame()
    
    # Nettoyage des doublons de colonnes Airtable
    for c in ["Prénom", "Courbe", "Périodicité", "Prime Target 100%", "Team", "Manager", "Matricule"]:
        if c in df_p.columns: df_p = df_p.drop(columns=[c])
    
    df_global = pd.merge(df_p, df_c, on="Nom", how="left")
    return df_c, df_global

df_collabs, df_historique = load_airtable_data()

if df_collabs.empty:
    st.warning("⚠️ La table 'Collaborateurs' est introuvable ou vide dans Airtable.")
    st.stop()

# --- MENU NAVIGATION (TOUT EST OUVERT) ---
st.title("💎 Ops Compensation Intelligence")
page = st.sidebar.radio("Menu", ["📊 Dashboard & Projections", "🧮 Simulateur & Courbes", "📤 Importer les données", "👥 Liste des Équipes"])

# Traitement global des perfs
if not df_historique.empty and "Objectif" in df_historique.columns:
    df_historique = df_historique.dropna(subset=['Période'])
    df_historique['Période'] = df_historique['Période'].astype(str).str.strip()
    df_historique = df_historique[~df_historique['Période'].isin(["", "None", "nan", "Non assigné"])]
    
    if not df_historique.empty:
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]

# --- PAGE 1 : DASHBOARD ---
if page == "📊 Dashboard & Projections":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Filtres Globaux")
    team_filtre = st.sidebar.selectbox("Team :", ["Toutes"] + list(df_collabs["Team"].unique()))
    manager_filtre = st.sidebar.selectbox("Manager :", ["Tous"] + list(df_collabs["Manager"].unique()))
    
    df_visu = df_historique.copy()
    if not df_visu.empty:
        if team_filtre != "Toutes": df_visu = df_visu[df_visu["Team"] == team_filtre]
        if manager_filtre != "Tous": df_visu = df_visu[df_visu["Manager"] == manager_filtre]

    if df_visu.empty:
        st.info("💡 Aucune donnée de performance enregistrée pour ces filtres. Utilisez l'onglet d'importation.")
    else:
        # Synthèse et Calcul Forecast
        df_synthese = df_visu.groupby(['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%', 'Team', 'Manager']).agg({
            'À Verser (€)': 'sum', 'Objectif': 'sum', 'Réalisation': 'sum'
        }).reset_index()
        df_synthese['TR Moyen (%)'] = df_synthese['Réalisation'] / df_synthese['Objectif']
        
        projections = []
        for idx, row in df_synthese.iterrows():
            deja_paye = row['À Verser (€)']
            target_annuelle = row['Prime Target 100%']
            df_sub = df_visu[df_visu['Nom'] == row['Nom']]
            parts_ecoulees = 0.0
            for p in df_sub['Période'].unique():
                p_str = str(p).strip()
                parts_ecoulees += 0.25 if "Q" in p_str else (1.0 / 12.0)
            parts_restantes = max(0.0, 1.0 - parts_ecoulees)
            target_theorique_passee = target_annuelle * parts_ecoulees
            perf_ratio = deja_paye / target_theorique_passee if target_theorique_passee > 0 else 1.0
            projections.append(deja_paye + (parts_restantes * target_annuelle * perf_ratio))
            
        df_synthese["Atterrissage Décembre Estimé (€)"] = projections
        
        # BANDEAU KPIS GLOBAL
        k1, k
