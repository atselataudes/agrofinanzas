import streamlit as st
import pandas as pd
from datetime import date
from src.database.repository import Repository
from src.models.schemas import ProductCreate, MovementCreate
from src.utils.helpers import float_to_cents
from src.ui.components import metric_card

def show_inventory():
    st.markdown("### 📦 Inventario de Productos")
    repo = Repository()
    
    tab1, tab2 = st.tabs(["Stock Actual", "🛒 Registrar Producto"])
    
    with tab1:
        df_inv = repo.get_products_df()
        
        if not df_inv.empty:
            # Metrics
            total_items = len(df_inv)
            low_stock = len(df_inv[df_inv['stock_actual'] < 10])
            
            c1, c2 = st.columns(2)
            with c1: metric_card("Total Productos", str(total_items))
            with c2: metric_card("Bajo Stock (<10)", str(low_stock), color="inverse" if low_stock > 0 else "normal")
            
            st.divider()
            
            # Display Grid
            for i, row in df_inv.iterrows():
                with st.container():
                    c_n, c_s, c_u, c_act = st.columns([3, 1, 1, 2])
                    c_n.markdown(f"**{row['nombre']}**")
                    c_n.caption(row['tipo'])
                    
                    c_s.markdown(f"**{row['stock_actual']}**")
                    c_u.caption(row['unidad_medida'])
                    
                    with c_act:
                        with st.popover("⚙️ Gestionar"):
                            st.write(f"**{row['nombre']}**")
                            val = st.number_input(f"Cantidad {row['unidad_medida']}", min_value=0.0, key=f"adj_{row['id']}")
                            
                            c_b1, c_b2 = st.columns(2)
                            if c_b1.button("➕ Stock", key=f"add_{row['id']}"):
                                repo.update_product_stock(row['id'], val, "add")
                                st.rerun()
                            if c_b2.button("➖ Uso", key=f"sub_{row['id']}"):
                                repo.update_product_stock(row['id'], val, "subtract")
                                st.rerun()
                            
                            st.divider()
                            st.write("🛒 **Registrar Compra (Contable)**")
                            costo = st.number_input("Costo Total $", min_value=0.0, key=f"cost_{row['id']}")
                            if st.button("💰 Registrar Compra y +\nStock", key=f"buy_{row['id']}", type="primary"):
                                if val > 0 and costo > 0:
                                    # 1. Update Stock
                                    repo.update_product_stock(row['id'], val, "add")
                                    # 2. Record Gasto
                                    mov = MovementCreate(
                                        fecha=date.today(),
                                        tipo="Gasto",
                                        categoria="Agroquímicos / Insumos",
                                        concepto=f"Compra de {val} {row['unidad_medida']} de {row['nombre']}",
                                        monto_centavos=float_to_cents(costo),
                                        cantidad=val
                                    )
                                    repo.create_movement(mov)
                                    st.success("Compra y stock actualizados.")
                                    st.rerun()
                                else:
                                    st.error("Cantidad y costo requeridos.")
                    st.divider()
        else:
            st.info("No hay productos registrados. Ve a la pestaña 'Registrar Producto'.")

    with tab2:
        with st.form("new_prod"):
            st.write("#### Nuevo Producto")
            n = st.text_input("Nombre Comercial")
            t = st.selectbox("Tipo", ["Fertilizante", "Foliar", "Herbicida", "Otro"])
            u = st.selectbox("Unidad", ["Litros", "Kilos", "Sacos", "Piezas"])
            s = st.number_input("Stock Inicial", min_value=0.0)
            
            if st.form_submit_button("Guardar Producto"):
                if n:
                    try:
                        repo.create_product(ProductCreate(nombre=n, tipo=t, unidad_medida=u, stock_actual=s))
                        st.success(f"Producto {n} creado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("El nombre es obligatorio.")
