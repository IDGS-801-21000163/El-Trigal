from flask import Blueprint, render_template


MODULES = [
    {
        "slug": "usuarios",
        "name": "Usuarios",
        "description": "Administracion de accesos, roles y credenciales del sistema.",
        "search_placeholder": "Buscar usuario...",
        "filter_label": "Todos los roles",
        "fields": ["ID", "Usuario", "Contrasena", "Rol"],
        "columns": ["ID", "Usuario", "Rol", "Estatus"],
        "items": [
            {"title": "admin01", "subtitle": "Administrador", "meta": "Activo"},
            {"title": "empleado07", "subtitle": "Empleado", "meta": "Pendiente"},
        ],
    },
    {
        "slug": "puestos",
        "name": "Puestos",
        "description": "Catalogo de puestos, actividades y sueldo base del personal.",
        "search_placeholder": "Buscar puesto...",
        "filter_label": "Todos los puestos",
        "fields": ["Nombre", "Descripcion", "Sueldo", "Estatus"],
        "columns": ["ID", "Puesto", "Sueldo", "Estatus"],
        "items": [
            {"title": "Panadero", "subtitle": "Produccion", "meta": "$12,500"},
            {"title": "Cajero", "subtitle": "Ventas", "meta": "$9,800"},
        ],
    },
    {
        "slug": "empleados",
        "name": "Empleados",
        "description": "Registro del personal, puesto asignado, RFC y sucursal de trabajo.",
        "search_placeholder": "Buscar empleado...",
        "filter_label": "Todas las sucursales",
        "fields": ["No. Empleado", "Nombre", "Puesto", "Sucursal"],
        "columns": ["No. Empleado", "Nombre", "Puesto", "Estatus"],
        "items": [
            {"title": "EMP-001", "subtitle": "Maria Lopez", "meta": "Matriz"},
            {"title": "EMP-002", "subtitle": "Jose Ramirez", "meta": "Norte"},
        ],
    },
    {
        "slug": "proveedores",
        "name": "Proveedores",
        "description": "Directorio de proveedores con datos comerciales y de contacto.",
        "search_placeholder": "Buscar proveedor...",
        "filter_label": "Todos los proveedores",
        "fields": ["Nombre Comercial", "Razon Social", "Telefono", "Direccion"],
        "columns": ["ID", "Proveedor", "Telefono", "Estatus"],
        "items": [
            {"title": "Molinos del Bajio", "subtitle": "Harinas", "meta": "Activo"},
            {"title": "Empaques Lara", "subtitle": "Cajas y bolsas", "meta": "Activo"},
        ],
    },
    {
        "slug": "sucursales",
        "name": "Sucursales",
        "description": "Gestion de sucursales con direccion, telefono y datos operativos.",
        "search_placeholder": "Buscar sucursal...",
        "filter_label": "Todas las zonas",
        "fields": ["Nombre", "Telefono", "Direccion", "Estatus"],
        "columns": ["ID", "Sucursal", "Telefono", "Estatus"],
        "items": [
            {"title": "Matriz", "subtitle": "Centro", "meta": "Abierta"},
            {"title": "Norte", "subtitle": "Blvd. principal", "meta": "Abierta"},
        ],
    },
    {
        "slug": "categorias-insumos",
        "name": "Categorias de insumos",
        "description": "Clasificacion de insumos usados por inventario, compras y recetas.",
        "search_placeholder": "Buscar categoria...",
        "filter_label": "Todas las categorias",
        "fields": ["Nombre", "Descripcion", "Estatus", "Observaciones"],
        "columns": ["ID", "Categoria", "Descripcion", "Estatus"],
        "items": [
            {"title": "Harinas", "subtitle": "Base seca", "meta": "Activa"},
            {"title": "Lacteos", "subtitle": "Caducidad corta", "meta": "Activa"},
        ],
    },
    {
        "slug": "insumos",
        "name": "Insumos",
        "description": "Catalogo de insumos con categoria y control de caducidad.",
        "search_placeholder": "Buscar insumo...",
        "filter_label": "Todas las categorias",
        "fields": ["Nombre", "Categoria", "Fecha de Caducidad", "Estatus"],
        "columns": ["ID", "Insumo", "Categoria", "Estatus"],
        "items": [
            {"title": "Harina premium", "subtitle": "Harinas", "meta": "Cad. 24/04"},
            {"title": "Levadura", "subtitle": "Fermentos", "meta": "Cad. 09/05"},
        ],
    },
    {
        "slug": "compras",
        "name": "Compras",
        "description": "Registro de compras de insumos por folio, proveedor y fecha.",
        "search_placeholder": "Buscar compra...",
        "filter_label": "Todos los estados",
        "fields": ["Folio", "Proveedor", "Total", "Fecha de Compra"],
        "columns": ["Folio", "Proveedor", "Total", "Estado"],
        "items": [
            {"title": "CMP-0192", "subtitle": "Molinos del Bajio", "meta": "$8,420"},
            {"title": "CMP-0193", "subtitle": "Lacteos del Centro", "meta": "$3,115"},
        ],
    },
    {
        "slug": "inventario-insumos",
        "name": "Inventario insumos",
        "description": "Consulta y ajuste visual del stock de insumos y mermas.",
        "search_placeholder": "Buscar insumo...",
        "filter_label": "Todas las categorias",
        "fields": ["Insumo", "Cantidad", "Fecha de Caducidad", "Estatus"],
        "columns": ["Insumo", "Cantidad", "Caducidad", "Estado"],
        "items": [
            {"title": "Harina premium", "subtitle": "Disponible", "meta": "120 kg"},
            {"title": "Mantequilla", "subtitle": "Disponible", "meta": "38 kg"},
        ],
    },
    {
        "slug": "categorias-productos",
        "name": "Categorias de productos",
        "description": "Clasificacion comercial de los productos finales de la panaderia.",
        "search_placeholder": "Buscar categoria...",
        "filter_label": "Todas las categorias",
        "fields": ["Nombre", "Descripcion", "Estatus", "Observaciones"],
        "columns": ["ID", "Categoria", "Descripcion", "Estatus"],
        "items": [
            {"title": "Pan dulce", "subtitle": "Linea diaria", "meta": "Activa"},
            {"title": "Temporada", "subtitle": "Ediciones especiales", "meta": "Activa"},
        ],
    },
    {
        "slug": "recetas",
        "name": "Recetas",
        "description": "Definicion de recetas y sus insumos asociados para produccion.",
        "search_placeholder": "Buscar receta...",
        "filter_label": "Todas las recetas",
        "fields": ["Nombre", "Descripcion", "Insumo Base", "Unidad"],
        "columns": ["ID", "Receta", "Descripcion", "Estatus"],
        "items": [
            {"title": "Concha vainilla", "subtitle": "Pan dulce", "meta": "Activa"},
            {"title": "Pan de muerto", "subtitle": "Temporada", "meta": "Activa"},
        ],
    },
    {
        "slug": "productos",
        "name": "Productos",
        "description": "Catalogo de productos con categoria, receta y fecha de caducidad.",
        "search_placeholder": "Buscar producto...",
        "filter_label": "Todas las categorias",
        "fields": ["Nombre", "Categoria", "Receta", "Fecha de Caducidad"],
        "columns": ["ID", "Producto", "Categoria", "Estatus"],
        "items": [
            {"title": "Concha de vainilla", "subtitle": "Conchas", "meta": "Disponible: 3"},
            {"title": "Pan de muerto", "subtitle": "Conchas", "meta": "Disponible: 5"},
        ],
    },
    {
        "slug": "inventario-productos",
        "name": "Inventario productos",
        "description": "Consulta y ajuste visual del inventario de productos terminados.",
        "search_placeholder": "Buscar producto...",
        "filter_label": "Todas las categorias",
        "fields": ["Producto", "Cantidad", "Fecha de Caducidad", "Estado"],
        "columns": ["Producto", "Cantidad", "Caducidad", "Estado"],
        "items": [
            {"title": "Concha de vainilla", "subtitle": "Conchas", "meta": "Disponible: 3"},
            {"title": "Pan de muerto", "subtitle": "Conchas", "meta": "Disponible: 5"},
        ],
    },
    {
        "slug": "produccion",
        "name": "Produccion",
        "description": "Seguimiento de produccion con estado, empleado y control de merma.",
        "search_placeholder": "Buscar produccion...",
        "filter_label": "Todos los estados",
        "fields": ["Empleado", "Estado", "Cantidad Producida", "Merma"],
        "columns": ["Folio", "Empleado", "Estado", "Fecha"],
        "items": [
            {"title": "PROD-104", "subtitle": "Maria Lopez", "meta": "Pendiente"},
            {"title": "PROD-105", "subtitle": "Juan Perez", "meta": "Terminado"},
        ],
    },
    {
        "slug": "pedidos",
        "name": "Pedidos",
        "description": "Registro de pedidos con cliente, anticipo, fechas y estado.",
        "search_placeholder": "Buscar pedido...",
        "filter_label": "Todos los estados",
        "fields": ["Cliente", "Anticipo", "Fecha de Pedido", "Fecha de Entrega"],
        "columns": ["Folio", "Cliente", "Estado", "Entrega"],
        "items": [
            {"title": "PED-022", "subtitle": "Laura Medina", "meta": "Produccion"},
            {"title": "PED-023", "subtitle": "Carlos Ruiz", "meta": "Pendiente"},
        ],
    },
    {
        "slug": "ventas",
        "name": "Ventas",
        "description": "Operacion de venta, caja, ticket y movimiento de inventario.",
        "search_placeholder": "Buscar venta...",
        "filter_label": "Todas las cajas",
        "fields": ["Caja", "Producto", "Cantidad", "Metodo de Pago"],
        "columns": ["Ticket", "Fecha", "Total", "Estado"],
        "items": [
            {"title": "TCK-8842", "subtitle": "Caja 1", "meta": "$182"},
            {"title": "TCK-8843", "subtitle": "Caja 2", "meta": "$96"},
        ],
    },
    {
    "slug": "solicitud-produccion",
    "name": "Solicitud de Producción",
    "description": "Solicitud desde ventas para producir productos cuando el stock es insuficiente.",
    "search_placeholder": "Buscar solicitud...",
    "filter_label": "Todos los estados",
    "fields": ["Producto", "Cantidad", "Empleado", "Estado"],
    "columns": ["ID", "Producto", "Cantidad", "Estado"],
    "items": [
        {"title": "SOL-001", "subtitle": "Conchas", "meta": "Pendiente"},
        {"title": "SOL-002", "subtitle": "Pan de muerto", "meta": "Aprobada"},
    ],
    },
    {
        "slug": "clientes",
        "name": "Clientes",
        "description": "Registro de clientes para pedidos, contacto y seguimiento comercial.",
        "search_placeholder": "Buscar cliente...",
        "filter_label": "Todos los clientes",
        "fields": ["Nombre", "Telefono", "Correo", "Direccion"],
        "columns": ["ID", "Cliente", "Telefono", "Estatus"],
        "items": [
            {"title": "Laura Medina", "subtitle": "Cliente frecuente", "meta": "Activa"},
            {"title": "Carlos Ruiz", "subtitle": "Mayoreo", "meta": "Activo"},
        ],
    },
]

