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
from src.ui.views.vista_encargado import show_encargado_app
from src.ui.views.vista_inversionista import show_inversionista_app

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

# ── LOGIN ────────────────────────────────────────────────────────────────────
def _check_login():
    from src.database.repository import Repository
    repo = Repository()

    if "rol_activo" in st.session_state:
        return True

    render_header()
    st.markdown("### Iniciar sesión")

    rol = st.radio("¿Quién eres?", ["👨‍💼 Administrador", "👷 Encargado", "📈 Inversionista"],
                   horizontal=True, key="login_rol")

    with st.container(border=True):
        pwd = st.text_input("Contraseña / PIN", type="password",
                            placeholder="••••", key="login_pwd")
        if st.button("Entrar", type="primary", use_container_width=True, key="login_btn"):
            if rol == "👨‍💼 Administrador":
                clave_admin = repo.get_setting("password_admin", "admin")
                if pwd == clave_admin:
                    st.session_state["rol_activo"] = "admin"
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            elif rol == "👷 Encargado":
                pin_enc = repo.get_setting("pin_encargado", "1234")
                if pwd == pin_enc:
                    st.session_state["rol_activo"] = "encargado"
                    st.rerun()
                else:
                    st.error("PIN incorrecto.")
            else:
                pin_inv = repo.get_setting("pin_inversionista", "0000")
                if pwd == pin_inv:
                    st.session_state["rol_activo"] = "inversionista"
                    st.rerun()
                else:
                    st.error("PIN incorrecto.")
    return False


if not _check_login():
    st.stop()

# ── ADMIN ────────────────────────────────────────────────────────────────────
if st.session_state.get("rol_activo") == "admin":
    render_header()

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
        ]
        _nav_index = _nav_options.index(_default_nav) if _default_nav in _nav_options else 0
        menu = st.radio("Ir a:", _nav_options, index=_nav_index,
                        label_visibility="collapsed")
        st.divider()
        if st.button("🔒 Cerrar sesión", use_container_width=True, key="admin_logout"):
            st.session_state.pop("rol_activo", None)
            st.rerun()

    if menu == "🏠 Inicio":          show_dashboard()
    elif menu == "🧠 Asistente":     show_asistente()
    elif menu == "🤖 Captura":       show_captura_inteligente()
    elif menu == "📒 Diario":        show_journal()
    elif menu == "🥑 Corte":         show_harvest()
    elif menu == "📝 Movimientos":   show_movements()
    elif menu == "📦 Inventario":    show_inventory()
    elif menu == "📂 Catálogos":     show_catalogs()
    elif menu == "🏦 Créditos":      show_credits()
    elif menu == "📊 Reportes":      show_reports()
    elif menu == "📋 Bitácora":      show_bitacora()

# ── ENCARGADO ────────────────────────────────────────────────────────────────
elif st.session_state.get("rol_activo") == "encargado":
    show_encargado_app()

# ── INVERSIONISTA ─────────────────────────────────────────────────────────────
elif st.session_state.get("rol_activo") == "inversionista":
    show_inversionista_app()
