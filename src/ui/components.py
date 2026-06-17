import streamlit as st
from config import Config

def inject_custom_css():
    st.markdown(f"""
    <style>
        /* ── Global ─────────────────────────────────────────────── */
        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* ── Metric cards ────────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
            padding: 1rem 1.2rem;
            border-radius: 10px;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 1.4rem !important;
            font-weight: 700;
            color: {Config.COLOR_PRIMARY};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.85rem;
            color: #607d8b;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* ── Buttons ─────────────────────────────────────────────── */
        .stButton button {{
            border-radius: 8px;
            font-weight: 600;
            min-height: 44px;
        }}
        .stButton button[kind="primary"] {{
            background-color: {Config.COLOR_PRIMARY};
            border-color: {Config.COLOR_PRIMARY};
        }}

        /* ── Typography ──────────────────────────────────────────── */
        h1, h2, h3 {{ color: #1b5e20; }}

        /* ── Header ──────────────────────────────────────────────── */
        .agro-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 6px 0 10px 0;
            border-bottom: 2px solid #e8f5e9;
            margin-bottom: 12px;
        }}
        .agro-header .icon {{ font-size: 1.6rem; line-height: 1; }}
        .agro-header .title {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #1b5e20;
            margin: 0;
        }}
        .agro-header .sub {{
            font-size: 0.8rem;
            color: #78909c;
            margin: 0;
        }}

        /* ── Chat ────────────────────────────────────────────────── */
        [data-testid="stChatInput"] textarea {{
            font-size: 1rem;
        }}

        /* ── MOBILE  ≤ 640 px ────────────────────────────────────── */
        @media (max-width: 640px) {{

            /* Métricas: de 4 en fila → 2×2 */
            [data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
            }}
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                min-width: calc(50% - 0.5rem) !important;
                flex: 1 1 calc(50% - 0.5rem) !important;
            }}

            /* Valores de métrica más pequeños para que entren */
            [data-testid="stMetricValue"] {{
                font-size: 1.1rem !important;
            }}
            [data-testid="stMetric"] {{
                padding: 0.6rem 0.7rem;
            }}

            /* Header compacto */
            .agro-header .title {{ font-size: 1.05rem !important; }}
            .agro-header .icon  {{ font-size: 1.3rem !important; }}

            /* Botones: tap target mínimo 48px */
            .stButton button {{
                min-height: 48px !important;
                font-size: 0.95rem !important;
            }}

            /* Tabs: scroll horizontal si no caben */
            [data-testid="stTabs"] > div:first-child {{
                overflow-x: auto !important;
                white-space: nowrap !important;
            }}

            /* Inputs y selects más altos para táctil */
            input, select, textarea {{
                font-size: 16px !important;   /* evita zoom automático en iOS */
            }}

            /* Dataframes con scroll horizontal y fuente más compacta */
            [data-testid="stDataFrame"] {{
                overflow-x: auto !important;
            }}
            [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {{
                font-size: 0.8rem !important;
            }}

            /* Radio buttons con más espacio y tamaño fijo */
            [data-testid="stRadio"] label {{
                padding: 6px 0 !important;
                min-height: 40px !important;
                display: flex !important;
                align-items: center !important;
                font-size: 0.95rem !important;
            }}

            /* Reducir padding general de la página */
            .block-container {{
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 0.75rem !important;
            }}

            /* Gráficas side-by-side → columna única */
            [data-testid="stHorizontalBlock"]:has(canvas) {{
                flex-direction: column !important;
            }}
            [data-testid="stHorizontalBlock"]:has(canvas) > [data-testid="column"] {{
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }}

            /* KPIs dentro de expander: 3 cols → wrap 1 col */
            [data-testid="stExpander"] [data-testid="stHorizontalBlock"] {{
                flex-wrap: wrap !important;
            }}
            [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }}

            /* Ocultar subtítulo del header */
            .agro-header .sub {{
                display: none !important;
            }}
        }}
    </style>
    """, unsafe_allow_html=True)

def metric_card(label: str, value: str, delta: str = None, color: str = "normal"):
    """
    Custom Metric Card Wrapper. 
    Standard streamlit metric is good, but we verify styling via CSS above.
    """
    st.metric(label=label, value=value, delta=delta, delta_color=color)


def render_header():
    st.markdown(
        f"""<div class="agro-header">
            <span class="icon">{Config.PAGE_ICON}</span>
            <div>
                <p class="title">{Config.PAGE_TITLE}</p>
                <p class="sub">Sistema de Gestión Agrícola · v2.1</p>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

def show_error(e: Exception):
    st.error(f"Ocurrió un error inesperado: {str(e)}")

def success_toast(msg: str = "Operación exitosa"):
    st.toast(msg, icon="✅")
    st.success(msg)
