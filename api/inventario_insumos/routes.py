from flask import render_template, redirect, url_for, flash, request, session
from . import inventario_insumos
from models import db, InventarioInsumo, InventarioInsumoMovimiento, Insumo, Sucursal
from forms import InventarioInsumoForm
from datetime import datetime

MODULE = {
    "name": "Inventario de Insumos",
    "slug": "inventario_insumos",
    "description": "Gestión de inventario de insumos"
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


# ==========================
# LISTAR
# ==========================
@inventario_insumos.route("/")
def inicio():
    inventario = InventarioInsumo.query.all()
    module = MODULE.copy()
    module["items"] = inventario
    return render_template("inventario-insumos/inicio.html", module=module)


# ==========================
# EDITAR CANTIDAD
# ==========================
@inventario_insumos.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    inventario = InventarioInsumo.query.get_or_404(id)
    form = InventarioInsumoForm()

    if request.method == "GET":
        form.cantidad.data = int(inventario.cantidad)

    if form.validate_on_submit():
        uid = usuario_sesion_id()

        cantidad_anterior = inventario.cantidad
        cantidad_nueva    = form.cantidad.data
        diferencia        = cantidad_nueva - cantidad_anterior

        # MOVIMIENTO
        movimiento = InventarioInsumoMovimiento(
            fk_inventario_insumo=inventario.id,
            tipo_movimiento=form.tipo_movimiento.data,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=cantidad_nueva,
            diferencia=diferencia,
            motivo=form.motivo.data,
            usuario_movimiento=uid
        )
        db.session.add(movimiento)

        # ACTUALIZAR INVENTARIO
        inventario.cantidad          = cantidad_nueva
        inventario.usuario_movimiento = uid

        # ACTUALIZAR ESTADO
        if cantidad_nueva <= 0:
            inventario.estatus = "NO DISPONIBLE"
        elif inventario.fecha_caducidad and inventario.fecha_caducidad < datetime.datetime.now():
            inventario.estatus = "CADUCADO"
        else:
            inventario.estatus = "DISPONIBLE"

        db.session.commit()

        flash("Inventario actualizado correctamente.", "success")
        return redirect(url_for("inventario_insumos.inicio"))

    return render_template(
        "inventario-insumos/editar.html",
        form=form,
        inventario=inventario,
        module=MODULE,
        action_label="Editar"
    )