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

        df_mov = df_all.copy()
        df_mov['Monto'] = df_mov['monto_centavos'].apply(cents_to_float)
        df_mov['fecha_dt'] = pd.to_datetime(df_mov['fecha'], errors='coerce')

        # ── Fecha de último corte ─────────────────────────────────────────────
        df_cortes = df_mov[df_mov['categoria'].str.contains("Venta Cosecha|Corte", case=False, na=False)]
        ultima_cosecha = df_cortes['fecha_dt'].max().date() if not df_cortes.empty else date(2000, 1, 1)

        # ── Mis ingresos netos = SOLO ventas de fruta ────────────────────────
        # Exportación: 50% es nuestro | Nacional y Descarte: 100% nuestro
        # Se aplica el factor aquí para corregir registros históricos
        df_ventas = df_mov[
            (df_mov['tipo'] == 'Ingreso') &
            (df_mov['categoria'].str.contains("Venta Cosecha|Venta Descarte", case=False, na=False))
        ].copy()

        def _mi_parte(row):
            if "Exportación" in str(row['categoria']):
                return row['Monto'] * 0.50
            return row['Monto']

        df_ventas['MiParte'] = df_ventas.apply(_mi_parte, axis=1)
        subtotal_ventas = df_ventas['MiParte'].sum()

        # 10% al Gerente de Operaciones sobre el subtotal
        comision_gerente = subtotal_ventas * 0.10
        mis_ingresos     = subtotal_ventas - comision_gerente

        # Para mostrar detalle
        exportacion_bruta = df_ventas[df_ventas['categoria'].str.contains("Exportación", na=False)]['Monto'].sum()
        exportacion_neta  = exportacion_bruta * 0.50
        nacional_total    = df_ventas[~df_ventas['categoria'].str.contains("Exportación", na=False)]['MiParte'].sum()

        # ── Todos los gastos del huerto (sin deuda ni personal) ───────────────
        df_gastos_cosecha = df_mov[
            (df_mov['tipo'] == 'Gasto') &
            (~df_mov['categoria'].isin(['Pago Deuda'] + CATEGORIAS_PERSONALES))
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
                cap  = cents_to_float(r['monto_capital_centavos'])
                pag  = cents_to_float(r['monto_pagado_centavos'])
                saldo = cap - pag
                dias  = (date.today() - date.fromisoformat(r['fecha_inicio'])).days
                inte  = saldo * (r['tasa_interes_anual'] / 100) * (dias / 365) if dias > 0 else 0
                total_con_interes = saldo + inte
                deuda_total += total_con_interes
                deuda_rows.append({
                    "Acreedor": terc_map.get(r['tercero_id'], '—'),
                    "Saldo": saldo,
                    "Intereses": inte,
                    "Total": total_con_interes,
                })

        # ── Indicadores clave ─────────────────────────────────────────────────
        utilidad_operativa = mis_ingresos - gastos_desde_cosecha   # antes de deuda
        posicion_neta      = mis_ingresos - gastos_desde_cosecha - deuda_total  # tras pagar todo
        pct_deuda          = (deuda_total / mis_ingresos * 100) if mis_ingresos > 0 else 0

        # ══════════════════════════════════════════════════════════════════════
        # INDICADOR PRINCIPAL — respuesta directa a la pregunta clave
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### ¿Me alcanza para pagar todo?")
        if posicion_neta >= 0:
            st.success(
                f"✅ **Sí te alcanza.** Si pagas toda tu deuda hoy, "
                f"te quedarían **{format_currency(posicion_neta)}**"
            )
        else:
            st.error(
                f"🔴 **No te alcanza todavía.** Te faltan **{format_currency(abs(posicion_neta))}** "
                f"para cubrir toda la deuda con los ingresos actuales."
            )

        # Barra de compromiso de deuda
        pct_display = min(pct_deuda, 100)
        color_barra = "🟢" if pct_deuda <= 60 else ("🟡" if pct_deuda <= 90 else "🔴")
        st.caption(
            f"{color_barra} Tu deuda representa el **{pct_deuda:.0f}%** de tus ingresos — "
            f"{'nivel manejable' if pct_deuda <= 60 else ('nivel de alerta' if pct_deuda <= 90 else 'nivel crítico')}"
        )
        st.progress(int(pct_display) / 100)

        st.divider()

        # ══════════════════════════════════════════════════════════════════════
        # INDICADORES DE SOPORTE
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("##### Detalle")
        c1, c2 = st.columns(2)

        # Ingresos
        with c1.container(border=True):
            st.metric(
                "💰 Mis Ingresos Netos",
                format_currency(mis_ingresos),
                help="Tu parte real — exportación al 50%, nacional al 100%"
            )
            st.caption(
                f"🌍 Exportación: {format_currency(exportacion_bruta)} × 50% = **{format_currency(exportacion_neta)}**  \n"
                f"🇲🇽 Nacional / Descarte: **{format_currency(nacional_total)}**  \n"
                f"👷 Gerente de operaciones (10%): −**{format_currency(comision_gerente)}**  \n"
                f"✅ Tu ingreso neto: **{format_currency(mis_ingresos)}**"
            )

        # Utilidad operativa
        with c2.container(border=True):
            st.metric(
                "📈 Utilidad Operativa",
                format_currency(utilidad_operativa),
                delta=f"{(utilidad_operativa/mis_ingresos*100):.1f}% margen" if mis_ingresos > 0 else None,
                delta_color="normal" if utilidad_operativa >= 0 else "inverse",
                help="Ingresos − Gastos del huerto (sin contar deuda)"
            )

        c3, c4 = st.columns(2)

        # Gastos desde corte
        with c3.container(border=True):
            pct_gas = (gastos_desde_cosecha / mis_ingresos * 100) if mis_ingresos > 0 else 0
            st.metric(
                "💸 Gastos del Huerto",
                format_currency(gastos_desde_cosecha),
                delta=f"{pct_gas:.1f}% de tus ingresos",
                delta_color="normal" if pct_gas <= 50 else "inverse",
                help="Total de gastos del huerto acumulados (excluye deuda y gastos personales)"
            )
            with st.expander("Ver por categoría", expanded=False):
                if not df_gastos_cosecha.empty:
                    g_det = df_gastos_cosecha.groupby('categoria')['Monto'].sum()\
                        .sort_values(ascending=False).reset_index()
                    g_det.columns = ['Categoría', 'Total']
                    g_det['Total'] = g_det['Total'].apply(format_currency)
                    st.dataframe(g_det, use_container_width=True, hide_index=True)

        # Deuda
        with c4.container(border=True):
            st.metric(
                "🏦 Deuda Total Vigente",
                format_currency(deuda_total),
                delta=f"{pct_deuda:.1f}% de tus ingresos",
                delta_color="inverse",
                help="Saldo de todos los préstamos activos con intereses acumulados"
            )
            with st.expander("Ver por acreedor", expanded=False):
                if deuda_rows:
                    df_dd = pd.DataFrame(deuda_rows)
                    df_dd['Saldo']     = df_dd['Saldo'].apply(format_currency)
                    df_dd['Intereses'] = df_dd['Intereses'].apply(format_currency)
                    df_dd['Total']     = df_dd['Total'].apply(format_currency)
                    st.dataframe(df_dd, use_container_width=True, hide_index=True)

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

        def _ingreso_neto_lote(row):
            """Aplica 50% exportación + descuenta 10% gerente."""
            monto = cents_to_float(row['monto_centavos'])
            if "Exportación" in str(row.get('categoria', '')):
                monto = monto * 0.50
            return monto * 0.90  # −10% gerente de operaciones

        for i, r in df_l.iterrows():
            df_this = df_all[df_all['lote_id'] == r['id']]
            g = cents_to_float(df_this[df_this['tipo']=='Gasto']['monto_centavos'].sum()) + prorr
            # Ingresos netos: 50% exportación, 100% nacional, −10% gerente
            df_ing = df_this[
                (df_this['tipo'] == 'Ingreso') &
                (df_this['categoria'].str.contains("Venta Cosecha|Venta Descarte", case=False, na=False))
            ]
            i_amount = df_ing.apply(_ingreso_neto_lote, axis=1).sum() if not df_ing.empty else 0.0
            res.append({"Huerto": r['nombre'], "Utilidad": i_amount - g})
        
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
