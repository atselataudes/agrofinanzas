import streamlit as st
import streamlit.components.v1 as components
from datetime import date, datetime

from src.database.repository import Repository
from src.models.schemas import MovementCreate
from src.utils.helpers import float_to_cents, format_currency, save_uploaded_file
from src.utils.constants import CATALOGO_OPS
from src.ai.parser import analizar_imagen, analizar_texto


# ---------- helpers ----------

_TIPO_MAP = {
    "ingreso":         "Ingreso",
    "gasto huerto":    "Gasto Huerto",
    "gasto personal":  "Gasto Personal",
}

_CAT_MAP = {
    # Gasto Huerto
    "nómina":          "👷 Nómina / Raya Semanal",
    "nomina":          "👷 Nómina / Raya Semanal",
    "fertilizantes":   "🧪 Fertilizantes (Suelo)",
    "agroquímicos":    "☠️ Agroquímicos (Foliares)",
    "agroquimicos":    "☠️ Agroquímicos (Foliares)",
    "combustible":     "⛽ Combustible",
    "mantenimiento":   "🚜 Mantenimiento",
    "herramientas":    "🔧 Herramientas",
    "servicios":       "💡 Servicios (Luz/Agua)",
    "administrativo":  "📑 Administrativo",
    "empaque":         "📦 Empaque",
    # Ingreso
    "anticipo":        "💸 Anticipo / Amarre Cosecha",
    "amarre":          "💸 Anticipo / Amarre Cosecha",
    "venta cosecha":   "🥑 Venta Cosecha (Nacional)",
    "venta descarte":  "🗑️ Venta Descarte/Merma",
    "otros ingresos":  "💰 Otros Ingresos",
    # Gasto Personal
    "salud":           "🏥 Salud / Médicos",
    "víveres":         "🛒 Víveres / Despensa",
    "viveres":         "🛒 Víveres / Despensa",
    "vacaciones":      "✈️ Vacaciones / Ocio",
    "gastos de casa":  "🏠 Gastos de Casa",
    "ropa":            "👗 Ropa y Calzado",
    "educación":       "🎓 Educación",
    "educacion":       "🎓 Educación",
    "transporte":      "🚗 Transporte Personal",
}


def _normalize_tipo(raw: str) -> str:
    if not raw:
        return "Gasto Huerto"
    return _TIPO_MAP.get(raw.lower().strip(), "Gasto Huerto")


def _normalize_cat(tipo: str, raw: str) -> str:
    if not raw:
        return list(CATALOGO_OPS[tipo].keys())[0]
    # Try exact match first
    cats = CATALOGO_OPS[tipo]
    for k in cats:
        if raw.lower() in k.lower() or k.lower() in raw.lower():
            return k
    # Try mapping table
    key = raw.lower().strip()
    mapped = _CAT_MAP.get(key)
    if mapped and mapped in cats:
        return mapped
    return list(cats.keys())[0]


def _get_media_type(file_name: str) -> str:
    ext = file_name.lower().split(".")[-1]
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif",
            "webp": "image/webp"}.get(ext, "image/jpeg")


# ---------- Speech Recognition JS component ----------

