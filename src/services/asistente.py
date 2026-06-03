import os
from datetime import date
import streamlit as st
from src.database.repository import Repository
from src.utils.helpers import cents_to_float


def _build_context(repo: Repository) -> str:
    """Construye el contexto de datos para el asistente."""
    parts = []

    # Movimientos
    df = repo.get_movements_df()
    if not df.empty:
        df["monto"] = df["monto_centavos"].apply(cents_to_float)
        total_ing = df[df["tipo"] == "Ingreso"]["monto"].sum()
        total_gas = df[df["tipo"] == "Gasto"]["monto"].sum()
        parts.append(
            f"RESUMEN GENERAL (todos los registros hasta hoy {date.today().strftime('%d/%m/%Y')}):\n"
            f"  - Total ingresos: ${total_ing:,.2f}\n"
            f"  - Total gastos:   ${total_gas:,.2f}\n"
            f"  - Utilidad neta:  ${total_ing - total_gas:,.2f}"
        )

        cols = ["fecha", "tipo", "categoria", "concepto", "monto", "tercero_nombre", "lote_nombre"]
        rows = df[cols].rename(columns={"tercero_nombre": "tercero", "lote_nombre": "huerto"})
        rows["monto"] = rows["monto"].map("${:,.2f}".format)
        rows = rows.fillna("—")
        parts.append("HISTORIAL COMPLETO DE MOVIMIENTOS:\n" + rows.to_string(index=False))
    else:
        parts.append("No hay movimientos registrados aún.")

    # Préstamos activos
    df_loans = repo.get_active_loans_df()
    if not df_loans.empty:
        lines = []
        for _, r in df_loans.iterrows():
            cap = cents_to_float(r["monto_capital_centavos"])
            pag = cents_to_float(r["monto_pagado_centavos"])
            lines.append(
                f"  - {r['acreedor_nombre']}: capital ${cap:,.2f}, "
                f"pagado ${pag:,.2f}, saldo ${cap - pag:,.2f}"
            )
        parts.append("PRÉSTAMOS ACTIVOS:\n" + "\n".join(lines))
    else:
        parts.append("No hay préstamos activos.")

    return "\n\n".join(parts)


def ask_assistant(repo: Repository, question: str, history: list) -> str:
    """Envía una pregunta a Claude con el contexto de la DB y devuelve la respuesta."""
    try:
        import anthropic
    except ImportError:
        return "❌ Falta el paquete `anthropic`. Ejecuta: pip install anthropic"

    key = None
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return "❌ No se encontró la API key. Agrégala en `.streamlit/secrets.toml`."

    client = anthropic.Anthropic(api_key=key)
    context = _build_context(repo)

    system_prompt = f"""Eres un asistente financiero experto para una finca aguacatera.
Tienes acceso a los datos financieros reales registrados en la app AgroFinanzas Pro.
Responde siempre en español, de forma clara y directa.
- Usa formato $1,234.56 para montos.
- Usa fechas legibles (ej: "lunes 3 de junio de 2024").
- Si haces cálculos, muestra brevemente cómo llegaste al resultado.
- Si no encuentras la información en los datos, dilo claramente. No inventes datos.
- Sé conciso: responde lo que se pregunta, sin rodeos.

{context}"""

    messages = [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    messages.append({"role": "user", "content": question})

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    return resp.content[0].text
