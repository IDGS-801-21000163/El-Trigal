from flask import flash, redirect, render_template, request, session, url_for

from . import categorias_insumos
from forms import CategoriaInsumoForm, EditCategoriaInsumoForm
from models import CategoriaInsumo, Insumo, db


MODULE = {
    "name": "Categoria de insumos",
    "slug": "categorias-insumos",
    "description": "Administracion de categorias para clasificar la materia prima del sistema.",
}


def usuario_sesion_id():
    return session.get("usuario_id") or 1


@categorias_insumos.route("/")
def inicio():
    busqueda = request.args.get("buscar", "", type=str).strip()
    estatus = request.args.get("estatus", "", type=str).strip().upper()

    query = CategoriaInsumo.query.order_by(CategoriaInsumo.nombre.asc())

    if busqueda:
        query = query.filter(CategoriaInsumo.nombre.ilike(f"%{busqueda}%"))

    if estatus in {"ACTIVO", "INACTIVO"}:
        query = query.filter(CategoriaInsumo.estatus == estatus)

    categorias = query.all()
    resumen = {
        "total": CategoriaInsumo.query.count(),
        "activas": CategoriaInsumo.query.filter_by(estatus="ACTIVO").count(),
        "inactivas": CategoriaInsumo.query.filter_by(estatus="INACTIVO").count(),
        "con_insumos": db.session.query(CategoriaInsumo.id)
        .join(Insumo, Insumo.fk_categoria == CategoriaInsumo.id)
        .distinct()
        .count(),
    }

    return render_template(
        "categorias-insumos/inicio.html",
        module=MODULE,
        current_action="inicio",
        categorias=categorias,
        resumen=resumen,
        buscar=busqueda,
        estatus=estatus,
    )


@categorias_insumos.route("/detalle/<int:id>")
def detalle(id):
    categoria = CategoriaInsumo.query.get_or_404(id)
    insumos = (
        Insumo.query.filter_by(fk_categoria=categoria.id)
        .order_by(Insumo.nombre.asc())
        .all()
    )
    return render_template(
        "categorias-insumos/detalle.html",
        module=MODULE,
        current_action="detalle",
        categoria=categoria,
        insumos=insumos,
    )


@categorias_insumos.route("/agregar", methods=["GET", "POST"])
def agregar():
    form = CategoriaInsumoForm()

    if form.validate_on_submit():
        uid = usuario_sesion_id()
        categoria = CategoriaInsumo(
            nombre=form.nombre.data.strip(),
            descripcion=form.descripcion.data.strip(),
            estatus=form.estatus.data,
            usuario_creacion=uid,
            usuario_movimiento=uid,
        )
        db.session.add(categoria)
        db.session.commit()
        flash("Categoria de insumo creada correctamente.", "success")
        return redirect(url_for("categorias_insumos.inicio"))

    return render_template(
        "categorias-insumos/agregar.html",
        module=MODULE,
        current_action="agregar",
        form=form,
        action_label="Agregar",
    )


@categorias_insumos.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    categoria = CategoriaInsumo.query.get_or_404(id)
    form = EditCategoriaInsumoForm(obj=categoria)
    form.categoria_id = id

    if form.validate_on_submit():
        categoria.nombre = form.nombre.data.strip()
        categoria.descripcion = form.descripcion.data.strip()
        categoria.estatus = form.estatus.data
        categoria.usuario_movimiento = usuario_sesion_id()
        db.session.commit()
        flash("Categoria de insumo actualizada correctamente.", "success")
        return redirect(url_for("categorias_insumos.inicio"))

    return render_template(
        "categorias-insumos/editar.html",
        module=MODULE,
        current_action="editar",
        form=form,
        categoria=categoria,
        action_label="Editar",
    )


@categorias_insumos.route("/eliminar/<int:id>")
def eliminar(id):
    categoria = CategoriaInsumo.query.get_or_404(id)

    if Insumo.query.filter_by(fk_categoria=categoria.id).count() > 0:
        flash("No se puede eliminar la categoría porque tiene insumos asociados.", "danger")
        return redirect(url_for("categorias_insumos.inicio"))

    categoria.estatus = "INACTIVO" if categoria.estatus == "ACTIVO" else "ACTIVO"
    categoria.usuario_movimiento = usuario_sesion_id()
    db.session.commit()
    flash(f"Categoria marcada como {categoria.estatus}.", "warning")
    return redirect(url_for("categorias_insumos.inicio"))
