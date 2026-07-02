import os
import json
from datetime import date
import streamlit as st
from src.database.repository import Repository
from src.utils.helpers import cents_to_float, float_to_cents


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

    # Préstamos activos (con ID para poder abonar)
    df_loans = repo.get_active_loans_df()
    if not df_loans.empty:
        lines = []
        for _, r in df_loans.iterrows():
            cap = cents_to_float(r["monto_capital_centavos"])
            pag = cents_to_float(r["monto_pagado_centavos"])
            lines.append(
                f"  - [prestamo_id={r['id']}] {r['acreedor_nombre']}: capital ${cap:,.2f}, "
                f"pagado ${pag:,.2f}, saldo ${cap - pag:,.2f}"
            )
        parts.append("PRÉSTAMOS ACTIVOS:\n" + "\n".join(lines))
    else:
        parts.append("No hay préstamos activos.")

    # Terceros (para asociar movimientos)
    terceros = repo.get_all_third_parties() or []
    if terceros:
        parts.append("TERCEROS REGISTRADOS:\n" + "\n".join(
            f"  - [tercero_id={t['id']}] {t['nombre']}" for t in terceros
        ))

    return "\n\n".join(parts)


# ── Herramientas que la IA puede ejecutar ────────────────────────────────────

_TOOLS = [
    {
        "name": "abonar_prestamo",
        "description": (
            "Registra un abono/pago a un préstamo activo. Reduce el saldo de la deuda. "
            "Usa el prestamo_id que aparece en PRÉSTAMOS ACTIVOS. "
            "También crea el movimiento de gasto 'Pago Deuda' en el diario para reflejar la salida de efectivo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prestamo_id": {"type": "integer", "description": "ID del préstamo (de la lista PRÉSTAMOS ACTIVOS)"},
                "monto": {"type": "number", "description": "Monto del abono en pesos"},
                "fecha": {"type": "string", "description": "Fecha del abono YYYY-MM-DD. Si no se menciona, hoy."},
                "nota": {"type": "string", "description": "Descripción breve del abono"},
            },
            "required": ["prestamo_id", "monto"],
        },
    },
    {
        "name": "registrar_movimiento",
        "description": (
            "Registra un ingreso o gasto en el diario. Úsalo cuando el usuario pida registrar "
            "un gasto o ingreso que NO sea abono a préstamo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {"type": "string", "enum": ["Ingreso", "Gasto"]},
                "categoria": {"type": "string", "description": "Categoría del movimiento"},
                "concepto": {"type": "string", "description": "Descripción del movimiento"},
                "monto": {"type": "number", "description": "Monto en pesos"},
                "fecha": {"type": "string", "description": "Fecha YYYY-MM-DD. Si no se menciona, hoy."},
                "tercero_id": {"type": "integer", "description": "ID del tercero si se conoce"},
            },
            "required": ["tipo", "categoria", "monto"],
        },
    },
]


def _ejecutar_tool(repo: Repository, name: str, inp: dict) -> str:
    """Ejecuta la herramienta solicitada por la IA y devuelve el resultado."""
    try:
        if name == "abonar_prestamo":
            prestamo_id = int(inp["prestamo_id"])
            monto = float(inp["monto"])
            fecha = inp.get("fecha") or date.today().isoformat()
            nota = inp.get("nota") or "Abono a préstamo"

            cents = float_to_cents(monto)
            liquidado = repo.update_loan_payment(prestamo_id, cents)

            # Reflejar salida de efectivo en el diario
            loan = repo._execute_query(
                "SELECT p.id, t.nombre, t.id as tid FROM fin_prestamos p JOIN cat_terceros t ON p.tercero_id=t.id WHERE p.id=?",
                (prestamo_id,), fetch_one=True
            )
            from src.models.schemas import MovementCreate
            repo.create_movement(MovementCreate(
                fecha=fecha,
                tipo="Gasto",
                categoria="Pago Deuda",
                concepto=f"{nota} — {loan['nombre'] if loan else ''}".strip(" —"),
                monto_centavos=cents,
                tercero_id=loan["tid"] if loan else None,
            ))

            estado = "El préstamo quedó LIQUIDADO. 🎉" if liquidado else "El préstamo sigue activo."
            return json.dumps({"ok": True, "mensaje": f"Abono de ${monto:,.2f} registrado el {fecha}. {estado}"})

        elif name == "registrar_movimiento":
            from src.models.schemas import MovementCreate
            fecha = inp.get("fecha") or date.today().isoformat()
            mov_id = repo.create_movement(MovementCreate(
                fecha=fecha,
                tipo=inp["tipo"],
                categoria=inp["categoria"],
                concepto=inp.get("concepto"),
                monto_centavos=float_to_cents(float(inp["monto"])),
                tercero_id=inp.get("tercero_id"),
            ))
            return json.dumps({"ok": True, "mensaje": f"Movimiento #{mov_id} registrado el {fecha}."})

        return json.dumps({"ok": False, "error": f"Herramienta desconocida: {name}"})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


def ask_assistant(repo: Repository, question: str, history: list) -> str:
    """Envía una pregunta a Claude con el contexto de la DB y devuelve la respuesta.
    Soporta herramientas: la IA puede registrar abonos a préstamos y movimientos."""
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

REGISTRO DE OPERACIONES:
- Puedes registrar abonos a préstamos (abonar_prestamo) y movimientos (registrar_movimiento).
- ANTES de ejecutar una herramienta, verifica que tengas los datos claros (monto, a quién, fecha).
- Si falta información o hay ambigüedad (ej: hay varios préstamos del mismo acreedor), PREGUNTA antes de ejecutar.
- Después de ejecutar, confirma al usuario exactamente qué se registró.
- NUNCA digas que registraste algo si la herramienta no se ejecutó o devolvió error.

{context}"""

    messages = [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    messages.append({"role": "user", "content": question})

    # Loop de tool use: hasta 5 iteraciones
    for _ in range(5):
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            tools=_TOOLS,
            messages=messages,
        )

        if resp.stop_reason != "tool_use":
            # Respuesta final de texto
            return "".join(b.text for b in resp.content if b.type == "text")

        # Ejecutar cada tool solicitada
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = _ejecutar_tool(repo, block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    return "⚠️ Se alcanzó el límite de operaciones en una sola consulta. Revisa el diario para confirmar qué se registró."
