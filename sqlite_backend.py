"""
Backend reutilizable para trabajar con SQLite desde Python.

Disenado para capas de analitica, APIs o integraciones con IA donde los
resultados deben salir en estructuras simples y serializables.
"""

import os
import sqlite3
from datetime import date
from contextlib import closing
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union


Params = Union[Sequence[Any], Mapping[str, Any], None]
QueryResult = List[Dict[str, Any]]


class SQLiteBackendError(RuntimeError):
    """Error controlado para operaciones del backend SQLite."""


def resolve_db_path(db_name: str = "ventas.db", base_dir: Optional[str] = None) -> str:
    """
    Construye una ruta absoluta a la base de datos.

    Si no se indica `base_dir`, usa la carpeta donde vive este modulo.
    """
    root_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root_dir, db_name)


def connect_db(db_path: str, timeout: float = 5.0) -> sqlite3.Connection:
    """
    Abre una conexion SQLite lista para consultas backend.

    - Activa foreign keys
    - Configura timeout para esperas por bloqueo
    - Usa `sqlite3.Row` para facilitar conversion a diccionario
    """
    try:
        connection = sqlite3.connect(db_path, timeout=timeout)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")
        return connection
    except sqlite3.Error as error:
        raise SQLiteBackendError(
            f"No se pudo abrir la base de datos '{db_path}': {error}"
        ) from error


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> QueryResult:
    """Convierte filas SQLite en una lista de diccionarios."""
    return [dict(row) for row in rows]


def execute_query(
    db_path: str,
    query: str,
    params: Params = None,
    timeout: float = 5.0,
) -> QueryResult:
    """
    Ejecuta un SELECT o cualquier sentencia que retorne filas.

    Retorna siempre una lista de diccionarios.
    Si la sentencia no genera filas, retorna una lista vacia.
    """
    normalized_params = _normalize_params(params)

    try:
        with closing(connect_db(db_path, timeout=timeout)) as connection:
            cursor = connection.execute(query, normalized_params)

            if cursor.description is None:
                connection.commit()
                return []

            return rows_to_dicts(cursor.fetchall())
    except sqlite3.Error as error:
        raise SQLiteBackendError(_build_query_error("ejecutar consulta", query, error)) from error


def execute_one(
    db_path: str,
    query: str,
    params: Params = None,
    timeout: float = 5.0,
) -> Optional[Dict[str, Any]]:
    """
    Ejecuta una consulta y devuelve solo la primera fila como diccionario.

    Retorna `None` si no hubo resultados.
    """
    normalized_params = _normalize_params(params)

    try:
        with closing(connect_db(db_path, timeout=timeout)) as connection:
            cursor = connection.execute(query, normalized_params)

            if cursor.description is None:
                connection.commit()
                return None

            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as error:
        raise SQLiteBackendError(_build_query_error("ejecutar consulta unica", query, error)) from error


