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

# --- CHARGEMENT DATA ---
@st.cache_data(ttl=2)
def load_airtable_data():
    df_c = pd.DataFrame([r["fields"] for r in table_collaborateurs.all()])
    df_p = pd.DataFrame([r["fields"] for r in table_performances.all()])
    if df_c.empty: return pd.DataFrame(), pd.DataFrame()
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
    st.subheader("🎯 Suivi et Atterrissage Budgétaire")
    
    if df_historique.empty or "Objectif" not in df_historique.columns:
        st.info("💡 Aucune donnée de performance. Utilisez l'onglet d'importation.")
    else:
        res = df_historique.apply(calculer_ligne, axis=1)
        df_historique['TR'] = [r[0] for r in res]
        df_historique['Atteinte'] = [r[1] for r in res]
        df_historique['À Verser (€)'] = [r[2] for r in res]
        df_historique['Nom du Mois'] = df_historique['Mois'].map(NOM_DES_MOIS)
        
        dernier_mois = int(df_historique['Mois'].max())
        
        df_synthese = df_historique.groupby(['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%']).agg({
            'À Verser (€)': 'sum', 'Objectif': 'mean', 'Réalisation': 'mean', 'TR': 'mean'
        }).reset_index()
        
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
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Dernier Mois Traité", NOM_DES_MOIS.get(dernier_mois, str(dernier_mois)))
        k2.metric("Total Versé YTD", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k3.metric("Atterrissage Annuel Estimé", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        k4.metric("Taux Réalisation Moyen Équipe", f"{df_synthese['TR'].mean() * 100:.1f} %")
        
        # Focus Analyse Individuelle
        st.write("---")
        st.markdown("### 🔍 Focus Analyse Individuelle")
        sales_selectionne = st.selectbox("Sélectionner un collaborateur :", df_synthese['Nom'].unique())
        df_sales = df_historique[df_historique['Nom'] == sales_selectionne].sort_values(by="Mois")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Indicateurs pour {sales_selectionne} :**")
            for _, r in df_sales.iterrows():
                st.info(f"**{r['Nom du Mois']}** : \n"
                        f"* Objectif : {r['Objectif']:,.2f} € | Réal : {r['Réalisation']:,.2f} €\n"
                        f"* **Taux d'Atteinte : {r['TR']*100:.1f} %** | Variable : {r['À Verser (€)']:,.2f} €")
        with col2:
            st.markdown("**Comparatif Graphique Objectif vs Réalisation**")
            st.bar_chart(df_sales.set_index('Nom du Mois')[['Objectif', 'Réalisation']])
            
        # Tableau Global
        st.write("---")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique")
        df_pivot = df_historique.pivot_table(index=['Nom', 'Prénom', 'Courbe', 'Périodicité'], columns='Nom du Mois', values='À Verser (€)', aggfunc='sum').fillna(0).reset_index()
        df_final = pd.merge(df_pivot, df_synthese[['Nom', 'Objectif', 'Réalisation', 'TR', 'Atterrissage Décembre Estimé (€)']], on='Nom')
        df_final = df_final.rename(columns={'Objectif': 'Ø Objectif (€)', 'Réalisation': 'Ø Réalisation (€)', 'TR': 'Ø Taux Réal (%)'})
        
        formats = {}
        for col in df_final.columns:
            if 'Taux' in col: formats[col] = lambda x: f"{x*100:.1f} %"
            elif any(m in col for m in ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre','Estimé','Objectif','Réalisation']):
                formats[col] = '{:,.2f} €'
                
        try:
            st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=[c for c in df_final.columns if any(char.isdigit() for char in c)]), use_container_width=True)
        except:
            st.dataframe(df_final.style.format(formats), use_container_width=True)

# --- PAGE : IMPORTER (MISE À JOUR MULTI-MOIS) ---
elif page == "📤 Importer les données":
    st.subheader("📥 Centralisation des Imports (Simple ou Multi-mois)")
    st.markdown("""
    💡 **Nouveauté** : Vous pouvez importer plusieurs mois d'un coup. Le fichier généré ci-dessous contient 
    automatiquement des lignes pour chaque commercial, du **Mois 1 (Janvier) au mois actuel**. 
    Remplissez simplement les lignes des mois concernés et laissez les autres à 0 ou supprimez-les.
    """)
    
    # Génération intelligente du masque multi-lignes (Mois 1 jusqu'au mois actuel)
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
        
    st.download_button("📥 Télécharger le nouveau Masque Multi-mois (Excel)", data=buf.getvalue(), file_name="masque_multi_mois_performances.xlsx")
    
    st.write("---")
    file = st.file_uploader("Déposez le fichier Excel complété (Multi-mois ou mensuel)", type=["xlsx"])
    
    if file and st.button("💾 Sauvegarder toutes les données dans Airtable"):
        df_up = pd.read_excel(file)
        
        # Gestion de la flexibilité des noms de colonnes
        if "Mois" in df_up.columns and "Mois (Chiffre de 1 à 12)" not in df_up.columns:
            df_up = df_up.rename(columns={"Mois": "Mois (Chiffre de 1 à 12)"})
            
        required_cols = ["Nom", "Mois (Chiffre de 1 à 12)", "Objectif", "Réalisation"]
        
        if not all(c in df_up.columns for c in required_cols):
            st.error(f"⚠️ Le fichier doit contenir au minimum les colonnes : {', '.join(required_cols)}")
        else:
            records = []
            for idx, row in df_up.iterrows():
                try:
                    m = int(row["Mois (Chiffre de 1 à 12)"])
                    obj = float(row["Objectif"])
                    real = float(row["Réalisation"])
                    
                    # On ignore les lignes restées à 0 pour ne pas polluer Airtable inutilement
                    if obj == 0.0 and real == 0.0:
                        continue
                        
                    if 1 <= m <= 12:
                        records.append({
                            "Nom": str(row["Nom"]),
                            "Mois": m,
                            "Objectif": obj,
                            "Réalisation": real
                        })
                except:
                    continue
            
            if records:
                table_performances.batch_create(records)
                st.cache_data.clear()
                st.success(f"🎉 Succès ! {len(records)} lignes de performances ont été injectées dans Airtable.")
            else:
                st.warning("⚠️ Aucune donnée modifiée détectée (toutes les lignes étaient à 0).")

# --- PAGE : LISTE ---
elif page == "👥 Liste des Équipes":
    st.subheader("Référentiel Collaborateurs")
    st.dataframe(df_collabs[['Nom', 'Prénom', 'Courbe', 'Périodicité', 'Prime Target 100%', 'Matricule']], use_container_width=True)
