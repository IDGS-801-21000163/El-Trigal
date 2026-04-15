from flask import Blueprint, render_template

from models import MetodoPago, Modulo, Rol, RolModulo, Usuario, db


DEFAULT_MODULES = [
    {"ruta": "dashboard", "nombre": "Dashboard", "icon": "dashboard", "description": "Panel ejecutivo con indicadores y alertas operativas."},
    {"ruta": "reportes", "nombre": "Reportes", "icon": "reportes", "description": "Descarga de reportes (tops, rangos de fechas, clientes y ventas)."},
    {"ruta": "usuarios", "nombre": "Usuarios", "icon": "usuarios", "description": "Administracion de accesos, roles y credenciales del sistema."},
    {"ruta": "puestos", "nombre": "Puestos", "icon": "puestos", "description": "Catalogo de puestos, actividades y sueldo base del personal."},
    {"ruta": "empleados", "nombre": "Empleados", "icon": "empleados", "description": "Registro del personal, puesto asignado y control operativo."},
    {"ruta": "proveedores", "nombre": "Proveedores", "icon": "proveedores", "description": "Directorio de proveedores con datos comerciales y de contacto."},
    {"ruta": "sucursales", "nombre": "Sucursales", "icon": "sucursales", "description": "Gestion de sucursales con direccion, telefono y datos operativos."},
    {"ruta": "categorias-insumos", "nombre": "Categorias de insumos", "icon": "categoria", "description": "Clasificacion de insumos usados por inventario, compras y recetas."},
    {"ruta": "insumos", "nombre": "Insumos", "icon": "insumos", "description": "Catalogo de insumos con categoria y control de caducidad."},
    {"ruta": "compras", "nombre": "Compras", "icon": "compras", "description": "Registro de compras de insumos por folio, proveedor y fecha."},
    {"ruta": "inventario-insumos", "nombre": "Inventario insumos", "icon": "inventario", "description": "Consulta y ajuste visual del stock de insumos y mermas."},
    {"ruta": "categorias-productos", "nombre": "Categorias de productos", "icon": "categoria", "description": "Clasificacion comercial de los productos finales."},
    {"ruta": "recetas", "nombre": "Recetas", "icon": "recetas", "description": "Definicion de recetas y sus insumos asociados para produccion."},
    {"ruta": "productos", "nombre": "Productos", "icon": "productos", "description": "Catalogo de productos con categoria, receta y precio."},
    {"ruta": "inventario-productos", "nombre": "Inventario productos", "icon": "inventario", "description": "Consulta y ajuste visual del inventario de productos terminados."},
    {"ruta": "produccion", "nombre": "Produccion", "icon": "produccion", "description": "Seguimiento de produccion con estado, empleado y control de merma."},
    {"ruta": "pedidos", "nombre": "Pedidos", "icon": "pedidos", "description": "Pedidos en linea y presenciales con carrito, pago y seguimiento."},
    {"ruta": "pedidos-presencial", "nombre": "Pedidos presencial", "icon": "pedidos", "description": "Registro de pedidos presenciales con anticipo, entrega y solicitud a produccion."},
    {"ruta": "ventas", "nombre": "Ventas", "icon": "ventas", "description": "Operacion de venta, caja, ticket y movimiento de inventario."},
    {"ruta": "pos", "nombre": "Punto de venta", "icon": "pos", "description": "Caja operativa con carrito local, cobro, tickets y corte de caja."},
    {"ruta": "solicitud-produccion", "nombre": "Solicitud de Producción", "icon": "solicitud", "description": "Solicitud desde ventas para producir productos cuando el stock es insuficiente."},
    {"ruta": "clientes", "nombre": "Clientes", "icon": "clientes", "description": "Registro de clientes para pedidos, contacto y seguimiento comercial."},
    {"ruta": "costo-producto", "nombre": "Categoria de Costo de producto", "icon": "costo", "description": "Visualizacion de los costos asociados a cada producto."},
]

MODULE_DETAILS = {item["ruta"]: item for item in DEFAULT_MODULES}

ACTIONS = [
    {"slug": "inicio", "name": "Inicio"},
    {"slug": "agregar", "name": "Agregar"},
    {"slug": "editar", "name": "Editar"},
    {"slug": "detalle", "name": "Detalle"},
    {"slug": "eliminar", "name": "Eliminar"},
]

ROL_ADMIN = "ADMIN"
ROL_EMPLEADO = "EMPLEADO"
ROL_CLIENTE = "CLIENTE"


