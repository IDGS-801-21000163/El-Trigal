from flask import render_template, redirect, url_for, flash, request, session
from sqlalchemy import or_
from . import puestos
from models import db, Empleado, Puesto
from forms import PuestoForm

MODULE = {
    "name": "Puestos",
    "slug": "puestos",
    "description": "Gestión de puestos del sistema"
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


# ==========================
# LISTAR
# ==========================
@puestos.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()

    query = Puesto.query.filter_by(estatus="ACTIVO")
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            or_(
                Puesto.nombre.ilike(like),
                Puesto.descripcion.ilike(like),
            )
        )

    puestos_lista = query.all()
    module = MODULE.copy()
    module["items"] = puestos_lista
    return render_template("puestos/inicio.html", module=module, buscar=buscar)


# ==========================
# AGREGAR
# ==========================
@puestos.route("/agregar", methods=["GET", "POST"])
def agregar():
    form = PuestoForm()

    if form.validate_on_submit():
        uid = usuario_sesion_id()
        puesto = Puesto(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            sueldo=form.sueldo.data,
            estatus=form.estatus.data,
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(puesto)
        db.session.commit()
        flash("Puesto creado correctamente.", "success")
        return redirect(url_for("puestos.inicio"))

    return render_template("puestos/agregar.html", form=form, module=MODULE, action_label="Agregar")


# ==========================
# EDITAR
# ==========================
@puestos.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    puesto = Puesto.query.get_or_404(id)
    form = PuestoForm(obj=puesto)

    if form.validate_on_submit():
        puesto.nombre              = form.nombre.data
        puesto.descripcion         = form.descripcion.data
        puesto.sueldo              = form.sueldo.data
        puesto.estatus             = form.estatus.data
        puesto.usuario_movimiento  = usuario_sesion_id()
        db.session.commit()
        flash("Puesto actualizado correctamente.", "success")
        return redirect(url_for("puestos.inicio"))

    return render_template("puestos/editar.html", form=form, module=MODULE, action_label="Editar")


# ==========================
# ELIMINAR (toggle estatus)
# ==========================
@puestos.route("/eliminar/<int:id>")
def eliminar(id):
    puesto = Puesto.query.get_or_404(id)

    if Empleado.query.filter_by(fk_puesto=puesto.id).count() > 0:
        flash("No se puede eliminar el puesto porque hay empleados asignados a este puesto.", "danger")
        return redirect(url_for("puestos.inicio"))

    puesto.estatus = "INACTIVO" if puesto.estatus == "ACTIVO" else "ACTIVO"
    puesto.usuario_movimiento = usuario_sesion_id()
    db.session.commit()
    flash(f"Puesto marcado como {puesto.estatus}.", "warning")
    return redirect(url_for("puestos.inicio"))
