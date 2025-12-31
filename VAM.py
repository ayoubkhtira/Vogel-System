import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
import plotly.express as px

# --- Configuration de la page ---
st.set_page_config(page_title="Solveur VAM - Transport", layout="wide")

# --- Fonction Logique VAM ---
def vogel_approximation_method(cost_matrix, supply, demand):
    supply = np.array(supply, dtype=float)
    demand = np.array(demand, dtype=float)
    costs = np.array(cost_matrix, dtype=float)
    
    n_rows, n_cols = costs.shape
    
    # Sauvegarde dimensions originales
    original_cols = n_cols
    original_rows = n_rows
    
    # Gestion des cas déséquilibrés (Dummy)
    if supply.sum() > demand.sum():
        diff = supply.sum() - demand.sum()
        demand = np.append(demand, diff)
        costs = np.c_[costs, np.zeros(n_rows)] 
        n_cols += 1
    elif demand.sum() > supply.sum():
        diff = demand.sum() - supply.sum()
        supply = np.append(supply, diff)
        costs = np.r_[costs, [np.zeros(n_cols)]]
        n_rows += 1
        
    allocation = np.zeros((n_rows, n_cols))
    costs_temp = costs.copy()
    supply_temp = supply.copy()
    demand_temp = demand.copy()
    
    INF = 10**9 

    while supply_temp.sum() > 0 and demand_temp.sum() > 0:
        row_penalties = []
        col_penalties = []

        # Pénalités Lignes
        for r in range(n_rows):
            if supply_temp[r] == 0:
                row_penalties.append(-1)
            else:
                row_valid = [c for c in costs_temp[r, :] if c < INF]
                if len(row_valid) >= 2:
                    sorted_row = np.sort(row_valid)
                    row_penalties.append(sorted_row[1] - sorted_row[0])
                elif len(row_valid) == 1:
                    row_penalties.append(row_valid[0])
                else:
                    row_penalties.append(-1)

        # Pénalités Colonnes
        for c in range(n_cols):
            if demand_temp[c] == 0:
                col_penalties.append(-1)
            else:
                col_valid = [r for r in costs_temp[:, c] if r < INF]
                if len(col_valid) >= 2:
                    sorted_col = np.sort(col_valid)
                    col_penalties.append(sorted_col[1] - sorted_col[0])
                elif len(col_valid) == 1:
                    col_penalties.append(col_valid[0])
                else:
                    col_penalties.append(-1)
        
        row_penalties = np.array(row_penalties)
        col_penalties = np.array(col_penalties)
        
        max_row_p = np.max(row_penalties)
        max_col_p = np.max(col_penalties)
        
        if max_row_p >= max_col_p:
            row_idx = np.argmax(row_penalties)
            valid_cols = np.where(costs_temp[row_idx, :] < INF)[0]
            if len(valid_cols) > 0:
                col_idx = valid_cols[np.argmin(costs_temp[row_idx, valid_cols])]
            else:
                 # Fallback rare edge case
                col_idx = np.argmax(demand_temp > 0)
        else:
            col_idx = np.argmax(col_penalties)
            valid_rows = np.where(costs_temp[:, col_idx] < INF)[0]
            if len(valid_rows) > 0:
                row_idx = valid_rows[np.argmin(costs_temp[valid_rows, col_idx])]
            else:
                row_idx = np.argmax(supply_temp > 0)

        qty = min(supply_temp[row_idx], demand_temp[col_idx])
        allocation[row_idx, col_idx] = qty
        supply_temp[row_idx] -= qty
        demand_temp[col_idx] -= qty
        
        if supply_temp[row_idx] == 0:
            costs_temp[row_idx, :] = INF
        if demand_temp[col_idx] == 0:
            costs_temp[:, col_idx] = INF

    total_cost = np.sum(allocation[:original_rows, :original_cols] * costs[:original_rows, :original_cols])
    return allocation, total_cost

# --- Export Excel ---
def generate_excel(input_df, demand_df, res_df, total_cost, currency):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Rapport VAM')
        writer.sheets['Rapport VAM'] = worksheet
        
        bold_fmt = workbook.add_format({'bold': True, 'font_size': 12})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'color': '#2c3e50'})
        
        row = 0
        worksheet.write(row, 0, "1. Données d'entrée", title_fmt)
        row += 2
        input_df.to_excel(writer, sheet_name='Rapport VAM', startrow=row, startcol=0)
        row += len(input_df) + 3
        
        worksheet.write(row, 0, "2. Demande Clients", title_fmt)
        row += 2
        demand_df.to_excel(writer, sheet_name='Rapport VAM', startrow=row, startcol=0)
        row += len(demand_df) + 4
        
        worksheet.write(row, 0, "3. Solution Optimale", title_fmt)
        row += 2
        res_df.to_excel(writer, sheet_name='Rapport VAM', startrow=row, startcol=0)
        row += len(res_df) + 3
        
        worksheet.write(row, 0, f"Coût Total Minimum : {total_cost:,.2f} {currency}", title_fmt)
        
    return output.getvalue()

