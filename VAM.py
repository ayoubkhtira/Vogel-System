import streamlit as st
import numpy as np
import pandas as pd
import time

# --- LOGIQUE VOGEL (VAM) ---
def vogel_approximation_method(supply, demand, costs):
    s = list(map(float, supply))
    d = list(map(float, demand))
    c = np.array(costs, dtype=float)
    num_suppliers, num_consumers = len(s), len(d)
    allocation = np.zeros((num_suppliers, num_consumers))
    s_curr, d_curr = s[:], d[:]
    
    while sum(s_curr) > 0.01 and sum(d_curr) > 0.01:
        penalties = []
        for i in range(num_suppliers):
            if s_curr[i] > 0:
                row_c = [c[i][j] for j in range(num_consumers) if d_curr[j] > 0]
                penalties.append((sorted(row_c)[1] - sorted(row_c)[0] if len(row_c) > 1 else row_c[0], 'row', i))
            else: penalties.append((-1, 'row', i))
        for j in range(num_consumers):
            if d_curr[j] > 0:
                col_c = [c[i][j] for i in range(num_suppliers) if s_curr[i] > 0]
                penalties.append((sorted(col_c)[1] - sorted(col_c)[0] if len(col_c) > 1 else col_c[0], 'col', j))
            else: penalties.append((-1, 'col', j))

        _, p_type, idx = max(penalties, key=lambda x: x[0])
        if p_type == 'row':
            row_idx = idx
            col_idx = min([(c[row_idx][j], j) for j in range(num_consumers) if d_curr[j] > 0], key=lambda x: x[0])[1]
        else:
            col_idx = idx
            row_idx = min([(c[i][col_idx], i) for i in range(num_suppliers) if s_curr[i] > 0], key=lambda x: x[0])[1]

        qty = min(s_curr[row_idx], d_curr[col_idx])
        allocation[row_idx][col_idx] = qty
        s_curr[row_idx] -= qty
        d_curr[col_idx] -= qty
    return allocation

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="VAM Optimizer", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    div.stButton > button:first-child {
        background: #1e293b; color: white; border-radius: 8px;
        padding: 0.75rem; width: 100%; font-weight: bold; border: none;
    }
    div.stButton > button:first-child:hover { background: #334155; border: none; color: white; }
    .metric-container { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚛 Vogel Transport Optimization")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Configuration")
    n_f = st.number_input("Fournisseurs", 1, 10, 3)
    n_c = st.number_input("Clients", 1, 10, 3)
    st.divider()
    devise_opt = st.selectbox("Devise", ["€", "$", "MAD", "Personnalisée"])
    symbole = st.text_input("Symbole", "DH") if devise_opt == "Personnalisée" else devise_opt

# --- ONGLETS ---
tab1, tab2 = st.tabs(["📥 Saisie", "📊 Analyse"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Capacités Fournisseurs**")
        s_vals = [st.number_input(f"Fournisseur {i+1}", 0, 1000, 100, key=f"s{i}") for i in range(n_f)]
    with c2:
        st.write("**Besoins Clients**")
        d_vals = [st.number_input(f"Client {j+1}", 0, 1000, 75, key=f"d{j}") for j in range(n_c)]
    
    st.write(f"**Coûts Unitaires ({symbole})**")
    costs = np.zeros((n_f, n_c))
    for i in range(n_f):
        cols = st.columns(n_c)
        for j in range(n_c):
            costs[i][j] = cols[j].number_input(f"F{i+1}➔C{j+1}", 0.0, 1000.0, 5.0, key=f"c{i}{j}")
    
    if st.button("LANCER LE CALCUL"):
        st.session_state['run'] = True

# --- RÉSULTATS ---
if st.session_state.get('run'):
    allocation = vogel_approximation_method(s_vals, d_vals, costs)
    total_cost = np.sum(allocation * costs)
    
    with tab2:
        # Indicateurs
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Coût Total de Transport", f"{total_cost:,.2f} {symbole}")
        with col_m2:
            st.metric("Volume total", f"{sum(s_vals)} unités")
        
        st.divider()
        
        # Tableau de résultat
        st.subheader("📋 Matrice d'Allocation Optimale")
        df_res = pd.DataFrame(allocation, 
                             index=[f"F{i+1}" for i in range(n_f)], 
                             columns=[f"C{j+1}" for j in range(n_c)])
        st.table(df_res) # Utilisation de .table pour une compatibilité maximale
        
        # Graphiques NAtifs (Pas besoin de Plotly !)
        st.divider()
        st.subheader("📈 Visualisation des flux")
        
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.write("Quantités livrées par Client")
            st.bar_chart(df_res.T) # Transposé pour grouper par client
            
        with c_g2:
            st.write("Volume total expédié par Fournisseur")
            st.bar_chart(df_res.sum(axis=1))

        st.success("Calcul terminé selon la méthode VAM.")