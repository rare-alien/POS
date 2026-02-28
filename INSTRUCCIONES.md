# Punto de Venta — Instrucciones de uso

## Requisitos
- Python 3.8 o superior (viene incluido en muchas distros Linux; en Windows descargar de python.org)
- No requiere instalar librerías externas (usa tkinter y sqlite3 que vienen con Python)

## Cómo ejecutar

### En Linux Mint (desarrollo):
```bash
python3 punto_de_venta.py
```

### En Windows 10 (producción):
1. Instalar Python desde https://python.org (marcar "Add Python to PATH" al instalar)
2. Doble clic en `punto_de_venta.py`
   — ó —
   Abrir CMD en la carpeta y escribir: `python punto_de_venta.py`

## Base de datos
- Se crea automáticamente el archivo `ventas.db` en la misma carpeta que el .py
- **Para hacer respaldos**: simplemente copia el archivo `ventas.db`
- Si borras `ventas.db`, se crea uno nuevo vacío al iniciar

---

## Funciones principales

### 🛒 Pestaña "Ventas" (pantalla principal)
- **Barra de búsqueda**: escribe el nombre o código del producto
- Presiona **Enter** o doble clic para agregar al carrito
- La tecla **↓** mueve el foco a la lista de resultados
- El botón **COBRAR VENTA** registra la venta y descuenta el stock automáticamente

### 📦 Pestaña "Productos"
- **Agregar producto nuevo**: llena el formulario y da clic en "＋ Guardar"
- **Editar producto**: haz clic en un producto de la tabla → se llena el formulario → modifica → "＋ Guardar"
- **Eliminar producto**: selecciona en tabla → "✕ Eliminar"
- Productos con stock ≤ 5 se muestran en amarillo como advertencia

### 📊 Pestaña "Historial"
- Muestra todas las ventas registradas con su detalle
- KPIs del día (ventas totales y monto)
- Filtro por fecha (formato YYYY-MM-DD)
- Al hacer clic en una venta se ve el detalle en el panel derecho

---

## Campos de producto
| Campo     | Descripción                        | Ejemplo      |
|-----------|------------------------------------|--------------|
| Código    | Identificador único (obligatorio)  | P001, 7501   |
| Nombre    | Nombre del producto (obligatorio)  | Refresco 600ml |
| Precio $  | Precio de venta                    | 18.50        |
| Stock     | Unidades disponibles               | 50           |
| Categoría | Clasificación (opcional)           | Bebidas      |

---

## Notas
- Los datos de ejemplo incluidos son solo para demostración; puedes eliminarlos
- El archivo .db y el .py deben estar en la misma carpeta
- Compatible con Windows 10, Windows 11, Linux, macOS
