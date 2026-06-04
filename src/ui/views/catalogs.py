import streamlit as st
import pandas as pd
from src.database.repository import Repository
from src.models.schemas import LotCreate, ThirdPartyCreate
from src.ui.views.vista_encargado import show_cambiar_pin

def show_catalogs():
    st.markdown("### 📂 Catálogos")
    t1, t2, t3 = st.tabs(["Lotes (Huertos)", "Terceros (Personas)", "⚙️ Configuración"])
    repo = Repository()

    with t1:
        c1, c2 = st.columns([1, 2])
        with c1.form("form_lote"):
            st.write("#### Nuevo Lote")
            n = st.text_input("Nombre Lote")
            s = st.number_input("Hectáreas", min_value=0.0)
            if st.form_submit_button("Guardar"):
                if n:
                    try: 
                        repo.create_lot(LotCreate(nombre=n, superficie_ha=s))
                        st.success("Lote guardado.")
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Error (posible duplicado): {e}")
                else:
                    st.error("Nombre requerido.")
        
        with c2:
            st.write("#### Lotes Registrados")
            df = repo.get_lots_df()
            st.dataframe(df, use_container_width=True)

    with t2:
        c1, c2 = st.columns([1, 2])
        with c1.form("form_tercero"):
            st.write("#### Nuevo Tercero")
            n = st.text_input("Nombre")
            r = st.selectbox("Rol", ["Proveedor", "Cliente", "Prestamista", "Empleado"])
            rfc = st.text_input("RFC (Opcional)")
            tel = st.text_input("Teléfono (Opcional)")
            
            if st.form_submit_button("Guardar"):
                if n:
                    try:
                        repo.create_third_party(ThirdPartyCreate(nombre=n, tipo=r, rfc=rfc, telefono=tel))
                        st.success("Tercero guardado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Nombre requerido.")
        
        with c2:
            st.write("#### Personas Registradas")
            df_t = repo.get_third_parties_df()
            st.dataframe(df_t, use_container_width=True)

    with t3:
        st.write("#### ⚙️ Configuración General")
        from src.utils.helpers import cents_to_float, float_to_cents
        
        current_balance_cents = int(repo.get_setting('saldo_inicial_centavos', '0'))
        current_balance_float = cents_to_float(current_balance_cents)
        
        with st.form("form_config"):
            st.info("💰 **Saldo Inicial**: Define cuánto dinero tenías en caja/banco al empezar a usar este sistema. Esto sincronizará tu 'Caja' con la realidad.")
            new_balance = st.number_input("Saldo Inicial ($)", value=current_balance_float, min_value=0.0)
            
            if st.form_submit_button("Guardar Configuración"):
                repo.update_setting('saldo_inicial_centavos', str(float_to_cents(new_balance)))
                st.success("Configuración guardada.")
                st.rerun()

        st.divider()
        show_cambiar_pin()