MODULE_MAP = {module["slug"]: module for module in MODULES}

NAV_MODULES = [
    {"slug": module["slug"], "name": module["name"]}
    for module in MODULES
]

ACTIONS = [
    {"slug": "inicio", "name": "Inicio"},
    {"slug": "agregar", "name": "Agregar"},
    {"slug": "editar", "name": "Editar"},
    {"slug": "detalle", "name": "Detalle"},
    {"slug": "eliminar", "name": "Eliminar"},
]


def create_module_blueprint(module_slug):
    module = MODULE_MAP[module_slug]
    blueprint = Blueprint(module_slug.replace("-", "_"), __name__, template_folder="../templates")

   
    if module_slug not in ("productos", "categorias-productos", "inventario-productos", "solicitud-produccion","produccion", "clientes"):

        @blueprint.route("/")
        def inicio():
            return render_template(
                f"{module_slug}/inicio.html",
                module=module,
                current_action="inicio",
            )

        @blueprint.route("/agregar")
        def agregar():
            return render_template(
                f"{module_slug}/agregar.html",
                module=module,
                current_action="agregar",
            )

        @blueprint.route("/editar")
        def editar():
            return render_template(
                f"{module_slug}/editar.html",
                module=module,
                current_action="editar",
            )

        @blueprint.route("/detalle")
        def detalle():
            return render_template(
                f"{module_slug}/detalle.html",
                module=module,
                current_action="detalle",
            )

        @blueprint.route("/eliminar")
        def eliminar():
            return render_template(
                f"{module_slug}/eliminar.html",
                module=module,
                current_action="eliminar",
            )

    return blueprint
