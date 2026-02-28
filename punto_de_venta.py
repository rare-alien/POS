"""
=============================================================
  PUNTO DE VENTA  —  Sistema local con SQLite
  Ejecutar:  python punto_de_venta.py
=============================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import sqlite3, os, datetime

# ──────────────────────────────────────────────────────────
#  BASE DE DATOS
# ──────────────────────────────────────────────────────────
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ventas.db")

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS productos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo    TEXT    UNIQUE NOT NULL,
                nombre    TEXT    NOT NULL,
                precio    REAL    NOT NULL DEFAULT 0,
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
                cantidad    INTEGER NOT NULL,
                subtotal    REAL    NOT NULL,
                FOREIGN KEY (venta_id)    REFERENCES ventas(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            );
        """)
        # Datos de ejemplo si la tabla está vacía
        cur = conn.execute("SELECT COUNT(*) FROM productos")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO productos (codigo,nombre,precio,stock,categoria) VALUES (?,?,?,?,?)",
                [
                    ("P001", "Refresco 600ml",  18.0, 50, "Bebidas"),
                    ("P002", "Agua 500ml",       10.0, 80, "Bebidas"),
                    ("P003", "Papas fritas",     15.0, 30, "Botanas"),
                    ("P004", "Galletas",         12.0, 40, "Botanas"),
                    ("P005", "Café americano",   25.0, 20, "Cafetería"),
                ]
            )

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
        self.carrito = []          # lista de dicts
        self._build_ui()
        self._cargar_productos()

    # ── UI principal ──────────────────────────────────────
    def _build_ui(self):
        # Título superior
        header = tk.Frame(self, bg=C["bg"], pady=0)
        header.pack(fill="x", padx=20, pady=(14, 0))

        tk.Label(header, text="●", fg=C["accent"], bg=C["bg"],
                 font=("Courier", 20)).pack(side="left")
        tk.Label(header, text="  PUNTO DE VENTA", fg=C["text"], bg=C["bg"],
                 font=("Courier", 16, "bold")).pack(side="left")

        # Botones de navegación
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

        # Contenedor principal (páginas)
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
    def _show_productos(self): self._cargar_tabla_productos(); self._show_page("productos")
    def _show_historial(self): self._cargar_historial(); self._show_page("historial")

    # ══════════════════════════════════════════════════════
    #  PÁGINA: VENTAS
    # ══════════════════════════════════════════════════════
    def _build_page_ventas(self):
        page = tk.Frame(self.content, bg=C["bg"])
        self.pages["ventas"] = page

        # ── Izquierda: búsqueda + resultados ─────────────
        left = tk.Frame(page, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0,12))

        # Barra de búsqueda
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

        # Tabla de productos
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

        # Botón agregar
        btn_add = tk.Button(left, text="＋  Agregar al carrito  (↵ Enter)",
                            bg=C["accent"], fg=C["white"], bd=0,
                            font=("Courier", 11, "bold"), pady=10, cursor="hand2",
                            activebackground="#3a7de0",
                            command=self._agregar_seleccionado)
        btn_add.pack(fill="x", pady=(8,0))

        # ── Derecha: carrito + total ──────────────────────
        right = tk.Frame(page, bg=C["panel"], width=360, padx=14, pady=14)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="CARRITO DE VENTA", fg=C["muted"],
                 bg=C["panel"], font=("Courier", 9, "bold")).pack(anchor="w")

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", pady=8)

        # Lista carrito
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

        # Total
        total_frame = tk.Frame(right, bg=C["panel"])
        total_frame.pack(fill="x")
        tk.Label(total_frame, text="TOTAL", fg=C["muted"],
                 bg=C["panel"], font=("Courier", 10)).pack(side="left")
        self.lbl_total = tk.Label(total_frame, text="$0.00", fg=C["green"],
                                  bg=C["panel"], font=("Courier", 22, "bold"))
        self.lbl_total.pack(side="right")

        # Botones carrito
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
                "SELECT id,codigo,nombre,precio,stock FROM productos ORDER BY nombre"
            ).fetchall()
        self._productos_cache = rows
        self._filtrar_productos()

    def _filtrar_productos(self):
        q = self.sv_busqueda.get().strip().lower()
        for row in self.tabla_busq.get_children():
            self.tabla_busq.delete(row)
        for prod in self._productos_cache:
            pid, codigo, nombre, precio, stock = prod
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
        pid, codigo, nombre, precio, stock = prod
        if stock <= 0:
            messagebox.showwarning("Sin stock",
                f'"{nombre}" no tiene stock disponible.', parent=self)
            return
        # ¿Ya en carrito?
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
                              "precio": precio, "cantidad": 1, "stock": stock})
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
                sub = item["precio"] * item["cantidad"]
                conn.execute(
                    "INSERT INTO detalle_venta (venta_id,producto_id,nombre,precio,cantidad,subtotal)"
                    " VALUES (?,?,?,?,?,?)",
                    (venta_id, item["id"], item["nombre"],
                     item["precio"], item["cantidad"], sub))
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

        # Formulario agregar/editar
        form_card = tk.Frame(page, bg=C["card"], padx=16, pady=14)
        form_card.pack(fill="x", pady=(0,12))

        tk.Label(form_card, text="AGREGAR / EDITAR PRODUCTO",
                 fg=C["muted"], bg=C["card"], font=("Courier", 9, "bold")).grid(
                     row=0, column=0, columnspan=6, sticky="w", pady=(0,10))

        fields = [("Código", "e_codigo"), ("Nombre", "e_nombre"),
                  ("Precio $", "e_precio"), ("Stock", "e_stock"),
                  ("Categoría", "e_categoria")]
        self._prod_entries = {}
        for col, (lbl, key) in enumerate(fields):
            tk.Label(form_card, text=lbl, fg=C["muted"], bg=C["card"],
                     font=("Courier", 9)).grid(row=1, column=col, padx=(0,4), sticky="w")
            ent = tk.Entry(form_card, bg=C["panel"], fg=C["text"],
                           insertbackground=C["text"], bd=0, font=("Courier", 11),
                           highlightbackground=C["border"], highlightthickness=1,
                           width=14)
            ent.grid(row=2, column=col, padx=(0,8), ipady=6, sticky="ew")
            self._prod_entries[key] = ent
        form_card.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(form_card, bg=C["card"])
        btn_frame.grid(row=2, column=5, padx=(8,0), sticky="e")

        tk.Button(btn_frame, text="＋ Guardar", bg=C["accent"], fg=C["white"],
                  bd=0, font=("Courier", 10, "bold"), padx=12, pady=6, cursor="hand2",
                  command=self._guardar_producto).pack(side="left", padx=(0,4))
        tk.Button(btn_frame, text="✕ Eliminar", bg=C["red"], fg=C["white"],
                  bd=0, font=("Courier", 10), padx=12, pady=6, cursor="hand2",
                  command=self._eliminar_producto).pack(side="left")

        # Tabla productos
        cols = ("id","codigo","nombre","precio","stock","categoria")
        heads = ("ID","Código","Nombre","Precio","Stock","Categoría")
        widths = [40,90,220,80,70,100]

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

        # Barra búsqueda productos
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

        # Reordenar para que la búsqueda esté antes de la tabla
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
                "SELECT id,codigo,nombre,precio,stock,categoria FROM productos ORDER BY nombre"
            ).fetchall()
        for r in rows:
            if q in r[1].lower() or q in r[2].lower():
                tag = "low" if r[4] <= 5 else ""
                self.tabla_prod.insert("", "end",
                    values=(r[0],r[1],r[2],f"${r[3]:.2f}",r[4],r[5]),
                    iid=str(r[0]), tags=(tag,))
        self.tabla_prod.tag_configure("low", foreground=C["yellow"])

    def _llenar_form_producto(self, event=None):
        sel = self.tabla_prod.selection()
        if not sel:
            return
        vals = self.tabla_prod.item(sel[0], "values")
        pid, codigo, nombre, precio, stock, cat = vals
        precio = precio.replace("$","")
        keys = ("e_codigo","e_nombre","e_precio","e_stock","e_categoria")
        datos = (codigo, nombre, precio, stock, cat)
        for k,d in zip(keys, datos):
            self._prod_entries[k].delete(0,"end")
            self._prod_entries[k].insert(0, d)
        self._editing_id = int(pid)

    def _guardar_producto(self):
        try:
            codigo   = self._prod_entries["e_codigo"].get().strip()
            nombre   = self._prod_entries["e_nombre"].get().strip()
            precio   = float(self._prod_entries["e_precio"].get().strip())
            stock    = int(self._prod_entries["e_stock"].get().strip())
            categoria= self._prod_entries["e_categoria"].get().strip() or "General"
        except ValueError:
            messagebox.showerror("Error", "Precio debe ser número. Stock debe ser entero.",
                                 parent=self)
            return
        if not codigo or not nombre:
            messagebox.showerror("Error", "Código y Nombre son obligatorios.", parent=self)
            return

        eid = getattr(self, "_editing_id", None)
        with get_conn() as conn:
            if eid:
                conn.execute(
                    "UPDATE productos SET codigo=?,nombre=?,precio=?,stock=?,categoria=?"
                    " WHERE id=?",
                    (codigo, nombre, precio, stock, categoria, eid))
                msg = "Producto actualizado."
            else:
                try:
                    conn.execute(
                        "INSERT INTO productos (codigo,nombre,precio,stock,categoria)"
                        " VALUES (?,?,?,?,?)",
                        (codigo, nombre, precio, stock, categoria))
                    msg = "Producto agregado."
                except sqlite3.IntegrityError:
                    messagebox.showerror("Error",
                        f'El código "{codigo}" ya existe.', parent=self)
                    return
        messagebox.showinfo("OK", msg, parent=self)
        for e in self._prod_entries.values():
            e.delete(0,"end")
        self._editing_id = None
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
            self._cargar_tabla_productos()
            self._cargar_productos()

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

        # KPIs
        self.kpi_frame = tk.Frame(page, bg=C["bg"])
        self.kpi_frame.pack(fill="x", pady=(0,10))
        self.kpi_ventas = self._kpi_box(self.kpi_frame, "VENTAS HOY", "0", C["accent"])
        self.kpi_total  = self._kpi_box(self.kpi_frame, "TOTAL HOY",  "$0.00", C["green"])

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
            columns=("nombre","cant","precio","sub"),
            show="headings", style="POS.Treeview")
        for c,h,w in zip(("nombre","cant","precio","sub"),
                          ("Producto","Cant","Precio","Subtotal"),
                          (160,40,70,80)):
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
            # KPIs hoy
            kpi = conn.execute(
                "SELECT COUNT(*),IFNULL(SUM(total),0) FROM ventas WHERE fecha LIKE ?",
                (f"{today}%",)).fetchone()
        for r in rows:
            self.tabla_hist.insert("","end",
                values=(r[0],r[1],f"${r[2]:.2f}"), iid=str(r[0]))
        if hasattr(self,"kpi_ventas"):
            self.kpi_ventas.config(text=str(kpi[0]))
            self.kpi_total.config(text=f"${kpi[1]:.2f}")

    def _ver_detalle_venta(self, event=None):
        sel = self.tabla_hist.selection()
        if not sel:
            return
        vid = int(sel[0])
        for row in self.tabla_det.get_children():
            self.tabla_det.delete(row)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT nombre,cantidad,precio,subtotal FROM detalle_venta"
                " WHERE venta_id=?", (vid,)).fetchall()
        for r in rows:
            self.tabla_det.insert("","end",
                values=(r[0],r[1],f"${r[2]:.2f}",f"${r[3]:.2f}"))


# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PuntoDeVenta()
    app.mainloop()
