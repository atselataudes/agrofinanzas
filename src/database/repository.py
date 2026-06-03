import sqlite3
import pandas as pd
import streamlit as st
from contextlib import closing
from typing import List, Optional, Dict, Any
from src.database.connection import get_connection
from src.models import schemas

class Repository:
    def __init__(self):
        pass

    # --- GENERIC HELPERS ---
    def _execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if commit:
                conn.commit()
                return cursor.lastrowid

            if fetch_one:
                res = cursor.fetchone()
                return dict(res) if res else None

            if fetch_all:
                res = cursor.fetchall()
                return [dict(row) for row in res]

    def get_dataframe(self, query: str, params: tuple = ()) -> pd.DataFrame:
        with closing(get_connection()) as conn:
            return pd.read_sql(query, conn, params=params)

    # --- LOTES (LOTS) ---
    def create_lot(self, lot: schemas.LotCreate):
        query = "INSERT INTO cat_lotes (nombre, superficie_ha) VALUES (?, ?)"
        result = self._execute_query(query, (lot.nombre, lot.superficie_ha), commit=True)
        st.cache_data.clear()
        return result

    def get_all_lots(self) -> List[Dict[str, Any]]:
        return self._execute_query("SELECT * FROM cat_lotes", fetch_all=True)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_lots_df(_self) -> pd.DataFrame:
        return _self.get_dataframe("SELECT * FROM cat_lotes")

    # --- TERCEROS (THIRD PARTIES) ---
    def create_third_party(self, person: schemas.ThirdPartyCreate):
        query = "INSERT INTO cat_terceros (nombre, rfc, tipo, telefono) VALUES (?, ?, ?, ?)"
        result = self._execute_query(query, (person.nombre, person.rfc, person.tipo, person.telefono), commit=True)
        st.cache_data.clear()
        return result

    def get_all_third_parties(self) -> List[Dict[str, Any]]:
        return self._execute_query("SELECT * FROM cat_terceros", fetch_all=True)

    @st.cache_data(ttl=300, show_spinner=False)
    def get_third_parties_df(_self) -> pd.DataFrame:
        return _self.get_dataframe("SELECT * FROM cat_terceros")

    # --- MOVIMIENTOS (MOVEMENTS) ---
    def create_movement(self, mov: schemas.MovementCreate):
        query = """
            INSERT INTO fin_movimientos 
            (fecha, tipo, categoria, concepto, cantidad, monto_centavos, tercero_id, lote_id, comprobante_path) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            mov.fecha, mov.tipo, mov.categoria, mov.concepto, mov.cantidad, 
            mov.monto_centavos, mov.tercero_id, mov.lote_id, mov.comprobante_path
        )
        return self._execute_query(query, params, commit=True)

    def get_movements_df(self, limit: int = None) -> pd.DataFrame:
        query = """
            SELECT m.id, m.fecha, m.tipo, m.categoria, m.concepto, m.cantidad, m.monto_centavos, 
                   m.comprobante_path, m.lote_id, m.tercero_id,
                   t.nombre as tercero_nombre, l.nombre as lote_nombre
            FROM fin_movimientos m 
            LEFT JOIN cat_terceros t ON m.tercero_id = t.id 
            LEFT JOIN cat_lotes l ON m.lote_id = l.id
            ORDER BY m.id DESC
        """
        if limit:
            query += " LIMIT ?"
            return self.get_dataframe(query, (limit,))
        return self.get_dataframe(query)
    
    def update_movement_evidence(self, move_id: int, path: str):
        self._execute_query("UPDATE fin_movimientos SET comprobante_path=? WHERE id=?", (path, move_id), commit=True)

    def delete_movement(self, move_id: int):
        self._execute_query("DELETE FROM fin_movimientos WHERE id=?", (move_id,), commit=True)

    def get_movement_by_id(self, move_id: int):
        return self._execute_query("SELECT * FROM fin_movimientos WHERE id=?", (move_id,), fetch_one=True)

    # --- PRESTAMOS (LOANS) ---
    def create_loan(self, loan: schemas.LoanCreate):
        query = """
            INSERT INTO fin_prestamos 
            (tercero_id, fecha_inicio, fecha_vencimiento, monto_capital_centavos, monto_pagado_centavos, tasa_interes_anual, notas) 
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """
        # If paying back or incoming money, it should be handled by transaction logic, but here we just create the record
        params = (
            loan.tercero_id, loan.fecha_inicio, loan.fecha_vencimiento, 
            loan.monto_capital_centavos, loan.tasa_interes_anual, loan.notas
        )
        return self._execute_query(query, params, commit=True)

    def get_active_loans_df(self) -> pd.DataFrame:
        query = """
            SELECT p.*, t.nombre as acreedor_nombre 
            FROM fin_prestamos p 
            JOIN cat_terceros t ON p.tercero_id = t.id 
            WHERE p.estado='Activo'
        """
        return self.get_dataframe(query)

    def update_loan_payment(self, loan_id: int, amount_cents: int):
        self._execute_query(
            "UPDATE fin_prestamos SET monto_pagado_centavos = monto_pagado_centavos + ? WHERE id=?",
            (amount_cents, loan_id),
            commit=True
        )
        loan = self._execute_query(
            "SELECT monto_capital_centavos, monto_pagado_centavos FROM fin_prestamos WHERE id=?",
            (loan_id,), fetch_one=True
        )
        if loan and loan['monto_pagado_centavos'] >= loan['monto_capital_centavos']:
            self._execute_query("UPDATE fin_prestamos SET estado='Pagado' WHERE id=?", (loan_id,), commit=True)
            return True
        return False

    def update_loan_balance_manually(self, loan_id: int, capital_cents: int, paid_cents: int):
        self._execute_query(
            "UPDATE fin_prestamos SET monto_capital_centavos = ?, monto_pagado_centavos = ? WHERE id = ?",
            (capital_cents, paid_cents, loan_id),
            commit=True
        )
        # Re-check state
        loan = self._execute_query("SELECT monto_capital_centavos, monto_pagado_centavos FROM fin_prestamos WHERE id=?", (loan_id,), fetch_one=True)
        if loan and loan['monto_pagado_centavos'] >= loan['monto_capital_centavos']:
            self._execute_query("UPDATE fin_prestamos SET estado='Pagado' WHERE id=?", (loan_id,), commit=True)
        else:
            self._execute_query("UPDATE fin_prestamos SET estado='Activo' WHERE id=?", (loan_id,), commit=True)

    def delete_loan(self, loan_id: int):
        self._execute_query("UPDATE fin_prestamos SET estado = 'Eliminado' WHERE id = ?", (loan_id,), commit=True)

    def restore_loan(self, loan_id: int):
        self._execute_query("UPDATE fin_prestamos SET estado = 'Activo' WHERE id = ?", (loan_id,), commit=True)

    # --- INVENTORY ---
    def create_product(self, prod: schemas.ProductCreate):
        self._execute_query(
            "INSERT INTO inv_products (nombre, tipo, unidad_medida, stock_actual) VALUES (?, ?, ?, ?)",
            (prod.nombre, prod.tipo, prod.unidad_medida, prod.stock_actual),
            commit=True
        )

    def get_products_df(self) -> pd.DataFrame:
        return self.get_dataframe("SELECT * FROM inv_products")

    def get_all_products(self):
        return self._execute_query("SELECT * FROM inv_products", fetch_all=True)

    def update_product_stock(self, product_id: int, quantity: float, operation: str = "add"):
        """Operation: 'add' or 'subtract'"""
        if operation == "add":
            q = "UPDATE inv_products SET stock_actual = stock_actual + ? WHERE id=?"
        else:
            q = "UPDATE inv_products SET stock_actual = stock_actual - ? WHERE id=?"
        self._execute_query(q, (quantity, product_id), commit=True)

    # --- HARVEST DETAILS ---
    def add_harvest_detail(self, detail: schemas.HarvestDetailCreate):
        self._execute_query(
            "INSERT INTO ops_harvest (movement_id, calibre, kilos, precio_kg) VALUES (?, ?, ?, ?)",
            (detail.movement_id, detail.calibre, detail.kilos, detail.precio_kg),
            commit=True
        )

    def get_harvest_details(self, movement_id: int):
        return self.get_dataframe("SELECT * FROM ops_harvest WHERE movement_id=?", (movement_id,))

    # --- SETTINGS ---
    def get_setting(self, key: str, default: str = None) -> str:
        res = self._execute_query("SELECT value FROM cat_settings WHERE key=?", (key,), fetch_one=True)
        return res['value'] if res else default

    def update_setting(self, key: str, value: str):
        self._execute_query("INSERT OR REPLACE INTO cat_settings (key, value) VALUES (?, ?)", (key, value), commit=True)
