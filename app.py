import streamlit as st
import pandas as pd
from pyairtable import Api
import io

# Config
st.set_page_config(page_title="Ops Variable Engine", page_icon="💎", layout="wide")

# Connexion
TOKEN_AIRTABLE = st.secrets["AIRTABLE_API_KEY"]
BASE_ID_AIRTABLE = st.secrets["AIRTABLE_BASE_ID"]

api = Api(TOKEN_AIRTABLE)
table_collaborateurs = api.table(BASE_ID_AIRTABLE, "Collaborateurs")
table_performances = api.table(BASE_ID_AIRTABLE, "Performances")

# Dictionnaire de traduction des mois pour l'UI
NOM_DES_MOIS = {
    1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars", 4: "04 - Avril",
    5: "05 - Mai", 6: "06 - Juin", 7: "07 - Juillet", 8: "08 - Août",
    9: "09 - Septembre", 10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre"
}

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

# --- CHARGEMENT DATA VIA MATRICULE ---
@st.cache_data(ttl=10)
def load_airtable_data():
    collabs = [r["fields"] for r in table_collaborateurs.all()]
    df_c = pd.DataFrame(collabs)
    perfs = [r["fields"] for r in table_performances.all()]
    if not perfs:
        return df_c, pd.DataFrame()
    df_p = pd.DataFrame(perfs)
    # Liaison robuste sécurisée sur le Matricule
    return df_c, pd.merge(df_p, df_c, on="Matricule", how="left")

# --- UI ---
st.title("💎 Ops Compensation Intelligence (v2.0)")
page = st.sidebar.radio("Menu", ["📊 Dashboard & Projections", "📤 Importer les données", "👥 Liste des Équipes"])

df_collabs, df_historique = load_airtable_data()

# --- PAGE : DASHBOARD ---
if page == "📊 Dashboard & Projections":
    st.subheader("🎯 Suivi et Atterrissage Budgétaire")
    
    if df_historique.empty or "Objectif" not in df_historique.columns:
        st.info("Aucune donnée de performance. Allez dans l'onglet 'Importer les données'.")
    else:
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]
        
        # Traduction numérique -> Texte pour l'affichage de l'utilisateur
        df_historique['Nom du Mois'] = df_historique['Mois'].map(NOM_DES_MOIS)
        
        dernier_mois = int(df_historique['Mois'].max())
        df_synthese = df_historique.groupby(['Matricule', 'Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%']).agg({'À Verser (€)': 'sum'}).reset_index()
        
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
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Dernier Mois Traité", NOM_DES_MOIS[dernier_mois])
        k2.metric("Total Versé YTD", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k3.metric("Atterrissage Annuel Estimé", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        
        # Pivot Horizontal basé sur le Nom du Mois textuel
        df_pivot = df_historique.pivot_table(index=['Matricule', 'Nom', 'Prénom', 'Courbe', 'Périodicité'], columns='Nom du Mois', values='À Verser (€)', aggfunc='sum').fillna(0)
        df_pivot = df_pivot.reset_index()
        
        df_final = pd.merge(df_pivot, df_synthese[['Matricule', 'Atterrissage Décembre Estimé (€)']], on='Matricule')
        
        st.write("")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique")
        
        formats = {col: '{:,.2f} €' for col in df_final.columns if 'Janvier' in col or 'Février' in col or 'Mars' in col or 'Avril' in col or 'Mai' in col or 'Juin' in col or 'Juillet' in col or 'Août' in col or 'Septembre' in col or 'Octobre' in col or 'Novembre' in col or 'Décembre' in col or 'Atterrissage' in col}
        
        # Utilisation de background_gradient uniquement si matplotlib est installé
        try:
            st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=[c for c in df_final.columns if 'Mois' in c or '0' in c]), use_container_width=True)
        except:
            st.dataframe(df_final.style.format(formats), use_container_width=True)

# --- PAGE : IMPORTER ---
elif page == "📤 Importer les données":
    st.subheader("📥 Charger un mois de performance")
    mois_select = st.slider("Mois de l'import", 1, 12, 1)
    
    # Masque basé sur le matricule sécurisé
    mask_data = {
        "Matricule": df_collabs["Matricule"].tolist(),
        "Nom": df_collabs["Nom"].tolist(),
        "Prénom": df_collabs["Prénom"].tolist(),
        "Objectif": [0]*len(df_collabs),
        "Réalisation": [0]*len(df_collabs)
    }
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        pd.DataFrame(mask_data).to_excel(w, index=False)
        
    st.download_button(f"📥 Télécharger le masque (Mois : {NOM_DES_MOIS[mois_select]})", data=buf.getvalue(), file_name=f"masque_mois_{mois_select}.xlsx")
    
    file = st.file_uploader("Déposez le fichier Excel complété", type=["xlsx"])
    if file and st.button("💾 Sauvegarder dans Airtable"):
        df_up = pd.read_excel(file)
        records = []
        for _, row in df_up.iterrows():
            records.append({
                "Matricule": str(row["Matricule"]),
                "Mois": int(mois_select),
                "Objectif": float(row["Objectif"]),
                "Réalisation": float(row["Réalisation"])
            })
        table_performances.batch_create(records)
        st.cache_data.clear()
        st.success(f"🎉 Données enregistrées pour {NOM_DES_MOIS[mois_select]} !")

# --- PAGE : LISTE ---
elif page == "👥 Liste des Équipes":
    st.subheader("Référentiel Collaborateurs")
    st.dataframe(df_collabs[['Matricule', 'Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%']], use_container_width=True)
