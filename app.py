import streamlit as st
import pandas as pd
from pyairtable import Api
import io
from datetime import datetime

# Config de l'application
st.set_page_config(page_title="Ops Variable Engine", page_icon="💎", layout="wide")

# Connexion sécurisée
TOKEN_AIRTABLE = st.secrets["AIRTABLE_API_KEY"]
BASE_ID_AIRTABLE = st.secrets["AIRTABLE_BASE_ID"]

api = Api(TOKEN_AIRTABLE)
table_collaborateurs = api.table(BASE_ID_AIRTABLE, "Collaborateurs")
table_performances = api.table(BASE_ID_AIRTABLE, "Performances")

# Ordre d'affichage logique des périodes dans le tableau de bord
ORDRE_PERIODES = [
    "1", "2", "3", "Q1", 
    "4", "5", "6", "Q2", 
    "7", "8", "9", "Q3", 
    "10", "11", "12", "Q4"
]

# --- MOTEURS DE CALCUL DE COURBE ---
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

# --- CALCUL DES LIGNES AVEC PRORATISATION TARGET ANNUELLE ---
def calculer_ligne(row):
    try:
        obj = float(row.get('Objectif', 0))
        real = float(row.get('Réalisation', 0))
        target_annuelle = float(row.get('Prime Target 100%', 0))
        courbe = str(row.get('Courbe', '')).strip()
        periode = str(row.get('Période', '')).strip()
        
        if obj <= 0 or pd.isna(row.get('Période')) or periode in ["", "None", "nan", "Non assigné"]: 
            return 0.0, 0.0, 0.0
            
        tr = real / obj
        
        # Choix de la courbe
        if courbe == "Standard": atteinte = calcul_standard(tr)
        elif courbe == "Manager": atteinte = calcul_manager(tr)
        elif courbe == "Manager IS": atteinte = calcul_manager_is(tr)
        elif courbe == "Inside Sales": atteinte = calcul_inside_sales(tr)
        else: atteinte = 0.0
        
        # Application de la règle de proratisation sur la Target Annuelle
        if "Q" in periode:
            target_proratisee = target_annuelle / 4.0
        else:
            target_proratisee = target_annuelle / 12.0
            
        return tr, atteinte, (target_proratisee * atteinte)
    except:
        return 0.0, 0.0, 0.0

# --- CHARGEMENT DATA SÉCURISÉ ---
@st.cache_data(ttl=2)
def load_airtable_data():
    df_c = pd.DataFrame([r["fields"] for r in table_collaborateurs.all()])
    df_p = pd.DataFrame([r["fields"] for r in table_performances.all()])
    
    if df_c.empty: return pd.DataFrame(), pd.DataFrame()
    
    # Nettoyage et fallbacks
    for col in ["Team", "Manager", "Courbe", "Périodicité", "Nom", "Prénom"]:
        if col not in df_c.columns: df_c[col] = "Non assigné"
        df_c[col] = df_c[col].fillna("Non assigné")
        
    if "Prime Target 100%" not in df_c.columns: df_c["Prime Target 100%"] = 0.0
    df_c["Prime Target 100%"] = df_c["Prime Target 100%"].fillna(0.0)

    if df_p.empty or "Nom" not in df_p.columns: return df_c, pd.DataFrame()
    
    # Élimination des conflits de colonnes si elles existent dans les deux bases
    for c in ["Prénom", "Courbe", "Périodicité", "Prime Target 100%", "Team", "Manager", "Matricule"]:
        if c in df_p.columns: df_p = df_p.drop(columns=[c])
        
    df_global = pd.merge(df_p, df_c, on="Nom", how="left")
    return df_c, df_global

# --- UI LOGIQUE ---
st.title("💎 Ops Compensation Intelligence")
page = st.sidebar.radio("Menu", ["📊 Dashboard & Projections", "📤 Importer les données", "👥 Liste des Équipes"])

df_collabs, df_historique = load_airtable_data()

if df_collabs.empty:
    st.warning("⚠️ La table 'Collaborateurs' ne renvoie aucune donnée.")
    st.stop()

