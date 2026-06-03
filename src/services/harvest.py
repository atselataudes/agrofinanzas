from datetime import date
from typing import List, Dict

from src.database.repository import Repository
from src.models.schemas import MovementCreate, HarvestDetailCreate
from src.utils.helpers import float_to_cents


def register_harvest(
    repo: Repository,
    fecha: date,
    lote_nombre: str,
    lote_id: int,
    cliente_id: int,
    details: List[Dict],
) -> int:
    """Creates the harvest movement and its calibre breakdown.
    Returns the new movement ID."""
    total_kilos = sum(d["kilos"] for d in details)
    total_monto = sum(d["subtotal"] for d in details)

    mov = MovementCreate(
        fecha=fecha,
        tipo="Ingreso",
        categoria="🥑 Venta Cosecha (Exportación)",
        concepto=f"Corte {lote_nombre} - {total_kilos}kg",
        cantidad=total_kilos,
        monto_centavos=float_to_cents(total_monto),
        tercero_id=cliente_id,
        lote_id=lote_id,
        comprobante_path=None,
    )
    mov_id = repo.create_movement(mov)

    for d in details:
        repo.add_harvest_detail(HarvestDetailCreate(
            movement_id=mov_id,
            calibre=d["calibre"],
            kilos=d["kilos"],
            precio_kg=d["precio_kg"],
        ))

    return mov_id
