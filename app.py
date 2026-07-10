import streamlit as st
import pandas as pd
from pyairtable import Api
import io
import requests
from datetime import datetime

# Config de l'application
st.set_page_config(page_title="Ops Variable Engine", page_icon="💎", layout="wide")

# Connexion sécurisée à Airtable
TOKEN_AIRTABLE = st.secrets["AIRTABLE_API_KEY"]
BASE_ID_AIRTABLE = st.secrets["AIRTABLE_BASE_ID"]

api = Api(TOKEN_AIRTABLE)
table_collaborateurs = api.table(BASE_ID_AIRTABLE, "Collaborateurs")
table_performances = api.table(BASE_ID_AIRTABLE, "Performances")

# Ordre d'affichage chronologique des mois et trimestres
ORDRE_PERIODES = ["1", "2", "3", "Q1", "4", "5", "6", "Q2", "7", "8", "9", "Q3", "10", "11", "12", "Q4"]

# --- MOTEURS DE CALCUL DE COURBE ---
def calcul_standard(tr):
    if tr < 0.50: return tr * 0.40
    elif tr < 0.90: return tr * tr * 0.80
    elif tr < 1.00: return tr * tr * 0.95
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

        if courbe in ["standard", "standard curve"]: atteinte = calcul_standard(tr)
        elif courbe in ["manager", "plan sales manager"]: atteinte = calcul_manager(tr)
        elif courbe in ["manager is"]: atteinte = calcul_manager_is(tr)
        elif courbe in ["is", "is curve", "inside sales", "standard is curve"]: atteinte = calcul_inside_sales(tr)
        else: atteinte = 0.0

        if "Q" in periode: target_proratisee = target_annuelle / 4.0
        else: target_proratisee = target_annuelle / 12.0

        return tr, atteinte, (target_proratisee * atteinte)
    except:
        return 0.0, 0.0, 0.0

# --- CHARGEMENT SÉCURISÉ DES DONNÉES (BLINDÉ & CACHE 24H) ---
@st.cache_data(ttl=86400)
def load_airtable_data():
    try:
        df_c = pd.DataFrame([r["fields"] for r in table_collaborateurs.all()])
        df_p = pd.DataFrame([r["fields"] for r in table_performances.all()])
    except Exception as e:
        st.error("⚠️ Connexion à Airtable instable. Veuillez rafraîchir la page.")
        return pd.DataFrame(), pd.DataFrame()

    if df_c.empty: return pd.DataFrame(), pd.DataFrame()

    for col in ["Team", "Manager", "Courbe", "Périodicité", "Nom", "Prénom", "Matricule"]:
        if col not in df_c.columns: df_c[col] = "Non assigné"
        df_c[col] = df_c[col].fillna("Non assigné")

    if "Prime Target 100%" not in df_c.columns: df_c["Prime Target 100%"] = 0.0
    df_c["Prime Target 100%"] = df_c["Prime Target 100%"].fillna(0.0)

    # Nettoyage strict des noms (Tout en majuscule, sans espaces)
    df_c["Nom"] = df_c["Nom"].astype(str).str.strip().str.upper()

    if df_p.empty or "Nom" not in df_p.columns: return df_c, pd.DataFrame()

    for c in ["Prénom", "Courbe", "Périodicité", "Prime Target 100%", "Team", "Manager", "Matricule"]:
        if c in df_p.columns: df_p = df_p.drop(columns=[c])

    # Nettoyage strict pour la table perf
    df_p["Nom"] = df_p["Nom"].astype(str).str.strip().str.upper()

    df_global = pd.merge(df_p, df_c, on="Nom", how="left")
    return df_c, df_global

df_collabs, df_historique = load_airtable_data()

if df_collabs.empty:
    st.warning("⚠️ La table 'Collaborateurs' est introuvable ou vide dans Airtable.")
    st.stop()

