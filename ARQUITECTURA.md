# Mapa visual de arquitectura (Punto de Venta)

Este documento muestra el flujo principal de llamadas entre métodos de `PuntoDeVenta` y propone el **primer refactor recomendado**.

## 1) Vista de alto nivel

```mermaid
flowchart TD
    A[main] --> B[PuntoDeVenta.__init__]
    B --> C[init_db]
    B --> D[_build_ui]
    B --> E[_cargar_productos]
    B --> F[_verificar_contrasena_inicial]

    D --> D1[_build_page_ventas]
    D --> D2[_build_page_productos]
    D --> D3[_build_page_historial]
    D --> D4[_show_ventas]

    D4 --> G[_show_page]
    D2 --> H[_cargar_tabla_productos]
    D3 --> I[_cargar_historial]
```

## 2) Mapa “qué método llama a cuál” por módulo funcional

### A. Ventas

```mermaid
flowchart TD
    V0[_build_page_ventas] --> V1[_filtrar_productos]
    V0 --> V2[_agregar_primero_al_carrito]
    V0 --> V3[_focus_tabla]
    V0 --> V4[_agregar_seleccionado]
    V0 --> V5[_quitar_del_carrito]
    V0 --> V6[_limpiar_carrito]
    V0 --> V7[_cobrar_venta]

    V8[_cargar_productos] --> V1
    V2 --> V4
    V4 --> V9[_refresh_carrito]
    V5 --> V9
    V6 --> V9

    V7 --> V9
    V7 --> V8
```

### B. Productos

```mermaid
flowchart TD
    P0[_build_page_productos] --> P1[_cargar_tabla_productos]
    P0 --> P2[_llenar_form_producto]
    P0 --> P3[_guardar_producto]
    P0 --> P4[_eliminar_producto]
    P0 --> P5[_nuevo_producto]
    P0 --> P6[_limpiar_form_producto]

    P3 --> P7[_autocodigo]
    P3 --> P1
    P3 --> P8[_cargar_productos]

    P4 --> P7
    P4 --> P1
    P4 --> P8

    P5 --> P7
```

### C. Historial + seguridad admin

```mermaid
flowchart TD
    H0[_build_page_historial] --> H1[_cargar_historial]
    H0 --> H2[_ver_detalle_venta]
    H0 --> H3[_exportar_csv]
    H0 --> H4[_cambiar_contrasena]
    H0 --> H5[_eliminar_venta_protegida]

    H5 --> H6[_pedir_y_validar_password]
    H5 --> H1

    S0[_verificar_contrasena_inicial] --> S1[set_admin_hash]
    H4 --> S1
    H4 --> S2[get_admin_hash]
    H6 --> S2
```

## 3) Dependencias y acoplamientos clave

- La clase `PuntoDeVenta` concentra UI + reglas + SQL directo.
- Casi todos los métodos de flujo invocan `get_conn()` y hacen consultas dentro del handler de evento.
- El estado de UI y dominio está mezclado (`self.carrito`, `StringVar`, selección de tablas, etc.).

## 4) Primer refactor recomendado (mínimo riesgo, alto impacto)

### Objetivo
Separar acceso a datos (SQLite) de la UI sin cambiar comportamiento visible.

### Paso 1 (primer sprint)
Crear una capa repositorio: `repositorio_pos.py` con funciones/métodos como:

- `listar_productos()`
- `buscar_productos(q)`
- `guardar_producto(...)`
- `eliminar_producto(id)`
- `registrar_venta(carrito)`
- `listar_ventas(fecha=None, limit=200)`
- `detalle_venta(venta_id)`
- `kpis_hoy()`
- `leer_admin_hash()/guardar_admin_hash()`

### Qué mover primero
1. **Lecturas puras** (sin efectos):
   - `_cargar_productos`, `_cargar_tabla_productos`, `_cargar_historial`, `_ver_detalle_venta`.
2. **Después transacciones**:
   - `_cobrar_venta`, `_eliminar_venta_protegida`.

### Beneficios inmediatos
- Menor complejidad en la clase Tkinter.
- Más fácil testear reglas sin abrir UI.
- Menor riesgo al introducir nuevas funciones (cortes de caja, reportes, etc.).

## 5) Orden sugerido de refactor (práctico)

1. Introducir `repositorio_pos.py` manteniendo la API actual.
2. Cambiar sólo llamadas de lectura en UI.
3. Agregar pruebas unitarias de repositorio con SQLite temporal.
4. Migrar operaciones de escritura/transacción.
5. Evaluar un segundo paso: `servicios_pos.py` para reglas (stock, ganancia, validaciones).

