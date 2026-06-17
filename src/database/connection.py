import os
import sqlite3
from config import Config

def get_connection():
    """Returns a connection to the SQLite database."""
    os.makedirs(os.path.dirname(Config.DB_NAME), exist_ok=True)
    conn = sqlite3.connect(Config.DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = 1")
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def init_db():
    """Initializes the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Lotes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cat_lotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        superficie_ha REAL DEFAULT 0
    )
    """)

    # 2. Terceros
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cat_terceros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        rfc TEXT,
        tipo TEXT,
        telefono TEXT
    )
    """)

    # 3. Movimientos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fin_movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        tipo TEXT CHECK(tipo IN ('Ingreso', 'Gasto')),
        categoria TEXT NOT NULL,
        concepto TEXT,
        cantidad REAL DEFAULT 0,
        monto_centavos INTEGER NOT NULL,
        tercero_id INTEGER,
        lote_id INTEGER,
        comprobante_path TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tercero_id) REFERENCES cat_terceros(id),
        FOREIGN KEY(lote_id) REFERENCES cat_lotes(id)
    )
    """)

    # 4. Préstamos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fin_prestamos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tercero_id INTEGER,
        fecha_inicio TEXT NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        monto_capital_centavos INTEGER NOT NULL,
        monto_pagado_centavos INTEGER DEFAULT 0,
        tasa_interes_anual REAL NOT NULL,
        estado TEXT DEFAULT 'Activo',
        notas TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tercero_id) REFERENCES cat_terceros(id)
    )
    """)

    # 5. Inventario (Productos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inv_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT,
        unidad_medida TEXT,
        stock_actual REAL DEFAULT 0
    )
    """)

    # 6. Detalle Cosecha (Calibres)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ops_harvest (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movement_id INTEGER NOT NULL,
        calibre TEXT NOT NULL,
        kilos REAL NOT NULL,
        precio_kg REAL NOT NULL,
        FOREIGN KEY(movement_id) REFERENCES fin_movimientos(id) ON DELETE CASCADE
    )
    """)
    
    # 7. Configuración (Key-Value)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cat_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # 8. Bitácora de actividades del huerto (trazabilidad)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ops_bitacora (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha           TEXT NOT NULL,
        lote_id         INTEGER REFERENCES cat_lotes(id) ON DELETE SET NULL,
        tipo_actividad  TEXT NOT NULL,
        descripcion     TEXT,
        producto        TEXT,
        dosis           TEXT,
        responsable     TEXT,
        observaciones   TEXT,
        created_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 9. Folios de tickets ya registrados (evita duplicados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reg_ticket_folios (
        folio           TEXT PRIMARY KEY,
        movement_id     INTEGER,
        empaque         TEXT,
        cliente         TEXT,
        lote            TEXT,
        fecha_ticket    TEXT,
        total_kilos     REAL,
        precio_kg       REAL,
        total_monto     REAL,
        registrado_at   TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Migración: agregar columnas si ya existía la tabla sin ellas
    for col, tipo in [
        ("empaque",      "TEXT"),
        ("cliente",      "TEXT"),
        ("lote",         "TEXT"),
        ("fecha_ticket", "TEXT"),
        ("total_kilos",  "REAL"),
        ("precio_kg",    "REAL"),
        ("total_monto",  "REAL"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE reg_ticket_folios ADD COLUMN {col} {tipo}")
        except Exception:
            pass

    # Migración: columnas de crédito en fin_movimientos
    for col, tipo in [
        ("es_credito",    "INTEGER DEFAULT 0"),
        ("fecha_cobro",   "TEXT"),
        ("cobrado",       "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE fin_movimientos ADD COLUMN {col} {tipo}")
        except Exception:
            pass

    # Migración de una sola vez: marcar ventas de cosecha EXISTENTES como crédito a 22 días.
    # Solo corre una vez (protegida por bandera) para no afectar ventas de contado futuras.
    cursor.execute("SELECT value FROM cat_settings WHERE key='migracion_credito_22d'")
    _ya_migrado = cursor.fetchone()
    if not _ya_migrado:
        try:
            cursor.execute("""
                UPDATE fin_movimientos
                SET es_credito = 1,
                    fecha_cobro = date(fecha, '+22 days'),
                    cobrado = 0
                WHERE tipo = 'Ingreso'
                  AND (categoria LIKE '%Venta Cosecha%' OR categoria LIKE '%Venta Descarte%')
                  AND (es_credito IS NULL OR es_credito = 0)
            """)
        except Exception:
            pass
        cursor.execute(
            "INSERT OR REPLACE INTO cat_settings (key, value) VALUES ('migracion_credito_22d', '1')"
        )

    # Insert default initial balance if not exists
    cursor.execute("INSERT OR IGNORE INTO cat_settings (key, value) VALUES ('saldo_inicial_centavos', '0')")
    
    conn.commit()
    conn.close()