_SPEECH_HTML = """
<style>
  body { margin: 0; font-family: sans-serif; }
  .mic-wrap { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  button { padding:10px 18px; border:none; border-radius:8px; font-size:15px; cursor:pointer; }
  #btnStart { background:#2e7d32; color:white; }
  #btnStop  { background:#c62828; color:white; }
  #btnStop:disabled, #btnStart:disabled { opacity:0.4; cursor:default; }
  #status { font-size:13px; color:#555; margin-top:6px; }
  #transcript {
    margin-top:8px; padding:10px; border-radius:6px;
    background:#f1f8e9; border:1px solid #aed581;
    min-height:48px; font-size:15px; white-space:pre-wrap;
  }
  #btnUsar { background:#1976d2; color:white; margin-top:8px; display:none; }
</style>

<div class="mic-wrap">
  <button id="btnStart" onclick="iniciar()">🎙️ Grabar</button>
  <button id="btnStop"  onclick="detener()" disabled>⏹️ Detener</button>
</div>
<div id="status">Presiona Grabar y habla claramente en español…</div>
<div id="transcript"></div>
<button id="btnUsar" onclick="usarTexto()">✅ Analizar este texto</button>

<script>
var rec, transcriptFinal = "";

function iniciar() {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    document.getElementById("status").innerText =
      "⚠️ Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.";
    return;
  }
  rec = new SR();
  rec.lang = "es-MX";
  rec.continuous = true;
  rec.interimResults = true;
  transcriptFinal = "";

  rec.onstart = function() {
    document.getElementById("status").innerText = "🔴 Grabando…";
    document.getElementById("btnStart").disabled = true;
    document.getElementById("btnStop").disabled  = false;
    document.getElementById("btnUsar").style.display = "none";
  };

  rec.onresult = function(e) {
    var interim = "";
    for (var i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) {
        transcriptFinal += e.results[i][0].transcript + " ";
      } else {
        interim += e.results[i][0].transcript;
      }
    }
    document.getElementById("transcript").innerText = transcriptFinal + interim;
  };

  rec.onerror = function(e) {
    document.getElementById("status").innerText = "❌ Error: " + e.error;
  };

  rec.start();
}

function detener() {
  if (rec) rec.stop();
  document.getElementById("status").innerText = "✅ Grabación terminada";
  document.getElementById("btnStart").disabled = false;
  document.getElementById("btnStop").disabled  = true;
  if (transcriptFinal.trim()) {
    document.getElementById("btnUsar").style.display = "inline-block";
  }
}

function usarTexto() {
  var t = transcriptFinal.trim();
  if (!t) return;
  // Encode and redirect parent so Streamlit picks it up via query_params
  var url = new URL(window.parent.location.href);
  url.searchParams.set("voz", t);
  window.parent.location.href = url.toString();
}
</script>
"""


# ---------- Form prefill helper ----------

