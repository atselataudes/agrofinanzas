import streamlit as st
import pandas as pd
import os
from datetime import date
from src.database.repository import Repository
from src.models.schemas import MovementCreate
from src.utils.helpers import float_to_cents, cents_to_float, format_currency, save_uploaded_file
from src.utils.constants import CATALOGO_OPS

def show_movements():
    st.markdown("### Gestión de Operaciones")

    if st.session_state.pop("mov_saved_ok", False):
        st.success("✅ Movimiento guardado correctamente.")

    repo = Repository()
    
    # Fetch needed data
    lotes_df = repo.get_lots_df()
    terceros_df = repo.get_third_parties_df()

    if terceros_df.empty:
        st.warning("⚠️ Ve a Catálogos para registrar Terceros primero.")
        return

    # Maps for Dropdowns
    ters_map = dict(zip(terceros_df['nombre'], terceros_df['id']))
    lotes_map = dict(zip(lotes_df['nombre'], lotes_df['id'])) if not lotes_df.empty else {}
    opc_lotes = ["🏢 Gasto General"] + list(lotes_map.keys())

    tab_nuevo, tab_historial = st.tabs(["➕ Nuevo Movimiento", "📂 Historial y Fotos Pasadas"])

    # --- TAB 1: NEW MOVEMENT ---
    with tab_nuevo:
        with st.container(border=True):
            c_f, c_t, c_c = st.columns([1, 1, 2])
            fecha = c_f.date_input("Fecha Operación", value=date.today())
            tipo_ui = c_t.radio("Tipo", ["Ingreso", "Gasto Huerto", "Gasto Personal"])
            categoria = c_c.selectbox("Categoría", list(CATALOGO_OPS[tipo_ui].keys()))
            
            reglas = CATALOGO_OPS[tipo_ui][categoria]
            st.caption(f"ℹ️ {reglas['ayuda']}")
            
            st.divider()
            c_a, c_b, c_c = st.columns(3)
            
            cant = 0.0
            if reglas['kilos']: 
                cant = c_a.number_input("Cantidad (Kilos/Litros)", min_value=0.0)
            else: 
                c_a.info("🔹 No aplica cantidad")
            
            monto_final = 0.0
            if reglas['precio_unitario']:
                pu = c_b.number_input("Precio Unitario ($)", min_value=0.0)
                monto_final = cant * pu
                c_c.metric("Total", format_currency(monto_final))
            else:
                monto_final = c_b.number_input("Importe Total ($)", min_value=0.0)
                c_c.write("")

            c1, c2, c3 = st.columns(3)
            tercero_nombre = c1.selectbox("Tercero / Cliente / Prov", list(ters_map.keys()))
            notas = c2.text_input("Notas / Referencia")
            
            # Logic for Lot Selection
            lote_id = None
            if reglas['lote'] == 'No': 
                c3.info("🚫 No aplica Lote")
                lote_nm = "N/A"
            elif reglas['lote'] == 'Obligatorio':
                if lotes_map: 
                    lote_nm = c3.selectbox("Huerto (Obligatorio)", list(lotes_map.keys()))
                    lote_id = lotes_map[lote_nm]
                else: 
                    st.error("¡Faltan Lotes!")
                    lote_nm = None
            else: 
                lote_nm = c3.selectbox("Asignar a", opc_lotes)
                if lote_nm != "🏢 Gasto General":
                    lote_id = lotes_map[lote_nm]

            st.divider()
            st.markdown("##### 📷 Evidencia (Opcional)")
            foto = st.file_uploader("Subir foto", type=["jpg","png","pdf"])
            
            if st.button("Guardar Movimiento", type="primary"):
                # VALIDATIONS
                if monto_final <= 0:
                    st.error("El monto debe ser mayor a 0.")
                elif reglas['lote'] == 'Obligatorio' and not lote_id:
                     st.error("Debes seleccionar un lote para esta categoría.")
                else:
                    path = save_uploaded_file(foto)
                    
                    # Create Object
                    mov = MovementCreate(
                        fecha=fecha,
                        tipo="Ingreso" if tipo_ui == "Ingreso" else "Gasto",
                        categoria=categoria,
                        concepto=notas,
                        cantidad=cant,
                        monto_centavos=float_to_cents(monto_final),
                        tercero_id=ters_map[tercero_nombre],
                        lote_id=lote_id,
                        comprobante_path=path
                    )
                    
                    try:
                        repo.create_movement(mov)
                        st.session_state["mov_saved_ok"] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error guardando: {e}")

    # --- TAB 2: HISTORY ---
    with tab_historial:
        st.info("Historial reciente (Últimos 20)")
        df_hist = repo.get_movements_df(limit=20)
        
        if not df_hist.empty:
            # Display format
            df_show = df_hist.copy()
            df_show['Importe'] = df_show['monto_centavos'].apply(lambda x: format_currency(cents_to_float(x)))
            df_show['Lote'] = df_show['lote_nombre'].fillna("🏢 GENERAL")
            df_show['Foto'] = df_show['comprobante_path'].apply(lambda x: "✅" if x else "⬜")
            
            st.dataframe(df_show[['id', 'fecha', 'categoria', 'concepto', 'Importe', 'Lote', 'Foto']], use_container_width=True)
        else:
            st.caption("No hay movimientos registrados aún.")
            
        st.write("---")
        st.subheader("🛠️ Herramientas de Gestión")
        c_adj, c_ver, c_del = st.columns(3)
        
        # 1. ADJUNTAR
        with c_adj.container(border=True):
            st.write("**📎 Adjuntar a Pasado**")
            id_adj = st.number_input("ID Movimiento:", min_value=1, key="id_a")
            file_adj = st.file_uploader("Archivo", key="f_a")
            if st.button("Subir Foto"):
                if file_adj:
                    try:
                        path_a = save_uploaded_file(file_adj)
                        repo.update_movement_evidence(id_adj, path_a)
                        st.success("Foto adjuntada.")
                        st.rerun()
                    except Exception as e:
                       st.error("Error al actualizar (¿Existe el ID?)")

        # 2. VER FOTO
        with c_ver.container(border=True):
            st.write("**👁️ Ver Foto**")
            id_v = st.number_input("ID Movimiento:", min_value=1, key="id_v")
            if st.button("Ver"):
                res = repo.get_movement_by_id(id_v)
                if res and res['comprobante_path']:
                    p = res['comprobante_path']
                    if os.path.exists(p): 
                        if p.endswith(".pdf"): st.info(f"Es PDF: {p}")
                        else: st.image(p)
                    else: st.error("Archivo no encontrado en disco.")
                else: st.warning("Sin foto o ID no encontrado.")

        # 3. BORRAR
        with c_del.container(border=True):
            st.write("**🗑️ Borrar**")
            id_d = st.number_input("ID a Borrar:", min_value=1, key="id_d")
            confirm_key = f"confirm_del_{id_d}"
            if not st.session_state.get(confirm_key, False):
                if st.button("Eliminar", key="btn_del_init"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning(f"¿Seguro? Se borrará el movimiento #{id_d}.")
                col_si, col_no = st.columns(2)
                if col_si.button("✅ Sí, borrar", type="primary", key="btn_del_confirm"):
                    try:
                        repo.delete_movement(id_d)
                        st.session_state.pop(confirm_key, None)
                        st.success("Borrado.")
                        st.rerun()
                    except:
                        st.error("Error al borrar.")
                if col_no.button("❌ Cancelar", key="btn_del_cancel"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
