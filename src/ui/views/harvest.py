import streamlit as st
import pandas as pd
from datetime import date
from src.database.repository import Repository
from src.services.harvest import register_harvest
from src.utils.helpers import format_currency, float_to_cents
from src.ai.parser import analizar_ticket_pesado

def show_harvest():
    st.markdown("### 🥑 Registro de Corte (Cosecha)")
    repo = Repository()
    
    # Init Repo Data
    lotes_df = repo.get_lots_df()
    terceros_df = repo.get_third_parties_df()
    
    if lotes_df.empty or terceros_df.empty:
        st.warning("⚠️ Debes registrar Lotes y Terceros (Clientes) primero.")
        return

    lotes_map = dict(zip(lotes_df['nombre'], lotes_df['id']))
    clientes_map = dict(zip(terceros_df['nombre'], terceros_df['id']))
    
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        fecha = c1.date_input("Fecha de Corte", value=date.today())
        lote_sel = c2.selectbox("Huerto Origen", list(lotes_map.keys()))
        cliente_sel = c3.selectbox("Cliente (Comprador)", list(clientes_map.keys()))
        
        st.divider()

        modo = st.radio(
            "Modo de captura",
            ["📊 Por calibre (precio individual)", "⚖️ Precio promedio (un solo precio)", "📷 Desde ticket de báscula"],
            horizontal=True,
            key="harvest_modo",
        )

        calibres = ["Jumbo", "Extra", "Primera", "Segunda", "Canica", "Descarte"]
        details = []
        total_kilos = 0.0
        total_monto = 0.0

        if modo.startswith("📊"):
            st.markdown("#### Desglose por Calibres")
            st.caption("Ingresa los kilos y precio de cada calibre que trajo el corte.")

            _calibres_base = pd.DataFrame({
                "Calibre": calibres,
                "Kilos": [0.0] * len(calibres),
                "Precio $": [0.0] * len(calibres),
            })
            edited = st.data_editor(
                _calibres_base,
                column_config={
                    "Calibre": st.column_config.TextColumn(disabled=True, width="small"),
                    "Kilos":   st.column_config.NumberColumn(min_value=0.0, format="%.1f", width="small"),
                    "Precio $": st.column_config.NumberColumn(min_value=0.0, format="$%.2f", width="small"),
                },
                hide_index=True,
                use_container_width=True,
                key="calibres_editor",
            )
            for _, row in edited.iterrows():
                k = float(row["Kilos"])
                p = float(row["Precio $"])
                if k > 0:
                    subtotal = k * p
                    details.append({"calibre": row["Calibre"], "kilos": k, "precio_kg": p, "subtotal": subtotal})
                    total_kilos += k
                    total_monto += subtotal

        elif modo.startswith("📷"):  # ticket de báscula
            st.markdown("#### 📷 Ticket de Báscula")
            st.caption("Sube la foto del ticket — la IA extrae los kilos por calibre. Tú solo pones el precio.")

            ticket_foto = st.file_uploader(
                "Foto del ticket (jpg, png)",
                type=["jpg", "jpeg", "png", "webp"],
                key="ticket_uploader",
            )

            if ticket_foto:
                col_img, col_btn = st.columns([2, 1])
                col_img.image(ticket_foto, caption="Vista previa del ticket", use_container_width=True)

                if col_btn.button("🔍 Leer ticket con IA", type="primary", key="ticket_analizar"):
                    with st.spinner("Leyendo ticket…"):
                        ext = ticket_foto.name.lower().split(".")[-1]
                        mtype = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                 "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                        resultado = analizar_ticket_pesado(ticket_foto.read(), mtype)
                        st.session_state["ticket_resultado"] = resultado
                        # Pre-llenar fecha si la IA la extrajo
                        if resultado.get("fecha") and not resultado.get("error"):
                            try:
                                from datetime import datetime
                                st.session_state["ticket_fecha"] = datetime.strptime(resultado["fecha"], "%Y-%m-%d").date()
                            except Exception:
                                pass
                    st.rerun()

            # Mostrar resultado de la IA
            if "ticket_resultado" in st.session_state:
                datos = st.session_state["ticket_resultado"]

                if "error" in datos:
                    st.error(f"❌ {datos['error']}")
                    if st.button("Limpiar", key="ticket_clear"):
                        st.session_state.pop("ticket_resultado", None)
                        st.rerun()
                else:
                    # Info extraída
                    folio = datos.get("folio") or "—"
                    total_ext = datos.get("total_kilos") or 0
                    st.success(f"✅ Ticket leído — Folio: **{folio}** · Total extraído: **{total_ext:,.1f} kg**")

                    total_ext = datos.get("total_kilos") or 0.0
                    st.markdown("##### Confirma los kilos y agrega el precio")
                    ca, cb = st.columns(2)
                    total_kilos = ca.number_input(
                        "Total Kilos", min_value=0.0, value=float(total_ext),
                        format="%.1f", key="ticket_kilos"
                    )
                    precio_ticket = cb.number_input(
                        "Precio ($ / kg)", min_value=0.0, format="%.2f",
                        key="ticket_precio_unico"
                    )
                    if total_kilos > 0 and precio_ticket > 0:
                        total_monto = total_kilos * precio_ticket
                        details.append({
                            "calibre": "Pela Palo",
                            "kilos": total_kilos,
                            "precio_kg": precio_ticket,
                            "subtotal": total_monto,
                        })

        else:  # precio promedio
            st.markdown("#### Captura por Precio Promedio")
            ca, cb = st.columns(2)
            total_kilos = ca.number_input("Total de Kilos", min_value=0.0, key="harvest_kilos_prom")
            precio_prom = cb.number_input("Precio Promedio ($ / kg)", min_value=0.0, key="harvest_precio_prom")
            if total_kilos > 0 and precio_prom > 0:
                total_monto = total_kilos * precio_prom
                details.append({"calibre": "Promedio", "kilos": total_kilos, "precio_kg": precio_prom, "subtotal": total_monto})

        st.divider()
        c_res1, c_res2, c_res3 = st.columns(3)
        c_res1.metric("Total Kilos", f"{total_kilos:,.2f} kg")
        c_res2.metric("Venta Total", format_currency(total_monto))
        avg_price = (total_monto / total_kilos) if total_kilos > 0 else 0
        c_res3.metric("Precio Promedio", format_currency(avg_price))
        
        if st.button("💾 Guardar Corte", type="primary"):
            if total_monto > 0:
                try:
                    register_harvest(
                        repo=repo,
                        fecha=fecha,
                        lote_nombre=lote_sel,
                        lote_id=lotes_map[lote_sel],
                        cliente_id=clientes_map[cliente_sel],
                        details=details,
                    )
                    st.balloons()
                    st.success("✅ Corte registrado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.error("El monto total debe ser mayor a 0.")
