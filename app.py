import streamlit as st
import os
import warnings
from dotenv import load_dotenv

# Import Custom Modules
from src.core.db_manager import get_db
from src.ui.utils import local_css
from src.ui.auth import show_auth_ui
from src.ui.sidebar import render_sidebar
from src.ui.tabs.alta import render_alta_tab
from src.ui.tabs.consultas import render_consultas_tab
from src.ui.tabs.anulaciones import render_anulaciones_tab
from src.ui.tabs.estadisticas import render_estadisticas_tab
from src.ui.tabs.historial import render_historial_tab
from src.ui.tabs.catalogo import render_catalogo_tab

# --- Load Environment Variables ---
load_dotenv(override=True)

# Suppress specific cryptography warning about PKCS#12 format
warnings.filterwarnings("ignore", category=UserWarning, message=".*PKCS#12 bundle could not be parsed as DER.*")

# --- Init State ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'client' not in st.session_state:
    st.session_state.client = None
if 'viajeros' not in st.session_state:
    st.session_state.viajeros = [{'nombre': '', 'apellido1': ''}]

# --- DB Check ---
try:
    get_db().init_db()
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False

# --- Page Configuration ---
st.set_page_config(
    page_title="Mirador - Registro de Huéspedes",
    page_icon="Logo.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.logo("Logo.png", icon_image="Logo.png")
local_css("static/css/style.css")

# --- Authentication UI ---
if not st.session_state.user:
    show_auth_ui()
    st.stop()

# --- Main App Logic ---
# 1. Top bar
col_user1, col_user2 = st.columns([8, 1])
with col_user2:
    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

# 2. Sidebar Configuration
config = render_sidebar(DB_AVAILABLE)

# 3. Header
h_col1, h_col2 = st.columns([1, 6], vertical_alignment="center")
with h_col1:
    st.image("Logo.png", width=100)
with h_col2:
    st.markdown("""
        <div>
            <h2 style='margin: 0; color: #f8fafc; font-weight: 700; font-size: 2.2rem;'>Mirador</h2>
            <p style='margin: 0; color: #94a3b8; font-size: 1.2rem; margin-top: -5px;'>Plataforma de Registro de Huéspedes</p>
        </div>
    """, unsafe_allow_html=True)
st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

# 4. Tabs Management
tab_titles = ["📤 Alta", "🔍 Consultas", "❌ Anulaciones", "📈 Estadísticas", "📅 Historial"]
if st.session_state.user.get('role') == 'admin':
    tab_titles.append("📋 Catálogo")

tabs = st.tabs(tab_titles)

with tabs[0]: render_alta_tab(config)
with tabs[1]: render_consultas_tab(config)
with tabs[2]: render_anulaciones_tab(config)
with tabs[3]: render_estadisticas_tab(config)
with tabs[4]: render_historial_tab(config)

if st.session_state.user.get('role') == 'admin':
    with tabs[5]: render_catalogo_tab(config, DB_AVAILABLE)

# 5. Footer
st.divider()
st.caption("Mirador - Todos los derechos reservados 2026 - Desarrollado por SerLau Tech, LLC")
