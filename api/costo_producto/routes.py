from flask import render_template, session
from . import costo_producto
from models import db, Producto, CategoriaProducto

MODULE = {
    "name": "Costo por Producto",
    "slug": "costo_producto",
    "description": "Gestión de costo por producto"
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


# ==========================
# LISTAR
# ==========================
@costo_producto.route("/")
def inicio():
    productos  = Producto.query.filter_by(estatus="ACTIVO").all()
    categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").all()

    module = MODULE.copy()
    module["items"] = productos

    return render_template(
        "costo-producto/inicio.html",
        module=module,
        productos=productos,
        categorias=categorias
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