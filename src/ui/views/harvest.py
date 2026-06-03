import streamlit as st
import pandas as pd
from datetime import date
from src.database.repository import Repository
from src.services.harvest import register_harvest
from src.utils.helpers import format_currency, float_to_cents

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
            ["📊 Por calibre (precio individual)", "⚖️ Precio promedio (un solo precio)"],
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
