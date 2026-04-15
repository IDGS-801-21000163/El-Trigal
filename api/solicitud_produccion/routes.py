from utils.modules import create_module_blueprint
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import func
from models import db, Producto, InventarioProducto, Receta, SolicitudProduccion, CategoriaProducto
import base64
from utils.session import get_current_employee_id, get_current_user_id

solicitud_produccion = create_module_blueprint("solicitud-produccion")
CHAROLA_TAMANO = 10


def get_user_id():
    return get_current_user_id()

def get_empleado_id():
    return get_current_employee_id()


def obtener_imagen_base64(foto):
    if not foto:
        return url_for('static', filename='img/defecto.jpg')
    if isinstance(foto, (bytes, bytearray)):
        imagen = base64.b64encode(foto).decode("utf-8")
        return f"data:image/jpeg;base64,{imagen}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/jpeg;base64,{foto}"
    return url_for('static', filename='img/defecto.jpg')


@solicitud_produccion.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str)
    categoria_id = request.args.get("categoria", 0, type=int)

    query = Producto.query.filter_by(estatus="ACTIVO")

    # Filtrar por nombre de producto
    if buscar:
        query = query.filter(Producto.nombre.ilike(f"%{buscar}%"))

    # Filtrar por categoría
    if categoria_id > 0:
        query = query.filter_by(fk_categoria=categoria_id)

    productos_db = query.all()

    productos = []

    for producto in productos_db:

        # Solo mostrar productos con receta activa
        receta = Receta.query.filter_by(
            fk_producto=producto.id,
            estatus="ACTIVO"
        ).first()

        if not receta:
            continue

        # Calcular stock total en inventario
        stock = db.session.query(
            func.coalesce(func.sum(InventarioProducto.cantidad_producto), 0)
        ).filter(
            InventarioProducto.fk_producto == producto.id,
            InventarioProducto.estatus == "ACTIVO"
        ).scalar()

        productos.append({
            "id": producto.id,
            "nombre": producto.nombre,
            "precio": float(producto.precio),
            "categoria": producto.categoria.nombre,
            "categoria_id": producto.fk_categoria,
            "stock": float(stock),
            "imagen": obtener_imagen_base64(producto.foto)
        })

    categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").all()

    return render_template(
        "solicitud-produccion/inicio.html",
        productos=productos,
        categorias=categorias,
        buscar=buscar,
        categoria_id=categoria_id
    )


@solicitud_produccion.route("/agregar", methods=["POST"])
def agregar():
    producto_id = request.form.get("producto_id")
    charolas = request.form.get("cantidad")

    # Validaciones básicas
    if not producto_id or not charolas:
        flash("Datos incompletos", "error")
        return redirect(url_for("solicitud_produccion.inicio"))

    producto = Producto.query.get(producto_id)

    if not producto or producto.estatus != "ACTIVO":
        flash("Producto inválido o inactivo", "error")
        return redirect(url_for("solicitud_produccion.inicio"))

    # Validar que el producto tenga receta activa
    receta = Receta.query.filter_by(
        fk_producto=producto.id,
        estatus="ACTIVO"
    ).first()

    if not receta:
        flash("El producto no tiene receta activa", "error")
        return redirect(url_for("solicitud_produccion.inicio"))

    try:
        charolas = int(charolas)
        if charolas <= 0:
            raise ValueError
    except Exception:
        flash("Las charolas deben ser un número mayor a 0.", "error")
        return redirect(url_for("solicitud_produccion.inicio"))

    piezas = charolas * CHAROLA_TAMANO

    # Crear solicitud
    nueva = SolicitudProduccion(
        fk_producto=producto.id,
        fk_empleado=get_empleado_id(),
        cantidad_solicitada=piezas,
        estado="PENDIENTE",
        usuario_creacion=get_user_id(),
        usuario_movimiento=get_user_id()
    )

    db.session.add(nueva)
    db.session.commit()

    flash("Solicitud de producción creada correctamente", "success")
    return redirect(url_for("solicitud_produccion.inicio"))


@solicitud_produccion.route("/detalle")
def detalle():
    estado = request.args.get("estado", "", type=str)
    busqueda = request.args.get("buscar", "", type=str)

    query = SolicitudProduccion.query

    # Filtrar por estado
    if estado:
        query = query.filter(SolicitudProduccion.estado == estado)

    # Filtrar por nombre de producto
    if busqueda:
        query = query.join(Producto).filter(
            Producto.nombre.ilike(f"%{busqueda}%")
        )

    ordenes = query.order_by(SolicitudProduccion.fecha_creacion.desc()).all()

    # Construir lista de datos para el template
    ordenes_data = []
    for o in ordenes:
        piezas = int(o.cantidad_solicitada or 0)
        charolas = piezas // CHAROLA_TAMANO if piezas > 0 else 0
        ordenes_data.append({
            "id": o.id,
            "producto": o.producto.nombre,
            "cantidad": piezas,
            "charolas": charolas,
            "estado": o.estado
        })

    return render_template(
        "solicitud-produccion/detalle.html",
        ordenes=ordenes_data,
        estado=estado,
        buscar=busqueda
    )
