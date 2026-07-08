import streamlit as st
import pandas as pd
import io

# Configuration de la page
st.set_page_config(
    page_title="Ops Compensation Intelligence", 
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
st.markdown("<h1 style='text-align: center; color: #1E293B; margin-bottom: 5px;'>💎 Ops Compensation Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748B; font-size: 1.1rem;'>La puissance des données alliée au confort visuel des équipes RH.</p>", unsafe_allow_html=True)
st.write("")

# --- INTERFACE ---
st.markdown("### 🛠️ 1. Préparation & Import de l'historique")
col_l, col_r = st.columns([1, 2], gap="large")

with col_l:
    # Génération du template idéal multi-mois
    template_data = {
        "Nom": ["Dupont", "Dupont", "Martin"],
        "Prénom": ["Jean", "Jean", "Sophie"],
        "Mois (1 à 12)": [1, 2, 1],
        "Courbe": ["Standard", "Standard", "Inside Sales"],
        "Objectif": [10000, 10000, 50000],
        "Réalisation": [9500, 11500, 52000],
        "Prime Target 100%": [2000, 2000, 3500]
    }
    df_template = pd.DataFrame(template_data)
    buffer_template = io.BytesIO()
    with pd.ExcelWriter(buffer_template, engine='xlsxwriter') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Historique')
        
    st.download_button(
        label="📥 Télécharger la matrice d'historique Excel",
        data=buffer_template.getvalue(),
        file_name="matrice_historique_variable.xlsx",
        mime="application/vnd.ms-excel",
        use_container_width=True
    )
    st.caption("💡 **Astuce :** Vous pouvez mettre plusieurs mois pour le même collaborateur à la suite (Ex: Dupont en mois 1, puis Dupont en mois 2).")

with col_r:
    uploaded_file = st.file_uploader("Glissez-déposez le fichier Excel de votre équipe", type=["xlsx", "xls"], label_visibility="collapsed")

if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = [c.strip() for c in df_raw.columns]
        
        # Identification automatique de la colonne mois
        col_m = [c for c in df_raw.columns if "Mois" in c][0]
        
        # Calcul de chaque ligne via notre moteur
        resultats = df_raw.apply(calculer_ligne, axis=1)
        df_raw['TR'] = [r[0] for r in resultats]
        df_raw['Atteinte'] = [r[1] for r in resultats]
        df_raw['À Verser (€)'] = [r[2] for r in resultats]
        
        # --- CALCUL DU FORECAST ---
        dernier_mois = int(df_raw[col_m].max())
        mois_restants = max(0, 12 - dernier_mois)
        
        st.divider()
        st.markdown(f"### 📈 2. Synthèse Globale (YTD & Forecast à Fin Mois {dernier_mois})")
        
        # Agrégation par collaborateur pour les statistiques annuelles
        df_collaboration = df_raw.groupby(['Nom', 'Prénom', 'Courbe', 'Prime Target 100%']).agg({
            'À Verser (€)': 'sum',
            'TR': 'mean'
        }).reset_index()
        
        # Projection
        df_collaboration["Projection Annuelle Établie (€)"] = df_collaboration['À Verser (€)'] + (mois_restants * (df_collaboration['Prime Target 100%'] * (df_collaboration['À Verser (€)'] / (df_collaboration['Prime Target 100%'] * dernier_mois))))
        
        # Métriques macro
        total_deja_verse = df_collaboration['À Verser (€)'].sum()
        total_atterrissage_an = df_collaboration["Projection Annuelle Établie (€)"].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Mois Max Détecté", f"Mois {dernier_mois} / 12")
        k2.metric("Cumul Déjà Versé (YTD)", f"{total_deja_verse:,.2f} €")
        k3.metric("Atterrissage Budgétaire Annuel", f"{total_atterrissage_an:,.2f} €")
        
        # --- 🔄 LA MAGIE DU PIVOT HORIZONTAL ---
        st.write("")
        st.markdown("### 📋 Vue Frise Chronologique Horizontale (Suivi des Primes par Mois)")
        
        # Création du tableau horizontal des versements par mois
        df_pivot = df_raw.pivot_table(
            index=['Nom', 'Prénom', 'Courbe'],
            columns=col_m,
            values='À Verser (€)',
            aggfunc='sum'
        ).fillna(0)
        
        # Renommer les colonnes de mois (1 -> Janvier, etc. ou M1)
        df_pivot.columns = [f"Mois {int(c)} (€)" for c in df_pivot.columns]
        df_pivot = df_pivot.reset_index()
        
        # Fusionner avec les totaux et projections
        df_final_horizontal = pd.merge(df_pivot, df_collaboration[['Nom', 'Prénom', 'À Verser (€)', "Projection Annuelle Établie (€)"]], on=['Nom', 'Prénom'])
        df_final_horizontal = df_final_horizontal.rename(columns={'À Verser (€)': 'Total Cumulé YTD (€)'})
        
        # Formatage des données pour un rendu Lux
        format_dict = {col: '{:,.2f} €' for col in df_final_horizontal.columns if 'Mois' in col or '€' in col}
        
        st.dataframe(
            df_final_horizontal.style.format(format_dict).background_gradient(cmap="Blues", subset=[c for c in df_final_horizontal.columns if 'Mois' in c]),
            use_container_width=True
        )
        
        # --- BOUTON EXPORT ---
        buffer_export = io.BytesIO()
        with pd.ExcelWriter(buffer_export, engine='xlsxwriter') as writer:
            df_final_horizontal.to_excel(writer, index=False, sheet_name='Suivi_Horizontal')
            df_raw.to_excel(writer, index=False, sheet_name='Donnees_Brutes_Calcules')
            
        st.write("")
        st.download_button(
            label="🟢 Télécharger le Grand Livre de Paie Horizontal (Excel)",
            data=buffer_export.getvalue(),
            file_name="suivi_horizontal_paie_variable.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Erreur d'analyse. Assurez-vous que le fichier respecte le modèle. Détails : {e}")
