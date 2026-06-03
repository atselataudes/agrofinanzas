import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, format_currency
from src.ui.components import metric_card

def show_journal():
    st.markdown("### 📒 Libro Diario")
    repo = Repository()
    
    # Range of dates (defaults to last 30 days)
    today = date.today()
    default_start = today - timedelta(days=30)
    
    with st.sidebar.expander("🔍 Filtros de Diario", expanded=True):
        show_all = st.checkbox("Ver Todo el Historial", value=False)
        if show_all:
            start_date = date(2000, 1, 1)
            end_date = date(2100, 1, 1)
        else:
            start_date = st.date_input("Fecha Inicio", value=default_start)
            end_date = st.date_input("Fecha Fin", value=today)
        
        tipo_filtro = st.multiselect("Tipo de Movimiento", ["Ingreso", "Gasto"], default=["Ingreso", "Gasto"])

    # Fetch all movements
    df = repo.get_movements_df()
    
    if df.empty:
        st.info("No hay movimientos registrados.")
        return

    # Filter data
    df['fecha_dt'] = pd.to_datetime(df['fecha']).dt.date
    mask = (df['fecha_dt'] >= start_date) & (df['fecha_dt'] <= end_date)
    if tipo_filtro:
        mask &= df['tipo'].isin(tipo_filtro)
    
    df_filtered = df.loc[mask].copy()

    if df_filtered.empty:
        st.warning("No hay movimientos para el rango seleccionado.")
        return

    # Calculate Totals
    df_filtered['Monto'] = df_filtered['monto_centavos'].apply(cents_to_float)
    total_ing = df_filtered[df_filtered['tipo']=='Ingreso']['Monto'].sum()
    total_gas = df_filtered[df_filtered['tipo']=='Gasto']['Monto'].sum()
    
    saldo_inicial_cents = int(repo.get_setting('saldo_inicial_centavos', '0'))

    # Solo incluir saldo inicial cuando se ve todo el historial
    if show_all:
        balance = cents_to_float(saldo_inicial_cents) + total_ing - total_gas
        balance_label = "Saldo Acumulado"
    else:
        balance = total_ing - total_gas
        balance_label = "Flujo Neto del Periodo"

    # Display Metrics
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("Ingresos Periodo", format_currency(total_ing))
    with c2: metric_card("Gastos Periodo", format_currency(total_gas), color="inverse")
    with c3: metric_card(balance_label, format_currency(balance), color="normal" if balance >= 0 else "inverse")

    st.divider()

    # Table View
    df_display = df_filtered.copy()
    df_display = df_display.sort_values('fecha', ascending=False)
    
    # Formatting for display
    df_display['Monto_Formato'] = df_display.apply(
        lambda x: f"🟢 {format_currency(x['Monto'])}" if x['tipo'] == 'Ingreso' else f"🔴 {format_currency(x['Monto'])}", 
        axis=1
    )
    
    # Drop existing Monto column (numeric) to avoid duplicates when renaming Monto_Formato to Monto
    df_display = df_display.drop(columns=['Monto'])
    
    df_display = df_display.rename(columns={
        'fecha': 'Fecha',
        'categoria': 'Categoría',
        'concepto': 'Concepto',
        'tercero_nombre': 'Tercero',
        'lote_nombre': 'Lote/Huerto',
        'Monto_Formato': 'Monto'
    })

    st.dataframe(
        df_display[['Fecha', 'Categoría', 'Concepto', 'Monto', 'Tercero', 'Lote/Huerto']], 
        use_container_width=True, 
        hide_index=True
    )

    # Download Option
    csv = df_display[['Fecha', 'Categoría', 'Concepto', 'Monto', 'Tercero', 'Lote/Huerto']].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 Descargar Diario (CSV)",
        csv,
        f"Libro_Diario_{start_date}_{end_date}.csv",
        "text/csv",
        key='download-csv'
    )
