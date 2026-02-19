import streamlit as st
import pandas as pd
import gspread
import plotly.graph_objects as go
from datetime import datetime
import io
import os
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Performance PickerPro", layout="wide", initial_sidebar_state="collapsed")

VALDI_NAVY = "#0d1b3e"
VALDI_PINK = "#d63384"
DARK_BG = "#0d1b3e" 

# --- CSS PARA BLINDAR DISEÑO ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG} !important; color: white !important; }}
    header, footer, #MainMenu, [data-testid="stToolbar"] {{ visibility: hidden !important; display: none !important; }}

    /* Banner Superior: Letras Blancas y Diseño */
    .valdi-header {{
        background-color: #162447 !important;
        padding: 30px 40px;
        border-bottom: 5px solid {VALDI_PINK} !important;
        border-radius: 15px;
        margin-bottom: 25px;
    }}
    .valdi-header h1 {{ color: #ffffff !important; margin: 0 !important; font-size: 28px !important; font-weight: 800 !important; }}
    .valdi-header p {{ color: {VALDI_PINK} !important; margin: 0 !important; font-weight: bold !important; }}

    /* Cards Métricas Blancas */
    .metric-card {{
        background: white !important;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }}
    .metric-title {{ color: #64748b !important; font-size: 0.85rem !important; font-weight: bold !important; text-transform: uppercase; }}
    .metric-value {{ color: {VALDI_NAVY} !important; font-size: 2.2rem !important; font-weight: 900 !important; }}

    /* Alineación de filtros y botones en la misma línea */
    label {{ color: white !important; font-weight: bold !important; }}
    .stButton > button, .stDownloadButton > button {{
        height: 45px !important;
        margin-top: 28px !important;
        border-radius: 10px !important;
    }}
    
    /* Botón ENVIAR color Pink */
    div.stButton > button:first-child {{
        background-color: {VALDI_PINK} !important;
        color: white !important;
        border: none !important;
    }}
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    # Carga desde Variable de Entorno GOOGLE_CREDS
    creds_info = json.loads(os.environ.get("GOOGLE_CREDS", "{}"))
    gc = gspread.service_account_from_dict(creds_info)
    sh = gc.open_by_key("1c_jufd-06AgiNObBkz0KL0jfqlESKEKiqwFHZwr_9Xg")
    df = pd.DataFrame(sh.worksheet("Resumen Diario Outsourcing").get_all_records())
    df.columns = df.columns.str.strip().str.lower()
    
    # Limpieza SKU anti-error
    df['sku totales'] = df['sku totales'].astype(str).str.replace(r'[\.\,]', '', regex=True)
    df['sku totales'] = pd.to_numeric(df['sku totales'], errors='coerce').fillna(0).astype(int)
    
    # Limpieza Pago
    df['pago variable'] = df['pago variable'].astype(str).str.replace(r'[\$\.\s]', '', regex=True)
    df['pago variable'] = pd.to_numeric(df['pago variable'], errors='coerce').fillna(0)
    
    df['fecha día'] = pd.to_datetime(df['fecha día'], dayfirst=True, errors='coerce')
    return df

try:
    df_raw = load_data()
    st.markdown(f'<div class="valdi-header"><h1>Performance PickerPro</h1><p>VALDISHOPPER</p></div>', unsafe_allow_html=True)

    # --- FILTROS Y BOTONES ALINEADOS EN UNA SOLA FILA ---
    c1, c2, c3, c4, c5 = st.columns([2.5, 2, 2, 1.5, 2])
    with c1:
        sala_sel = st.selectbox("SALA", options=["Todas las Salas"] + sorted([str(s) for s in df_raw['local'].unique()]))
    with c2:
        f_ini = st.date_input("DESDE", df_raw['fecha día'].min().date() if not df_raw['fecha día'].isnull().all() else datetime.now().date())
    with c3:
        f_fin = st.date_input("HASTA", df_raw['fecha día'].max().date() if not df_raw['fecha día'].isnull().all() else datetime.now().date())
    
    # Filtrado
    df = df_raw.copy()
    if sala_sel != "Todas las Salas":
        df = df[df['local'].astype(str) == sala_sel]
    df = df[(df['fecha día'].dt.date >= f_ini) & (df['fecha día'].dt.date <= f_fin)]
    df['cumple_meta'] = df['sku totales'] >= 200

    # Botones alineados a la derecha de los filtros
    with c4:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Reporte')
        st.download_button(label="📥 EXCEL", data=output.getvalue(), file_name=f"Reporte_{sala_sel}.xlsx", use_container_width=True)
    with c5:
        if st.button("📧 ENVIAR", type="primary", use_container_width=True):
            st.success("Preparando envío...")

    # --- MÉTRICAS ---
    eficacia = (df['cumple_meta'].sum() / len(df) * 100) if len(df) > 0 else 0
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(f'<div class="metric-card"><div class="metric-title">Turnos</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="metric-card"><div class="metric-title">Metas OK</div><div class="metric-value" style="color:#2ecc71;">{df["cumple_meta"].sum()}</div></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="metric-card"><div class="metric-title">Eficacia</div><div class="metric-value" style="color:{VALDI_PINK};">{eficacia:.1f}%</div></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="metric-card"><div class="metric-title">Incentivo</div><div class="metric-value">${df["pago variable"].sum():,.0f}</div></div>', unsafe_allow_html=True)

    # --- GRÁFICO ---
    st.write("### Tendencia de Productividad")
    df_chart = df.groupby(df['fecha día'].dt.date).agg({'sku totales': 'sum', 'cumple_meta': 'mean'}).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_chart['fecha día'], y=df_chart['sku totales'], name="SKU", marker_color='rgba(255,255,255,0.2)'))
    fig.add_trace(go.Scatter(x=df_chart['fecha día'], y=df_chart['cumple_meta']*100, name="%", line=dict(color=VALDI_PINK, width=4), yaxis="y2"))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"),
        yaxis=dict(title="SKU Totales", gridcolor='rgba(255,255,255,0.1)'),
        yaxis2=dict(title="% Meta", overlaying="y", side="right", range=[0, 100], showgrid=False),
        margin=dict(l=0, r=0, t=10, b=0), height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLA ---
    st.dataframe(df[['local', 'rut', 'fecha día', 'sku totales', 'pago variable']].sort_values('fecha día', ascending=False), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error técnico: {e}")
