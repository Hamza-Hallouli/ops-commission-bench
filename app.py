import streamlit as st
import pandas as pd
import io

# 1. Configuration de la page avec un thème large et moderne
st.set_page_config(
    page_title="Ops Variable Hub", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS CUSTOM (Pour injecter un look épuré et premium) ---
st.markdown("""
    <style>
    /* Modification de la police globale et des arrondis */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    /* Style pour les cartes de résultats */
    .metric-container {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    /* Style pour la zone de dépôt de fichier drag & drop */
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

# --- HEADER PREMIUM ---
st.markdown("<h1 style='text-align: center; color: #1E293B; margin-bottom: 5px;'>💎 Ops Variable Hub</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748B; font-size: 1.1rem;'>Pilotez et calculez les commissions de vos équipes en toute simplicité.</p>", unsafe_allow_html=True)
st.write("")

# Onglets épurés
onglet_masse, onglet_unitaire = st.tabs(["📁 Traitement Global (Excel)", "👤 Estimateur Individuel"])

# --- ONGLET 1 : CALCUL EN MASSE ---
with onglet_masse:
    # Utilisation de colonnes pour structurer les actions de manière élégante
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("### 🛠️ Étape 1 : Préparation")
        st.caption("Téléchargez notre matrice pré-configurée, complétez-la avec vos données d'équipe, puis déposez-la à droite.")
        
        # Génération du template Excel
        template_data = {
            "Nom": ["Dupont", "Martin"], "Prénom": ["Jean", "Sophie"],
            "Courbe": ["Standard", "Inside Sales"], "Objectif": [10000, 50000],
            "Réalisation": [9500, 52000], "Prime Target 100%": [2000, 3500]
        }
        df_template = pd.DataFrame(template_data)
        buffer_template = io.BytesIO()
        with pd.ExcelWriter(buffer_template, engine='xlsxwriter') as writer:
            df_template.to_excel(writer, index=False, sheet_name='Data')
            
        st.download_button(
            label="📥 Télécharger le modèle Excel",
            data=buffer_template.getvalue(),
            file_name="modele_saisie_variable.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
        
        with st.expander("📖 Guide des profils autorisés"):
            st.markdown("""
            Pour la colonne **Courbe**, utilisez uniquement :
            - `Standard`
            - `Manager`
            - `Manager IS`
            - `Inside Sales`
            """)

    with col_right:
        st.markdown("### 📤 Étape 2 : Import & Calcul")
        uploaded_file = st.file_uploader("Glissez-déposez votre fichier d'équipe ici", type=["xlsx", "xls"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            with st.spinner("Calcul des commissions en cours..."):
                try:
                    df_input = pd.read_excel(uploaded_file)
                    resultats = df_input.apply(calculer_ligne, axis=1)
                    
                    df_input['Taux Performance (TR)'] = [r[0] for r in resultats]
                    df_input["Taux Atteinte"] = [r[1] for r in resultats]
                    df_input["Variable Final à Verser (€)"] = [r[2] for r in resultats]
                    
                    st.toast("Calculs terminés !", icon="🎉")
                    
                    st.write("")
                    st.markdown("### 🎯 Étape 3 : Synthèse & Export")
                    
                    # KPIs Globaux très élégants
                    total_variable = df_input["Variable Final à Verser (€)"].sum()
                    effectif = len(df_input)
                    tr_moyen = df_input['Taux Performance (TR)'].mean()
                    
                    kpi1, kpi2, kpi3 = st.columns(3)
                    kpi1.metric("Effectif Traité", f"{effectif} collaborateurs")
                    kpi2.metric("TR Moyen Équipe", f"{tr_moyen:.1%}")
                    kpi3.metric("Enveloppe Globale (€)", f"{total_variable:,.2f} €")
                    
                    st.write("")
                    
                    # Nouveau tableau de données interactif (Streamlit Data Editor)
                    df_display = df_input.copy()
                    st.dataframe(
                        df_display.style.format({
                            'Objectif': '{:,.0f} €',
                            'Réalisation': '{:,.0f} €',
                            'Prime Target 100%': '{:,.0f} €',
                            'Taux Performance (TR)': '{:.2%}',
                            'Taux Atteinte': '{:.2%}',
                            'Variable Final à Verser (€)': '{:,.2f} €'
                        }),
                        use_container_width=True
                    )
                    
                    # Bouton d'export final premium
                    buffer_output = io.BytesIO()
                    with pd.ExcelWriter(buffer_output, engine='xlsxwriter') as writer:
                        df_input.to_excel(writer, index=False, sheet_name='Resultats')
                        
                    st.write("")
                    st.download_button(
                        label="🟢 Exporter le Rapport de Paie Officiel (Excel)",
                        data=buffer_output.getvalue(),
                        file_name="rapport_paie_variable.xlsx",
                        mime="application/vnd.ms-excel",
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"Structure de fichier non valide. Erreur : {e}")

# --- ONGLET 2 : CALCUL UNITAIRE ---
with onglet_unitaire:
    st.markdown("### 👤 Simuler un profil individuel")
    
    col_u1, col_u2 = st.columns([1, 1], gap="large")
    
    with col_u1:
        c_selected = st.selectbox("Sélectionner la courbe de référence", ["Standard", "Manager", "Manager IS", "Inside Sales"])
        obj = st.number_input("Objectif Financier (€)", min_value=1.0, value=10000.0, step=500.0)
        real = st.number_input("Réalisation Constatée (€)", min_value=0.0, value=9500.0, step=500.0)
        target = st.number_input("Package Prime Cible (€)", min_value=0.0, value=2000.0, step=100.0)
        
        tr = real / obj
        if c_selected == "Standard": att = calcul_standard(tr)
        elif c_selected == "Manager": att = calcul_manager(tr)
        elif c_selected == "Manager IS": att = calcul_manager_is(tr)
        else: att = calcul_inside_sales(tr)
        
    with col_u2:
        st.write("")
        st.write("")
        # Encadré visuel pour le résultat individuel
        st.markdown(f"""
        <div class='metric-container'>
            <p style='color: #64748B; margin-bottom: 5px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px;'>Montant Prévisonnel à Verser</p>
            <h1 style='color: #4F46E5; margin: 0; font-size: 2.8rem;'>{target * att:,.2f} €</h1>
            <hr style='border: 0; border-top: 1px solid #e9ecef; margin: 15px 0;'>
            <p style='margin: 5px 0; color: #334155;'><b>Taux de Performance (TR) :</b> {tr:.2%}</p>
            <p style='margin: 5px 0; color: #334155;'><b>Taux d'Atteinte Grille :</b> {att:.2%}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Barre de progression visuelle pour le TR
        st.progress(min(float(tr), 1.0))
