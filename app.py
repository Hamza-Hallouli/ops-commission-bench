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

# Dictionnaire des mois
NOM_DES_MOIS = {
    1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars", 4: "04 - Avril",
    5: "05 - Mai", 6: "06 - Juin", 7: "07 - Juillet", 8: "08 - Août",
    9: "09 - Septembre", 10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre"
}

# --- MOTEURS DE CALCUL ---
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

def calculer_ligne(row):
    try:
        obj = float(row.get('Objectif', 0))
        real = float(row.get('Réalisation', 0))
        target = float(row.get('Prime Target 100%', 0))
        courbe = str(row.get('Courbe', '')).strip()
        if obj <= 0: return 0.0, 0.0, 0.0
        tr = real / obj
        
        if courbe == "Standard": atteinte = calcul_standard(tr)
        elif courbe == "Manager": atteinte = calcul_manager(tr)
        elif courbe == "Manager IS": atteinte = calcul_manager_is(tr)
        elif courbe == "Inside Sales": atteinte = calcul_inside_sales(tr)
        else: atteinte = 0.0
            
        return tr, atteinte, (target * atteinte)
    except:
        return 0.0, 0.0, 0.0

# --- CHARGEMENT DATA SÉCURISÉ ---
@st.cache_data(ttl=2)
def load_airtable_data():
    df_c = pd.DataFrame([r["fields"] for r in table_collaborateurs.all()])
    df_p = pd.DataFrame([r["fields"] for r in table_performances.all()])
    if df_c.empty: return pd.DataFrame(), pd.DataFrame()
    
    # Sécurité si les nouvelles colonnes sont vides / absentes
    if "Team" not in df_c.columns: df_c["Team"] = "Non assigné"
    if "Manager" not in df_c.columns: df_c["Manager"] = "Non assigné"
    df_c["Team"] = df_c["Team"].fillna("Non assigné")
    df_c["Manager"] = df_c["Manager"].fillna("Non assigné")
    
    if "Matricule" not in df_c.columns: df_c["Matricule"] = ""
    if not df_p.empty and "Matricule" not in df_p.columns: df_p["Matricule"] = ""
    if df_p.empty or "Nom" not in df_p.columns: return df_c, pd.DataFrame()
    if "Matricule" in df_p.columns: df_p = df_p.drop(columns=["Matricule"])
    
    df_global = pd.merge(df_p, df_c, on="Nom", how="left")
    return df_c, df_global

# --- LOGIQUE INTERFACE ---
st.title("💎 Ops Compensation Intelligence")
page = st.sidebar.radio("Menu", ["📊 Dashboard & Projections", "📤 Importer les données", "👥 Liste des Équipes"])

df_collabs, df_historique = load_airtable_data()

if df_collabs.empty:
    st.warning("⚠️ Votre table 'Collaborateurs' est vide.")
    st.stop()

