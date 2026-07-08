import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Ops Variable Calculator", page_icon="📊", layout="wide")

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

# --- INTERFACE FRONT-END ---
st.title("🚀 Hub de Calcul de Paie Variable (Mode Productif)")
st.write("Gagnez du temps en traitant toute votre équipe d'un coup.")

# Création d'onglets pour séparer les usages
onglet_masse, onglet_unitaire = st.tabs(["📁 Calcul en Masse (Excel)", "👤 Calcul Unitaire (Simulation)"])

with onglet_masse:
    st.subheader("1. Téléchargez le masque de saisie officiel")
    
    # Création du template de base
    template_data = {
        "Nom": ["Dupont", "Martin"],
        "Prénom": ["Jean", "Sophie"],
        "Courbe": ["Standard", "Inside Sales"],
        "Objectif": [10000, 50000],
        "Réalisation": [9500, 52000],
        "Prime Target 100%": [2000, 3500]
    }
    df_template = pd.DataFrame(template_data)
    
    # Bouton de téléchargement du masque
    buffer_template = io.BytesIO()
    with pd.ExcelWriter(buffer_template, engine='xlsxwriter') as writer:
        df_template.to_excel(writer, index=False, sheet_name='Data_A_Remplir')
    
    st.download_button(
        label="📥 Télécharger le modèle de masque Excel",
        data=buffer_template.getvalue(),
        file_name="masque_saisie_variable.xlsx",
        mime="application/vnd.ms-excel"
    )
    
    st.info("💡 **Conseil :** Remplissez ce fichier avec vos 20 collaborateurs. Les valeurs valides pour la colonne 'Courbe' sont : *Standard*, *Manager*, *Manager IS*, *Inside Sales*.")

    st.divider()
    st.subheader("2. Déposez votre fichier complété")
    
    uploaded_file = st.file_uploader("Glissez le fichier Excel ici", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            df_input = pd.read_excel(uploaded_file)
            
            # Application de la logique sur toutes les lignes d'un coup
            resultats = df_input.apply(calculer_ligne, axis=1)
            
            # Décomposition des résultats dans de nouvelles colonnes
            df_input['Taux Performance (TR)'] = [r[0] for r in resultats]
            df_input["Taux Atteinte"] = [r[1] for r in resultats]
            df_input["Variable Final à Verser"] = [r[2] for r in resultats]
            
            st.success("✅ Calculs effectués avec succès pour toute l'équipe !")
            
            # Affichage du masque de résultat
            st.subheader("📋 Aperçu des résultats")
            
            # Formatage visuel pour l'affichage web
            df_display = df_input.copy()
            df_display['Taux Performance (TR)'] = df_display['Taux Performance (TR)'].map('{:.2%}'.format)
            df_display['Taux Atteinte'] = df_display['Taux Atteinte'].map('{:.2%}'.format)
            df_display['Variable Final à Verser'] = df_display['Variable Final à Verser'].map('{:,.2f} €'.format)
            
            st.dataframe(df_display, use_container_width=True)
            
            # Export vers le fichier de sortie
            buffer_output = io.BytesIO()
            with pd.ExcelWriter(buffer_output, engine='xlsxwriter') as writer:
                df_input.to_excel(writer, index=False, sheet_name='Resultats_Paie')
                
            st.download_button(
                label="🟢 Télécharger le fichier de Paie Final (Excel)",
                data=buffer_output.getvalue(),
                file_name="resultats_paie_variable.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier. Vérifiez que les colonnes correspondent exactement au modèle. Erreur : {e}")

with onglet_unitaire:
    # Le code précédent reste ici pour faire une simulation rapide si besoin
    st.subheader("Simuler un profil individuel")
    c_selected = st.selectbox("Courbe", ["Standard", "Manager", "Manager IS", "Inside Sales"], key="unit_c")
    obj = st.number_input("Objectif", min_value=1.0, value=10000.0, key="unit_o")
    real = st.number_input("Réalisation", min_value=0.0, value=9500.0, key="unit_r")
    target = st.number_input("Target (€)", min_value=0.0, value=2000.0, key="unit_t")
    
    tr = real / obj
    if c_selected == "Standard": att = calcul_standard(tr)
    elif c_selected == "Manager": att = calcul_manager(tr)
    elif c_selected == "Manager IS": att = calcul_manager_is(tr)
    else: att = calcul_inside_sales(tr)
    
    st.metric(label="Variable à payer", value=f"{target * att:,.2f} €")
