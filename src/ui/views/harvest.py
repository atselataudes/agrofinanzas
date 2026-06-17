import streamlit as st
import pandas as pd
from datetime import date
from src.database.repository import Repository
from src.services.harvest import register_harvest
from src.utils.helpers import format_currency, float_to_cents
from src.ai.parser import analizar_ticket_pesado
from src.utils.helpers import save_uploaded_file

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
        _clientes_list = list(clientes_map.keys())
        _default_idx = _clientes_list.index("otro") if "otro" in _clientes_list else (
            _clientes_list.index("Otro") if "Otro" in _clientes_list else 0
        )
        cliente_sel = c3.selectbox("Cliente (Comprador)", _clientes_list, index=_default_idx)
        
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
                        img_bytes = ticket_foto.read()
                        resultado = analizar_ticket_pesado(img_bytes, mtype)
                        st.session_state["ticket_resultado"] = resultado
                        # Guardar foto del ticket en disco
                        ticket_foto.seek(0)
                        path = save_uploaded_file(ticket_foto)
                        st.session_state["ticket_foto_path"] = path
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
                    folio = datos.get("folio") or None
                    total_ext = datos.get("total_kilos") or 0

                    # Validar folio duplicado
                    if folio and repo.folio_exists(folio):
                        st.error(f"⛔ El folio **{folio}** ya fue registrado anteriormente. No se puede registrar dos veces el mismo ticket.")
                        if st.button("Limpiar", key="ticket_clear_dup"):
                            for k in ["ticket_resultado", "ticket_foto_path"]:
                                st.session_state.pop(k, None)
                            st.rerun()
                        # Salir sin mostrar el formulario
                    else:
                        st.success(f"✅ Ticket leído — Folio: **{folio or '(sin folio)'}** · Total extraído: **{datos.get('total_kilos') or 0:,.1f} kg**")
                        st.markdown("##### Confirma los kilos y agrega el precio")
                        ca, cb = st.columns(2)
                        total_kilos = ca.number_input(
                            "Total Kilos", min_value=0.0,
                            value=float(datos.get("total_kilos") or 0.0),
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

        # ── % de participación ───────────────────────────────────────────────
        cp1, cp2 = st.columns([2, 1])
        tipo_venta = cp1.radio(
            "Tipo de venta",
            ["🌍 Exportación (socios al 50%)", "🇲🇽 Nacional (100% nuestro)"],
            horizontal=True,
            key="harvest_tipo_venta",
        )
        pct_default = 50.0 if tipo_venta.startswith("🌍") else 100.0
        mi_parte_pct = cp2.number_input(
            "% mi parte", min_value=1.0, max_value=100.0,
            value=pct_default, format="%.0f", key="harvest_mi_parte"
        )

        total_venta_bruta = total_monto
        mi_ingreso = total_venta_bruta * (mi_parte_pct / 100)

        c_res1, c_res2, c_res3, c_res4 = st.columns(4)
        c_res1.metric("Total Kilos", f"{total_kilos:,.2f} kg")
        c_res2.metric("Venta Total", format_currency(total_venta_bruta))
        c_res3.metric(f"Mi {mi_parte_pct:.0f}%", format_currency(mi_ingreso),
                      delta=f"-{format_currency(total_venta_bruta - mi_ingreso)} socio" if mi_parte_pct < 100 else None)
        avg_price = (total_venta_bruta / total_kilos) if total_kilos > 0 else 0
        c_res4.metric("Precio Prom.", format_currency(avg_price))
        
        st.divider()
        # ── Condiciones de pago ──────────────────────────────────────────────
        cp_a, cp_b = st.columns([2, 1])
        es_credito = cp_a.toggle("💳 Venta a crédito (pago diferido)", value=True, key="harvest_credito")
        dias_credito = cp_b.number_input("Días crédito", min_value=1, max_value=90,
                                         value=22, key="harvest_dias_credito") if es_credito else 0
        if es_credito:
            from datetime import timedelta
            fecha_cobro = fecha + timedelta(days=int(dias_credito))
            st.caption(f"📅 Fecha estimada de cobro: **{fecha_cobro.strftime('%d/%m/%Y')}**")
        else:
            fecha_cobro = None

        if st.button("💾 Guardar Corte", type="primary"):
            if total_monto > 0:
                try:
                    # Aplicar % de participación a cada detalle
                    factor = mi_parte_pct / 100
                    details_ajustados = [
                        {**d, "subtotal": d["subtotal"] * factor}
                        for d in details
                    ]

                    # Foto del ticket (si viene de modo ticket)
                    ticket_path = st.session_state.get("ticket_foto_path")
                    ticket_folio = None
                    if "ticket_resultado" in st.session_state:
                        ticket_folio = st.session_state["ticket_resultado"].get("folio")

                    mov_id = register_harvest(
                        repo=repo,
                        fecha=fecha,
                        lote_nombre=lote_sel,
                        lote_id=lotes_map[lote_sel],
                        cliente_id=clientes_map[cliente_sel],
                        details=details_ajustados,
                        comprobante_path=ticket_path,
                        folio=ticket_folio,
                        es_credito=1 if es_credito else 0,
                        fecha_cobro=str(fecha_cobro) if fecha_cobro else None,
                    )

                    # Registrar folio con todos los datos para historial
                    if ticket_folio:
                        datos_ticket = st.session_state.get("ticket_resultado", {})
                        repo.register_folio(
                            folio=ticket_folio,
                            movement_id=mov_id,
                            empaque=datos_ticket.get("empaque"),
                            cliente=cliente_sel,
                            lote=lote_sel,
                            fecha_ticket=datos_ticket.get("fecha"),
                            total_kilos=sum(d["kilos"] for d in details),
                            precio_kg=details[0]["precio_kg"] if details else None,
                            total_monto=sum(d["subtotal"] for d in details),
                        )

                    # Limpiar estado del ticket
                    for k in ["ticket_resultado", "ticket_foto_path"]:
                        st.session_state.pop(k, None)

                    st.balloons()
                    st.success("✅ Corte registrado exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.error("El monto total debe ser mayor a 0.")
