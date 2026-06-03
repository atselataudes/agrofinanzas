import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, format_currency
from src.utils.constants import CATEGORIAS_PERSONALES
from src.ui.components import metric_card

def show_dashboard():
    repo = Repository()
    
    # Fetch Data
    df_movs = repo.get_dataframe("SELECT tipo, monto_centavos, fecha, categoria, cantidad FROM fin_movimientos")
    
    if df_movs.empty:
        st.markdown("### 👋 Bienvenido a AgroFinanzas Pro")
        st.markdown("Sigue estos pasos para empezar:")
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("#### 1️⃣ Catálogos")
                st.caption("Agrega tus proveedores, clientes y huertos antes de registrar movimientos.")
                if st.button("Ir a Catálogos →", key="dash_goto_cat"):
                    st.session_state["_nav"] = "📂 Catálogos"   # label sin cambio
                    st.rerun()
        with c2:
            with st.container(border=True):
                st.markdown("#### 2️⃣ Primer Movimiento")
                st.caption("Registra un ingreso o gasto desde 'Otros Movimientos' o con foto desde 'Captura Inteligente'.")
                if st.button("Registrar Movimiento →", key="dash_goto_mov"):
                    st.session_state["_nav"] = "🤖 Captura"
                    st.rerun()
        with c3:
            with st.container(border=True):
                st.markdown("#### 3️⃣ Ver Reportes")
                st.caption("Una vez que tengas datos, aquí verás tu utilidad, gastos por categoría y KPIs.")
                st.info("Disponible con datos registrados.")
        return

    # 1. CAJA (Saldo Inicial + Ingresos - Gastos)
    saldo_inicial_cents = int(repo.get_setting('saldo_inicial_centavos', '0'))
    ing_tot = df_movs[df_movs['tipo']=='Ingreso']['monto_centavos'].sum()
    gas_tot = df_movs[df_movs['tipo']=='Gasto']['monto_centavos'].sum()
    saldo = saldo_inicial_cents + ing_tot - gas_tot

    # 2. NEGOCIO
    # Exclude loans and personal expenses for Business Logic
    df_neg = df_movs[~df_movs['categoria'].isin(['Financiamiento', 'Pago Deuda'] + CATEGORIAS_PERSONALES)]
    v_huerto = df_neg[df_neg['tipo']=='Ingreso']['monto_centavos'].sum()
    g_huerto = df_neg[df_neg['tipo']=='Gasto']['monto_centavos'].sum()
    util_huerto = v_huerto - g_huerto

    # 3. PERSONAL
    g_pers = df_movs[df_movs['categoria'].isin(CATEGORIAS_PERSONALES)]['monto_centavos'].sum()

    # 4. DEUDA (Active Only)
    df_d = repo.get_dataframe("SELECT * FROM fin_prestamos WHERE estado='Activo'")
    deuda = 0.0
    if not df_d.empty:
        for i, r in df_d.iterrows():
            c = cents_to_float(r['monto_capital_centavos'])
            p = cents_to_float(r['monto_pagado_centavos'])
            s = c - p
            fi = date.fromisoformat(r['fecha_inicio'])
            d = (date.today() - fi).days
            # Simple daily interest calculation logic from original app
            inte = s * (r['tasa_interes_anual']/100) * (d/365) if d>0 else 0
            deuda += (s + inte)

    st.markdown("### 📊 Resumen Financiero")
    
    # Top Row Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("💰 Caja (Efectivo)", format_currency(cents_to_float(saldo)))
    with c2:
        metric_card("🚜 Utilidad Huerto", format_currency(cents_to_float(util_huerto)), "Negocio")
    with c3:
        metric_card("🏠 Gasto Personal", format_currency(cents_to_float(g_pers)), "Retiro", "inverse")
    with c4:
        metric_card("🏦 Deuda Total", format_currency(deuda), "A Pagar", "inverse")

    st.divider()

    # ── Gráfica de tendencia mensual ────────────────────────────────────────
    st.markdown("#### 📅 Ingresos vs Gastos por Mes")
    df_trend = df_movs.copy()
    df_trend['fecha_dt'] = pd.to_datetime(df_trend['fecha'], errors='coerce')
    df_trend = df_trend.dropna(subset=['fecha_dt'])
    df_trend['Mes'] = df_trend['fecha_dt'].dt.to_period('M').astype(str)
    df_trend['Monto'] = df_trend['monto_centavos'].apply(cents_to_float)
    df_trend_g = df_trend.groupby(['Mes', 'tipo'])['Monto'].sum().reset_index()

    if not df_trend_g.empty:
        trend_chart = alt.Chart(df_trend_g).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X('Mes:N', title=None, sort=None, axis=alt.Axis(labelAngle=-35)),
            y=alt.Y('Monto:Q', title='Monto ($)', axis=alt.Axis(format='$,.0f')),
            color=alt.Color('tipo:N',
                scale=alt.Scale(domain=['Ingreso', 'Gasto'], range=['#2e7d32', '#d32f2f']),
                legend=alt.Legend(title=None, orient='top')
            ),
            xOffset='tipo:N',
            tooltip=[
                alt.Tooltip('Mes:N', title='Mes'),
                alt.Tooltip('tipo:N', title='Tipo'),
                alt.Tooltip('Monto:Q', title='Monto', format='$,.2f')
            ]
        ).properties(height=220)
        st.altair_chart(trend_chart, use_container_width=True)

    st.divider()

    # ── Gráficas de distribución ─────────────────────────────────────────────
    c_charts_1, c_charts_2 = st.columns([1, 1])

    with c_charts_1:
        st.markdown("#### 🚜 Huerto vs Personal")
        dp = pd.DataFrame({
            'Tipo': ['Gasto Huerto', 'Gasto Personal'],
            'Monto': [cents_to_float(g_huerto), cents_to_float(g_pers)]
        })
        if dp['Monto'].sum() > 0:
            dp['Porcentaje'] = dp['Monto'] / dp['Monto'].sum()
            pie = alt.Chart(dp).mark_arc(outerRadius=110).encode(
                theta=alt.Theta("Monto:Q", stack=True),
                color=alt.Color("Tipo:N",
                    scale=alt.Scale(domain=['Gasto Huerto', 'Gasto Personal'], range=['#d32f2f', '#1976d2']),
                    legend=alt.Legend(title=None, orient='bottom')
                ),
                order=alt.Order("Monto:Q", sort="descending"),
                tooltip=["Tipo:N", alt.Tooltip("Monto:Q", format="$,.2f"), alt.Tooltip("Porcentaje:Q", format=".1%")]
            ).properties(height=240)
            st.altair_chart(pie, use_container_width=True)
        else:
            st.info("Sin gastos registrados.")

    with c_charts_2:
        st.markdown("#### 📉 Top 5 Gastos del Huerto")
        df_ch = df_neg[df_neg['tipo'] == 'Gasto'].copy()
        if not df_ch.empty:
            df_ch['Monto'] = df_ch['monto_centavos'].apply(cents_to_float)
            ch = df_ch.groupby("categoria")["Monto"].sum().sort_values(ascending=False).reset_index().head(5)
            bar = alt.Chart(ch).mark_bar(cornerRadiusEnd=4).encode(
                x=alt.X("Monto:Q", title=None, axis=alt.Axis(format='$,.0f')),
                y=alt.Y("categoria:N", sort="-x", title=None),
                color=alt.Color("categoria:N", scale=alt.Scale(scheme="tableau10"), legend=None),
                tooltip=[alt.Tooltip("categoria:N", title="Categoría"), alt.Tooltip("Monto:Q", format="$,.2f")]
            ).properties(height=240)
            st.altair_chart(bar, use_container_width=True)
        else:
            st.caption("Sin datos.")

    # KPIs colapsables
    with st.expander("📈 Indicadores Clave (KPIs)", expanded=False):
        df_neg_kpi = df_movs[~df_movs['categoria'].isin(['Financiamiento', 'Pago Deuda'] + CATEGORIAS_PERSONALES)].copy()
        if not df_neg_kpi.empty:
            df_neg_kpi['Monto'] = df_neg_kpi['monto_centavos'].apply(cents_to_float)
            ingresos_neg = df_neg_kpi[df_neg_kpi['tipo']=='Ingreso']['Monto'].sum()
            gastos_neg   = df_neg_kpi[df_neg_kpi['tipo']=='Gasto']['Monto'].sum()
            util_op      = ingresos_neg - gastos_neg
            df_ventas_kpi = df_neg_kpi[(df_neg_kpi['tipo']=='Ingreso') & (df_neg_kpi['categoria'].str.contains("Venta", case=False, na=False))]
            total_kg     = df_ventas_kpi['cantidad'].sum()
            margen       = (util_op / ingresos_neg) if ingresos_neg > 0 else 0.0
            costo_kg     = (gastos_neg / total_kg) if total_kg > 0 else 0.0
            precio_prom  = (df_ventas_kpi['Monto'].sum() / total_kg) if total_kg > 0 else 0.0
            ck1, ck2, ck3 = st.columns(3)
            ck1.metric("Margen Utilidad", f"{margen:.1%}", help="(Ingresos − Gastos) / Ingresos")
            ck2.metric("Costo por Kg", format_currency(costo_kg), help="Gasto Total / Kilos vendidos")
            ck3.metric("Precio Prom. Venta", format_currency(precio_prom), help="Venta Total / Kilos vendidos")
        else:
            st.info("Registra ingresos y gastos de negocio para ver los KPIs.")

    st.divider()

    # Recent Activity Feed
    st.markdown("#### 🕒 Actividad Reciente")
    recent = repo.get_movements_df(limit=8)
    if not recent.empty:
        recent["Tipo"] = recent["tipo"].map(lambda t: "🟢 Ingreso" if t == "Ingreso" else "🔴 Gasto")
        recent["Monto"] = recent["monto_centavos"].apply(lambda x: format_currency(cents_to_float(x)))
        recent["Concepto"] = recent["concepto"].fillna("—")
        st.dataframe(
            recent[["fecha", "Tipo", "categoria", "Concepto", "Monto", "tercero_nombre"]].rename(columns={
                "fecha": "Fecha", "categoria": "Categoría", "tercero_nombre": "Tercero"
            }),
            use_container_width=True,
            hide_index=True,
        )