# --- MENU NAVIGATION ---
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
        st.info("💡 Aucune donnée de performance enregistrée pour ces filtres.")
    else:
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
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Variables Générés YTD", f"{df_synthese['À Verser (€)'].sum():,.2f} €")
        k2.metric("Atterrissage Budgétaire Annuel", f"{df_synthese['Atterrissage Décembre Estimé (€)'].sum():,.2f} €")
        k3.metric("Ø Taux de Réalisation Équipe", f"{df_synthese['TR Moyen (%)'].mean() * 100:.1f} %")

        st.write("---")
        st.markdown("### 🔍 Focus Analyse Individuelle & Méthodes de calcul")
        sales_selectionne = st.selectbox("Sélectionner un collaborateur :", df_synthese['Nom'].unique())
        df_sales = df_visu[df_visu['Nom'] == sales_selectionne].sort_values(by="Période")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Détails de l'année pour {sales_selectionne} :**")
            for _, r in df_sales.iterrows():
                st.info(f"**Période : {r['Période']}** \n* Objectif : {r['Objectif']:,.2f} € | Réal : {r['Réalisation']:,.2f} €\n* **TR : {r['TR']*100:.1f} %** | Variable : **{r['À Verser (€)']:,.2f} €**")

                with st.expander(f"⚙️ Décomposition mathématique détaillée ({r['Période']})"):
                    base_diviseur = 4.0 if "Q" in str(r['Période']) else 12.0
                    target_prorata = r['Prime Target 100%'] / base_diviseur
                    st.write(f"1. **Enveloppe Période** : {r['Prime Target 100%']:,.2f} € / {int(base_diviseur)} = **{target_prorata:,.2f} €**")
                    st.write(f"2. **Taux Réalisation (TR)** : {r['Réalisation']:,.2f} € / {r['Objectif']:,.2f} € = **{r['TR']*100:.1f}%**")
                    st.write(f"3. **Taux d'Atteinte Courbe** (`{r['Courbe']}`) = **{r['Atteinte']*100:.1f}%**")
                    st.write(f"4. **Calcul Final** : {target_prorata:,.2f} € × {r['Atteinte']*100:.1f}% = **{r['À Verser (€)']:,.2f} €**")
        with col2:
            st.markdown("**Comparatif Graphique Objectif vs Réalisation**")
            st.bar_chart(df_sales.set_index('Période')[['Objectif', 'Réalisation']])

        st.write("---")
        st.markdown("### 📋 Grand Tableau de Bord Chronologique (Hybride)")
        df_pivot = df_visu.pivot_table(index=['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité'], columns='Période', values='À Verser (€)', aggfunc='sum').fillna(0).reset_index()
        cols_metiers = [c for c in df_pivot.columns if c in ORDRE_PERIODES]
        cols_metiers_triees = sorted(cols_metiers, key=lambda x: ORDRE_PERIODES.index(x))
        cols_exotiques = [c for c in df_pivot.columns if c not in ORDRE_PERIODES and c not in ['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité']]
        cols_metiers_totale = cols_metiers_triees + cols_exotiques
        cols_fixes = ['Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité']
        df_pivot = df_pivot[cols_fixes + cols_metiers_totale]

        df_final = pd.merge(df_pivot, df_synthese[['Nom', 'Objectif', 'Réalisation', 'TR Moyen (%)', 'Atterrissage Décembre Estimé (€)']], on='Nom')
        df_final = df_final.rename(columns={'Objectif': 'Cumul Objectifs (€)', 'Réalisation': 'Cumul Réalisations (€)'})
        formats = {col: ('{:,.2f} €' if 'Moyen' not in col else lambda x: f"{x*100:.1f} %") for col in df_final.columns if col not in cols_fixes}
        try:
            st.dataframe(df_final.style.format(formats).background_gradient(cmap="Blues", subset=cols_metiers_totale), use_container_width=True)
        except:
            st.dataframe(df_final.style.format(formats), use_container_width=True)