def _render_form_prefilled(datos: dict, repo: Repository, origen: str = "imagen"):
    """Render the movement form pre-filled with AI-extracted data."""
    lotes_df     = repo.get_lots_df()
    terceros_df  = repo.get_third_parties_df()

    if terceros_df.empty:
        st.warning("⚠️ Ve a Catálogos para registrar Terceros primero.")
        return

    ters_map  = dict(zip(terceros_df["nombre"], terceros_df["id"]))
    lotes_map = dict(zip(lotes_df["nombre"], lotes_df["id"])) if not lotes_df.empty else {}
    opc_lotes = ["🏢 Gasto General"] + list(lotes_map.keys())

    # Normalize AI output
    tipo_ai = _normalize_tipo(datos.get("tipo", "Gasto Huerto"))
    cat_ai  = _normalize_cat(tipo_ai, datos.get("categoria", ""))

    try:
        fecha_ai = datetime.strptime(datos["fecha"], "%Y-%m-%d").date() if datos.get("fecha") else date.today()
    except Exception:
        fecha_ai = date.today()

    monto_ai    = float(datos["monto"])   if datos.get("monto")    else 0.0
    concepto_ai = datos.get("concepto")  or ""
    proveedor_ai = datos.get("proveedor") or ""

    st.success(f"✅ IA extrajo los datos desde {origen}. Revisa y confirma antes de guardar.")

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2])
        fecha    = c1.date_input("Fecha", value=fecha_ai, key=f"ci_fecha_{origen}")
        tipo_ui  = c2.radio("Tipo", list(CATALOGO_OPS.keys()), index=list(CATALOGO_OPS.keys()).index(tipo_ai), key=f"ci_tipo_{origen}")
        cats     = list(CATALOGO_OPS[tipo_ui].keys())
        cat_idx  = cats.index(cat_ai) if cat_ai in cats else 0
        categoria = c3.selectbox("Categoría", cats, index=cat_idx, key=f"ci_cat_{origen}")

        reglas = CATALOGO_OPS[tipo_ui][categoria]
        st.caption(f"ℹ️ {reglas['ayuda']}")
        st.divider()

        c_a, c_b, c_c = st.columns(3)
        cant = c_a.number_input("Cantidad (kg/L)", min_value=0.0, key=f"ci_cant_{origen}") if reglas["kilos"] else 0.0

        if reglas["precio_unitario"]:
            pu = c_b.number_input("Precio unitario ($)", min_value=0.0, key=f"ci_pu_{origen}")
            monto_final = cant * pu
            c_c.metric("Total", format_currency(monto_final))
        else:
            monto_final = c_b.number_input("Importe total ($)", min_value=0.0, value=monto_ai, key=f"ci_monto_{origen}")

        c1b, c2b, c3b = st.columns(3)

        # Tercero
        ter_opts   = list(ters_map.keys())
        ter_default = 0
        for i, n in enumerate(ter_opts):
            if proveedor_ai.lower() in n.lower() or n.lower() in proveedor_ai.lower():
                ter_default = i
                break
        tercero_nombre = c1b.selectbox("Tercero / Proveedor", ter_opts, index=ter_default, key=f"ci_ter_{origen}")

        notas = c2b.text_input("Notas / Referencia", value=concepto_ai, key=f"ci_notas_{origen}")

        # Lote
        lote_id = None
        if reglas["lote"] == "No":
            c3b.info("🚫 No aplica Lote")
        elif reglas["lote"] == "Obligatorio":
            if lotes_map:
                lote_nm = c3b.selectbox("Huerto (Obligatorio)", list(lotes_map.keys()), key=f"ci_lote_{origen}")
                lote_id = lotes_map[lote_nm]
            else:
                st.error("¡Faltan Lotes! Agrégalos en Catálogos.")
        else:
            lote_nm = c3b.selectbox("Asignar a", opc_lotes, key=f"ci_lote2_{origen}")
            if lote_nm != "🏢 Gasto General":
                lote_id = lotes_map[lote_nm]

        st.divider()
        st.markdown("##### 📷 Comprobante (Opcional)")
        foto = st.file_uploader("Subir comprobante adicional", type=["jpg", "png", "pdf"], key=f"ci_foto_{origen}")

        if st.button("💾 Guardar Movimiento", type="primary", key=f"ci_save_{origen}"):
            if monto_final <= 0:
                st.error("El monto debe ser mayor a 0.")
            elif reglas["lote"] == "Obligatorio" and not lote_id:
                st.error("Selecciona un lote para esta categoría.")
            else:
                path = save_uploaded_file(foto)
                mov = MovementCreate(
                    fecha=fecha,
                    tipo="Ingreso" if tipo_ui == "Ingreso" else "Gasto",
                    categoria=categoria,
                    concepto=notas,
                    cantidad=cant,
                    monto_centavos=float_to_cents(monto_final),
                    tercero_id=ters_map[tercero_nombre],
                    lote_id=lote_id,
                    comprobante_path=path,
                )
                try:
                    repo.create_movement(mov)
                    st.balloons()
                    st.success("✅ Movimiento guardado correctamente.")
                    # Clear AI result from session
                    for k in ["ci_imagen_result", "ci_voz_result"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")


# ---------- Main view ----------

def _check_api_key() -> bool:
    """Returns True if API key is configured, else shows setup instructions."""
    import os
    key = None
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        pass
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY", None)
    if key and not key.startswith("sk-ant-PEGA"):
        return True

    st.warning("⚙️ **Configura tu API key para usar esta función**")
    with st.expander("📋 Instrucciones paso a paso", expanded=True):
        st.markdown("""
**1.** Obtén tu API key gratuita en [console.anthropic.com](https://console.anthropic.com) → sección *API Keys*.

**2.** Abre el archivo `.streamlit/secrets.toml` en tu carpeta AgroFinanzas y reemplaza la línea:
```toml
ANTHROPIC_API_KEY = "sk-ant-TU_KEY_AQUI"
```
por tu clave real.

**3.** Reinicia la app con:
```bash
streamlit run app.py
```
""")
    return False


def show_captura_inteligente():
    st.markdown("### 🤖 Captura Inteligente")
    st.caption("Registra gastos desde una foto de recibo o dictando por voz. La IA extrae los datos automáticamente.")

    if not _check_api_key():
        return

    repo = Repository()

    # Read voice transcript from query params (set by JS mic component)
    qp = st.query_params
    voz_qp = qp.get("voz", "").strip()
    if voz_qp and "ci_voz_result" not in st.session_state:
        with st.spinner("🧠 Interpretando nota de voz…"):
            st.session_state["ci_voz_result"]  = analizar_texto(voz_qp)
            st.session_state["ci_voz_texto"]   = voz_qp
        # Clean URL
        st.query_params.clear()
        st.rerun()

    tab_img, tab_voz = st.tabs(["📷 Foto de Recibo / Nota", "🎙️ Nota de Voz"])

    # ─── TAB 1: IMAGE ────────────────────────────────────────────────────────
    with tab_img:
        st.markdown("**Sube la foto de tu nota de gasto o comprobante y la IA leerá los datos.**")

        foto = st.file_uploader(
            "Selecciona imagen (jpg, png) o PDF",
            type=["jpg", "jpeg", "png", "webp"],
            key="ci_uploader",
        )

        col_prev, col_btn = st.columns([2, 1])
        if foto:
            col_prev.image(foto, caption="Vista previa", use_container_width=True)

        if foto and col_btn.button("🔍 Analizar con IA", type="primary", key="ci_analizar_img"):
            with st.spinner("🧠 Leyendo comprobante…"):
                bytes_data = foto.read()
                media_type = _get_media_type(foto.name)
                result = analizar_imagen(bytes_data, media_type)
                st.session_state["ci_imagen_result"] = result
                st.session_state["ci_imagen_nombre"]  = foto.name
                st.rerun()

        if "ci_imagen_result" in st.session_state:
            datos = st.session_state["ci_imagen_result"]
            if "error" in datos:
                st.error(f"❌ {datos['error']}")
                if st.button("Limpiar", key="ci_clear_img"):
                    st.session_state.pop("ci_imagen_result", None)
                    st.rerun()
            else:
                with st.expander("📄 Datos extraídos por la IA", expanded=False):
                    st.json(datos)
                _render_form_prefilled(datos, repo, origen="imagen")

    # ─── TAB 2: VOICE ────────────────────────────────────────────────────────
    with tab_voz:
        st.markdown("**Habla o escribe el gasto y la IA lo contabilizará.**")
        st.info(
            "💡 **Ejemplos:** \n"
            "- *\"Pagué 850 pesos de fertilizante en AgroInsumos hoy\"*\n"
            "- *\"Gasté 300 en gasolina para el tractor\"*\n"
            "- *\"Cobré 12 mil pesos de anticipo de cosecha a Bodega Norte\"*"
        )

        # Option A: Browser Speech Recognition
        st.markdown("**Opción A — Micrófono del navegador** *(Chrome/Edge)*")
        components.html(_SPEECH_HTML, height=200)

        st.divider()

        # Option B: Text input
        st.markdown("**Opción B — Escribe directamente**")
        texto_manual = st.text_area(
            "Describe el gasto o movimiento",
            placeholder="Ej: Pagué 1,200 pesos de jornales a los 3 trabajadores del lote norte",
            height=80,
            key="ci_texto_manual",
        )

        if st.button("🔍 Analizar texto", type="primary", key="ci_analizar_voz"):
            texto = texto_manual.strip()
            if not texto:
                st.warning("Escribe o graba algo primero.")
            else:
                with st.spinner("🧠 Interpretando…"):
                    result = analizar_texto(texto)
                    st.session_state["ci_voz_result"] = result
                    st.session_state["ci_voz_texto"]  = texto
                # Debug temporal
                if "error" in result:
                    st.error(f"Error: {result.get('error')}")
                    st.code(result.get("raw", "(sin respuesta de la IA)"), language="text")
                st.rerun()

        # Show voice result
        if "ci_voz_result" in st.session_state:
            datos = st.session_state["ci_voz_result"]
            texto_orig = st.session_state.get("ci_voz_texto", "")
            if texto_orig:
                st.caption(f"📝 Texto interpretado: *\"{texto_orig}\"*")

            if "error" in datos:
                st.error(f"❌ {datos['error']}")
                if st.button("Limpiar", key="ci_clear_voz"):
                    st.session_state.pop("ci_voz_result", None)
                    st.session_state.pop("ci_voz_texto", None)
                    st.rerun()
            else:
                with st.expander("📄 Datos extraídos por la IA", expanded=False):
                    st.json(datos)
                _render_form_prefilled(datos, repo, origen="voz")
