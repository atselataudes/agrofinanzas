import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.database.repository import Repository

TIPOS_ACTIVIDAD = [
    "Fumigación",
    "Fertilización",
    "Poda",
    "Riego",
    "Revisión / Monitoreo",
    "Cosecha",
    "Mantenimiento",
    "Otro",
]

ICONOS = {
    "Fumigación":          "☠️",
    "Fertilización":       "🧪",
    "Poda":                "✂️",
    "Riego":               "💧",
    "Revisión / Monitoreo":"🔍",
    "Cosecha":             "🥑",
    "Mantenimiento":       "🔧",
    "Otro":                "📋",
}


def show_bitacora(modo_encargado: bool = False):
    st.markdown("### 📋 Bitácora del Huerto")
    st.caption("Registra y consulta todas las actividades realizadas en cada lote.")

    repo = Repository()
    lotes_df = repo.get_lots_df()

    if lotes_df.empty:
        st.warning("⚠️ Primero registra los lotes en Catálogos.")
        return

    lotes_map = dict(zip(lotes_df["nombre"], lotes_df["id"]))
    lotes_opciones = ["Todos los lotes"] + list(lotes_map.keys())

    tab_reg, tab_historial = st.tabs(["➕ Registrar Actividad", "📅 Historial"])

    # ── TAB 1: REGISTRO ────────────────────────────────────────────────────────
    with tab_reg:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            fecha = c1.date_input("Fecha", value=date.today(), key="bit_fecha")
            lote_sel = c2.selectbox("Lote / Huerto", list(lotes_map.keys()), key="bit_lote")

            tipo = st.selectbox("Tipo de actividad", TIPOS_ACTIVIDAD, key="bit_tipo")
            descripcion = st.text_area(
                "¿Qué se hizo?",
                placeholder="Describe la actividad realizada…",
                height=80, key="bit_desc"
            )

            # Producto y dosis solo para fumigación y fertilización
            if tipo in ("Fumigación", "Fertilización"):
                cp, cd = st.columns(2)
                producto = cp.text_input("Producto aplicado", key="bit_prod")
                dosis = cd.text_input("Dosis / Concentración", key="bit_dosis")
            else:
                producto = None
                dosis = None

            responsable = st.text_input(
                "Responsable", placeholder="Nombre de quien realizó la actividad",
                key="bit_resp"
            )
            observaciones = st.text_area(
                "Observaciones adicionales", height=60, key="bit_obs"
            )

            if st.button("💾 Guardar actividad", type="primary", key="bit_save"):
                if not descripcion.strip():
                    st.error("Escribe una descripción de la actividad.")
                else:
                    try:
                        repo.create_bitacora_entry(
                            fecha=str(fecha),
                            lote_id=lotes_map[lote_sel],
                            tipo_actividad=tipo,
                            descripcion=descripcion.strip(),
                            producto=producto or None,
                            dosis=dosis or None,
                            responsable=responsable.strip() or None,
                            observaciones=observaciones.strip() or None,
                        )
                        st.success(f"✅ Actividad registrada: {ICONOS.get(tipo,'')} {tipo} — {lote_sel}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

    # ── TAB 2: HISTORIAL ───────────────────────────────────────────────────────
    with tab_historial:
        # Filtros
        fc1, fc2, fc3 = st.columns(3)
        lote_filtro = fc1.selectbox("Lote", lotes_opciones, key="bit_f_lote")
        hoy = date.today()
        f_ini = fc2.date_input("Desde", value=hoy - timedelta(days=30), key="bit_f_ini")
        f_fin = fc3.date_input("Hasta", value=hoy, key="bit_f_fin")

        lote_id_filtro = lotes_map.get(lote_filtro) if lote_filtro != "Todos los lotes" else None

        df = repo.get_bitacora_df(
            lote_id=lote_id_filtro,
            fecha_inicio=str(f_ini),
            fecha_fin=str(f_fin),
        )

        if df.empty:
            st.info("Sin actividades en este periodo.")
        else:
            # Añadir icono al tipo
            df["Actividad"] = df["tipo_actividad"].map(
                lambda t: f"{ICONOS.get(t, '📋')} {t}"
            )

            # Vista semanal agrupada
            df["fecha_dt"] = pd.to_datetime(df["fecha"])
            df["Semana"] = df["fecha_dt"].dt.to_period("W").apply(
                lambda p: f"{p.start_time.strftime('%d %b')} – {p.end_time.strftime('%d %b %Y')}"
            )

            for semana, grupo in df.groupby("Semana", sort=False):
                with st.expander(f"📅 Semana {semana} — {len(grupo)} actividades", expanded=True):
                    for _, row in grupo.iterrows():
                        with st.container(border=True):
                            col_ico, col_info = st.columns([1, 8])
                            col_ico.markdown(f"## {ICONOS.get(row['tipo_actividad'],'📋')}")
                            with col_info:
                                st.markdown(
                                    f"**{row['tipo_actividad']}** · {row['lote'] or '—'} · "
                                    f"`{row['fecha']}`"
                                )
                                if row.get("descripcion"):
                                    st.write(row["descripcion"])
                                details = []
                                if row.get("producto"):
                                    details.append(f"🧴 **Producto:** {row['producto']}")
                                if row.get("dosis"):
                                    details.append(f"⚗️ **Dosis:** {row['dosis']}")
                                if row.get("responsable"):
                                    details.append(f"👤 **Responsable:** {row['responsable']}")
                                if details:
                                    st.caption(" · ".join(details))
                                if row.get("observaciones"):
                                    st.caption(f"📝 {row['observaciones']}")

                            # Botón borrar solo para el dueño
                            if not modo_encargado:
                                if st.button("🗑️", key=f"bit_del_{row['id']}", help="Eliminar"):
                                    repo.delete_bitacora_entry(int(row["id"]))
                                    st.rerun()
