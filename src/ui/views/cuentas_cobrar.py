import streamlit as st
from datetime import date, datetime
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, format_currency


def _neto(monto_centavos: int) -> float:
    """Descuenta 10% gerente — el monto en DB ya tiene aplicado 50%/100%."""
    return cents_to_float(monto_centavos) * 0.90


def show_cuentas_cobrar(solo_lectura: bool = False):
    st.markdown("### 💳 Cuentas por Cobrar")
    st.caption("Montos = nuestra parte ya descontando el 10% del gerente de operaciones.")
    repo = Repository()

    df = repo.get_cuentas_por_cobrar_df()

    if df.empty:
        st.info("No hay ventas a crédito registradas.")
        return

    hoy = date.today().isoformat()

    pendientes = df[df["cobrado"] == 0].copy()
    cobradas   = df[df["cobrado"] == 1].copy()

    total_por_cobrar = sum(_neto(r) for r in pendientes["monto_centavos"]) if not pendientes.empty else 0.0
    vencidas = pendientes[pendientes["fecha_cobro"] < hoy] if not pendientes.empty else pendientes.iloc[0:0]
    proximas = pendientes[pendientes["fecha_cobro"] >= hoy] if not pendientes.empty else pendientes.iloc[0:0]
    monto_vencido = sum(_neto(r) for r in vencidas["monto_centavos"]) if not vencidas.empty else 0.0

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Total que vamos a recibir", format_currency(total_por_cobrar))
    k2.metric("Vencidas", f"{len(vencidas)}",
              delta=f"-{format_currency(monto_vencido)}" if not vencidas.empty else None,
              delta_color="inverse")
    k3.metric("Por vencer", f"{len(proximas)}")

    st.divider()

    # Pendientes
    if not pendientes.empty:
        st.markdown("#### ⏳ Pendientes de Cobro")
        for _, r in pendientes.sort_values("fecha_cobro").iterrows():
            neto = _neto(r["monto_centavos"])
            vencida = str(r["fecha_cobro"]) < hoy
            icono = "🔴" if vencida else "🟡"
            dias_label = ""
            if r["fecha_cobro"]:
                delta = (datetime.strptime(str(r["fecha_cobro"]), "%Y-%m-%d").date() - date.today()).days
                dias_label = f" · **Vencida hace {abs(delta)} días**" if vencida else f" · vence en {delta} días"

            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                col_info.markdown(
                    f"{icono} **{r['fecha_cobro']}**{dias_label}  \n"
                    f"{r.get('concepto') or r.get('categoria', '')} · {r.get('lote_nombre') or ''}  \n"
                    f"💰 **{format_currency(neto)}** *(nuestra parte neta)*"
                )
                if not solo_lectura:
                    if col_btn.button("✅ Cobrado", key=f"cobrar_{r['id']}"):
                        repo.marcar_cobrado(int(r["id"]))
                        st.success("Marcado como cobrado.")
                        st.rerun()

    # Historial cobradas
    if not cobradas.empty:
        with st.expander(f"✅ Historial cobrado ({len(cobradas)} registros)", expanded=False):
            df_show = cobradas.copy()
            df_show["Neto recibido"] = df_show["monto_centavos"].apply(_neto).apply(format_currency)
            df_show = df_show.rename(columns={"fecha": "Fecha venta", "fecha_cobro": "Fecha cobro", "concepto": "Descripción"})
            st.dataframe(df_show[["Fecha venta", "Fecha cobro", "Descripción", "Neto recibido"]], use_container_width=True, hide_index=True)
