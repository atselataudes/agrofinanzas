from decimal import Decimal
import os
from datetime import datetime
from config import Config

def save_uploaded_file(uploaded_file) -> str:
    """Saves a streamlit uploaded file to the configured folder."""
    if uploaded_file is None: 
        return None
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{ts}_{uploaded_file.name.replace(' ', '_')}"
        path = os.path.join(Config.UPLOAD_FOLDER, name)
        with open(path, "wb") as f: 
            f.write(uploaded_file.getbuffer())
        return path
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def float_to_cents(amount_float: float) -> int:
    """Converts 100.50 -> 10050"""
    if not amount_float:
        return 0
    # Convert to string first to avoid floating point errors
    return int(Decimal(str(amount_float)) * 100)

def cents_to_float(amount_cents: int) -> float:
    """Converts 10050 -> 100.50"""
    if amount_cents is None:
        return 0.0
    return float(Decimal(str(amount_cents)) / 100)

def format_currency(amount_float: float) -> str:
    """Returns string formatted as $1,234.56"""
    if amount_float is None:
        return "$0.00"
    return "${:,.2f}".format(amount_float)
