import os
import json
import base64
from datetime import date

import streamlit as st


# ---------- helpers ----------

def _get_client():
    """Returns (client, error_msg). Reads key from secrets or env."""
    try:
        import anthropic
    except ImportError:
        return None, "Falta el paquete 'anthropic'. Ejecuta: pip install anthropic"

    key = None
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        pass
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY", None)
    if not key:
        return None, (
            "No se encontró ANTHROPIC_API_KEY. "
            "Agrégala en `.streamlit/secrets.toml`:\n"
            "ANTHROPIC_API_KEY = 'sk-ant-...'"
        )
    import anthropic
    return anthropic.Anthropic(api_key=key), None


def _clean_json(text: str) -> dict:
    """Strip markdown fences and parse JSON, with fallback regex extraction."""
    text = text.strip()
    # Remove markdown fences
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if block.startswith("{"):
                text = block
                break
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback: extract first {...} block
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError("No JSON found")


_PROMPT_SUFFIX = """
Tipos posibles: Ingreso | Gasto Huerto | Gasto Personal
Categorías posibles (elige la más cercana):
  Ingreso       → Anticipo/Amarre | Venta Cosecha | Venta Descarte | Otros Ingresos
  Gasto Huerto  → Nómina | Fertilizantes | Agroquímicos | Combustible | Mantenimiento | Herramientas | Servicios | Administrativo | Empaque
  Gasto Personal→ Salud | Víveres | Vacaciones | Gastos de Casa | Ropa | Educación | Transporte Personal
"""

_JSON_TEMPLATE = """{{
  "fecha": "{today}",
  "monto": null,
  "concepto": null,
  "proveedor": null,
  "tipo": "Gasto Huerto",
  "categoria": "Fertilizantes"
}}"""


# ---------- public API ----------

def analizar_imagen(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Send a receipt image to Claude Vision and return extracted fields as dict.
    Returns {"error": "..."} on failure.
    """
    client, err = _get_client()
    if err:
        return {"error": err}

    today = date.today().isoformat()
    b64 = base64.standard_b64encode(image_bytes).decode()

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64}
                },
                {
                    "type": "text",
                    "text": (
                        f"Analiza este comprobante/nota de gasto agrícola. Hoy: {today}.\n"
                        f"Devuelve SOLO JSON válido con esta estructura:\n"
                        f"{_JSON_TEMPLATE.format(today=today)}\n"
                        f"{_PROMPT_SUFFIX}\n"
                        "Si no puedes leer un campo usa null."
                    )
                }
            ]
        }]
    )

    try:
        return _clean_json(resp.content[0].text)
    except Exception:
        return {"error": "No se pudo leer el comprobante. Intenta con mejor iluminación.", "raw": resp.content[0].text}


def analizar_ticket_pesado(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Lee un ticket de báscula/pesado de aguacate y extrae calibres + kilos.
    Retorna:
      { "fecha": "YYYY-MM-DD", "folio": "...", "total_kilos": 0.0,
        "calibres": [{"calibre": "Extra", "kilos": 0.0}, ...] }
    o {"error": "..."} en caso de fallo.
    """
    client, err = _get_client()
    if err:
        return {"error": err}

    today = date.today().isoformat()
    b64 = base64.standard_b64encode(image_bytes).decode()

    prompt = f"""Eres un asistente especializado en tickets de báscula de empacadoras de aguacate.
Analiza este ticket de pesado y extrae la información. Hoy es {today}.

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "fecha": null,
  "folio": null,
  "empaque": null,
  "total_kilos": null,
  "calibres": []
}}

Reglas:
- "fecha": en formato YYYY-MM-DD. Si no aparece usa "{today}".
- "folio": número o clave del ticket. null si no aparece.
- "empaque": nombre de la empacadora, empresa o cliente que emite el ticket. null si no aparece.
- "total_kilos": peso total neto en kilos (número decimal).
- "calibres": lista de objetos {{"calibre": "...", "kilos": 0.0}}.
  Calibres estándar: Jumbo, Extra, Primera, Segunda, Canica, Descarte.
  Si el ticket usa otros nombres (p.ej. "Grande", "Chico", "4s", "6s"), mapea al más cercano.
  Si no puedes mapear, usa "Otros".
- Usa null para campos que no puedas leer con certeza.
- NO incluyas texto fuera del JSON."""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64}
                },
                {"type": "text", "text": prompt}
            ]
        }]
    )

    try:
        return _clean_json(resp.content[0].text)
    except Exception:
        return {"error": "No se pudo leer el ticket. Intenta con mejor iluminación.", "raw": resp.content[0].text}


def analizar_texto(texto: str) -> dict:
    """
    Parse a free-form expense description into one or more structured movements.
    Returns {"movimientos": [...]} or {"error": "..."}.
    """
    client, err = _get_client()
    if err:
        return {"error": err}

    today = date.today().isoformat()

    prompt = (
        f"Eres asistente contable de una finca de aguacate.\n"
        f"El usuario describió: \"{texto}\"\n"
        f"Hoy: {today}\n\n"
        f"Puede haber UNO O VARIOS movimientos en el texto. Extrae TODOS y devuelve SOLO JSON válido:\n"
        f"{{\"movimientos\": [\n"
        f"  {{\"fecha\": \"{today}\", \"monto\": null, \"concepto\": null, \"proveedor\": null, \"tipo\": \"Gasto Huerto\", \"categoria\": \"Fertilizantes\"}}\n"
        f"]}}\n"
        f"{_PROMPT_SUFFIX}\n"
        "Reglas:\n"
        "- Si menciona venta/cobro/ingreso/amarre → tipo=Ingreso.\n"
        "- Si hay varios gastos o ingresos distintos, crea un objeto por cada uno.\n"
        "- Si no puedes inferir un campo usa null.\n"
        "- Devuelve SOLO el JSON, sin texto adicional."
    )

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        data = _clean_json(resp.content[0].text)
        # Normalize: si la IA devolvió un objeto solo (sin lista), lo envolvemos
        if "movimientos" not in data:
            data = {"movimientos": [data]}
        return data
    except Exception as exc:
        raw = resp.content[0].text
        return {"error": f"No se pudo interpretar el texto ({exc}).", "raw": raw}
