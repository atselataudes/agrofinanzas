from decimal import Decimal

def float_to_cents(amount_float):
    """Convierte 100.50 -> 10050"""
    if not amount_float:
        return 0
    # Convertimos a string primero para evitar errores de punto flotante
    return int(Decimal(str(amount_float)) * 100)

def cents_to_float(amount_cents):
    """Convierte 10050 -> 100.50"""
    if amount_cents is None:
        return 0.0
    
    # --- CORRECCIÓN AQUÍ ---
    # Convertimos a string (texto) primero. 
    # Esto hace que 'numpy.int64' se vuelva compatible con Decimal.
    return float(Decimal(str(amount_cents)) / 100)

def formato_moneda(cantidad_float):
    """Devuelve string con formato $1,234.56"""
    if cantidad_float is None:
        return "$0.00"
    return "${:,.2f}".format(cantidad_float)
