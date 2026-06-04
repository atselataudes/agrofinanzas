import streamlit as st
from src.database.repository import Repository
from src.ui.views.bitacora import show_bitacora
from src.ui.views.movements import show_movements
from src.ui.views.harvest import show_harvest
from src.ui.views.captura_inteligente import show_captura_inteligente

_SESSION_KEY  = "encargado_autenticado"
_NAV_KEY      = "encargado_nav"
_PIN_SETTING  = "pin_encargado"
_PIN_DEFAULT  = "1234"

_MENU = [
    "🤖 Captura",
    "📝 Gastos",
    "🥑 Corte",
    "📋 Bitácora",
]


def _get_pin(repo: Repository) -> str:
    return repo.get_setting(_PIN_SETTING, _PIN_DEFAULT)


def _login(repo: Repository):
    st.markdown("## 👷 Acceso Encargado")
    st.caption("Ingresa el PIN para continuar.")

    with st.container(border=True):
        pin = st.text_input(
            "PIN de acceso", type="password", max_chars=4,
            placeholder="••••", key="enc_pin_input"
        )
        if st.button("Entrar", type="primary", use_container_width=True, key="enc_login_btn"):
            if pin == _get_pin(repo):
                st.session_state[_SESSION_KEY] = True
                st.rerun()
            else:
                st.error("PIN incorrecto.")


def show_vista_encargado():
    repo = Repository()

    if not st.session_state.get(_SESSION_KEY):
        _login(repo)
        return

    # Sidebar del encargado — solo su menú
    with st.sidebar:
        st.markdown("### 👷 Encargado")
        seccion = st.radio(
            "Ir a:",
            _MENU,
            index=_MENU.index(st.session_state.get(_NAV_KEY, _MENU[0])),
            label_visibility="collapsed",
            key="enc_nav_radio",
        )
        st.session_state[_NAV_KEY] = seccion
        st.divider()
        if st.button("🔒 Cerrar sesión", use_container_width=True, key="enc_logout"):
            st.session_state[_SESSION_KEY] = False
            st.session_state.pop(_NAV_KEY, None)
            st.rerun()

    # Routing
    if seccion == "🤖 Captura":
        show_captura_inteligente()
    elif seccion == "📝 Gastos":
        show_movements()
    elif seccion == "🥑 Corte":
        show_harvest()
    elif seccion == "📋 Bitácora":
        show_bitacora(modo_encargado=True)


def show_cambiar_pin():
    """Bloque para cambiar el PIN — se incrusta en Catálogos."""
    repo = Repository()
    st.markdown("#### 🔑 PIN del Encargado")
    pin_actual = _get_pin(repo)

    with st.container(border=True):
        c1, c2 = st.columns(2)
        nuevo = c1.text_input("Nuevo PIN (4 dígitos)", type="password", max_chars=4, key="pin_nuevo")
        confirma = c2.text_input("Confirmar PIN", type="password", max_chars=4, key="pin_confirma")
        st.caption(f"PIN actual: {'*' * len(pin_actual)}")
        if st.button("Guardar PIN", key="pin_save_btn"):
            if len(nuevo) != 4 or not nuevo.isdigit():
                st.error("El PIN debe ser exactamente 4 dígitos numéricos.")
            elif nuevo != confirma:
                st.error("Los PINs no coinciden.")
            else:
                repo.update_setting(_PIN_SETTING, nuevo)
                st.success("✅ PIN actualizado.")
