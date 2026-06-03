from src.database.repository import Repository
from src.models.schemas import LoanCreate, MovementCreate
from src.utils.helpers import float_to_cents


def create_loan_with_movement(
    repo: Repository,
    loan: LoanCreate,
    acreedor_nombre: str,
    register_income: bool,
) -> int:
    """Creates a loan record and optionally a matching income movement."""
    loan_id = repo.create_loan(loan)

    if register_income:
        mov = MovementCreate(
            fecha=loan.fecha_inicio,
            tipo="Ingreso",
            categoria="Financiamiento",
            concepto=f"Préstamo de {acreedor_nombre}",
            monto_centavos=loan.monto_capital_centavos,
            tercero_id=loan.tercero_id,
            lote_id=None,
        )
        repo.create_movement(mov)

    return loan_id


def register_payment(
    repo: Repository,
    loan_id: int,
    amount: float,
    fecha,
) -> bool:
    """Records a loan payment as an expense movement and updates the loan balance.
    Returns True if the loan is now fully paid."""
    mov = MovementCreate(
        fecha=fecha,
        tipo="Gasto",
        categoria="Pago Deuda",
        concepto=f"Abono a crédito #{loan_id}",
        monto_centavos=float_to_cents(amount),
        tercero_id=None,
        lote_id=None,
    )
    repo.create_movement(mov)
    return repo.update_loan_payment(loan_id, float_to_cents(amount))