def get_module_config(module_slug):
    detail = MODULE_DETAILS.get(module_slug, {})
    return {
        "slug": module_slug,
        "name": detail.get("nombre", module_slug.replace("-", " ").title()),
        "description": detail.get("description", "Modulo del sistema."),
    }


def ensure_module_catalog():
    existentes = {item.ruta: item for item in Modulo.query.all()}
    created = False

    for item in DEFAULT_MODULES:
        if item["ruta"] in existentes:
            modulo = existentes[item["ruta"]]
            if modulo.nombre != item["nombre"]:
                modulo.nombre = item["nombre"]
                created = True
            continue

        db.session.add(Modulo(nombre=item["nombre"], ruta=item["ruta"]))
        created = True

    if created:
        db.session.commit()

    primer_usuario = Usuario.query.order_by(Usuario.id.asc()).first()
    if primer_usuario and not MetodoPago.query.filter_by(nombre="Tarjeta guardada").first():
        db.session.add(
            MetodoPago(
                nombre="Tarjeta guardada",
                estatus="ACTIVO",
                usuario_creacion=primer_usuario.id,
                usuario_movimiento=primer_usuario.id,
            )
        )
        db.session.commit()

    ensure_role_module_permissions()


def ensure_role_module_permissions():
    # Soportar nombres legacy en BD (ej: "Administrador", "Cliente") además de los códigos internos.
    all_roles = Rol.query.all()
    roles_by_name = {rol.nombre: rol for rol in all_roles}

    def pick_role(*names):
        for name in names:
            if name in roles_by_name:
                return roles_by_name[name]
        return None

    rol_admin = pick_role(ROL_ADMIN, "Administrador", "ADMINISTRADOR")
    rol_empleado = pick_role(ROL_EMPLEADO, "Empleado", "EMPLEADO")
    rol_cliente = pick_role(ROL_CLIENTE, "Cliente", "CLIENTE")

    modulos = {modulo.ruta: modulo for modulo in Modulo.query.all()}

    if not modulos:
        return

    desired = {
        (rol_admin.id if rol_admin else None): list(modulos.keys()),
        (rol_empleado.id if rol_empleado else None): [ruta for ruta in modulos.keys() if ruta != "usuarios"],
        (rol_cliente.id if rol_cliente else None): ["pedidos"],
    }

    existing_pairs = {
        (permiso.fk_rol, permiso.fk_modulo)
        for permiso in RolModulo.query.all()
    }

    created = False

    for role_id, rutas in desired.items():
        if not role_id:
            continue

        for ruta in rutas:
            modulo = modulos.get(ruta)
            if not modulo:
                continue
            pair = (role_id, modulo.id)
            if pair in existing_pairs:
                continue
            db.session.add(RolModulo(fk_rol=role_id, fk_modulo=modulo.id))
            created = True

    if created:
        db.session.commit()


def get_nav_modules_for_role(role_id):
    if not role_id:
        return []

    rows = (
        db.session.query(Modulo)
        .join(RolModulo, RolModulo.fk_modulo == Modulo.id)
        .filter(RolModulo.fk_rol == role_id)
        .all()
    )
    rows_by_slug = {row.ruta: row for row in rows}
    ordered = []
    for item in DEFAULT_MODULES:
        row = rows_by_slug.get(item["ruta"])
        if row:
            ordered.append({"slug": row.ruta, "name": row.nombre, "icon": item.get("icon", "modulo")})
    return ordered


def role_has_module_access(role_id, module_slug):
    if not role_id or not module_slug:
        return False

    return (
        db.session.query(RolModulo.id)
        .join(Modulo, RolModulo.fk_modulo == Modulo.id)
        .filter(RolModulo.fk_rol == role_id, Modulo.ruta == module_slug)
        .first()
        is not None
    )


def get_first_allowed_module(role_id):
    modules = get_nav_modules_for_role(role_id)
    if not modules:
        return None

    dashboard = next((item for item in modules if item["slug"] == "dashboard"), None)
    return dashboard or modules[0]


def create_module_blueprint(module_slug):
    module = get_module_config(module_slug)
    blueprint = Blueprint(module_slug.replace("-", "_"), __name__, template_folder="../templates")

    if module_slug not in ("productos", "categorias-productos", "inventario-productos", "solicitud-produccion", "produccion", "clientes", "pedidos"):

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
