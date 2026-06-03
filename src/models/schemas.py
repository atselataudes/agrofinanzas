from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Literal

# Enums
TransactionType = Literal["Ingreso", "Gasto"]
ThirdPartyRole = Literal["Proveedor", "Cliente", "Prestamista", "Empleado"]
CreditStatus = Literal["Activo", "Pagado", "Vencido", "Eliminado"]
ProductType = Literal["Fertilizante", "Foliar", "Herbicida", "Otro"]

@dataclass
class ThirdPartyBase:
    nombre: str
    rfc: Optional[str] = None
    tipo: Optional[ThirdPartyRole] = "Proveedor"
    telefono: Optional[str] = None

@dataclass
class ThirdPartyCreate(ThirdPartyBase):
    pass

@dataclass
class ThirdParty(ThirdPartyBase):
    id: int = 0

@dataclass
class LotBase:
    nombre: str
    superficie_ha: float = 0.0

@dataclass
class LotCreate(LotBase):
    pass

@dataclass
class Lot(LotBase):
    id: int = 0

@dataclass
class MovementBase:
    fecha: date
    tipo: TransactionType
    categoria: str
    monto_centavos: int
    concepto: Optional[str] = None
    cantidad: float = 0.0
    tercero_id: Optional[int] = None
    lote_id: Optional[int] = None
    comprobante_path: Optional[str] = None

@dataclass
class MovementCreate(MovementBase):
    pass

@dataclass
class Movement(MovementBase):
    id: int = 0
    created_at: Optional[datetime] = None

@dataclass
class LoanBase:
    tercero_id: int
    fecha_inicio: date
    fecha_vencimiento: date
    monto_capital_centavos: int
    tasa_interes_anual: float
    notas: Optional[str] = None

@dataclass
class LoanCreate(LoanBase):
    pass

@dataclass
class Loan(LoanBase):
    id: int = 0
    monto_pagado_centavos: int = 0
    estado: CreditStatus = "Activo"
    created_at: Optional[datetime] = None

# --- NEW MODELS ---

@dataclass
class ProductBase:
    nombre: str
    tipo: ProductType
    unidad_medida: str # Litros, Kilos, Sacos
    stock_actual: float = 0.0

@dataclass
class ProductCreate(ProductBase):
    pass

@dataclass
class Product(ProductBase):
    id: int = 0

@dataclass
class HarvestDetailBase:
    movement_id: int
    calibre: str # Jumbo, Extra, Primera, Segunda, Canica
    kilos: float
    precio_kg: float

@dataclass
class HarvestDetailCreate(HarvestDetailBase):
    pass
