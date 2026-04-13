import base64

from flask import render_template, request, session, url_for
from . import costo_producto
from models import db, Producto, CategoriaProducto

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
