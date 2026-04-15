import base64
from decimal import Decimal

from flask import render_template, request, session, url_for
from . import costo_producto
from models import db, Producto, CategoriaProducto, Receta, RecetaDetalle, CompraDetalle, UnidadMedida

MODULE = {
    "name": "Costo por Producto",
    "slug": "costo_producto",
    "description": "Gestión de costo por producto"
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


def _format_image(foto):
    if not foto:
        return url_for("static", filename="img/defecto.jpg")
    if isinstance(foto, (bytes, bytearray)):
        encoded = base64.b64encode(foto).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/png;base64,{foto}"
    return url_for("static", filename="img/defecto.jpg")


def _factor_unidad_base(unidad: UnidadMedida | None) -> Decimal:
    if not unidad:
        return Decimal("1")
    factor = Decimal(str(unidad.factor_conversion or 1))
    actual = unidad.unidad_base
    while actual:
        factor *= Decimal(str(actual.factor_conversion or 1))
        actual = actual.unidad_base
    return factor


def _calcular_costo_desde_receta(producto_id: int) -> Decimal | None:
    receta = Receta.query.filter_by(fk_producto=producto_id, estatus="ACTIVO").first()
    if not receta:
        return None

    total = Decimal("0")
    detalles = RecetaDetalle.query.filter_by(fk_receta=receta.id, estatus="ACTIVO").all()
    if not detalles:
        return Decimal("0")

    for det in detalles:
        compra = (
            CompraDetalle.query.filter_by(fk_insumo=det.fk_insumo, estatus="ACTIVO")
            .order_by(CompraDetalle.id.desc())
            .first()
        )
        if not compra or not compra.unidad:
            # Sin compra para costear este insumo.
            continue

        factor_compra = _factor_unidad_base(compra.unidad)
        if factor_compra <= 0:
            continue

        costo_compra = Decimal(str(compra.costo or 0))  # costo unitario en unidad de compra
        costo_base = costo_compra / factor_compra       # costo por unidad base

        unidad_receta = UnidadMedida.query.get(det.fk_unidad) if det.fk_unidad else None
        factor_receta = _factor_unidad_base(unidad_receta)
        if factor_receta <= 0:
            continue

        cantidad = Decimal(str(det.cantidad_insumo or 0))
        cantidad_base = cantidad * factor_receta
        total += cantidad_base * costo_base

    return total.quantize(Decimal("0.01"))


# ==========================
# LISTAR
# ==========================
@costo_producto.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()
    categoria_id = request.args.get("categoria", 0, type=int)

    query = Producto.query.filter_by(estatus="ACTIVO")
    if categoria_id:
        query = query.filter_by(fk_categoria=categoria_id)
    if buscar:
        query = query.filter(Producto.nombre.ilike(f"%{buscar}%"))

    productos = query.all()
    categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").all()

    productos_data = []
    for item in productos:
        # Si el costo está en 0, intenta recalcularlo desde receta + últimas compras.
        if float(item.costo_produccion or 0) <= 0:
            costo_calc = _calcular_costo_desde_receta(item.id)
            if costo_calc is not None and costo_calc > 0:
                item.costo_produccion = costo_calc
                item.usuario_movimiento = usuario_sesion_id()
                db.session.add(item)

        precio = float(item.precio or 0)
        costo = float(item.costo_produccion or 0)
        utilidad = round(precio - costo, 2)
        margen = round(((precio - costo) / precio * 100), 1) if precio > 0 else 0

        productos_data.append(
            {
                "id": item.id,
                "nombre": item.nombre,
                "categoria": item.categoria.nombre if item.categoria else "Sin categoría",
                "precio": precio,
                "costo_produccion": costo,
                "utilidad": utilidad,
                "margen": margen,
                "imagen": _format_image(item.foto),
            }
        )

    # Persistir recalculos si los hubo.
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    module = MODULE.copy()
    module["items"] = productos_data

    return render_template(
        "costo-producto/inicio.html",
        module=module,
        productos=productos_data,
        categorias=categorias,
        buscar=buscar,
        categoria_id=categoria_id,
    )


# ==========================
# DETALLE
# ==========================
@costo_producto.route("/detalle/<int:id>")
def detalle(id):
    producto  = Producto.query.get_or_404(id)
    productos = Producto.query.filter_by(estatus="ACTIVO").all()

    return render_template(
        "costo-producto/detalle.html",
        module=MODULE,
        producto=producto,
        productos=productos
    )
