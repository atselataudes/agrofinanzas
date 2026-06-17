"""
Script para cargar los gastos faltantes de mayo 2025 y 2026.
Corre con: python3 cargar_gastos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.database.connection import init_db
from src.database.repository import Repository
from src.models.schemas import MovementCreate
from src.utils.helpers import float_to_cents

init_db()
repo = Repository()

gastos = [
    # ── Semana 4–9 mayo 2025 ────────────────────────────────────────────────
    ("2025-05-05", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Raya semana 4-9 mayo",        4890.0),
    ("2025-05-05", "Gasto Huerto", "⛽ Combustible",             "Diesel semana 4-9 mayo",        681.0),
    ("2025-05-05", "Gasto Huerto", "⛽ Combustible",             "Gasolina semana 4-9 mayo",      381.0),
    ("2025-05-05", "Gasto Huerto", "🚜 Mantenimiento",           "Sementante y tractor camino",  3107.0),
    ("2025-05-05", "Gasto Huerto", "🚜 Mantenimiento",           "Servicio camioneta",           2208.0),
    ("2025-05-05", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Lalito semana 4-9 mayo",        227.0),

    # ── Semana 11–16 mayo 2026 ──────────────────────────────────────────────
    ("2026-05-13", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Raya semana 11-16 mayo",       4890.0),
    ("2026-05-13", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Lalito semana 11-16 mayo",      454.0),
    ("2026-05-13", "Gasto Huerto", "⛽ Combustible",             "Diesel semana 11-16 mayo",      681.0),
    ("2026-05-13", "Gasto Huerto", "🔧 Herramientas",            "Guantes (wantes)",               34.0),
    ("2026-05-13", "Gasto Huerto", "📑 Administrativo",          "Cubrebocas",                     28.0),
    ("2026-05-13", "Gasto Huerto", "📦 Empaque",                 "Jabón Roma",                    362.0),
    ("2026-05-13", "Gasto Huerto", "⛽ Combustible",             "Gasolina semana 11-16 mayo",    150.0),

    # ── Semana 18–23 mayo 2026 ──────────────────────────────────────────────
    ("2026-05-20", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Raya semana 18-23 mayo",       4890.0),
    ("2026-05-20", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Lalito semana 18-23 mayo",      454.0),
    ("2026-05-20", "Gasto Huerto", "⛽ Combustible",             "Gasolina bomba",                189.0),
    ("2026-05-20", "Gasto Huerto", "⛽ Combustible",             "Gasolina semana 18-23 mayo",    189.0),
    ("2026-05-20", "Gasto Huerto", "🚜 Mantenimiento",           "Aceite para tractor",            77.0),

    # ── Semana 25–30 mayo 2026 ──────────────────────────────────────────────
    ("2026-05-27", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Raya semana 25-30 mayo",       4890.0),
    ("2026-05-27", "Gasto Huerto", "👷 Nómina / Raya Semanal",  "Lalito semana 25-30 mayo",      568.0),
    ("2026-05-27", "Gasto Huerto", "🚜 Mantenimiento",           "Aceite para tractor",           267.0),
    ("2026-05-27", "Gasto Huerto", "⛽ Combustible",             "Gasolina wirear",               264.0),
    ("2026-05-27", "Gasto Huerto", "📑 Administrativo",          "Papel/servitoallas/vasos/jabón",405.0),
    ("2026-05-27", "Gasto Huerto", "⛽ Combustible",             "Diesel semana 25-30 mayo",      381.0),
    ("2026-05-27", "Gasto Huerto", "⛽ Combustible",             "Gasolina semana 25-30 mayo",    190.0),
    ("2026-05-27", "Gasto Huerto", "🔧 Herramientas",            "Ferretería Israel",             341.0),
    ("2026-05-27", "Gasto Huerto", "🚜 Mantenimiento",           "Mecánico",                      114.0),
    ("2026-05-27", "Gasto Huerto", "💡 Servicios (Luz/Agua)",    "Wiros servicio",                721.0),
]

ok = 0
for fecha, tipo_raw, categoria, concepto, monto in gastos:
    tipo = "Gasto"
    mov = MovementCreate(
        fecha=fecha,
        tipo=tipo,
        categoria=categoria,
        concepto=concepto,
        monto_centavos=float_to_cents(monto),
        cantidad=0.0,
        tercero_id=None,
        lote_id=None,
        comprobante_path=None,
    )
    repo.create_movement(mov)
    ok += 1
    print(f"  ✅ {fecha}  {concepto:<40} ${monto:,.2f}")

print(f"\n✅ {ok} movimientos cargados exitosamente.")