# --- Visualisation Sankey ---
def plot_sankey(allocation_matrix, source_names, dest_names):
    # Préparation des labels (Sources + Dests)
    labels = source_names + dest_names
    
    # Indices Plotly : Sources [0..n-1], Dests [n..n+m-1]
    source_indices = []
    target_indices = []
    values = []
    custom_data = [] # Pour afficher les infos au survol

    n_sources = len(source_names)
    
    for r in range(allocation_matrix.shape[0]):
        for c in range(allocation_matrix.shape[1]):
            qty = allocation_matrix[r, c]
            if qty > 0:
                source_indices.append(r)
                target_indices.append(n_sources + c) # Offset pour les destinations
                values.append(qty)
                
                # Info bulle
                src_name = source_names[r]
                dst_name = dest_names[c]
                custom_data.append(f"{src_name} → {dst_name}")

    # Création du diagramme
    fig = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = labels,
            color = "blue"
        ),
        link = dict(
            source = source_indices,
            target = target_indices,
            value = values,
            customdata = custom_data,
            hovertemplate='%{customdata}<br />Quantité: %{value}<extra></extra>'
        ))])

    fig.update_layout(title_text="Diagramme de Flux (Sankey)", font_size=12, height=500)
    return fig

# --- Interface Utilisateur ---

st.title("🚛 Optimisation de Transport : Méthode VAM")
st.markdown("Minimisation des coûts et visualisation des flux logistiques.")

with st.sidebar:
    st.header("1. Configuration")
    currency = st.text_input("Symbole de la devise", value="€")
    num_sources = st.number_input("Nombre de Fournisseurs", min_value=2, value=3)
    num_dests = st.number_input("Nombre de Clients", min_value=2, value=3)

st.subheader("2. Personnalisation des Noms")
col1, col2 = st.columns(2)
with col1:
    source_names = []
    with st.expander("Noms des Fournisseurs", expanded=False):
        for i in range(num_sources):
            source_names.append(st.text_input(f"Fournisseur {i+1}", value=f"Usine {i+1}", key=f"src_{i}"))
with col2:
    dest_names = []
    with st.expander("Noms des Clients", expanded=False):
        for i in range(num_dests):
            dest_names.append(st.text_input(f"Client {i+1}", value=f"Client {i+1}", key=f"dst_{i}"))

st.subheader("3. Saisie des Coûts et Capacités")
df_structure = pd.DataFrame(0.0, index=source_names, columns=dest_names + ["OFFRE (Capacité)"])
st.caption(f"Entrez les coûts unitaires ({currency}) et la capacité de chaque fournisseur.")
input_df = st.data_editor(df_structure, key="input_matrix", use_container_width=True)

st.caption("Entrez la demande pour chaque client.")
demand_structure = pd.DataFrame(0.0, index=["DEMANDE"], columns=dest_names)
demand_df = st.data_editor(demand_structure, key="demand_matrix", use_container_width=True)

if st.button("🚀 Lancer l'Optimisation et Visualiser", type="primary"):
    try:
        costs = input_df.iloc[:, :-1].values
        supply = input_df.iloc[:, -1].values
        demand = demand_df.iloc[0, :].values
        
        if np.any(costs < 0) or np.any(supply < 0) or np.any(demand < 0):
            st.error("Les valeurs doivent être positives.")
        else:
            allocation, total_cost = vogel_approximation_method(costs, supply, demand)
            
            # --- Préparation des Labels Finaux (avec Dummy si nécessaire) ---
            final_sources = source_names.copy()
            final_dests = dest_names.copy()
            
            if allocation.shape[0] > len(source_names):
                final_sources.append("Fictif (Offre)")
            if allocation.shape[1] > len(dest_names):
                final_dests.append("Fictif (Demande)")
                
            res_df = pd.DataFrame(allocation, index=final_sources, columns=final_dests)
            
            st.divider()
            
            # --- TABS POUR RÉSULTATS & VISUALISATION ---
            tab1, tab2, tab3 = st.tabs(["📋 Tableau des Résultats", "📊 Visualisation des Flux", "📥 Export Excel"])
            
            with tab1:
                st.subheader("Plan de Transport Optimal")
                st.metric(label="Coût Total Minimum", value=f"{total_cost:,.2f} {currency}")
                
                def highlight_cells(val):
                    return 'background-color: #d4edda; color: black' if val > 0 else ''
                st.dataframe(res_df.style.applymap(highlight_cells), use_container_width=True)
                
            with tab2:
                st.subheader("Flux Physiques (Source → Destination)")
                sankey_fig = plot_sankey(allocation, final_sources, final_dests)
                st.plotly_chart(sankey_fig, use_container_width=True)
                
                st.divider()
                st.subheader("Détail des Coûts par Fournisseur")
                # Calcul des coûts par ligne pour graphique
                # Attention: dimensions de costs vs allocation peuvent différer si dummy
                real_rows = min(costs.shape[0], allocation.shape[0])
                real_cols = min(costs.shape[1], allocation.shape[1])
                
                cost_per_source = []
                for r in range(real_rows):
                    row_cost = np.sum(allocation[r, :real_cols] * costs[r, :real_cols])
                    cost_per_source.append(row_cost)
                
                # Création Bar Chart
                bar_fig = px.bar(
                    x=source_names[:real_rows], 
                    y=cost_per_source,
                    labels={'x': 'Fournisseur', 'y': f'Coût ({currency})'},
                    title="Coût total généré par Fournisseur",
                    color=cost_per_source,
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(bar_fig, use_container_width=True)

            with tab3:
                st.subheader("Télécharger le rapport")
                excel_data = generate_excel(input_df, demand_df, res_df, total_cost, currency)
                st.download_button(
                    label="📄 Télécharger le rapport Excel (.xlsx)",
                    data=excel_data,
                    file_name="rapport_vam_transport_visu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            
    except Exception as e:
        st.error(f"Erreur de calcul : {e}")
