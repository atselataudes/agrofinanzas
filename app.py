import streamlit as st
from config import Config
from src.database.connection import init_db
from src.ui.components import inject_custom_css, render_header
from src.ui.views.dashboard import show_dashboard
from src.ui.views.movements import show_movements
from src.ui.views.catalogs import show_catalogs
from src.ui.views.credits import show_credits
from src.ui.views.reports import show_reports
from src.ui.views.inventory import show_inventory
from src.ui.views.harvest import show_harvest
from src.ui.views.journal import show_journal
from src.ui.views.captura_inteligente import show_captura_inteligente
from src.ui.views.asistente import show_asistente
from src.ui.views.bitacora import show_bitacora
from src.ui.views.vista_encargado import show_vista_encargado

# --- CONFIGURATION ---
st.set_page_config(
    page_title=Config.PAGE_TITLE, 
    page_icon=Config.PAGE_ICON, 
    layout=Config.LAYOUT, 
    initial_sidebar_state="expanded"
)

# --- INITIALIZATION ---
init_db()
Config.setup_folders()
inject_custom_css()

# --- HEADER ---
render_header()

# --- NAVIGATION ---
with st.sidebar:
    st.title("Menú")
    _default_nav = st.session_state.pop("_nav", "🏠 Inicio")
    _nav_options = [
        "🏠 Inicio",
        "🧠 Asistente",
        "🤖 Captura",
        "📒 Diario",
        "🥑 Corte",
        "📝 Movimientos",
        "📦 Inventario",
        "📂 Catálogos",
        "🏦 Créditos",
        "📊 Reportes",
        "📋 Bitácora",
        "👷 Encargado",
    ]
    _nav_index = _nav_options.index(_default_nav) if _default_nav in _nav_options else 0
    menu = st.radio(
        "Ir a:",
        _nav_options,
        index=_nav_index,
        label_visibility="collapsed"
    )
    st.divider()

# --- ROUTING ---
if menu == "🏠 Inicio":
    show_dashboard()

elif menu == "🧠 Asistente":
    show_asistente()

elif menu == "🤖 Captura":
    show_captura_inteligente()

elif menu == "📒 Diario":
    show_journal()

elif menu == "🥑 Corte":
    show_harvest()

elif menu == "📝 Movimientos":
    show_movements()

elif menu == "📦 Inventario":
    show_inventory()

elif menu == "📂 Catálogos":
    show_catalogs()

elif menu == "🏦 Créditos":
    show_credits()

elif menu == "📊 Reportes":
    show_reports()

elif menu == "📋 Bitácora":
    show_bitacora()

elif menu == "👷 Encargado":
    show_vista_encargado()
