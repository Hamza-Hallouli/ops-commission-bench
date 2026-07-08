import streamlit as st
import pandas as pd
from pyairtable import Api
import io

# --- 1. CONFIGURATION DE L'APPLICATION ---
st.set_page_config(
    page_title="Ops Variable Engine", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS CUSTOM PREMIUM ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .metric-container {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .stFileUploader {
        border: 2px dashed #4F46E5 !important;
        border-radius: 12px;
        padding: 10px;
        background-color: #FAFAFA;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNEXION SÉCURISÉE AVEC LE JETON AIRTABLE ---
# Récupération automatique du Jeton et de l'ID de base depuis les "Secrets" de Streamlit
TOKEN_AIRTABLE = st.secrets["AIRTABLE_API_KEY"]
BASE_ID_AIRTABLE = st.secrets["AIRTABLE_BASE_ID"]

# Initialisation du client officiel avec le Jeton (PAT)
api = Api(TOKEN_AIRTABLE)
table_collaborateurs = api.table(BASE_ID_AIRTABLE, "Collaborateurs")
table_performances = api.table(BASE_ID_AIRTABLE, "Performances")

# --- 3. MOTEURS DE CALCUL (LES 4 COURBES) ---
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
        obj = float(row['Objectif'])
        real = float(row['Réalisation'])
        target = float(row['Prime Target 100%'])
        courbe = str(row['Courbe']).strip()
        if obj <= 0: return 0.0, 0.0, 0.0
        tr = real / obj
        
        if courbe == "Standard": atteinte = calcul_standard(tr)
        elif courbe == "Manager": atteinte = calcul_manager(tr)
        elif courbe == "Manager IS": atteinte = calcul_manager_is(tr)
        elif courbe == "Inside Sales": atteinte = calcul_inside_sales(tr)
        else: atteinte = 0.0
            
        variable = target * atteinte
        return tr, atteinte, variable
    except:
        return 0.0, 0.0, 0.0

# --- 4. RÉCUPÉRATION DES DONNÉES DEPUIS LE JETON ---
@st.cache_data(ttl=30)
def load_airtable_data():
    collabs = [r["fields"] for r in table_collaborateurs.all()]
    df_c = pd.DataFrame(collabs)
    perfs = [r["fields"] for r in table_performances.all()]
    if not perfs:
        return df_c, pd.DataFrame()
    df_p = pd.DataFrame(perfs)
    return df_c, pd.merge(df_p, df_c, on="Nom", how="left")

# --- 5. INTERFACE ET MENUS ---
st.markdown("<h1 style='text-align: center; color: #1E293B; margin-bottom: 5px;'>💎 Ops Compensation Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748B; font-size: 1.1rem;'>MVP de suivi de paie variable et prévisions budgétaires.</p>", unsafe_allow_html=True)
st.write("")

page = st.sidebar.radio("Navigation MVP", ["📊 Dashboard & Projections", "📤 Importer les données", "👥 Liste des Équipes"])

# Lecture des données via le Token
try:
    df_collabs, df_historique = load_airtable_data()
except Exception as e:
    st.error("⚠️ Impossible de s'authentifier auprès d'Airtable. Vérifiez votre Jeton (PAT) et votre Base ID dans les Secrets Streamlit.")
    st.stop()

# --- PAGE : DASHBOARD & PROJECTIONS ---
if page == "📊 Dashboard & Projections":
    st.subheader("🎯 Suivi et Atterrissage Budgétaire")
    
    if df_historique.empty or "Objectif" not in df_historique.columns:
        st.info("Aucune donnée disponible. Veuillez importer vos premiers fichiers de performance.")
    else:
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]
        
        dernier_mois = int(df_historique['Mois'].max())
        
        # Logique de Forecast (Mensuel vs Trimestriel)
        df_synthese = df_historique.groupby(['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%']).agg({'À Verser (€)': 'sum'}).reset_index()
        
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
        
        # Affichage Macro
        k1, k2, k3 = st.columns(3)
        k1.metric("Statut Période", f"Mois {dernier_mois} / 12 traité")
        k2.metric("Total Versé YTD (Cumulé)", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k3.metric("Atterrissage Annuel Estimé", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        
        # Pivot Horizontal
        df_pivot = df_historique.pivot_table(index=['Nom', 'Prénom', 'Courbe', 'Périodicité'], columns='Mois', values='À Verser (€)', aggfunc='sum').fillna(0)
        df_pivot.columns = [f"Mois {int(c)} (€)" for c in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        df_final = pd.merge(df_pivot, df_synthese[['Nom', 'Prénom', 'Atterrissage Décembre Estimé (€)']], on=['Nom', 'Prénom'])
        
        st.write("")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique")
        
        formats = {col: '{:,.2f} €' for col in df_final.columns if 'Mois' in col or '€' in col or 'Atterrissage' in col}
        st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=[c for c in df_final.columns if 'Mois' in c]), use_container_width=True)

# --- PAGE : IMPORTER LES DONNÉES ---
elif page == "📤 Importer les données":
    st.subheader("📥 Importer les réalisations du mois")
    mois_select = st.slider("Sélectionnez le mois de l'import", 1, 12, 1)
    
    if mois_select in [3, 6, 9, 12]:
        st.info(f"💡 Fin du trimestre détectée (Mois {mois_select}). Vos collaborateurs trimestriels seront calculés sur cet import.")
        
    mask_data = {"Nom": df_collabs["Nom"].tolist(), "Prénom": df_collabs["Prénom"].tolist(), "Objectif": [0]*len(df_collabs), "Réalisation": [0]*len(df_collabs)}
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        pd.DataFrame(mask_data).to_excel(w, index=False)
        
    st.download_button(f"📥 Télécharger le masque pré-rempli (Mois {mois_select})", data=buf.getvalue(), file_name=f"masque_mois_{mois_select}.xlsx")
    
    file = st.file_uploader("Déposez le fichier Excel rempli ici", type=["xlsx"])
    if file and st.button("💾 Enregistrer définitivement dans Airtable via Jeton"):
        df_up = pd.read_excel(file)
        records = []
        for _, row in df_up.iterrows():
            records.append({
                "Nom": str(row["Nom"]),
                "Mois": int(mois_select),
                "Objectif": float(row["Objectif"]),
                "Réalisation": float(row["Réalisation"])
            })
        # Envoi sécurisé par lots vers Airtable
        table_performances.batch_create(records)
        st.cache_data.clear()
        st.success("🎉 Données synchronisées avec succès dans la base de données via ton jeton d'accès !")

# --- PAGE : LISTE DES ÉQUIPES ---
elif page == "👥 Liste des Équipes":
    st.subheader("Référentiel Collaborateurs Actifs")
    st.dataframe(df_collabs[['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%']], use_container_width=True)
