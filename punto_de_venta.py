"""
=============================================================
  PUNTO DE VENTA  —  Sistema local con SQLite
  Ejecutar:  python punto_de_venta.py
=============================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import sqlite3, os, datetime, hashlib

# ──────────────────────────────────────────────────────────
#  BASE DE DATOS
# ──────────────────────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ventas.db")

def get_conn():
    return sqlite3.connect(DB_FILE)

def _hash(texto):
    """Devuelve el SHA-256 hexadecimal de un texto. Único punto de hashing en todo el sistema."""
    return hashlib.sha256(texto.encode()).hexdigest()

def get_admin_hash():
    """Lee el hash de contraseña guardado en BD. Retorna None si aún no se ha creado."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracion WHERE clave = 'admin_hash'"
        ).fetchone()
    return row[0] if row else None

def set_admin_hash(nuevo_hash):
    """Guarda o actualiza el hash en BD (INSERT OR REPLACE)."""
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('admin_hash', ?)",
            (nuevo_hash,)
        )

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave  TEXT PRIMARY KEY,
                valor  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS productos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo    TEXT    UNIQUE NOT NULL,
                nombre    TEXT    NOT NULL,
                precio    REAL    NOT NULL DEFAULT 0,
                costo     REAL    NOT NULL DEFAULT 0,
                stock     INTEGER NOT NULL DEFAULT 0,
                categoria TEXT    DEFAULT 'General'
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha      TEXT    NOT NULL,
                total      REAL    NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS detalle_venta (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id    INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                nombre      TEXT    NOT NULL,
                precio      REAL    NOT NULL,
                costo       REAL    NOT NULL DEFAULT 0,
                cantidad    INTEGER NOT NULL,
                subtotal    REAL    NOT NULL,
                ganancia    REAL    NOT NULL DEFAULT 0,
                FOREIGN KEY (venta_id)    REFERENCES ventas(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
        """)
        # Migración: agregar columnas a BD existente sin perder datos
        for sql in [
            "ALTER TABLE productos ADD COLUMN costo REAL NOT NULL DEFAULT 0",
            "ALTER TABLE detalle_venta ADD COLUMN costo REAL NOT NULL DEFAULT 0",
            "ALTER TABLE detalle_venta ADD COLUMN ganancia REAL NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass  # La columna ya existe — ignorar
        cur = conn.execute("SELECT COUNT(*) FROM productos")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO productos (codigo,nombre,precio,costo,stock,categoria) VALUES (?,?,?,?,?,?)",
                [
                    ("P001", "Refresco 600ml",  18.0, 12.0, 50, "Bebidas"),
                    ("P002", "Agua 500ml",       10.0,  6.0, 80, "Bebidas"),
                    ("P003", "Papas fritas",     15.0,  9.0, 30, "Botanas"),
                    ("P004", "Galletas",         12.0,  7.0, 40, "Botanas"),
                    ("P005", "Café americano",   25.0, 14.0, 20, "Cafetería"),
                ]
            )

def _generar_codigo_unico():
    """
    Genera un código de producto único con formato PRD-YYYYMMDD-XXXX.
    Verifica contra la BD y reintenta hasta 10 veces si hay colisión
    (probabilidad prácticamente nula, pero se maneja correctamente).
    """
    import random
    for _ in range(10):
        fecha  = datetime.date.today().strftime("%Y%m%d")
        sufijo = format(random.randint(0, 0xFFFF), "04X")   # 0000–FFFF
        codigo = f"PRD-{fecha}-{sufijo}"
        with get_conn() as conn:
            existe = conn.execute(
                "SELECT 1 FROM productos WHERE codigo = ?", (codigo,)
            ).fetchone()
        if not existe:
            return codigo
    # Fallback teórico: timestamp completo con microsegundos
    return f"PRD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"

# ──────────────────────────────────────────────────────────
#  COLORES Y ESTILO
# ──────────────────────────────────────────────────────────
C = {
    "bg":        "#0f1117",
    "panel":     "#1a1d27",
    "card":      "#222638",
    "border":    "#2e3247",
    "accent":    "#4f8ef7",
    "accent2":   "#7c5cbf",
    "green":     "#2ecc71",
    "red":       "#e74c3c",
    "yellow":    "#f39c12",
    "text":      "#e8eaf0",
    "muted":     "#7a7f99",
    "white":     "#ffffff",
    "hover":     "#2d3250",
}

# ──────────────────────────────────────────────────────────
#  APLICACIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────
class PuntoDeVenta(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()
        self.title("Punto de Venta")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])
        self.carrito = []
        self._build_ui()
        self._cargar_productos()
        # Verificar contraseña al arrancar — si no existe, forzar creación
        self.after(200, self._verificar_contrasena_inicial)

    # ── UI principal ──────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self, bg=C["bg"], pady=0)
        header.pack(fill="x", padx=20, pady=(14, 0))

        tk.Label(header, text="●", fg=C["accent"], bg=C["bg"],
                 font=("Courier", 20)).pack(side="left")
        tk.Label(header, text="  PUNTO DE VENTA", fg=C["text"], bg=C["bg"],
                 font=("Courier", 16, "bold")).pack(side="left")

        self.nav_btns = {}
        nav_frame = tk.Frame(header, bg=C["bg"])
        nav_frame.pack(side="right")
        for label, cmd in [("🛒  Ventas", self._show_ventas),
                           ("📦  Productos", self._show_productos),
                           ("📊  Historial", self._show_historial)]:
            b = tk.Button(nav_frame, text=label, bg=C["panel"], fg=C["muted"],
                          bd=0, padx=16, pady=6, cursor="hand2",
                          font=("Courier", 10), activebackground=C["hover"],
                          activeforeground=C["text"], command=cmd)
            b.pack(side="left", padx=3)
            self.nav_btns[label] = b

        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.pack(fill="x", padx=20, pady=10)

        self.content = tk.Frame(self, bg=C["bg"])
        self.content.pack(fill="both", expand=True, padx=20, pady=(0,16))

        self.pages = {}
        self._build_page_ventas()
        self._build_page_productos()
        self._build_page_historial()
        self._show_ventas()

    def _show_page(self, name):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        labels = {"ventas": "🛒  Ventas", "productos": "📦  Productos",
                  "historial": "📊  Historial"}
        for k, b in self.nav_btns.items():
            b.config(fg=C["accent"] if k == labels[name] else C["muted"],
                     bg=C["card"] if k == labels[name] else C["panel"])

    def _show_ventas(self):    self._show_page("ventas")
    def _show_productos(self):
        self._cargar_tabla_productos()
        self._show_page("productos")
        # Auto-generar código si el form está vacío (no hay edición activa)
        if not getattr(self, "_editing_id", None):
            cod = self._prod_entries["e_codigo"].get().strip()
            if not cod:
                self._autocodigo()
    def _show_historial(self): self._cargar_historial(); self._show_page("historial")

    # ══════════════════════════════════════════════════════
    #  PÁGINA: VENTAS
    # ══════════════════════════════════════════════════════
    def _build_page_ventas(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self.pages["ventas"] = page

        left = tk.Frame(page, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0,12))

        search_card = tk.Frame(left, bg=C["card"], padx=12, pady=10)
        search_card.pack(fill="x", pady=(0,10))
        tk.Label(search_card, text="BUSCAR PRODUCTO", fg=C["muted"],
                 bg=C["card"], font=("Courier", 9)).pack(anchor="w")

        sf = tk.Frame(search_card, bg=C["border"], pady=1)
        sf.pack(fill="x", pady=(4,0))
        inner = tk.Frame(sf, bg=C["panel"])
        inner.pack(fill="x")

        tk.Label(inner, text="⌕", fg=C["accent"], bg=C["panel"],
                 font=("Courier", 14), padx=8).pack(side="left")

        self.sv_busqueda = tk.StringVar()
        self.sv_busqueda.trace_add("write", lambda *a: self._filtrar_productos())
        entry = tk.Entry(inner, textvariable=self.sv_busqueda,
                         bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                         bd=0, font=("Courier", 12), highlightthickness=0)
        entry.pack(side="left", fill="x", expand=True, ipady=8)
        entry.focus()
        entry.bind("<Return>", lambda e: self._agregar_primero_al_carrito())
        entry.bind("<Down>", lambda e: self._focus_tabla())

        cols = ("codigo", "nombre", "precio", "stock")
        heads = ("Código", "Nombre", "Precio", "Stock")
        frame_t = tk.Frame(left, bg=C["bg"])
        frame_t.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("POS.Treeview",
            background=C["card"], fieldbackground=C["card"],
            foreground=C["text"], rowheight=32,
            font=("Courier", 10), borderwidth=0)
        style.configure("POS.Treeview.Heading",
            background=C["border"], foreground=C["muted"],
            font=("Courier", 9, "bold"), relief="flat")
        style.map("POS.Treeview",
            background=[("selected", C["accent2"])],
            foreground=[("selected", C["white"])])

        self.tabla_busq = ttk.Treeview(frame_t, columns=cols, show="headings",
                                       style="POS.Treeview", selectmode="browse")
        widths = [80, 260, 90, 70]
        for c, h, w in zip(cols, heads, widths):
            self.tabla_busq.heading(c, text=h)
            self.tabla_busq.column(c, width=w, anchor="center" if c != "nombre" else "w")

        sb = ttk.Scrollbar(frame_t, orient="vertical",
                           command=self.tabla_busq.yview)
        self.tabla_busq.configure(yscrollcommand=sb.set)
        self.tabla_busq.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tabla_busq.bind("<Double-1>", lambda e: self._agregar_seleccionado())
        self.tabla_busq.bind("<Return>", lambda e: self._agregar_seleccionado())

        btn_add = tk.Button(left, text="＋  Agregar al carrito  (↵ Enter)",
                            bg=C["accent"], fg=C["white"], bd=0,
                            font=("Courier", 11, "bold"), pady=10, cursor="hand2",
                            activebackground="#3a7de0",
                            command=self._agregar_seleccionado)
        btn_add.pack(fill="x", pady=(8,0))

        right = tk.Frame(page, bg=C["panel"], width=360, padx=14, pady=14)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="CARRITO DE VENTA", fg=C["muted"],
                 bg=C["panel"], font=("Courier", 9, "bold")).pack(anchor="w")

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", pady=8)

        cart_frame = tk.Frame(right, bg=C["panel"])
        cart_frame.pack(fill="both", expand=True)

        self.lista_carrito = tk.Listbox(cart_frame, bg=C["card"], fg=C["text"],
                                        selectbackground=C["accent2"], bd=0,
                                        font=("Courier", 10), activestyle="none",
                                        highlightthickness=0, relief="flat")
        sb2 = ttk.Scrollbar(cart_frame, orient="vertical",
                             command=self.lista_carrito.yview)
        self.lista_carrito.configure(yscrollcommand=sb2.set)
        self.lista_carrito.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", pady=8)

        total_frame = tk.Frame(right, bg=C["panel"])
        total_frame.pack(fill="x")
        tk.Label(total_frame, text="TOTAL", fg=C["muted"],
                 bg=C["panel"], font=("Courier", 10)).pack(side="left")
        self.lbl_total = tk.Label(total_frame, text="$0.00", fg=C["green"],
                                  bg=C["panel"], font=("Courier", 22, "bold"))
        self.lbl_total.pack(side="right")

        btn_quitar = tk.Button(right, text="✕  Quitar seleccionado",
                               bg=C["card"], fg=C["red"], bd=0,
                               font=("Courier", 10), pady=8, cursor="hand2",
                               activebackground=C["hover"],
                               command=self._quitar_del_carrito)
        btn_quitar.pack(fill="x", pady=(10,4))

        btn_limpiar = tk.Button(right, text="⟳  Limpiar carrito",
                                bg=C["card"], fg=C["yellow"], bd=0,
                                font=("Courier", 10), pady=8, cursor="hand2",
                                activebackground=C["hover"],
                                command=self._limpiar_carrito)
        btn_limpiar.pack(fill="x", pady=4)

        btn_cobrar = tk.Button(right, text="✔  COBRAR VENTA",
                               bg=C["green"], fg=C["white"], bd=0,
                               font=("Courier", 13, "bold"), pady=14, cursor="hand2",
                               activebackground="#27ae60",
                               command=self._cobrar_venta)
        btn_cobrar.pack(fill="x", pady=(8,0))

    # ── Lógica de búsqueda ────────────────────────────────
    def _cargar_productos(self):
        self._productos_cache = []
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id,codigo,nombre,precio,costo,stock FROM productos ORDER BY nombre"
            ).fetchall()
        self._productos_cache = rows
        self._filtrar_productos()

    def _filtrar_productos(self):
        q = self.sv_busqueda.get().strip().lower()
        for row in self.tabla_busq.get_children():
            self.tabla_busq.delete(row)
        for prod in self._productos_cache:
            pid, codigo, nombre, precio, costo, stock = prod
            if q in codigo.lower() or q in nombre.lower():
                tag = "low" if stock <= 5 else ""
                self.tabla_busq.insert("", "end",
                    values=(codigo, nombre, f"${precio:.2f}", stock),
                    iid=str(pid), tags=(tag,))
        self.tabla_busq.tag_configure("low", foreground=C["yellow"])

    def _focus_tabla(self):
        children = self.tabla_busq.get_children()
        if children:
            self.tabla_busq.selection_set(children[0])
            self.tabla_busq.focus(children[0])
            self.tabla_busq.focus_set()

    def _agregar_primero_al_carrito(self):
        children = self.tabla_busq.get_children()
        if children:
            self.tabla_busq.selection_set(children[0])
            self._agregar_seleccionado()

    def _agregar_seleccionado(self):
        sel = self.tabla_busq.selection()
        if not sel:
            self._agregar_primero_al_carrito()
            return
        pid = int(sel[0])
        prod = next((p for p in self._productos_cache if p[0] == pid), None)
        if not prod:
            return
        pid, codigo, nombre, precio, costo, stock = prod
        if stock <= 0:
            messagebox.showwarning("Sin stock",
                f'"{nombre}" no tiene stock disponible.', parent=self)
            return
        for item in self.carrito:
            if item["id"] == pid:
                if item["cantidad"] >= stock:
                    messagebox.showwarning("Stock insuficiente",
                        f'Stock máximo: {stock}', parent=self)
                    return
                item["cantidad"] += 1
                self._refresh_carrito()
                self.sv_busqueda.set("")
                return
        self.carrito.append({"id": pid, "codigo": codigo, "nombre": nombre,
                              "precio": precio, "costo": costo,
                              "cantidad": 1, "stock": stock})
        self._refresh_carrito()
        self.sv_busqueda.set("")

    # ── Carrito ───────────────────────────────────────────
    def _refresh_carrito(self):
        self.lista_carrito.delete(0, "end")
        total = 0
        for i, item in enumerate(self.carrito):
            sub = item["precio"] * item["cantidad"]
            total += sub
            line = f"  {item['nombre'][:22]:<22}  x{item['cantidad']}  ${sub:.2f}"
            self.lista_carrito.insert("end", line)
            if i % 2 == 0:
                self.lista_carrito.itemconfig(i, bg=C["card"])
            else:
                self.lista_carrito.itemconfig(i, bg=C["hover"])
        self.lbl_total.config(text=f"${total:.2f}")

    def _quitar_del_carrito(self):
        sel = self.lista_carrito.curselection()
        if not sel:
            return
        idx = sel[0]
        self.carrito.pop(idx)
        self._refresh_carrito()

    def _limpiar_carrito(self):
        if not self.carrito:
            return
        if messagebox.askyesno("Limpiar", "¿Vaciar el carrito?", parent=self):
            self.carrito.clear()
            self._refresh_carrito()

    def _cobrar_venta(self):
        if not self.carrito:
            messagebox.showinfo("Carrito vacío", "Agrega productos antes de cobrar.",
                                parent=self)
            return
        total = sum(i["precio"] * i["cantidad"] for i in self.carrito)
        confirm = messagebox.askyesno("Confirmar venta",
            f"¿Registrar venta por ${total:.2f}?", parent=self)
        if not confirm:
            return
        with get_conn() as conn:
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute("INSERT INTO ventas (fecha,total) VALUES (?,?)",
                               (fecha, total))
            venta_id = cur.lastrowid
            for item in self.carrito:
                sub      = item["precio"] * item["cantidad"]
                ganancia = (item["precio"] - item["costo"]) * item["cantidad"]
                conn.execute(
                    "INSERT INTO detalle_venta"
                    " (venta_id,producto_id,nombre,precio,costo,cantidad,subtotal,ganancia)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (venta_id, item["id"], item["nombre"],
                     item["precio"], item["costo"], item["cantidad"], sub, ganancia))
                conn.execute("UPDATE productos SET stock = stock - ? WHERE id = ?",
                             (item["cantidad"], item["id"]))
        messagebox.showinfo("✔ Venta registrada",
            f"Venta #{venta_id} guardada.\nTotal: ${total:.2f}", parent=self)
        self.carrito.clear()
        self._refresh_carrito()
        self._cargar_productos()

    # ══════════════════════════════════════════════════════
    #  PÁGINA: PRODUCTOS
    # ══════════════════════════════════════════════════════
    def _build_page_productos(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self.pages["productos"] = page

        form_card = tk.Frame(page, bg=C["card"], padx=16, pady=14)
        form_card.pack(fill="x", pady=(0,12))

        tk.Label(form_card, text="AGREGAR / EDITAR PRODUCTO",
                 fg=C["muted"], bg=C["card"], font=("Courier", 9, "bold")).grid(
                     row=0, column=0, columnspan=6, sticky="w", pady=(0,10))

        fields = [("Código", "e_codigo"), ("Nombre", "e_nombre"),
                  ("Costo $", "e_costo"), ("Precio venta $", "e_precio"),
                  ("Stock", "e_stock"), ("Categoría", "e_categoria")]
        self._prod_entries = {}
        for col, (lbl, key) in enumerate(fields):
            color_lbl = C["yellow"] if key == "e_costo" else C["muted"]
            tk.Label(form_card, text=lbl, fg=color_lbl, bg=C["card"],
                     font=("Courier", 9)).grid(row=1, column=col, padx=(0,4), sticky="w")

            if key == "e_codigo":
                # Campo Código: entry + botón ⟳ en un sub-frame
                wrap = tk.Frame(form_card, bg=C["card"])
                wrap.grid(row=2, column=col, padx=(0,8), sticky="ew")
                ent = tk.Entry(wrap, bg=C["panel"], fg=C["text"],
                               insertbackground=C["text"], bd=0, font=("Courier", 11),
                               highlightbackground=C["border"], highlightthickness=1,
                               width=12)
                ent.pack(side="left", fill="x", expand=True, ipady=6)
                tk.Button(wrap, text="⟳", bg=C["accent2"], fg=C["white"],
                          bd=0, font=("Courier", 10), padx=5, cursor="hand2",
                          activebackground="#6a4aaf",
                          command=self._limpiar_form_producto).pack(side="left", padx=(2,0))
            else:
                ent = tk.Entry(form_card, bg=C["panel"], fg=C["text"],
                               insertbackground=C["text"], bd=0, font=("Courier", 11),
                               highlightbackground=C["border"], highlightthickness=1,
                               width=12)
                ent.grid(row=2, column=col, padx=(0,8), ipady=6, sticky="ew")

            self._prod_entries[key] = ent
        form_card.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(form_card, bg=C["card"])
        btn_frame.grid(row=2, column=6, padx=(8,0), sticky="e")
        # Nuevo: botón para crear un producto nuevo (limpia campos y genera código único)
        tk.Button(btn_frame, text="● Producto nuevo", bg=C["accent2"], fg=C["white"],
              bd=0, font=("Courier", 10), padx=12, pady=6, cursor="hand2",
              activebackground="#6a4aaf",
              command=self._nuevo_producto).pack(side="left", padx=(0,4))

        tk.Button(btn_frame, text="＋ Guardar", bg=C["accent"], fg=C["white"],
              bd=0, font=("Courier", 10, "bold"), padx=12, pady=6, cursor="hand2",
              command=self._guardar_producto).pack(side="left", padx=(0,4))
        tk.Button(btn_frame, text="✕ Eliminar", bg=C["red"], fg=C["white"],
              bd=0, font=("Courier", 10), padx=12, pady=6, cursor="hand2",
              command=self._eliminar_producto).pack(side="left")

        cols = ("id","codigo","nombre","costo","precio","stock","categoria")
        heads = ("ID","Código","Nombre","Costo","Precio venta","Stock","Categoría")
        widths = [40,80,190,70,80,60,90]

        frame_t = tk.Frame(page, bg=C["bg"])
        frame_t.pack(fill="both", expand=True)

        self.tabla_prod = ttk.Treeview(frame_t, columns=cols, show="headings",
                                       style="POS.Treeview", selectmode="browse")
        for c,h,w in zip(cols,heads,widths):
            self.tabla_prod.heading(c, text=h)
            self.tabla_prod.column(c, width=w, anchor="center" if c!="nombre" else "w")
        sb = ttk.Scrollbar(frame_t, orient="vertical",
                           command=self.tabla_prod.yview)
        self.tabla_prod.configure(yscrollcommand=sb.set)
        self.tabla_prod.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tabla_prod.bind("<<TreeviewSelect>>", self._llenar_form_producto)

        search_f = tk.Frame(page, bg=C["bg"])
        search_f.pack(fill="x", pady=(0,6))
        tk.Label(search_f, text="Filtrar: ", fg=C["muted"], bg=C["bg"],
                 font=("Courier",10)).pack(side="left")
        self.sv_prod_filter = tk.StringVar()
        self.sv_prod_filter.trace_add("write", lambda *a: self._cargar_tabla_productos())
        tk.Entry(search_f, textvariable=self.sv_prod_filter,
                 bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                 bd=0, font=("Courier",10), highlightthickness=1,
                 highlightbackground=C["border"], width=30).pack(side="left", ipady=5)

        search_f.pack_forget()
        form_card.pack_forget()
        frame_t.pack_forget()
        form_card.pack(fill="x", pady=(0,8))
        search_f.pack(fill="x", pady=(0,6))
        frame_t.pack(fill="both", expand=True)

    def _cargar_tabla_productos(self):
        q = ""
        if hasattr(self, "sv_prod_filter"):
            q = self.sv_prod_filter.get().strip().lower()
        for row in self.tabla_prod.get_children():
            self.tabla_prod.delete(row)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id,codigo,nombre,costo,precio,stock,categoria FROM productos ORDER BY nombre"
            ).fetchall()
        for r in rows:
            if q in r[1].lower() or q in r[2].lower():
                tag = "low" if r[5] <= 5 else ""
                self.tabla_prod.insert("", "end",
                    values=(r[0],r[1],r[2],f"${r[3]:.2f}",f"${r[4]:.2f}",r[5],r[6]),
                    iid=str(r[0]), tags=(tag,))
        self.tabla_prod.tag_configure("low", foreground=C["yellow"])

    def _llenar_form_producto(self, event=None):
        sel = self.tabla_prod.selection()
        if not sel:
            return
        vals = self.tabla_prod.item(sel[0], "values")
        pid, codigo, nombre, costo, precio, stock, cat = vals
        costo = costo.replace("$","")
        precio = precio.replace("$","")
        keys = ("e_codigo","e_nombre","e_costo","e_precio","e_stock","e_categoria")
        datos = (codigo, nombre, costo, precio, stock, cat)
        for k,d in zip(keys, datos):
            self._prod_entries[k].delete(0,"end")
            self._prod_entries[k].insert(0, d)
        self._editing_id = int(pid)

    def _guardar_producto(self):
        try:
            codigo   = self._prod_entries["e_codigo"].get().strip()
            nombre   = self._prod_entries["e_nombre"].get().strip()
            costo    = float(self._prod_entries["e_costo"].get().strip() or 0)
            precio   = float(self._prod_entries["e_precio"].get().strip())
            stock    = int(self._prod_entries["e_stock"].get().strip())
            categoria= self._prod_entries["e_categoria"].get().strip() or "General"
        except ValueError:
            messagebox.showerror("Error",
                "Costo y Precio deben ser números. Stock debe ser entero.",
                parent=self)
            return
        if not codigo or not nombre:
            messagebox.showerror("Error", "Código y Nombre son obligatorios.", parent=self)
            return
        if costo < 0 or precio < 0:
            messagebox.showerror("Error", "Costo y Precio no pueden ser negativos.", parent=self)
            return

        eid = getattr(self, "_editing_id", None)
        with get_conn() as conn:
            if eid:
                conn.execute(
                    "UPDATE productos SET codigo=?,nombre=?,costo=?,precio=?,stock=?,categoria=?"
                    " WHERE id=?",
                    (codigo, nombre, costo, precio, stock, categoria, eid))
                msg = "Producto actualizado."
            else:
                try:
                    conn.execute(
                        "INSERT INTO productos (codigo,nombre,costo,precio,stock,categoria)"
                        " VALUES (?,?,?,?,?,?)",
                        (codigo, nombre, costo, precio, stock, categoria))
                    msg = "Producto agregado."
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error",
                        f'El código "{codigo}" ya existe.', parent=self)
                    return
        messagebox.showinfo("OK", msg, parent=self)
        for e in self._prod_entries.values():
            e.delete(0,"end")
        self._editing_id = None
        self._autocodigo()           # pre-cargar código para el siguiente producto
        self._cargar_tabla_productos()
        self._cargar_productos()

    def _eliminar_producto(self):
        eid = getattr(self, "_editing_id", None)
        if not eid:
            messagebox.showinfo("Selecciona un producto",
                "Haz clic en un producto de la tabla primero.", parent=self)
            return
        sel = self.tabla_prod.selection()
        nombre = self.tabla_prod.item(sel[0])["values"][2] if sel else "?"
        if messagebox.askyesno("Eliminar",
            f'¿Eliminar "{nombre}"? (No se puede deshacer)', parent=self):
            with get_conn() as conn:
                conn.execute("DELETE FROM productos WHERE id=?", (eid,))
            for e in self._prod_entries.values():
                e.delete(0,"end")
            self._editing_id = None
            self._autocodigo()       # pre-cargar código para el siguiente producto
            self._cargar_tabla_productos()
            self._cargar_productos()

    def _autocodigo(self):
        """
        Genera un código único y lo coloca en el campo Código del formulario.
        Solo actúa cuando NO se está editando un producto existente,
        para no pisar el código real de un producto cargado.
        """
        # Si hay un producto seleccionado para edición, no tocar el campo
        if getattr(self, "_editing_id", None):
            return
        codigo = _generar_codigo_unico()
        e = self._prod_entries["e_codigo"]
        e.delete(0, "end")
        e.insert(0, codigo)

    def _limpiar_form_producto(self):
        """
        Limpia todos los campos del formulario de producto y cancela cualquier edición.
        El botón de flecha debe usar esta acción para vaciar código y datos.
        """
        for k, ent in self._prod_entries.items():
            ent.delete(0, "end")
        self._editing_id = None

    def _nuevo_producto(self):
        """
        Preparar formulario para un producto nuevo: limpiar campos y generar
        un código único verificando que no exista en la base de datos.
        """
        # Asegurarse de no estar en modo edición
        self._editing_id = None
        for ent in self._prod_entries.values():
            ent.delete(0, "end")
        # Genera y escribe un código único
        self._autocodigo()
        # Poner foco en el nombre para facilitar entrada
        if "e_nombre" in self._prod_entries:
            self._prod_entries["e_nombre"].focus()

    # ══════════════════════════════════════════════════════
    #  PÁGINA: HISTORIAL
    # ══════════════════════════════════════════════════════
    def _build_page_historial(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self.pages["historial"] = page

        # Filtro fecha
        filter_f = tk.Frame(page, bg=C["card"], padx=12, pady=10)
        filter_f.pack(fill="x", pady=(0,10))
        tk.Label(filter_f, text="Filtrar por fecha (YYYY-MM-DD):", fg=C["muted"],
                 bg=C["card"], font=("Courier",9)).pack(side="left")
        self.sv_hist_fecha = tk.StringVar()
        self.sv_hist_fecha.trace_add("write", lambda *a: self._cargar_historial())
        tk.Entry(filter_f, textvariable=self.sv_hist_fecha,
                 bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                 bd=0, font=("Courier",11), width=14, highlightthickness=1,
                 highlightbackground=C["border"]).pack(side="left", padx=8, ipady=5)

        # Botón eliminar venta (con candado) — alineado a la derecha en la misma barra
        tk.Button(filter_f, text="🗑  Eliminar venta seleccionada",
                  bg=C["red"], fg=C["white"], bd=0,
                  font=("Courier", 10, "bold"), padx=14, pady=4, cursor="hand2",
                  activebackground="#c0392b",
                  command=self._eliminar_venta_protegida).pack(side="right")

        # Botón cambiar contraseña
        tk.Button(filter_f, text="🔑  Cambiar contraseña",
                  bg=C["accent2"], fg=C["white"], bd=0,
                  font=("Courier", 10), padx=12, pady=4, cursor="hand2",
                  activebackground="#6a4aaf",
                  command=self._cambiar_contrasena).pack(side="right", padx=(0,8))

        # KPIs
        self.kpi_frame = tk.Frame(page, bg=C["bg"])
        self.kpi_frame.pack(fill="x", pady=(0,10))
        self.kpi_ventas   = self._kpi_box(self.kpi_frame, "VENTAS HOY",   "0",      C["accent"])
        self.kpi_total    = self._kpi_box(self.kpi_frame, "TOTAL HOY",    "$0.00",  C["green"])
        self.kpi_ganancia = self._kpi_box(self.kpi_frame, "GANANCIA HOY", "$0.00",  C["yellow"])

        # Tabla historial ventas
        cols_v = ("id","fecha","total")
        fr1 = tk.Frame(page, bg=C["bg"])
        fr1.pack(fill="both", expand=True)

        tk.Label(fr1, text="VENTAS REGISTRADAS", fg=C["muted"], bg=C["bg"],
                 font=("Courier",9,"bold")).pack(anchor="w", pady=(0,4))

        split = tk.Frame(fr1, bg=C["bg"])
        split.pack(fill="both", expand=True)

        left_h = tk.Frame(split, bg=C["bg"])
        left_h.pack(side="left", fill="both", expand=True, padx=(0,8))

        self.tabla_hist = ttk.Treeview(left_h, columns=cols_v, show="headings",
                                       style="POS.Treeview", height=12)
        for c,h,w in zip(cols_v,("ID","Fecha","Total"),(50,200,100)):
            self.tabla_hist.heading(c, text=h)
            self.tabla_hist.column(c, width=w, anchor="center")
        sb = ttk.Scrollbar(left_h, orient="vertical", command=self.tabla_hist.yview)
        self.tabla_hist.configure(yscrollcommand=sb.set)
        self.tabla_hist.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tabla_hist.bind("<<TreeviewSelect>>", self._ver_detalle_venta)

        # Detalle venta
        right_h = tk.Frame(split, bg=C["card"], padx=12, pady=12, width=350)
        right_h.pack(side="right", fill="y")
        right_h.pack_propagate(False)

        tk.Label(right_h, text="DETALLE DE VENTA", fg=C["muted"], bg=C["card"],
                 font=("Courier",9,"bold")).pack(anchor="w", pady=(0,6))

        self.tabla_det = ttk.Treeview(right_h,
            columns=("nombre","cant","precio","sub","ganancia"),
            show="headings", style="POS.Treeview")
        for c,h,w in zip(("nombre","cant","precio","sub","ganancia"),
                          ("Producto","Cant","Precio","Subtotal","Ganancia"),
                          (130,35,65,70,70)):
            self.tabla_det.heading(c,text=h)
            self.tabla_det.column(c,width=w,anchor="center" if c!="nombre" else "w")
        self.tabla_det.pack(fill="both", expand=True)

    def _kpi_box(self, parent, label, value, color):
        box = tk.Frame(parent, bg=C["card"], padx=20, pady=12)
        box.pack(side="left", padx=(0,8))
        tk.Label(box, text=label, fg=C["muted"], bg=C["card"],
                 font=("Courier",8)).pack(anchor="w")
        lbl = tk.Label(box, text=value, fg=color, bg=C["card"],
                       font=("Courier",18,"bold"))
        lbl.pack(anchor="w")
        return lbl

    def _cargar_historial(self):
        f = ""
        if hasattr(self, "sv_hist_fecha"):
            f = self.sv_hist_fecha.get().strip()
        today = datetime.date.today().isoformat()
        for row in self.tabla_hist.get_children():
            self.tabla_hist.delete(row)
        with get_conn() as conn:
            if f:
                rows = conn.execute(
                    "SELECT id,fecha,total FROM ventas WHERE fecha LIKE ? ORDER BY id DESC",
                    (f"%{f}%",)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id,fecha,total FROM ventas ORDER BY id DESC LIMIT 200"
                ).fetchall()
            kpi = conn.execute(
                "SELECT COUNT(*), IFNULL(SUM(v.total),0),"
                " IFNULL(SUM(dv.ganancia),0)"
                " FROM ventas v"
                " LEFT JOIN detalle_venta dv ON dv.venta_id = v.id"
                " WHERE v.fecha LIKE ?",
                (f"{today}%",)).fetchone()
        for r in rows:
            self.tabla_hist.insert("","end",
                values=(r[0],r[1],f"${r[2]:.2f}"), iid=str(r[0]))
        if hasattr(self,"kpi_ventas"):
            self.kpi_ventas.config(text=str(kpi[0]))
            self.kpi_total.config(text=f"${kpi[1]:.2f}")
            self.kpi_ganancia.config(text=f"${kpi[2]:.2f}")

    def _ver_detalle_venta(self, event=None):
        sel = self.tabla_hist.selection()
        if not sel:
            return
        vid = int(sel[0])
        for row in self.tabla_det.get_children():
            self.tabla_det.delete(row)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT nombre,cantidad,precio,subtotal,ganancia FROM detalle_venta"
                " WHERE venta_id=?", (vid,)).fetchall()
        for r in rows:
            self.tabla_det.insert("","end",
                values=(r[0],r[1],f"${r[2]:.2f}",f"${r[3]:.2f}",f"${r[4]:.2f}"))

    # ══════════════════════════════════════════════════════
    #  GESTIÓN DE CONTRASEÑA DE ADMINISTRADOR
    # ══════════════════════════════════════════════════════
    def _verificar_contrasena_inicial(self):
        """
        Se llama al arrancar. Si no existe contraseña en BD, muestra un
        diálogo obligatorio para crear una. No se puede cerrar sin crearla.
        """
        if get_admin_hash() is not None:
            return  # Ya existe contraseña → todo en orden, continuar normalmente

        # No hay contraseña: mostrar diálogo de creación obligatorio
        dlg = tk.Toplevel(self)
        dlg.title("🔐 Crear contraseña de administrador")
        dlg.configure(bg=C["card"])
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.focus_set()

        # No se puede cerrar con la X hasta crear la contraseña
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  // 2) - 240
        y = self.winfo_y() + (self.winfo_height() // 2) - 160
        dlg.geometry(f"480x320+{x}+{y}")

        tk.Label(dlg, text="🔐  PRIMERA CONFIGURACIÓN",
                 fg=C["accent"], bg=C["card"],
                 font=("Courier", 12, "bold")).pack(pady=(22, 4))
        tk.Label(dlg, text="Crea la contraseña de administrador para proteger\nla eliminación de ventas. Guárdala en un lugar seguro.",
                 fg=C["text"], bg=C["card"],
                 font=("Courier", 9), justify="center").pack(pady=(0, 14))

        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x", padx=20, pady=(0, 14))

        fields_frame = tk.Frame(dlg, bg=C["card"])
        fields_frame.pack(padx=30, fill="x")

        tk.Label(fields_frame, text="Nueva contraseña:", fg=C["muted"],
                 bg=C["card"], font=("Courier", 9)).pack(anchor="w")
        sv_nueva = tk.StringVar()
        e_nueva = tk.Entry(fields_frame, textvariable=sv_nueva, show="•",
                           bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                           bd=0, font=("Courier", 12), highlightthickness=1,
                           highlightbackground=C["border"])
        e_nueva.pack(fill="x", ipady=7, pady=(2, 10))
        e_nueva.focus()

        tk.Label(fields_frame, text="Confirmar contraseña:", fg=C["muted"],
                 bg=C["card"], font=("Courier", 9)).pack(anchor="w")
        sv_conf = tk.StringVar()
        e_conf = tk.Entry(fields_frame, textvariable=sv_conf, show="•",
                          bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                          bd=0, font=("Courier", 12), highlightthickness=1,
                          highlightbackground=C["border"])
        e_conf.pack(fill="x", ipady=7, pady=(2, 0))

        lbl_error = tk.Label(dlg, text="", fg=C["red"], bg=C["card"],
                             font=("Courier", 9))
        lbl_error.pack(pady=(6, 0))

        def _guardar():
            nueva = sv_nueva.get()
            conf  = sv_conf.get()

            # Validaciones antes de guardar
            if not nueva:
                lbl_error.config(text="✕ La contraseña no puede estar vacía.")
                return
            if len(nueva) < 4:
                lbl_error.config(text="✕ Mínimo 4 caracteres.")
                return
            if nueva != conf:
                lbl_error.config(text="✕ Las contraseñas no coinciden.")
                sv_conf.set("")
                e_conf.focus()
                return

            set_admin_hash(_hash(nueva))
            dlg.destroy()
            messagebox.showinfo("✔ Contraseña creada",
                "Contraseña de administrador guardada correctamente.\n"
                "Recuérdala: la necesitarás para eliminar ventas.", parent=self)

        e_conf.bind("<Return>", lambda e: _guardar())
        e_nueva.bind("<Return>", lambda e: e_conf.focus())

        tk.Button(dlg, text="✔  Guardar contraseña",
                  bg=C["green"], fg=C["white"], bd=0,
                  font=("Courier", 11, "bold"), pady=10, cursor="hand2",
                  activebackground="#27ae60",
                  command=_guardar).pack(fill="x", padx=30, pady=(12, 0))

    def _cambiar_contrasena(self):
        """
        Flujo para cambiar la contraseña:
          1. Pedir contraseña ACTUAL y validar
          2. Pedir contraseña NUEVA con confirmación
          3. Guardar nuevo hash en BD

        Si no existe contraseña aún, redirige al flujo de creación.
        """
        if get_admin_hash() is None:
            # Caso borde: el usuario llega aquí sin haber creado contraseña aún
            self._verificar_contrasena_inicial()
            return

        dlg = tk.Toplevel(self)
        dlg.title("🔑 Cambiar contraseña de administrador")
        dlg.configure(bg=C["card"])
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.focus_set()
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  // 2) - 240
        y = self.winfo_y() + (self.winfo_height() // 2) - 180
        dlg.geometry(f"480x360+{x}+{y}")

        tk.Label(dlg, text="🔑  CAMBIAR CONTRASEÑA",
                 fg=C["accent2"], bg=C["card"],
                 font=("Courier", 12, "bold")).pack(pady=(22, 4))
        tk.Label(dlg, text="Debes ingresar tu contraseña actual antes de establecer una nueva.",
                 fg=C["muted"], bg=C["card"],
                 font=("Courier", 9), justify="center").pack(pady=(0, 12))

        tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x", padx=20, pady=(0, 14))

        ff = tk.Frame(dlg, bg=C["card"])
        ff.pack(padx=30, fill="x")

        def _campo(parent, label, sv):
            tk.Label(parent, text=label, fg=C["muted"], bg=C["card"],
                     font=("Courier", 9)).pack(anchor="w")
            ent = tk.Entry(parent, textvariable=sv, show="•",
                           bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                           bd=0, font=("Courier", 12), highlightthickness=1,
                           highlightbackground=C["border"])
            ent.pack(fill="x", ipady=7, pady=(2, 10))
            return ent

        sv_actual = tk.StringVar()
        sv_nueva  = tk.StringVar()
        sv_conf   = tk.StringVar()

        e_actual = _campo(ff, "Contraseña actual:", sv_actual)
        e_nueva  = _campo(ff, "Nueva contraseña:", sv_nueva)
        e_conf   = _campo(ff, "Confirmar nueva contraseña:", sv_conf)
        e_actual.focus()

        lbl_error = tk.Label(dlg, text="", fg=C["red"], bg=C["card"],
                             font=("Courier", 9))
        lbl_error.pack(pady=(0, 4))

        intentos_actuales = [0]  # Lista mutable para modificar desde closure

        def _guardar():
            actual = sv_actual.get()
            nueva  = sv_nueva.get()
            conf   = sv_conf.get()

            # Capa 1: campos vacíos
            if not actual or not nueva or not conf:
                lbl_error.config(text="✕ Todos los campos son obligatorios.")
                return

            # Capa 2: validar contraseña actual con hash (máx 3 intentos)
            intentos_actuales[0] += 1
            if _hash(actual) != get_admin_hash():
                restantes = 3 - intentos_actuales[0]
                if restantes <= 0:
                    dlg.destroy()
                    messagebox.showerror("Acceso denegado",
                        "Demasiados intentos incorrectos.\nOperación cancelada.", parent=self)
                    return
                lbl_error.config(
                    text=f"✕ Contraseña actual incorrecta. {restantes} intento(s) restante(s)."
                )
                sv_actual.set("")
                e_actual.focus()
                return

            # Capa 3: validar nueva contraseña
            if len(nueva) < 4:
                lbl_error.config(text="✕ La nueva contraseña debe tener al menos 4 caracteres.")
                return
            if nueva != conf:
                lbl_error.config(text="✕ La nueva contraseña y su confirmación no coinciden.")
                sv_conf.set("")
                e_conf.focus()
                return
            if _hash(nueva) == get_admin_hash():
                lbl_error.config(text="✕ La nueva contraseña es igual a la actual.")
                return

            # Todo OK: guardar nuevo hash
            set_admin_hash(_hash(nueva))
            dlg.destroy()
            messagebox.showinfo("✔ Contraseña actualizada",
                "La contraseña de administrador fue cambiada exitosamente.", parent=self)

        e_actual.bind("<Return>", lambda e: e_nueva.focus())
        e_nueva.bind("<Return>",  lambda e: e_conf.focus())
        e_conf.bind("<Return>",   lambda e: _guardar())

        btn_f = tk.Frame(dlg, bg=C["card"])
        btn_f.pack(padx=30, fill="x", pady=(4, 0))
        tk.Button(btn_f, text="✔  Guardar cambios", bg=C["accent2"], fg=C["white"],
                  bd=0, font=("Courier", 11, "bold"), pady=9, cursor="hand2",
                  command=_guardar).pack(side="left", expand=True, fill="x", padx=(0,4))
        tk.Button(btn_f, text="✕  Cancelar", bg=C["panel"], fg=C["muted"],
                  bd=0, font=("Courier", 10), pady=9, cursor="hand2",
                  command=dlg.destroy).pack(side="left", expand=True, fill="x")

    # ══════════════════════════════════════════════════════
    #  ELIMINAR VENTA CON CONTRASEÑA
    # ══════════════════════════════════════════════════════
    def _eliminar_venta_protegida(self):
        """
        Flujo de eliminación segura de una venta del historial.

        Capas de validación (fail-fast, de menor a mayor costo):
          1. ¿Hay venta seleccionada?         → barato, solo leer UI
          2. ¿Se ingresó contraseña?          → diálogo modal
          3. ¿Contraseña correcta? (hash)     → comparación en memoria
          4. ¿Confirmar con resumen?          → doble intención
          5. DELETE en transacción atómica    → detalle primero, luego cabecera
          6. Manejo de excepción de BD        → rollback automático
        """

        # ── Capa 1: Validar que haya una venta seleccionada ──────────────
        sel = self.tabla_hist.selection()
        if not sel:
            messagebox.showinfo(
                "Sin selección",
                "Primero selecciona una venta de la tabla antes de eliminar.",
                parent=self
            )
            return  # Salida temprana: no tiene sentido continuar

        # Extraer datos de la venta para mostrarlos en los diálogos
        vals = self.tabla_hist.item(sel[0], "values")
        venta_id   = int(vals[0])
        venta_fecha = vals[1]
        venta_total = vals[2]

        # ── Capa 2 y 3: Diálogo de contraseña con validación de hash ─────
        password_ok = self._pedir_y_validar_password(venta_id, venta_fecha, venta_total)
        if not password_ok:
            return  # El método interno ya mostró el mensaje de error

        # ── Capa 4: Confirmación final con resumen de la venta ────────────
        confirmado = messagebox.askyesno(
            "⚠ Confirmar eliminación",
            f"Estás a punto de eliminar PERMANENTEMENTE:\n\n"
            f"  Venta #:  {venta_id}\n"
            f"  Fecha:    {venta_fecha}\n"
            f"  Total:    {venta_total}\n\n"
            "Esta acción NO se puede deshacer.\n¿Continuar?",
            icon="warning",
            parent=self
        )
        if not confirmado:
            return  # El usuario canceló en el último momento

        # ── Capa 5 y 6: Eliminar en transacción atómica ───────────────────
        try:
            with get_conn() as conn:
                # ORDEN CRÍTICO: primero el detalle (FK hijo), luego la cabecera (FK padre)
                # Si se invirtiera el orden, SQLite lanzaría un error de integridad referencial.
                conn.execute(
                    "DELETE FROM detalle_venta WHERE venta_id = ?", (venta_id,)
                )
                conn.execute(
                    "DELETE FROM ventas WHERE id = ?", (venta_id,)
                )
                # El 'with' hace COMMIT automático al salir sin excepciones.
                # Si algo falla aquí dentro, hace ROLLBACK automático,
                # dejando la BD intacta.

        except sqlite3.Error as e:
            # Error inesperado de base de datos (disco lleno, BD corrupta, etc.)
            messagebox.showerror(
                "Error de base de datos",
                f"No se pudo eliminar la venta.\nDetalle técnico: {e}",
                parent=self
            )
            return

        # ── Éxito: limpiar UI y recargar ──────────────────────────────────
        # Limpiar el panel de detalle (puede mostrar datos de la venta eliminada)
        for row in self.tabla_det.get_children():
            self.tabla_det.delete(row)

        self._cargar_historial()  # Refresca tabla e indicadores KPI

        messagebox.showinfo(
            "✔ Venta eliminada",
            f"La venta #{venta_id} fue eliminada correctamente.",
            parent=self
        )

    def _pedir_y_validar_password(self, venta_id, fecha, total):
        """
        Muestra un diálogo modal para ingresar la contraseña de administrador.
        Permite hasta 3 intentos antes de bloquear la operación.
        Retorna True si la contraseña es correcta, False en caso contrario.

        Por qué un método separado:
          - Responsabilidad única: solo se ocupa de autenticar
          - Testeable de forma independiente
          - Reutilizable si en el futuro se necesita en otras acciones protegidas
        """
        MAX_INTENTOS = 3

        for intento in range(1, MAX_INTENTOS + 1):

            # ── Construir el diálogo modal ────────────────────────────────
            dlg = tk.Toplevel(self)
            dlg.title("🔒 Autenticación requerida")
            dlg.configure(bg=C["card"])
            dlg.resizable(False, False)
            dlg.grab_set()   # Modal: bloquea la ventana principal mientras está abierto
            dlg.focus_set()

            # Centrar el diálogo sobre la ventana principal
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width()  // 2) - 220
            y = self.winfo_y() + (self.winfo_height() // 2) - 120
            dlg.geometry(f"440x240+{x}+{y}")

            # ── Contenido del diálogo ─────────────────────────────────────
            tk.Label(dlg, text="🔒  ELIMINAR VENTA — ACCESO RESTRINGIDO",
                     fg=C["red"], bg=C["card"],
                     font=("Courier", 10, "bold")).pack(pady=(18,4))

            tk.Label(dlg,
                     text=f"Venta #{venta_id}  •  {fecha}  •  {total}",
                     fg=C["muted"], bg=C["card"],
                     font=("Courier", 9)).pack()

            tk.Frame(dlg, bg=C["border"], height=1).pack(fill="x", padx=20, pady=10)

            # Indicador de intento si ya hubo errores previos
            if intento > 1:
                tk.Label(dlg,
                         text=f"✕ Contraseña incorrecta — intento {intento} de {MAX_INTENTOS}",
                         fg=C["yellow"], bg=C["card"],
                         font=("Courier", 9)).pack(pady=(0,4))

            tk.Label(dlg, text="Ingresa la contraseña de administrador:",
                     fg=C["text"], bg=C["card"],
                     font=("Courier", 10)).pack(pady=(0,6))

            # Campo de contraseña (show="•" oculta los caracteres)
            sv_pass = tk.StringVar()
            entry_pass = tk.Entry(dlg, textvariable=sv_pass,
                                  show="•",
                                  bg=C["panel"], fg=C["text"],
                                  insertbackground=C["text"],
                                  bd=0, font=("Courier", 13),
                                  highlightthickness=1,
                                  highlightbackground=C["border"],
                                  width=24)
            entry_pass.pack(ipady=7, pady=(0,12))
            entry_pass.focus()

            # Variable de resultado del diálogo
            resultado = {"accion": None}  # "ok" | "cancelar"

            def _confirmar(event=None):
                resultado["accion"] = "ok"
                dlg.destroy()

            def _cancelar(event=None):
                resultado["accion"] = "cancelar"
                dlg.destroy()

            entry_pass.bind("<Return>", _confirmar)
            entry_pass.bind("<Escape>", _cancelar)
            dlg.protocol("WM_DELETE_WINDOW", _cancelar)  # El botón X también cancela

            btn_frame = tk.Frame(dlg, bg=C["card"])
            btn_frame.pack()
            tk.Button(btn_frame, text="✔ Confirmar", bg=C["red"], fg=C["white"],
                      bd=0, font=("Courier", 10, "bold"), padx=16, pady=6,
                      cursor="hand2", command=_confirmar).pack(side="left", padx=4)
            tk.Button(btn_frame, text="✕ Cancelar", bg=C["panel"], fg=C["muted"],
                      bd=0, font=("Courier", 10), padx=16, pady=6,
                      cursor="hand2", command=_cancelar).pack(side="left", padx=4)

            # Esperar a que el diálogo se cierre (bloqueo local del event loop)
            dlg.wait_window()

            # ── Evaluar resultado ─────────────────────────────────────────
            if resultado["accion"] == "cancelar":
                # El usuario cerró o presionó Cancelar/Escape — salir limpiamente
                return False

            # ── Capa 3: Validar contraseña con hash SHA-256 ───────────────
            # Nunca comparar texto plano. Hashear lo ingresado y comparar hashes.
            ingresada = sv_pass.get()

            # Error de validación: campo vacío
            if not ingresada:
                messagebox.showwarning(
                    "Campo vacío", "Debes ingresar una contraseña.", parent=self
                )
                continue  # Cuenta como intento

            hash_ingresada = _hash(ingresada)

            if hash_ingresada == get_admin_hash():
                return True  # ✔ Autenticación exitosa

            # Contraseña incorrecta — si no quedan intentos, abortar
            if intento == MAX_INTENTOS:
                messagebox.showerror(
                    "Acceso denegado",
                    f"Se superaron {MAX_INTENTOS} intentos fallidos.\n"
                    "La operación ha sido cancelada por seguridad.",
                    parent=self
                )
                return False

            # Queda al menos un intento más → el bucle abre un nuevo diálogo

        return False  # Salvaguarda: nunca debería llegar aquí


# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PuntoDeVenta()
    app.mainloop()