# --- PAGE : DASHBOARD ---
if page == "📊 Dashboard & Projections":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Filtres")
    team_filtre = st.sidebar.selectbox("Team :", ["Toutes"] + list(df_collabs["Team"].unique()))
    manager_filtre = st.sidebar.selectbox("Manager :", ["Tous"] + list(df_collabs["Manager"].unique()))

    if df_historique.empty or "Objectif" not in df_historique.columns:
        st.info("💡 Aucune donnée de performance enregistrée. Allez dans l'onglet d'importation.")
    else:
        # Nettoyage préventif des périodes manquantes ou nulles
        df_historique = df_historique.dropna(subset=['Période'])
        df_historique['Période'] = df_historique['Période'].astype(str).str.strip()
        df_historique = df_historique[~df_historique['Période'].isin(["", "None", "nan", "Non assigné"])]
        
        if df_historique.empty:
            st.info("💡 Toutes les lignes de performance actuelles possèdent des périodes vides ou invalides.")
            st.stop()
            
        # Exécuter les calculs métiers
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]
        
        # Filtrage
        df_visu = df_historique.copy()
        if team_filtre != "Toutes": df_visu = df_visu[df_visu["Team"] == team_filtre]
        if manager_filtre != "Tous": df_visu = df_visu[df_visu["Manager"] == manager_filtre]
            
        if df_visu.empty:
            st.warning("Aucune donnée disponible pour ces filtres.")
            st.stop()

        # --- CALCULATE FORECAST / PROJECTIONS ANNUELLES SÉCURISÉES ---
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
                p_str = str(p).strip() if p is not None else ""
                if p_str != "" and p_str != "nan" and p_str != "Non assigné":
                    parts_ecoulees += 0.25 if "Q" in p_str else (1.0 / 12.0)
                
            parts_restantes = max(0.0, 1.0 - parts_ecoulees)
            target_theorique_passee = target_annuelle * parts_ecoulees
            perf_ratio = deja_paye / target_theorique_passee if target_theorique_passee > 0 else 1.0
            
            projections.append(deja_paye + (parts_restantes * target_annuelle * perf_ratio))
            
        df_synthese["Atterrissage Décembre Estimé (€)"] = projections
        
        # BANDEAU KPIS
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Variables Générés YTD", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k2.metric("Atterrissage Budgétaire Annuel", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        k3.metric("O Taux de Réalisation Équipe", f"{df_synthese['TR Moyen (%)'].mean() * 100:.1f} %")
        
        # --- PERFORMANCE PAR TEAM ---
        st.write("---")
        st.markdown("### 📊 Performance par Team")
        df_t = df_visu.groupby(['Team']).agg({'Objectif': 'sum', 'Réalisation': 'sum', 'À Verser (€)': 'sum'}).reset_index()
        df_t['Atteinte globale (%)'] = df_t['Réalisation'] / df_t['Objectif']
        st.dataframe(df_t.style.format({
            'Objectif': '{:,.2f} €', 'Réalisation': '{:,.2f} €', 'À Verser (€)': '{:,.2f} €', 'Atteinte globale (%)': lambda x: f"{x*100:.1f} %"
        }), use_container_width=True)

        # --- DYNAMIC CHRONO PIVOT TABLE ---
        st.write("---")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique (Hybride)")
        
        df_pivot = df_visu.pivot_table(index=['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité'], columns='Période', values='À Verser (€)', aggfunc='sum').fillna(0).reset_index()
        
        # Tri chronologique dynamique
        cols_metiers = [c for c in df_pivot.columns if c in ORDRE_PERIODES]
        cols_metiers_triees = sorted(cols_metiers, key=lambda x: ORDRE_PERIODES.index(x))
        cols_fixes = ['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité']
        df_pivot = df_pivot[cols_fixes + cols_metiers_triees]
        
        df_final = pd.merge(df_pivot, df_synthese[['Nom', 'Objectif', 'Réalisation', 'TR Moyen (%)', 'Atterrissage Décembre Estimé (€)']], on='Nom')
        df_final = df_final.rename(columns={'Objectif': 'Cumul Objectifs (€)', 'Réalisation': 'Cumul Réalisations (€)'})
        
        formats = {}
        for col in df_final.columns:
            if 'Moyen (%)' in col: formats[col] = lambda x: f"{x*100:.1f} %"
            elif col not in cols_fixes: formats[col] = '{:,.2f} €'
                
        try:
            st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=cols_metiers_triees), use_container_width=True)
        except:
            st.dataframe(df_final.style.format(formats), use_container_width=True)

# --- PAGE : IMPORTER ---
elif page == "📤 Importer les données":
    st.subheader("📥 Générateur d'Import Multi-Périodes Automatique")
    st.markdown("""
    L'outil analyse la colonne **Périodicité** de ton équipe :
    * Les profils **Mensuel** reçoivent 12 lignes (Mois 1 à 12).
    * Les profils **Trimestriel** reçoivent 4 lignes (`Q1`, `Q2`, `Q3`, `Q4`).
    """)
    
    mask_rows = []
    for _, col in df_collabs.iterrows():
        periodicite = str(col["Périodicité"]).strip()
        if periodicite == "Trimestriel":
            periodes_target = ["Q1", "Q2", "Q3", "Q4"]
        else:
            periodes_target = [str(i) for i in range(1, 13)]
            
        for p in periodes_target:
            mask_rows.append({
                "Nom": col["Nom"],
                "Prénom": col["Prénom"],
                "Période (Mois ou Q)": p,
                "Objectif": 0.0,
                "Réalisation": 0.0
            })
            
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        pd.DataFrame(mask_rows).to_excel(w, index=False)
        
    st.download_button("📥 Télécharger le modèle Excel Hybride personnalisé", data=buf.getvalue(), file_name="gabarit_import_ops.xlsx")
    
    st.write("---")
    file = st.file_uploader("Déposer le fichier Excel complété", type=["xlsx"])
    
    if file and st.button("💾 Sauvegarder et injecter dans Airtable"):
        df_up = pd.read_excel(file)
        
        if "Période" in df_up.columns and "Période (Mois ou Q)" not in df_up.columns:
            df_up = df_up.rename(columns={"Période": "Période (Mois ou Q)"})
            
        required_cols = ["Nom", "Période (Mois ou Q)", "Objectif", "Réalisation"]
        if not all(c in df_up.columns for c in required_cols):
            st.error(f"Fichier invalide. Les en-têtes requis sont : {', '.join(required_cols)}")
        else:
            records = []
            for idx, row in df_up.iterrows():
                try:
                    p = str(row["Période (Mois ou Q)"]).strip()
                    obj = float(row["Objectif"])
                    real = float(row["Réalisation"])
                    if obj == 0.0 and real == 0.0: continue
                    
                    records.append({
                        "Nom": str(row["Nom"]),
                        "Période": p,
                        "Objectif": obj,
                        "Réalisation": real
                    })
                except:
                    continue
            if records:
                table_performances.batch_create(records)
                st.cache_data.clear()
                st.success(f"🎉 Import réussi ! {len(records)} lignes ajoutées.")

# --- PAGE : LISTE ---
elif page == "👥 Liste des Équipes":
    st.subheader("Référentiel Collaborateurs")
    st.dataframe(df_collabs[['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité', 'Prime Target 100%']], use_container_width=True)
