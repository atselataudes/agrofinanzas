import os
import shutil
import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, format_currency
from src.utils.constants import CATEGORIAS_PERSONALES
from config import Config

def show_reports(ocultar_personal: bool = False):
    st.markdown("### 📊 Reportes Gerenciales")
    _tabs_base = ["💼 Balance General", "Negocio", "Deudas", "Lotes", "🎫 Tickets", "💾 Exportar"]
    if not ocultar_personal:
        _tabs_base.insert(2, "Personal")
    _tabs = _tabs_base
    _tab_objs = st.tabs(_tabs)
    repo = Repository()

    # Fetch all data once for processing
    df_all = repo.get_movements_df()

    # Mapeo dinámico de tabs según modo
    def _tab(nombre):
        idx = _tabs.index(nombre) if nombre in _tabs else None
        return _tab_objs[idx] if idx is not None else None

    # --- TAB BALANCE GENERAL ---
    with _tab("💼 Balance General"):
        st.markdown("#### 💼 Balance General")

        df_mov = df_all.copy()
        df_mov['Monto'] = df_mov['monto_centavos'].apply(cents_to_float)
        df_mov['fecha_dt'] = pd.to_datetime(df_mov['fecha'], errors='coerce')

        # ── Fecha de último corte ─────────────────────────────────────────────
        df_cortes = df_mov[df_mov['categoria'].str.contains("Venta Cosecha|Corte", case=False, na=False)]
        if not df_cortes.empty:
            ultima_cosecha = df_cortes['fecha_dt'].max().date()
        else:
            ultima_cosecha = date(2000, 1, 1)

        # ── Mis ingresos netos (ya descontado el 50% en exportación al guardar) ──
        mis_ingresos = df_mov[
            (df_mov['tipo'] == 'Ingreso') &
            (~df_mov['categoria'].isin(['Financiamiento']))
        ]['Monto'].sum()

        # ── Gastos desde última cosecha ────────────────────────────────────────
        df_gastos_cosecha = df_mov[
            (df_mov['tipo'] == 'Gasto') &
            (~df_mov['categoria'].isin(['Pago Deuda'] + CATEGORIAS_PERSONALES)) &
            (df_mov['fecha_dt'].dt.date >= ultima_cosecha)
        ]
        gastos_desde_cosecha = df_gastos_cosecha['Monto'].sum()

        # ── Deuda total vigente ────────────────────────────────────────────────
        df_loans = repo.get_dataframe("SELECT * FROM fin_prestamos WHERE estado='Activo'")
        deuda_total = 0.0
        deuda_rows = []
        if not df_loans.empty:
            df_terc = repo.get_dataframe("SELECT id, nombre FROM cat_terceros")
            terc_map = dict(zip(df_terc['id'], df_terc['nombre'])) if not df_terc.empty else {}
            for _, r in df_loans.iterrows():
                cap = cents_to_float(r['monto_capital_centavos'])
                pag = cents_to_float(r['monto_pagado_centavos'])
                saldo = cap - pag
                dias = (date.today() - date.fromisoformat(r['fecha_inicio'])).days
                inte = saldo * (r['tasa_interes_anual'] / 100) * (dias / 365) if dias > 0 else 0
                total_con_interes = saldo + inte
                deuda_total += total_con_interes
                deuda_rows.append({
                    "Acreedor": terc_map.get(r['tercero_id'], '—'),
                    "Saldo": saldo,
                    "Intereses": inte,
                    "Total": total_con_interes,
                })

        # ── Utilidad ──────────────────────────────────────────────────────────
        utilidad = mis_ingresos - gastos_desde_cosecha - deuda_total

        # ── VISTA PRINCIPAL ───────────────────────────────────────────────────
        st.caption(f"Gastos calculados desde el último corte registrado: **{ultima_cosecha.strftime('%d/%m/%Y')}**")
        st.divider()

        m1, m2 = st.columns(2)
        with m1.container(border=True):
            st.metric(
                "💰 Mis Ingresos Netos",
                format_currency(mis_ingresos),
                help="Monto que te corresponde — exportación ya va al 50%, nacional al 100%"
            )
        with m2.container(border=True):
            st.metric(
                "🏦 Deuda Total Vigente",
                format_currency(deuda_total),
                help="Saldo de todos los préstamos activos con intereses acumulados"
            )

        g1, g2 = st.columns(2)
        with g1.container(border=True):
            st.metric(
                "💸 Gastos desde Último Corte",
                format_currency(gastos_desde_cosecha),
                help=f"Gastos del huerto acumulados desde {ultima_cosecha.strftime('%d/%m/%Y')}"
            )
        with g2.container(border=True):
            color = "normal" if utilidad >= 0 else "inverse"
            st.metric(
                "📈 Utilidad",
                format_currency(utilidad),
                delta="Ingresos − Gastos − Deuda",
                delta_color=color
            )

        st.divider()

        if utilidad >= 0:
            st.success(f"✅ Utilidad positiva de **{format_currency(utilidad)}**")
        else:
            st.error(f"🔴 Déficit de **{format_currency(abs(utilidad))}** — deuda + gastos superan los ingresos")

        # ── Desglose de deuda por acreedor ────────────────────────────────────
        if deuda_rows:
            with st.expander("📋 Detalle de deuda por acreedor", expanded=False):
                df_deuda_det = pd.DataFrame(deuda_rows)
                df_deuda_det['Saldo'] = df_deuda_det['Saldo'].apply(format_currency)
                df_deuda_det['Intereses'] = df_deuda_det['Intereses'].apply(format_currency)
                df_deuda_det['Total'] = df_deuda_det['Total'].apply(format_currency)
                st.dataframe(df_deuda_det, use_container_width=True, hide_index=True)

        # ── Detalle de gastos desde cosecha ───────────────────────────────────
        if not df_gastos_cosecha.empty:
            with st.expander("📋 Detalle de gastos desde último corte", expanded=False):
                g_det = df_gastos_cosecha.groupby('categoria')['Monto'].sum().sort_values(ascending=False).reset_index()
                g_det['Monto'] = g_det['Monto'].apply(format_currency)
                g_det.columns = ['Categoría', 'Total']
                st.dataframe(g_det, use_container_width=True, hide_index=True)

    # --- TAB NEGOCIO ---
    with _tab("Negocio"):
        st.info("ℹ️ Reporte EXCLUSIVO del Negocio (Sin gastos personales ni deudas).")
        df_neg = df_all[~df_all['categoria'].isin(['Financiamiento', 'Pago Deuda'] + CATEGORIAS_PERSONALES)].copy()
        
        if not df_neg.empty:
            df_neg['Monto'] = df_neg['monto_centavos'].apply(cents_to_float)
            ing = df_neg[df_neg['tipo']=='Ingreso']['Monto'].sum()
            gas = df_neg[df_neg['tipo']=='Gasto']['Monto'].sum()
            
            st.metric("Utilidad Neta Huerto", format_currency(ing-gas))
            
            c_tbl, c_pie = st.columns(2)
            df_chart = df_neg[df_neg['tipo']=='Gasto'].groupby('categoria')['Monto'].sum().reset_index()
            
            with c_tbl:
                if not df_chart.empty:
                    df_chart = df_chart.sort_values('Monto', ascending=False)
                    df_chart['%'] = (df_chart['Monto'] / gas)
                    
                    df_show = df_chart.copy()
                    df_show['% Del Gasto'] = df_show['%'].map('{:.1%}'.format)
                    df_show['Monto'] = df_show['Monto'].apply(format_currency)
                    st.dataframe(df_show[['categoria', 'Monto', '% Del Gasto']], use_container_width=True, hide_index=True)

            with c_pie:
                if not df_chart.empty:
                    pie = alt.Chart(df_chart).mark_arc(outerRadius=130).encode(
                        theta=alt.Theta("Monto:Q", stack=True),
                        color=alt.Color("categoria:N", scale=alt.Scale(scheme="tableau20"),
                                        legend=alt.Legend(title=None, orient="bottom", columns=2)),
                        order=alt.Order("Monto:Q", sort="descending"),
                        tooltip=["categoria:N", alt.Tooltip("Monto:Q", format="$,.2f"), alt.Tooltip("%:Q", format=".1%")]
                    ).properties(height=300)
                    st.altair_chart(pie, use_container_width=True)
        else: st.info("Sin datos.")

    # --- TAB PERSONAL (solo admin) ---
    if not ocultar_personal:
     with _tab("Personal"):
        df_per = df_all[df_all['categoria'].isin(CATEGORIAS_PERSONALES)].copy()
        if not df_per.empty:
            df_per['Monto'] = df_per['monto_centavos'].apply(cents_to_float)
            tot_p = df_per['Monto'].sum()
            st.metric("Total Gastos Personales", format_currency(tot_p))
            
            df_p_chart = df_per.groupby('categoria')['Monto'].sum().reset_index().sort_values('Monto', ascending=False)
            df_p_chart['%'] = df_p_chart['Monto'] / tot_p
            
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                df_show_p = df_p_chart.copy()
                df_show_p['%'] = df_show_p['%'].map('{:.1%}'.format)
                df_show_p['Monto'] = df_show_p['Monto'].apply(format_currency)
                st.dataframe(df_show_p, use_container_width=True, hide_index=True)

            with c_p2:
                pie = alt.Chart(df_p_chart).mark_arc(outerRadius=130).encode(
                    theta=alt.Theta("Monto:Q", stack=True),
                    color=alt.Color("categoria:N", scale=alt.Scale(scheme="tableau20"),
                                    legend=alt.Legend(title=None, orient="bottom", columns=2)),
                    order=alt.Order("Monto:Q", sort="descending"),
                    tooltip=["categoria:N", alt.Tooltip("Monto:Q", format="$,.2f"), alt.Tooltip("%:Q", format=".1%")]
                ).properties(height=300)
                st.altair_chart(pie, use_container_width=True)
        else: st.info("Sin datos.")

    # --- TAB DEUDAS ---
    with _tab("Deudas"):
        df_loans = repo.get_active_loans_df()
        if not df_loans.empty:
            data = []
            for i, r in df_loans.iterrows():
                cap = cents_to_float(r['monto_capital_centavos'])
                pag = cents_to_float(r['monto_pagado_centavos'])
                sal = cap - pag
                fi = date.fromisoformat(r['fecha_inicio'])
                d = (date.today() - fi).days
                inte = sal * (r['tasa_interes_anual']/100) * (d/365) if d > 0 else 0
                data.append({"Acreedor": r['acreedor_nombre'], "Deuda Total": sal+inte})
            
            df_rep = pd.DataFrame(data)
            if not df_rep.empty:
                df_rep = df_rep.groupby("Acreedor")["Deuda Total"].sum().reset_index()
            
            tot_d = df_rep['Deuda Total'].sum()
            st.metric("Total Deuda", format_currency(tot_d), delta_color="inverse")
            
            df_rep['%'] = df_rep['Deuda Total'] / tot_d
            
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                df_show_d = df_rep.copy()
                df_show_d['%'] = df_show_d['%'].map('{:.1%}'.format)
                df_show_d['Deuda Total'] = df_show_d['Deuda Total'].apply(format_currency)
                st.dataframe(df_show_d, use_container_width=True, hide_index=True)
            with c_d2:
                pie = alt.Chart(df_rep).mark_arc(outerRadius=130).encode(
                    theta=alt.Theta("Deuda Total:Q", stack=True),
                    color=alt.Color("Acreedor:N", scale=alt.Scale(scheme="tableau10"),
                                    legend=alt.Legend(title=None, orient="bottom", columns=2)),
                    tooltip=["Acreedor:N", alt.Tooltip("Deuda Total:Q", format="$,.2f"), alt.Tooltip("%:Q", format=".1%")]
                ).properties(height=300)
                st.altair_chart(pie, use_container_width=True)
        else: st.success("Sin deudas.")

    # --- TAB LOTES ---
    with _tab("Lotes"):
        df_l = repo.get_lots_df()
        res = []
        df_op = df_all[(df_all['tipo']=='Gasto') & (~df_all['categoria'].isin(['Pago Deuda']+CATEGORIAS_PERSONALES))]
        g_gen = cents_to_float(df_op[df_op['lote_id'].isnull()]['monto_centavos'].sum())
        prorr = g_gen / len(df_l) if not df_l.empty else 0
        
        for i,r in df_l.iterrows():
            df_this = df_all[df_all['lote_id']==r['id']]
            g = cents_to_float(df_this[df_this['tipo']=='Gasto']['monto_centavos'].sum()) + prorr
            i_amount = cents_to_float(df_this[df_this['tipo']=='Ingreso']['monto_centavos'].sum())
            res.append({"Huerto":r['nombre'], "Utilidad": i_amount - g})
        
        dfr = pd.DataFrame(res)
        if not dfr.empty:
            tot_u = dfr['Utilidad'].sum()
            st.metric("Utilidad Global", format_currency(tot_u))
            
            df_pos = dfr[dfr['Utilidad']>0].copy()
            
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                dfr = dfr.sort_values('Utilidad', ascending=False)
                dfr['Utilidad'] = dfr['Utilidad'].apply(format_currency)
                st.dataframe(dfr, use_container_width=True, hide_index=True)
            with c_l2:
                if not df_pos.empty:
                    df_pos['%'] = df_pos['Utilidad'] / df_pos['Utilidad'].sum()
                    pie = alt.Chart(df_pos).mark_arc(outerRadius=130).encode(
                        theta=alt.Theta("Utilidad:Q", stack=True),
                        color=alt.Color("Huerto:N", scale=alt.Scale(scheme="tableau10"),
                                        legend=alt.Legend(title=None, orient="bottom", columns=2)),
                        tooltip=["Huerto:N", alt.Tooltip("Utilidad:Q", format="$,.2f"), alt.Tooltip("%:Q", format=".1%")]
                    ).properties(height=300)
                    st.altair_chart(pie, use_container_width=True)
        else: st.info("Sin datos.")

    # --- TAB TICKETS ---
    with _tab("🎫 Tickets"):
        st.markdown("### 🎫 Historial de Tickets Registrados")
        df_tickets = repo.get_ticket_folios_df()
        if not df_tickets.empty:
            df_tickets = df_tickets.rename(columns={
                "folio":        "Folio",
                "empaque":      "Empaque",
                "cliente":      "Cliente",
                "lote":         "Huerto",
                "fecha_ticket": "Fecha Ticket",
                "total_kilos":  "Kilos",
                "precio_kg":    "Precio $/kg",
                "total_monto":  "Total Venta",
                "registrado_at":"Registrado",
            })
            df_tickets["Total Venta"] = df_tickets["Total Venta"].apply(
                lambda x: format_currency(x) if x else "—"
            )
            df_tickets["Precio $/kg"] = df_tickets["Precio $/kg"].apply(
                lambda x: format_currency(x) if x else "—"
            )
            df_tickets["Kilos"] = df_tickets["Kilos"].apply(
                lambda x: f"{x:,.1f} kg" if x else "—"
            )
            st.dataframe(df_tickets, use_container_width=True, hide_index=True)
            st.caption(f"Total tickets registrados: {len(df_tickets)}")
        else:
            st.info("Aún no hay tickets registrados desde la báscula.")

    # --- TAB EXPORTAR ---
    with _tab("💾 Exportar"):
        st.header("💾 Descargar Base de Datos")
        if not df_all.empty:
            df_export = df_all.copy()
            df_export['Monto'] = df_export['monto_centavos'].apply(cents_to_float)
            df_export = df_export.rename(columns={
                'id': 'Folio', 'tercero_nombre': 'Tercero', 'lote_nombre': 'Lote', 'comprobante_path': 'Path_Archivo'
            })
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 Descargar CSV (Excel)",
                data=csv,
                file_name=f"AgroFinanzas_Respaldo_{date.today()}.csv",
                mime="text/csv",
                type="primary"
            )
            st.dataframe(df_export.head(), use_container_width=True)
        else:
            st.info("No hay datos para exportar.")

        st.divider()
        with st.expander("⬆️ Restaurar base de datos desde archivo local", expanded=False):
            st.warning("⚠️ Esto **reemplaza** todos los datos actuales con los del archivo que subas. Úsalo solo para migrar datos desde tu equipo.")
            db_file = st.file_uploader("Selecciona tu archivo agro_finanzas_pro.db", type=["db"], key="db_upload")
            if db_file and st.button("🔄 Restaurar ahora", type="primary", key="db_restore_btn"):
                try:
                    dest = Config.DB_NAME
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(db_file.read())
                    st.cache_data.clear()
                    st.success("✅ Base de datos restaurada. Recarga la página para ver los datos.")
                except Exception as e:
                    st.error(f"Error al restaurar: {e}")

    # KPIs movidos al Dashboard (ver src/ui/views/dashboard.py)
