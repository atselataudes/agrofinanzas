import streamlit as st
import pandas as pd
from datetime import date
from src.database.repository import Repository
from src.models.schemas import LoanCreate
from src.services.credits import create_loan_with_movement, register_payment
from src.utils.helpers import float_to_cents, cents_to_float, format_currency

def show_credits():
    st.markdown("### 🏦 Gestión de Deuda")
    repo = Repository()

    # --- UNDO LOGIC ---
    if "last_deleted_loan_id" in st.session_state:
        loan_id = st.session_state["last_deleted_loan_id"]
        col_undo_1, col_undo_2 = st.columns([5, 1])
        col_undo_1.warning(f"⚠️ Crédito #{loan_id} marcado como eliminado.")
        if col_undo_2.button("Deshacer", type="primary"):
            repo.restore_loan(loan_id)
            del st.session_state["last_deleted_loan_id"]
            st.success("Acción desecha. Crédito restaurado.")
            st.rerun()

    c1, c2 = st.columns(2)
    
    # Fetch Data
    terceros_df = repo.get_third_parties_df()
    
    # --- NEW LOAN ---
    with c1.container(border=True):
        st.write("#### ➕ Nuevo Crédito")
        if not terceros_df.empty:
            pres_nombre = st.selectbox("Acreedor", terceros_df['nombre'])
            dinero_entra = st.checkbox("¿Registrar entrada de dinero a caja?")
            monto = st.number_input("Monto Prestado ($)", min_value=0.0)
            tasa = st.number_input("Tasa Interés Anual %", min_value=0.0)
            fi = st.date_input("Fecha Inicio", value=date.today())
            fv = st.date_input("Fecha Vencimiento")
            notas = st.text_input("Notas / Garantía")
            
            if st.button("Crear Crédito", type="primary"):
                if monto > 0:
                    try:
                        tercero_id = int(terceros_df[terceros_df['nombre']==pres_nombre]['id'].values[0])
                        loan = LoanCreate(
                            tercero_id=tercero_id,
                            fecha_inicio=fi,
                            fecha_vencimiento=fv,
                            monto_capital_centavos=float_to_cents(monto),
                            tasa_interes_anual=tasa,
                            notas=notas
                        )
                        create_loan_with_movement(repo, loan, pres_nombre, dinero_entra)
                        st.success("Crédito creado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.error("Monto debe ser mayor a 0.")
        else:
            st.warning("Registra terceros primero.")

    # --- PAY LOAN ---
    with c2.container(border=True):
        st.write("#### 💸 Abonar a Deuda")
        df_loans = repo.get_active_loans_df()
        
        if not df_loans.empty:
            # Create a selection list
            opts = []
            loan_map = {}
            for i, r in df_loans.iterrows():
                saldo = cents_to_float(r['monto_capital_centavos'] - r['monto_pagado_centavos'])
                label = f"#{r['id']} {r['acreedor_nombre']} (Saldo: {format_currency(saldo)})"
                opts.append(label)
                loan_map[label] = r['id']
            
            sel = st.selectbox("Selecciona Deuda", opts)
            loan_id = loan_map[sel]
            
            fp = st.date_input("Fecha del Pago", value=date.today())
            abono = st.number_input("Monto Abono ($)", min_value=0.0)
            
            if st.button("Registrar Abono"):
                if abono > 0:
                    try:
                        fully_paid = register_payment(repo, loan_id, abono, fp)

                        if fully_paid:
                            st.balloons()
                            st.success("¡Deuda liquidada!")
                        else:
                            st.success("Abono registrado.")
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("No hay deudas activas.")

    st.divider()

    # --- MANUAL MODIFICATION ---
    st.write("#### 🛠️ Ajuste Manual de Saldo")
    all_loans = repo.get_dataframe("SELECT p.*, t.nombre as acreedor_nombre FROM fin_prestamos p JOIN cat_terceros t ON p.tercero_id = t.id")
    
    if not all_loans.empty:
        l_opts = [f"#{r['id']} {r['acreedor_nombre']}" for i, r in all_loans.iterrows()]
        l_sel = st.selectbox("Selecciona Crédito para ajustar", l_opts)
        l_id = int(l_sel.split(" ")[0].replace("#", ""))
        
        l_data = all_loans[all_loans['id'] == l_id].iloc[0]
        
        col_adj1, col_adj2 = st.columns(2)
        new_cap = col_adj1.number_input("Nuevo Capital ($)", value=cents_to_float(l_data['monto_capital_centavos']))
        new_pag = col_adj2.number_input("Nuevo Pagado ($)", value=cents_to_float(l_data['monto_pagado_centavos']))
        
        # Use a checkbox for "Unlock" or a popover for confirmation as per Streamlit best practices
        with st.expander("⚠️ Zona de Peligro"):
            st.warning("Esto modificará directamente los valores en la base de datos sin crear movimientos contables.")
            if st.button("Confirmar Cambio Manual", type="primary", use_container_width=True):
                try:
                    repo.update_loan_balance_manually(l_id, float_to_cents(new_cap), float_to_cents(new_pag))
                    st.success("Saldo ajustado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            
            st.divider()
            st.error("💣 Acción Permanente")
            if st.button("Eliminar Registro de Crédito", type="primary", use_container_width=True, key="del_loan_btn"):
                try:
                    repo.delete_loan(l_id)
                    st.session_state["last_deleted_loan_id"] = l_id
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
    else:
        st.info("No hay créditos para ajustar.")
