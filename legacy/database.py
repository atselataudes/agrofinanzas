import sqlite3
import os

DB_NAME = "agro_finanzas_pro.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = 1") 
    return conn

def init_db():
    # Crear carpeta para fotos si no existe
    if not os.path.exists("comprobantes"):
        os.makedirs("comprobantes")

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

    # 3. Movimientos (Con campo para Foto)
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

    # Migración de seguridad (por si vienes de una versión vieja sin fotos)
    try:
        cursor.execute("ALTER TABLE fin_movimientos ADD COLUMN comprobante_path TEXT")
    except:
        pass 

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos lista.")