def execute_command(
    db_path: str,
    query: str,
    params: Params = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Ejecuta INSERT, UPDATE o DELETE y retorna metadatos utiles.

    Esta salida es comoda para integraciones con IA o APIs porque informa si
    la operacion afecto filas y el ultimo ID insertado.
    """
    normalized_params = _normalize_params(params)

    try:
        with closing(connect_db(db_path, timeout=timeout)) as connection:
            cursor = connection.execute(query, normalized_params)
            connection.commit()

            return {
                "rows_affected": cursor.rowcount,
                "last_row_id": cursor.lastrowid,
            }
    except sqlite3.Error as error:
        raise SQLiteBackendError(_build_query_error("ejecutar comando", query, error)) from error


def check_connection(db_path: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Verifica rapidamente si la base de datos responde.

    Retorna un diccionario simple para monitoreo, APIs o agentes de IA.
    """
    try:
        row = execute_one(db_path, "SELECT 1 AS ok", timeout=timeout)
        return {
            "ok": bool(row and row.get("ok") == 1),
            "db_path": db_path,
        }
    except SQLiteBackendError as error:
        return {
            "ok": False,
            "db_path": db_path,
            "error": str(error),
        }


def get_resumen_ventas(
    fecha_inicio: str,
    fecha_fin: str,
    db_path: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Resume las ventas en un rango de fechas y devuelve un diccionario simple.

    La salida esta pensada para consumirse facilmente desde APIs, analitica o
    prompts para LLMs.
    """
    fecha_inicio_norm = _normalize_iso_date(fecha_inicio, "fecha_inicio")
    fecha_fin_norm = _normalize_iso_date(fecha_fin, "fecha_fin")

    if fecha_inicio_norm > fecha_fin_norm:
        raise SQLiteBackendError(
            "fecha_inicio no puede ser mayor que fecha_fin."
        )

    resolved_db_path = db_path or resolve_db_path("ventas.db")
    row = execute_one(
        resolved_db_path,
        """
        SELECT
            IFNULL(SUM(total), 0) AS total_ventas,
            COUNT(*) AS numero_ventas,
            CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE IFNULL(SUM(total), 0) / COUNT(*)
            END AS ticket_promedio
        FROM ventas
        WHERE date(fecha) BETWEEN date(?) AND date(?)
        """,
        (fecha_inicio_norm, fecha_fin_norm),
        timeout=timeout,
    ) or {}

    return {
        "consulta": "resumen_ventas",
        "fecha_inicio": fecha_inicio_norm,
        "fecha_fin": fecha_fin_norm,
        "total_ventas": round(float(row.get("total_ventas", 0) or 0), 2),
        "numero_ventas": int(row.get("numero_ventas", 0) or 0),
        "ticket_promedio": round(float(row.get("ticket_promedio", 0) or 0), 2),
    }


def get_top_productos(
    limit: int = 5,
    db_path: Optional[str] = None,
    timeout: float = 5.0,
) -> QueryResult:
    """
    Devuelve los productos mas vendidos usando la tabla detalle_venta.

    Cada elemento de salida contiene solo campos simples para facilitar su uso
    en analitica, APIs o prompts para LLMs.
    """
    limit_value = _normalize_limit(limit)
    resolved_db_path = db_path or resolve_db_path("ventas.db")
    rows = execute_query(
        resolved_db_path,
        """
        SELECT
            MAX(nombre) AS nombre,
            SUM(cantidad) AS cantidad,
            SUM(subtotal) AS ingresos
        FROM detalle_venta
        GROUP BY producto_id
        ORDER BY cantidad DESC, ingresos DESC, nombre ASC
        LIMIT ?
        """,
        (limit_value,),
        timeout=timeout,
    )

    return [
        {
            "nombre": row.get("nombre"),
            "cantidad": round(float(row.get("cantidad", 0) or 0), 2),
            "ingresos": round(float(row.get("ingresos", 0) or 0), 2),
        }
        for row in rows
    ]


def get_productos_sin_rotacion(
    dias: int = 30,
    db_path: Optional[str] = None,
    timeout: float = 5.0,
) -> QueryResult:
    """
    Devuelve productos que no han tenido ventas en los ultimos X dias.

    Usa `productos` y `detalle_venta` como base y se apoya en `ventas` para
    conocer la fecha real de la ultima venta.
    """
    dias_value = _normalize_positive_int(dias, "dias")
    resolved_db_path = db_path or resolve_db_path("ventas.db")
    rows = execute_query(
        resolved_db_path,
        """
        SELECT
            p.id AS producto_id,
            p.codigo AS codigo,
            p.nombre AS nombre,
            p.stock AS stock_actual,
            MAX(v.fecha) AS ultima_venta
        FROM productos p
        LEFT JOIN detalle_venta dv ON dv.producto_id = p.id
        LEFT JOIN ventas v ON v.id = dv.venta_id
        GROUP BY p.id, p.codigo, p.nombre, p.stock
        HAVING
            MAX(date(v.fecha)) IS NULL
            OR MAX(date(v.fecha)) <= date('now', 'localtime', ?)
        ORDER BY p.stock DESC, p.nombre ASC
        """,
        (f"-{dias_value} days",),
        timeout=timeout,
    )

    return [
        {
            "nombre": row.get("nombre"),
            "stock_actual": round(float(row.get("stock_actual", 0) or 0), 2),
            "ultima_venta": row.get("ultima_venta"),
        }
        for row in rows
    ]


def get_margen_productos(
    db_path: Optional[str] = None,
    timeout: float = 5.0,
) -> QueryResult:
    """
    Calcula ingreso, costo, ganancia y margen por producto.

    Usa los campos `precio`, `costo` y `cantidad` de `detalle_venta` para
    generar una salida clara y estable para analitica o integraciones con IA.
    """
    resolved_db_path = db_path or resolve_db_path("ventas.db")
    rows = execute_query(
        resolved_db_path,
        """
        SELECT
            producto_id,
            MAX(nombre) AS nombre,
            SUM(precio * cantidad) AS ingreso_total,
            SUM(costo * cantidad) AS costo_total,
            SUM((precio - costo) * cantidad) AS ganancia,
            CASE
                WHEN SUM(precio * cantidad) = 0 THEN 0
                ELSE (SUM((precio - costo) * cantidad) * 100.0) / SUM(precio * cantidad)
            END AS margen_porcentaje
        FROM detalle_venta
        GROUP BY producto_id
        ORDER BY ganancia DESC, ingreso_total DESC, nombre ASC
        """,
        timeout=timeout,
    )

    return [
        {
            "nombre": row.get("nombre"),
            "ingreso_total": round(float(row.get("ingreso_total", 0) or 0), 2),
            "costo_total": round(float(row.get("costo_total", 0) or 0), 2),
            "ganancia": round(float(row.get("ganancia", 0) or 0), 2),
            "margen_porcentaje": round(float(row.get("margen_porcentaje", 0) or 0), 2),
        }
        for row in rows
    ]


def generar_contexto_ia(
    fecha_inicio: str,
    fecha_fin: str,
    top_limit: int = 5,
    dias_sin_rotacion: int = 30,
    db_path: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Consolida el contexto comercial principal en una sola estructura.

    La salida usa nombres de claves simples y predecibles para que un LLM
    pueda consumir el contexto sin transformaciones adicionales.
    """
    resolved_db_path = db_path or resolve_db_path("ventas.db")

    return {
        "resumen": get_resumen_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            db_path=resolved_db_path,
            timeout=timeout,
        ),
        "top_productos": get_top_productos(
            limit=top_limit,
            db_path=resolved_db_path,
            timeout=timeout,
        ),
        "productos_lentos": get_productos_sin_rotacion(
            dias=dias_sin_rotacion,
            db_path=resolved_db_path,
            timeout=timeout,
        ),
        "margenes": get_margen_productos(
            db_path=resolved_db_path,
            timeout=timeout,
        ),
    }


def _normalize_params(params: Params) -> Union[Sequence[Any], Mapping[str, Any]]:
    """Normaliza parametros para sqlite3 evitando errores comunes."""
    if params is None:
        return ()

    if isinstance(params, Mapping):
        return params

    if isinstance(params, (str, bytes)):
        return (params,)

    return params


def _normalize_iso_date(value: str, field_name: str) -> str:
    """Valida y normaliza fechas a formato YYYY-MM-DD."""
    if not isinstance(value, str) or not value.strip():
        raise SQLiteBackendError(f"'{field_name}' debe ser una fecha en formato YYYY-MM-DD.")

    normalized_value = value.strip()[:10]

    try:
        date.fromisoformat(normalized_value)
    except ValueError as error:
        raise SQLiteBackendError(
            f"'{field_name}' debe ser una fecha valida en formato YYYY-MM-DD."
        ) from error

    return normalized_value


def _normalize_positive_int(value: int, field_name: str) -> int:
    """Valida enteros positivos para filtros y limites."""
    if not isinstance(value, int):
        raise SQLiteBackendError(f"'{field_name}' debe ser un entero.")

    if value <= 0:
        raise SQLiteBackendError(f"'{field_name}' debe ser mayor que 0.")

    return value


def _normalize_limit(value: int) -> int:
    """Valida limites enteros para consultas agregadas."""
    return _normalize_positive_int(value, "limit")


def _build_query_error(action: str, query: str, error: sqlite3.Error) -> str:
    """Construye mensajes de error compactos y utiles para logs o IA."""
    compact_query = " ".join(query.strip().split())
    return f"No fue posible {action}. Query: '{compact_query}'. Detalle: {error}"


__all__ = [
    "SQLiteBackendError",
    "check_connection",
    "connect_db",
    "execute_command",
    "execute_one",
    "execute_query",
    "generar_contexto_ia",
    "get_margen_productos",
    "get_productos_sin_rotacion",
    "get_top_productos",
    "get_resumen_ventas",
    "resolve_db_path",
    "rows_to_dicts",
]
