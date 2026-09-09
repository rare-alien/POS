"""
Capa de repositorio (acceso a datos) del Punto de Venta.

Separa el SQL directo de la UI (Tkinter). Todas las conexiones salen por
`connect()`, que configura un timeout de espera por bloqueo y `Row` como
fábrica de filas para poder leer por índice o por nombre de columna.

Nota: `foreign_keys` se deja desactivado por defecto para no romper el
borrado histórico de productos/ventas que ya existía en la app; se puede
activar por operación cuando sea necesario.
"""

import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Optional

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(APP_DIR, "ventas.db")


def connect(
    db_path: Optional[str] = None,
    timeout: float = 5.0,
    foreign_keys: bool = False,
) -> sqlite3.Connection:
    """Abre una conexión SQLite configurada para el POS."""
    conn = sqlite3.connect(db_path or DB_FILE, timeout=timeout)
    conn.row_factory = sqlite3.Row
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
    return conn


def _query(db_path: str, sql: str, params: Any = ()) -> List[Dict[str, Any]]:
    with closing(connect(db_path)) as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def _query_one(db_path: str, sql: str, params: Any = ()) -> Optional[Dict[str, Any]]:
    with closing(connect(db_path)) as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def listar_productos(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Devuelve todos los productos ordenados por nombre."""
    return _query(
        db_path or DB_FILE,
        "SELECT id, codigo, nombre, precio, costo, stock, categoria,"
        " a_granel, caducidad FROM productos ORDER BY nombre",
    )


def listar_ventas(
    fecha: Optional[str] = None,
    limit: int = 200,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista ventas con su cliente, opcionalmente filtradas por fecha."""
    sql = (
        "SELECT v.id, v.fecha, IFNULL(c.nombre, 'Público general') AS cliente,"
        " v.total FROM ventas v"
        " LEFT JOIN clientes c ON c.id = v.cliente_id"
    )
    params: List[Any] = []
    if fecha:
        sql += " WHERE v.fecha LIKE ?"
        params.append(f"{fecha}%")
    sql += " ORDER BY v.id DESC LIMIT ?"
    params.append(limit)
    return _query(db_path or DB_FILE, sql, params)


def detalle_venta(venta_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Devuelve las líneas de detalle de una venta."""
    return _query(
        db_path or DB_FILE,
        "SELECT id, producto_id, nombre, precio, costo, cantidad, subtotal,"
        " ganancia, es_granel FROM detalle_venta WHERE venta_id = ?",
        (venta_id,),
    )


def kpis_hoy(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calcula ventas, total y ganancia de hoy."""
    row = _query_one(
        db_path or DB_FILE,
        "SELECT COUNT(*) AS ventas,"
        " IFNULL(SUM(total), 0) AS total,"
        " IFNULL((SELECT SUM(ganancia) FROM detalle_venta d"
        "   JOIN ventas v ON v.id = d.venta_id"
        "   WHERE date(v.fecha) = date('now','localtime')), 0) AS ganancia"
        " FROM ventas"
        " WHERE date(fecha) = date('now','localtime')",
    ) or {}
    return {
        "ventas": int(row.get("ventas", 0) or 0),
        "total": round(float(row.get("total", 0) or 0), 2),
        "ganancia": round(float(row.get("ganancia", 0) or 0), 2),
    }


def listar_clientes(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Devuelve todos los clientes ordenados por nombre."""
    return _query(
        db_path or DB_FILE,
        "SELECT id, nombre, telefono, email, notas, ultima_visita,"
        " total_compras, fecha_alta FROM clientes ORDER BY nombre",
    )


def leer_admin_hash(db_path: Optional[str] = None) -> Optional[str]:
    """Lee el hash de contraseña del administrador (None si aún no existe)."""
    row = _query_one(
        db_path or DB_FILE,
        "SELECT valor FROM configuracion WHERE clave = 'admin_hash'",
    )
    return row["valor"] if row else None


def guardar_admin_hash(nuevo_hash: str, db_path: Optional[str] = None) -> None:
    """Guarda o actualiza el hash de contraseña del administrador."""
    with closing(connect(db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO configuracion (clave, valor)"
            " VALUES ('admin_hash', ?)",
            (nuevo_hash,),
        )
        conn.commit()


__all__ = [
    "DB_FILE",
    "connect",
    "detalle_venta",
    "guardar_admin_hash",
    "kpis_hoy",
    "leer_admin_hash",
    "listar_clientes",
    "listar_productos",
    "listar_ventas",
]
