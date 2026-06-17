import streamlit as st
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, format_currency


def _mi_parte(row) -> float:
    monto = cents_to_float(row["monto_centavos"])
    if "Exportación" in str(row.get("categoria", "")):
        return monto * 0.50
    return monto


def show_inversionista_app():
    from src.ui.components import render_header, inject_custom_css
    inject_custom_css()
    render_header()

    repo = Repository()

    with st.sidebar:
        st.markdown("### 📈 Inversionista")
        st.divider()
        if st.button("🔒 Cerrar sesión", use_container_width=True, key="inv_logout"):
            st.session_state.pop("rol_activo", None)
            st.rerun()

    st.markdown("## 📊 Resumen del Negocio")
    st.caption("Vista simplificada para inversionistas")

    df = repo.get_movements_df()

    if df.empty:
        st.info("Aún no hay movimientos registrados.")
        return

    # ── Ventas ────────────────────────────────────────────────────────────────
    df_ventas = df[
        df["categoria"].str.contains("Venta Cosecha|Venta Descarte", case=False, na=False)
    ].copy()

    venta_bruta = cents_to_float(df_ventas["monto_centavos"].sum())

    if not df_ventas.empty:
        df_ventas["mi_parte"] = df_ventas.apply(_mi_parte, axis=1)
        subtotal = df_ventas["mi_parte"].sum()
    else:
        subtotal = 0.0

    pagado_encargado = subtotal * 0.10
    ingreso_neto = subtotal - pagado_encargado

    # ── Gastos ────────────────────────────────────────────────────────────────
    df_gastos = df[df["tipo"] == "Gasto"].copy()
    total_gastos = cents_to_float(df_gastos["monto_centavos"].sum())
    utilidad = ingreso_neto - total_gastos

    # ── Deuda (créditos activos) ───────────────────────────────────────────────
    df_prestamos = repo.get_active_loans_df()
    total_deuda = 0.0
    if not df_prestamos.empty:
        total_deuda = cents_to_float(
            (df_prestamos["monto_capital_centavos"] - df_prestamos["monto_pagado_centavos"]).sum()
        )

    # ── KPIs principales ──────────────────────────────────────────────────────
    st.markdown("### 💰 ¿Cuánto dinero entró?")
    k1, k2 = st.columns(2)
    k1.metric("Nuestra parte de las ventas", format_currency(subtotal),
              help="Exportación: 50% · Nacional: 100%")
    k2.metric("Pagado al Encargado (10%)", format_currency(pagado_encargado),
              delta=f"-{format_currency(pagado_encargado)}", delta_color="inverse")

    st.markdown("### 🧾 ¿Cuánto se gastó?")
    g1, g2 = st.columns(2)
    g1.metric("Total Gastos Operativos", format_currency(total_gastos))
    g2.metric("Deuda Pendiente", format_currency(total_deuda),
              help="Préstamos activos sin liquidar")

    st.markdown("### 📈 Resultado Final")
    color = "normal" if utilidad >= 0 else "inverse"
    u1, u2 = st.columns(2)
    u1.metric(
        "Utilidad Neta",
        format_currency(utilidad),
        delta=("✅ Positiva" if utilidad >= 0 else "⚠️ Negativa"),
        delta_color=color,
    )
    u2.metric(
        "Ingreso Neto (sin gastos)",
        format_currency(ingreso_neto),
        help="Lo que entra después de pagar al encargado, antes de gastos operativos",
    )

    # ── Desglose de ventas ────────────────────────────────────────────────────
    if not df_ventas.empty:
        st.divider()
        st.markdown("### 🥑 Desglose de Ventas")

        exp = df_ventas.groupby("categoria").agg(
            Kilos=("cantidad", "sum"),
            Venta_Bruta=("monto_centavos", "sum"),
        ).reset_index()
        exp["Venta Bruta"] = exp["Venta_Bruta"].apply(lambda x: format_currency(cents_to_float(x)))
        exp["Kilos"] = exp["Kilos"].apply(lambda x: f"{x:,.0f} kg")
        exp = exp.rename(columns={"categoria": "Categoría"})
        st.dataframe(exp[["Categoría", "Kilos", "Venta Bruta"]], use_container_width=True, hide_index=True)

    # ── Últimas ventas ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📅 Últimas Ventas Registradas")
    df_ult = df_ventas.sort_values("fecha", ascending=False).head(8)
    if not df_ult.empty:
        df_show = df_ult[["fecha", "concepto", "monto_centavos", "lote_nombre"]].copy()
        df_show["Monto"] = df_show["monto_centavos"].apply(lambda x: format_currency(cents_to_float(x)))
        df_show = df_show.rename(columns={"fecha": "Fecha", "concepto": "Descripción", "lote_nombre": "Huerto"})
        st.dataframe(df_show[["Fecha", "Descripción", "Monto", "Huerto"]], use_container_width=True, hide_index=True)
    else:
        st.caption("Sin ventas registradas aún.")
