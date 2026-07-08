import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Ops Variable & Forecast Hub", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS CUSTOM ---
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
        obj = float(row['Objectif Mensuel'])
        real = float(row['Réalisation Mensuelle'])
        target = float(row['Prime Target Mensuelle'])
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

# --- HEADER PREMIUM ---
st.markdown("<h1 style='text-align: center; color: #1E293B; margin-bottom: 5px;'>💎 Ops Variable & Forecast Hub</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748B; font-size: 1.1rem;'>Calculez le mois en cours et anticipez les budgets de fin d'année.</p>", unsafe_allow_html=True)
st.write("")

onglet_masse, onglet_unitaire = st.tabs(["📁 Traitement Global & Forecast", "👤 Estimateur Individuel"])

# --- ONGLET 1 : CALCUL EN MASSE & PROJECTION ---
with onglet_masse:
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("### 🛠️ Étape 1 : Préparation")
        st.caption("Notre nouveau modèle intègre la notion de 'Mois' pour générer automatiquement l'atterrissage budgétaire de fin d'année.")
        
        # Modèle de données mis à jour avec le mois courant (ex: 6 pour Juin)
        template_data = {
            "Nom": ["Dupont", "Martin"], "Prénom": ["Jean", "Sophie"], "Mois (Nombre de 1 à 12)": [6, 6],
            "Courbe": ["Standard", "Inside Sales"], "Objectif Mensuel": [10000, 50000],
            "Réalisation Mensuelle": [9500, 52000], "Prime Target Mensuelle": [2000, 3500]
        }
        df_template = pd.DataFrame(template_data)
        buffer_template = io.BytesIO()
        with pd.ExcelWriter(buffer_template, engine='xlsxwriter') as writer:
            df_template.to_excel(writer, index=False, sheet_name='Data')
            
        st.download_button(
            label="📥 Télécharger le modèle Excel (Mois + Forecast)",
            data=buffer_template.getvalue(),
            file_name="modele_saisie_forecast.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )

        # Choix de la méthode de prévision
        st.write("")
        st.markdown("### 🔮 Méthode de Projection")
        methode_forecast = st.radio(
            "Hypothèse pour les mois restants :",
            ["Conserver la performance actuelle (Run Rate)", "Atteindre 100% des objectifs futurs (Budget)"]
        )

    with col_right:
        st.markdown("### 📤 Étape 2 : Import & Atterrissage")
        uploaded_file = st.file_uploader("Glissez-déposez votre fichier d'équipe ici", type=["xlsx", "xls"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            with St.spinner("Calcul et projections en cours..."):
                try:
                    df_input = pd.read_excel(uploaded_file)
                    
                    # Renommer dynamiquement si les titres varient légèrement
                    df_input.columns = [c.strip() for c in df_input.columns]
                    col_mois = [c for c in df_input.columns if "Mois" in c][0]
                    
                    # Alignement des noms de colonnes pour le moteur
                    df_moteur = df_input.rename(columns={
                        "Objectif Mensuel": "Objectif",
                        "Réalisation Mensuelle": "Réalisation",
                        "Prime Target Mensuelle": "Prime Target 100%"
                    })
                    
                    resultats = df_moteur.apply(calculer_ligne, axis=1)
                    
                    # Injection des résultats du mois en cours
                    df_input['TR Mois en Cours'] = [r[0] for r in resultats]
                    df_input["Atteinte Mois en Cours"] = [r[1] for r in resultats]
                    df_input["À Verser (Ce Mois-ci)"] = [r[2] for r in resultats]
                    
                    # --- LOGIQUE DU FORECAST (PRÉVISION FIN D'ANNÉE) ---
                    projections_annee = []
                    for idx, row in df_input.iterrows():
                        m_actuel = int(row[col_mois])
                        m_restants = max(0, 12 - m_actuel)
                        
                        deja_paye = row["À Verser (Ce Mois-ci)"] * m_actuel # Estimation cumulée passée
                        target_mensuelle = row["Prime Target Mensuelle"]
                        courbe = str(row['Courbe']).strip()
                        
                        if methode_forecast == "Conserver la performance actuelle (Run Rate)":
                            atteinte_future = row["Atteinte Mois en Cours"]
                        else: # Hypothèse objectif atteint à 100%
                            atteinte_future = 1.0
                            
                        reste_a_payer_estime = m_restants * (target_mensuelle * atteinte_future)
                        projection_totale_annee = deja_paye + reste_a_payer_estime
                        projections_annee.append(projection_totale_annee)
                        
                    df_input["Estimation Fin d'Année (Total)"] = projections_annee
                    
                    # --- AFFICHAGE DE LA SYNTHÈSE LUX ---
                    st.toast("Analyses prévisionnelles prêtes !", icon="📈")
                    st.write("")
                    
                    total_ce_mois = df_input["À Verser (Ce Mois-ci)"].sum()
                    total_estime_annee = df_input["Estimation Fin d'Année (Total)"].sum()
                    
                    kpi1, kpi2 = st.columns(2)
                    kpi1.metric("Budget Global Ce Mois-ci", f"{total_ce_mois:,.2f} €")
                    kpi2.metric("Atterrissage Budgétaire Annuel Estimé", f"{total_estime_annee:,.2f} €", help="Cumul du passé réel + projection du futur.")
                    
                    st.write("")
                    st.markdown("### 📋 Tableau de Bord Équipe")
                    
                    # Affichage propre du tableau complet
                    st.dataframe(
                        df_input.style.format({
                            'Objectif Mensuel': '{:,.0f} €',
                            'Réalisation Mensuelle': '{:,.0f} €',
                            'Prime Target Mensuelle': '{:,.0f} €',
                            'TR Mois en Cours': '{:.2%}',
                            'Atteinte Mois en Cours': '{:.2%}',
                            'À Verser (Ce Mois-ci)': '{:,.2f} €',
                            "Estimation Fin d'Année (Total)": '{:,.2f} €'
                        }),
                        use_container_width=True
                    )
                    
                    # Export du rapport enrichi
                    buffer_output = io.BytesIO()
                    with pd.ExcelWriter(buffer_output, engine='xlsxwriter') as writer:
                        df_input.to_excel(writer, index=False, sheet_name='Resultats_Et_Forecast')
                        
                    st.write("")
                    st.download_button(
                        label="🟢 Télécharger le Rapport Financier Global (Excel)",
                        data=buffer_output.getvalue(),
                        file_name="rapport_paie_et_forecast.xlsx",
                        mime="application/vnd.ms-excel",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de l'analyse : {e}")

# --- ONGLET 2 : ESTIMATEUR INDIVIDUEL ---
with onglet_unitaire:
    st.markdown("### 👤 Modélisation Individuelle Prévisonnelle")
    col_u1, col_u2 = st.columns([1, 1], gap="large")
    
    with col_u1:
        c_selected = st.selectbox("Sélectionner la courbe", ["Standard", "Manager", "Manager IS", "Inside Sales"])
        mois_select = st.slider("Mois en cours de calcul", 1, 12, 6)
        obj = st.number_input("Objectif Mensuel (€)", min_value=1.0, value=10000.0)
        real = st.number_input("Réalisation Mensuelle (€)", min_value=0.0, value=9500.0)
        target = st.number_input("Prime Mensuelle Target (€)", min_value=0.0, value=2000.0)
        
        tr = real / obj
        if c_selected == "Standard": att = calcul_standard(tr)
        elif c_selected == "Manager": att = calcul_manager(tr)
        elif c_selected == "Manager IS": att = calcul_manager_is(tr)
        else: att = calcul_inside_sales(tr)
        
        prime_ce_mois = target * att
        mois_restants = 12 - mois_select
        
    with col_u2:
        st.write("")
        # Mode Run Rate automatique en unitaire
        total_annuel_estime = (prime_ce_mois * mois_select) + (mois_restants * prime_ce_mois)
        
        st.markdown(f"""
        <div class='metric-container'>
            <p style='color: #64748B; margin-bottom: 5px; font-size: 0.9rem; text-transform: uppercase;'>À Verser Ce Mois-ci</p>
            <h1 style='color: #4F46E5; margin: 0 0 15px 0; font-size: 2.3rem;'>{prime_ce_mois:,.2f} €</h1>
            
            <p style='color: #64748B; margin-bottom: 5px; font-size: 0.9rem; text-transform: uppercase;'>Projection Gains Annuels (Run Rate)</p>
            <h2 style='color: #10B981; margin: 0; font-size: 2rem;'>{total_annuel_estime:,.2f} €</h2>
            <hr style='border: 0; border-top: 1px solid #e9ecef; margin: 15px 0;'>
            <p style='margin: 5px 0; color: #334155;'><b>Performance courante :</b> {tr:.2%}</p>
            <p style='margin: 5px 0; color: #334155;'><b>Mois restants projetés :</b> {mois_restants} mois</p>
        </div>
        """, unsafe_allow_html=True)