# --- PAGE 2 : SIMULATEUR INTERACTIF ---
elif page == "🧮 Simulateur & Courbes":
    st.title("🧮 Simulateur de Variable")
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.markdown("### 📐 Paramètres de simulation")
        courbe_sim = st.selectbox("Type de plan de courbe :", ["Plan Sales Manager / Manager", "Standard / Standard Curve", "Inside Sales / IS", "Manager IS"])
        target_sim = st.number_input("Package Variable Annuel à 100% (€) :", value=10000, step=1000)
        p_type = st.radio("Rythme de la période :", ["Mensuelle (1/12)", "Trimestrielle (1/4)"])
        base_prime = target_sim / 4.0 if p_type == "Trimestrielle (1/4)" else target_sim / 12.0
        st.metric("Enveloppe théorique pour cette période", f"{base_prime:,.2f} €")

    with s_col2:
        st.markdown("### 🎯 Performance Fictive")
        obj_sim = st.number_input("Objectif fixé (€) :", value=50000, step=5000)
        real_sim = st.number_input("Réalisation envisagée (€) :", value=55000, step=5000)
        if obj_sim > 0:
            tr_sim = real_sim / obj_sim
            if "Manager" in courbe_sim and "IS" not in courbe_sim: coeff = calcul_manager(tr_sim)
            elif "Standard" in courbe_sim: coeff = calcul_standard(tr_sim)
            elif "Manager IS" in courbe_sim: coeff = calcul_manager_is(tr_sim)
            else: coeff = calcul_inside_sales(tr_sim)

            prime_finale_sim = base_prime * coeff
            c1, c2 = st.columns(2)
            c1.metric("TR Simulé", f"{tr_sim*100:.1f} %")
            c2.metric("Variable simulé à verser", f"{prime_finale_sim:,.2f} €")

# --- PAGE 3 : IMPORT DES DONNÉES ---
elif page == "📤 Importer les données":
    st.title("📥 Import des Performances de l'équipe")

    mask_rows = []
    for _, col in df_collabs.iterrows():
        periodicite = str(col["Périodicité"]).strip()
        periodes_target = ["Q1", "Q2", "Q3", "Q4"] if periodicite == "Trimestriel" else [str(i) for i in range(1, 13)]
        for p in periodes_target:
            mask_rows.append({"Nom": col["Nom"], "Prénom": col["Prénom"], "Période (Mois ou Q)": p, "Objectif": 0.0, "Réalisation": 0.0})

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        pd.DataFrame(mask_rows).to_excel(w, index=False)

    st.download_button("📥 Télécharger le modèle Excel Hybride vierge", data=buf.getvalue(), file_name="gabarit_import_ops.xlsx")

    st.write("---")
    file = st.file_uploader("Déposer votre fichier Excel rempli (.xlsx)", type=["xlsx"])

    if file and st.button("💾 Sauvegarder et Envoyer vers Airtable"):
        df_up = pd.read_excel(file)
        if "Période" in df_up.columns: df_up = df_up.rename(columns={"Période": "Période (Mois ou Q)"})

        records = []
        for idx, row in df_up.iterrows():
            try:
                p = str(row["Période (Mois ou Q)"]).strip()
                if float(row["Objectif"]) == 0.0 and float(row["Réalisation"]) == 0.0: continue
                records.append({
                    "Nom": str(row["Nom"]),
                    "Période": p,
                    "Objectif": float(row["Objectif"]),
                    "Réalisation": float(row["Réalisation"])
                })
            except: continue

        if records:
            try:
                table_performances.batch_create(records)
                st.cache_data.clear()
                st.success(f"🎉 Import réussi ! {len(records)} lignes injectées dans Airtable avec succès.")
            except requests.exceptions.HTTPError as e:
                st.error("❌ Airtable a refusé l'importation. Voici le message d'erreur :")
                st.code(e.response.text)
        else:
            st.warning("⚠️ Aucune ligne valide (avec Objectif > 0) n'a été détectée dans le fichier.")

# --- PAGE 4 : LISTE DES ÉQUIPES ---
elif page == "👥 Liste des Équipes":
    st.title("👥 Référentiel Collaborateurs")
    st.dataframe(df_collabs[['Matricule', 'Nom', 'Prénom', 'Team', 'Manager', 'Courbe', 'Périodicité', 'Prime Target 100%']], use_container_width=True)