# --- PAGE : DASHBOARD ---
if page == "📊 Dashboard & Projections":
    
    # BARRE DE FILTRES OPS (SIDEBAR)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎛️ Filtres du Dashboard")
    
    teams_dispos = ["Toutes"] + list(df_collabs["Team"].unique())
    team_filtre = st.sidebar.selectbox("Filtrer par Team :", teams_dispos)
    
    managers_dispos = ["Tous"] + list(df_collabs["Manager"].unique())
    manager_filtre = st.sidebar.selectbox("Filtrer par Manager :", managers_dispos)

    if df_historique.empty or "Objectif" not in df_historique.columns:
        st.info("💡 Aucune donnée de performance. Utilisez l'onglet d'importation.")
    else:
        # Calculs métiers
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]
        df_historique['Nom du Mois'] = df_historique['Mois'].map(NOM_DES_MOIS)
        
        dernier_mois = int(df_historique['Mois'].max())
        
        # --- APPLICATION DES FILTRES ---
        df_visu = df_historique.copy()
        if team_filtre != "Toutes":
            df_visu = df_visu[df_visu["Team"] == team_filtre]
        if manager_filtre != "Tous":
            df_visu = df_visu[df_visu["Manager"] == manager_filtre]
            
        if df_visu.empty:
            st.warning("⚠️ Aucun résultat pour les filtres sélectionnés.")
            st.stop()

        # Synthèse Individuelle filtrée
        df_synthese = df_visu.groupby(['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%', 'Team', 'Manager']).agg({
            'À Verser (€)': 'sum', 'Objectif': 'sum', 'Réalisation': 'sum'
        }).reset_index()
        
        # Calcul Taux Atteinte Global Période
        df_synthese['Taux Réal Global (%)'] = df_synthese['Réalisation'] / df_synthese['Objectif']
        
        projections = []
        for idx, row in df_synthese.iterrows():
            deja_paye = row['À Verser (€)']
            target = row['Prime Target 100%']
            if row['Périodicité'] == 'Mensuel':
                mois_restants = max(0, 12 - dernier_mois)
                perf_moyenne = deja_paye / (target * dernier_mois) if deja_paye > 0 else 1.0
                projections.append(deja_paye + (mois_restants * (target * perf_moyenne)))
            else:
                trimestres_passes = max(1, dernier_mois // 3)
                trimestres_restants = max(0, 4 - trimestres_passes)
                perf_trim_moyenne = deja_paye / (target * trimestres_passes) if deja_paye > 0 else 1.0
                projections.append(deja_paye + (trimestres_restants * (target * perf_trim_moyenne)))
                
        df_synthese["Atterrissage Décembre Estimé (€)"] = projections
        
        # KPIS GENERAUX FILTRÉS
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Période active max", NOM_DES_MOIS.get(dernier_mois, str(dernier_mois)))
        k2.metric("Total Versé YTD (Sélection)", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k3.metric("Atterrissage Estimé (Sélection)", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        k4.metric("Ø Réalisation (Sélection)", f"{df_synthese['Taux Réal Global (%)'].mean() * 100:.1f} %")
        
        # --- SECTION ANALYSE D'ÉQUIPE (TEAM AGGREGATION) ---
        st.write("---")
        st.markdown("### 📊 Performance Groupée par Team")
        df_team_perf = df_visu.groupby(['Team']).agg({
            'Objectif': 'sum',
            'Réalisation': 'sum',
            'À Verser (€)': 'sum'
        }).reset_index()
        df_team_perf['Taux Atteinte Global'] = df_team_perf['Réalisation'] / df_team_perf['Objectif']
        
        # Formatage rapide pour le tableau d'équipe
        df_team_show = df_team_perf.rename(columns={
            'Objectif': 'Total Objectifs (€)',
            'Réalisation': 'Total Réalisations (€)',
            'À Verser (€)': 'Variable Total Généré (€)',
            'Taux Atteinte Global': 'Taux Atteinte Global (%)'
        })
        st.dataframe(df_team_show.style.format({
            'Total Objectifs (€)': '{:,.2f} €',
            'Total Réalisations (€)': '{:,.2f} €',
            'Variable Total Généré (€)': '{:,.2f} €',
            'Taux Atteinte Global (%)': lambda x: f"{x*100:.1f} %"
        }), use_container_width=True)

        # --- SECTION ANALYSE INDIVIDUELLE ---
        st.write("---")
        st.markdown("### 🔍 Focus Analyse Individuelle")
        sales_selectionne = st.selectbox("Sélectionner un collaborateur :", df_synthese['Nom'].unique())
        df_sales = df_visu[df_visu['Nom'] == sales_selectionne].sort_values(by="Mois")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Détails de l'année pour {sales_selectionne} :**")
            for _, r in df_sales.iterrows():
                st.info(f"**{r['Nom du Mois']}** : \n"
                        f"* Objectif : {r['Objectif']:,.2f} € | Réal : {r['Réalisation']:,.2f} €\n"
                        f"* **Taux d'Atteinte : {r['TR']*100:.1f} %** | Variable : {r['À Verser (€)']:,.2f} €")
        with col2:
            st.markdown("**Comparatif Graphique Objectif vs Réalisation**")
            st.bar_chart(df_sales.set_index('Nom du Mois')[['Objectif', 'Réalisation']])
            
        # --- GRAND TABLEAU CHRONOLOGIQUE ---
        st.write("---")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique")
        df_pivot = df_visu.pivot_table(index=['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité'], columns='Nom du Mois', values='À Verser (€)', aggfunc='sum').fillna(0).reset_index()
        
        df_final = pd.merge(df_pivot, df_synthese[['Nom', 'Objectif', 'Réalisation', 'Taux Réal Global (%)', 'Atterrissage Décembre Estimé (€)']], on='Nom')
        df_final = df_final.rename(columns={'Objectif': 'Cumul Objectifs (€)', 'Réalisation': 'Cumul Réalisations (€)'})
        
        formats = {}
        for col in df_final.columns:
            if 'Global (%)' in col: formats[col] = lambda x: f"{x*100:.1f} %"
            elif any(m in col for m in ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre','Estimé','Objectif','Réalisation']):
                formats[col] = '{:,.2f} €'
                
        try:
            st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=[c for c in df_final.columns if any(char.isdigit() for char in c)]), use_container_width=True)
        except:
            st.dataframe(df_final.style.format(formats), use_container_width=True)

# --- PAGE : IMPORTER ---
elif page == "📤 Importer les données":
    st.subheader("📥 Centralisation des Imports (Simple ou Multi-mois)")
    
    mois_actuel = datetime.now().month
    mask_rows = []
    for _, col in df_collabs.iterrows():
        for m in range(1, mois_actuel + 1):
            mask_rows.append({
                "Nom": col["Nom"],
                "Prénom": col["Prénom"],
                "Mois (Chiffre de 1 à 12)": m,
                "Objectif": 0.0,
                "Réalisation": 0.0
            })
            
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        pd.DataFrame(mask_rows).to_excel(w, index=False)
        
    st.download_button("📥 Télécharger le Masque d'Import (Excel)", data=buf.getvalue(), file_name="masque_performances.xlsx")
    
    st.write("---")
    file = st.file_uploader("Déposez le fichier Excel complété", type=["xlsx"])
    
    if file and st.button("💾 Sauvegarder dans Airtable"):
        df_up = pd.read_excel(file)
        if "Mois" in df_up.columns and "Mois (Chiffre de 1 à 12)" not in df_up.columns:
            df_up = df_up.rename(columns={"Mois": "Mois (Chiffre de 1 à 12)"})
            
        required_cols = ["Nom", "Mois (Chiffre de 1 à 12)", "Objectif", "Réalisation"]
        if not all(c in df_up.columns for c in required_cols):
            st.error(f"⚠️ Le fichier doit contenir : {', '.join(required_cols)}")
        else:
            records = []
            for idx, row in df_up.iterrows():
                try:
                    m = int(row["Mois (Chiffre de 1 à 12)"])
                    obj = float(row["Objectif"])
                    real = float(row["Réalisation"])
                    if obj == 0.0 and real == 0.0: continue
                    if 1 <= m <= 12:
                        records.append({"Nom": str(row["Nom"]), "Mois": m, "Objectif": obj, "Réalisation": real})
                except:
                    continue
            if records:
                table_performances.batch_create(records)
                st.cache_data.clear()
                st.success(f"🎉 {len(records)} lignes enregistrées !")

# --- PAGE : LISTE ---
elif page == "👥 Liste des Équipes":
    st.subheader("Référentiel Collaborateurs")
    st.dataframe(df_collabs[['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité', 'Prime Target 100%']], use_container_width=True)
