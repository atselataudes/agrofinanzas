import streamlit as st
from src.database.repository import Repository
from src.services.asistente import ask_assistant

_EJEMPLOS = [
    "¿Cuándo fue la última vez que pagamos nómina?",
    "¿Cuánto hemos gastado en fertilizantes?",
    "¿Cuál es el saldo actual de caja?",
    "¿Cuánto debemos en total de préstamos?",
    "¿Cuál fue el corte con mayor ingreso?",
    "¿Cuánto gastamos en gasolina el último mes?",
    "¿Cuáles son los 3 gastos más grandes del huerto?",
    "¿Qué semana pagamos más en nómina?",
]


def show_asistente():
    st.markdown("### 🧠 Asistente Financiero")
    st.caption(
        "Pregúntame sobre tus finanzas en lenguaje natural. "
        "Tengo acceso a todos tus movimientos, préstamos e ingresos."
    )

    repo = Repository()

    if "asistente_history" not in st.session_state:
        st.session_state["asistente_history"] = []

    history: list = st.session_state["asistente_history"]

    # Ejemplos solo cuando el chat está vacío
    if not history:
        st.markdown("#### 💡 Preguntas frecuentes — toca una para empezar")
        cols = st.columns(2)
        for i, ej in enumerate(_EJEMPLOS):
            if cols[i % 2].button(ej, key=f"ej_{i}", use_container_width=True):
                st.session_state["_asistente_rapida"] = ej
                st.rerun()
        st.divider()

    # Mostrar historial
    for msg in history:
        avatar = "🧑‍🌾" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Pregunta rápida (desde botón de ejemplo)
    pregunta_rapida = st.session_state.pop("_asistente_rapida", None)

    # Input de chat
    prompt = st.chat_input("Escribe tu pregunta sobre las finanzas del huerto…")
    if pregunta_rapida:
        prompt = pregunta_rapida

    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍🌾"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Consultando datos…"):
                respuesta = ask_assistant(repo, prompt, history[:-1])
            st.markdown(respuesta)

        history.append({"role": "assistant", "content": respuesta})
        st.session_state["asistente_history"] = history
        st.rerun()

    # Botón limpiar
    if history:
        st.divider()
        if st.button("🗑️ Limpiar conversación", key="asistente_clear"):
            st.session_state["asistente_history"] = []
            st.rerun()
