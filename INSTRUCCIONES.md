# Punto de Venta — Guía de instalación en Windows (Producción)

---

## Estructura de archivos que debes tener

Antes de empezar, asegúrate de que **todos estos archivos estén en la misma carpeta**:

```
📁 PuntoDeVenta/
 ├── punto_de_venta.py      ← el programa
 ├── CONSTRUIR_EXE.bat      ← script de construcción (nuevo)
 └── INSTRUCCIONES.md       ← este archivo
```

> La carpeta `respaldos_csv/` y el archivo `ventas.db` se crean automáticamente
> la primera vez que ejecutas el programa.

---

## PASO 1 — Instalar Python en Windows (solo una vez)

1. Entra a **https://python.org** → Downloads → descarga la versión más reciente
2. Ejecuta el instalador
3. ⚠️ **MUY IMPORTANTE:** en la primera pantalla del instalador,
   activa la casilla **"Add Python to PATH"** antes de hacer clic en *Install Now*
4. Cuando termine, abre el *Símbolo del sistema* (CMD) y escribe:
   ```
   python --version
   ```
   Si ves un número de versión, Python está correctamente instalado.

---

## PASO 2 — Construir el ejecutable .exe (solo una vez)

1. Abre la carpeta `PuntoDeVenta/` en el Explorador de Windows
2. Haz doble clic en **`CONSTRUIR_EXE.bat`**
3. Se abrirá una ventana negra que mostrará el progreso — espera entre 1 y 3 minutos
4. Cuando termine, la carpeta `dist/` se abrirá automáticamente con el archivo:

```
📁 dist/
 └── PuntoDeVenta.exe    ← este es tu programa
```

> Este proceso solo necesitas hacerlo **una vez**, o cuando actualices el código `.py`.
> La base de datos `ventas.db` no se ve afectada al reconstruir el ejecutable.

---

## PASO 3 — Configurar la carpeta de producción

### 3.1 — Crear la carpeta definitiva del programa

Crea una carpeta en una ubicación permanente, por ejemplo:

```
C:\PuntoDeVenta\
```

### 3.2 — Copiar los archivos necesarios

Copia **exactamente** estos archivos a `C:\PuntoDeVenta\`:

| Archivo | Descripción |
|---------|-------------|
| `dist\PuntoDeVenta.exe` | El ejecutable principal |
| `ventas.db` *(si ya tienes datos)* | Tu base de datos existente |

> ⚠️ **Importante:** el `.exe` busca `ventas.db` en **la misma carpeta donde él esté**.
> Si mueves el `.exe` sin mover la `ventas.db`, el programa creará una base de datos nueva vacía.

### 3.3 — Estructura final en producción

```
📁 C:\PuntoDeVenta\
 ├── PuntoDeVenta.exe       ← programa
 ├── ventas.db              ← base de datos (se crea sola si no existe)
 └── respaldos_csv\         ← se crea sola al exportar por primera vez
```

---

## PASO 4 — Crear el acceso directo en el escritorio

1. En `C:\PuntoDeVenta\`, haz **clic derecho** sobre `PuntoDeVenta.exe`
2. Selecciona **Enviar a → Escritorio (crear acceso directo)**
3. Opcionalmente, haz clic derecho sobre el acceso directo → **Cambiar nombre** → ponle `Punto de Venta`

Desde ese momento, un **doble clic** en el acceso directo abre el programa directamente,
sin terminal, sin Python visible, como cualquier programa de Windows.

---

## Respaldos de datos

Tu base de datos está en `C:\PuntoDeVenta\ventas.db`. Para respaldarla:

- **Manual:** copia el archivo `ventas.db` a una USB o carpeta de respaldo
- **Desde el programa:** usa el botón **💾 Exportar CSV** en la pestaña Historial

> Recomendación: haz una copia de `ventas.db` al final de cada semana.

---

## Solución de problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| El `.exe` se abre y se cierra inmediatamente | Falta una librería o error en el código | Ejecuta el `.py` original en VSC para ver el error exacto |
| "Windows protegió tu PC" al ejecutar | Windows SmartScreen bloquea ejecutables nuevos | Haz clic en "Más información" → "Ejecutar de todas formas" |
| Los datos no aparecen al abrir | El `.exe` no encuentra `ventas.db` | Asegúrate de que `ventas.db` esté en la **misma carpeta** que el `.exe` |
| `CONSTRUIR_EXE.bat` da error de Python | Python no está en el PATH | Reinstala Python marcando "Add Python to PATH" |

---

## Cuándo volver a construir el .exe

Solo necesitas repetir el **Paso 2** cuando:
- Hayas modificado el código `punto_de_venta.py`
- Quieras agregar nuevas funciones al programa

Los datos en `ventas.db` **nunca** se borran al reconstruir el ejecutable.
