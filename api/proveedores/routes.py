import base64

from flask import render_template, redirect, url_for, flash, request, jsonify, session
from sqlalchemy import or_
from . import proveedores
from models import Compra, db, Direccion, Estado, Municipio, Proveedor
from forms import ProveedorForm

MODULE = {
    "name": "Proveedores",
    "slug": "proveedores",
    "description": "Gestión de proveedores del sistema",
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


# ==========================
# LISTAR
# ==========================
@proveedores.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()

    query = Proveedor.query.filter_by(estatus="ACTIVO")
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            or_(
                Proveedor.nombre_comercial.ilike(like),
                Proveedor.razon_social.ilike(like),
                Proveedor.correo.ilike(like),
                Proveedor.telefono.ilike(like),
            )
        )

    proveedores_lista = query.all()
    module = MODULE.copy()
    module["items"] = proveedores_lista
    return render_template("proveedores/inicio.html", module=module, buscar=buscar)


# ==========================
# DETALLE
# ==========================
@proveedores.route("/detalle/<int:id>")
def detalle(id):
    proveedor = Proveedor.query.get_or_404(id)
    return render_template("proveedores/detalle.html", proveedor=proveedor, module=MODULE)


# ==========================
# AGREGAR
# ==========================
@proveedores.route("/agregar", methods=["GET", "POST"])
def agregar():
    if Estado.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay estados registrados. No se puede continuar con el alta de proveedores.", "warning")
        return redirect(url_for("proveedores.inicio"))

    form = ProveedorForm()

    form.fk_estado.choices = [(0, "Seleccione un estado")] + [
        (e.id, e.nombre) for e in Estado.query.order_by(Estado.nombre)
    ]

    if request.method == "POST":
        form.fk_municipio.choices = [
            (m.id, m.nombre)
            for m in Municipio.query
            .filter_by(fk_estado=request.form.get("fk_estado", type=int))
            .order_by(Municipio.nombre)
        ]
    else:
        form.fk_municipio.choices = []

    if form.validate_on_submit():

        uid = usuario_sesion_id()

        direccion = Direccion(
            fk_estado=form.fk_estado.data,
            fk_municipio=form.fk_municipio.data,
            calle=form.calle.data,
            colonia=form.colonia.data,
            codigo_postal=form.codigo_postal.data,
            num_exterior=form.num_exterior.data,
            num_interior=form.num_interior.data,
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(direccion)
        db.session.flush()

        proveedor = Proveedor(
            nombre_comercial=form.nombre_comercial.data,
            razon_social=form.razon_social.data,
            telefono=form.telefono.data,
            correo=form.correo.data,
            fk_direccion=direccion.id,
            estatus=form.estatus.data or "ACTIVO",
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(proveedor)
        db.session.commit()

        flash("Proveedor agregado correctamente.", "success")
        return redirect(url_for("proveedores.inicio"))

    return render_template(
        "proveedores/agregar.html", form=form, module=MODULE, action_label="Agregar"
    )


# ==========================
# EDITAR
# ==========================
@proveedores.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    proveedor = Proveedor.query.get_or_404(id)
    direccion = proveedor.direccion
    form = ProveedorForm()

    form.fk_estado.choices = [
        (e.id, e.nombre) for e in Estado.query.order_by(Estado.nombre)
    ]

    if request.method == "POST":
        estado_id = request.form.get("fk_estado", type=int) or direccion.fk_estado
    else:
        estado_id = direccion.fk_estado

    form.fk_municipio.choices = [
        (m.id, m.nombre)
        for m in Municipio.query.filter_by(fk_estado=estado_id).order_by(Municipio.nombre)
    ]

    if request.method == "POST" and not request.form.get("estatus"):
        form.estatus.data = proveedor.estatus

    if request.method == "GET":
        form.nombre_comercial.data = proveedor.nombre_comercial
        form.razon_social.data     = proveedor.razon_social
        form.telefono.data         = proveedor.telefono
        form.correo.data           = proveedor.correo
        form.estatus.data          = proveedor.estatus

        form.calle.data          = direccion.calle
        form.colonia.data        = direccion.colonia
        form.codigo_postal.data  = direccion.codigo_postal
        form.num_exterior.data   = direccion.num_exterior
        form.num_interior.data   = direccion.num_interior
        form.fk_estado.data      = direccion.fk_estado
        form.fk_municipio.data   = direccion.fk_municipio

    if form.validate_on_submit():

        uid = usuario_sesion_id()

        proveedor.nombre_comercial     = form.nombre_comercial.data
        proveedor.razon_social         = form.razon_social.data
        proveedor.telefono             = form.telefono.data
        proveedor.correo               = form.correo.data
        proveedor.estatus              = form.estatus.data
        proveedor.usuario_movimiento   = uid

        direccion.calle              = form.calle.data
        direccion.colonia            = form.colonia.data
        direccion.codigo_postal      = form.codigo_postal.data
        direccion.num_exterior       = form.num_exterior.data
        direccion.num_interior       = form.num_interior.data
        direccion.fk_estado          = form.fk_estado.data
        direccion.fk_municipio       = form.fk_municipio.data
        direccion.usuario_movimiento = uid

        db.session.commit()
        flash("Proveedor actualizado correctamente.", "success")
        return redirect(url_for("proveedores.inicio"))

    return render_template(
        "proveedores/editar.html",
        form=form,
        proveedor=proveedor,
        module=MODULE,
        action_label="Editar",
    )


# ==========================
# ELIMINAR
# ==========================
@proveedores.route("/eliminar/<int:id>")
def eliminar(id):
    proveedor = Proveedor.query.get_or_404(id)

    if Compra.query.filter_by(fk_proveedor=proveedor.id).count() > 0:
        flash("No se puede eliminar el proveedor porque tiene compras relacionadas.", "danger")
        return redirect(url_for("proveedores.inicio"))

    if proveedor.direccion:
        proveedor.direccion.estatus = "INACTIVO"

    proveedor.estatus = "INACTIVO"
    db.session.commit()

    flash("Proveedor eliminado correctamente.", "warning")
    return redirect(url_for("proveedores.inicio"))


# ==========================
# MUNICIPIOS AJAX
# ==========================
@proveedores.route("/municipios/<int:estado_id>")
def municipios_por_estado(estado_id):
    municipios = Municipio.query.filter_by(fk_estado=estado_id).order_by(Municipio.nombre).all()
    return jsonify({"municipios": [{"id": m.id, "nombre": m.nombre} for m in municipios]})
