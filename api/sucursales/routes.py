from flask import flash, jsonify, redirect, render_template, request, session, url_for

from . import sucursales
from forms import SucursalForm
from models import (
    Caja,
    Direccion,
    Estado,
    InventarioInsumo,
    InventarioProducto,
    Pedido,
    Produccion,
    Municipio,
    Sucursal,
    Venta,
    db,
)


MODULE = {
    "name": "Sucursales",
    "slug": "sucursales",
    "description": "Gestión de sucursales, contacto y dirección operativa.",
}


def usuario_sesion_id():
    return session.get("usuario_id") or 1


def direccion_completa(direccion):
    if not direccion:
        return "Sin dirección"
    partes = [
        direccion.calle,
        f"#{direccion.num_exterior}" if direccion.num_exterior else None,
        f"Int. {direccion.num_interior}" if direccion.num_interior else None,
        direccion.colonia,
        direccion.codigo_postal,
        direccion.municipio.nombre if direccion.municipio else None,
        direccion.estado.nombre if direccion.estado else None,
    ]
    return ", ".join(parte for parte in partes if parte)


@sucursales.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()
    query = Sucursal.query.order_by(Sucursal.nombre.asc())

    if buscar:
        query = query.filter(Sucursal.nombre.ilike(f"%{buscar}%"))

    sucursales_lista = query.all()
    module = MODULE.copy()
    module["items"] = sucursales_lista
    return render_template("sucursales/inicio.html", module=module, buscar=buscar)


@sucursales.route("/agregar", methods=["GET", "POST"])
def agregar():
    if Estado.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay estados registrados. No se puede continuar con el alta de sucursales.", "warning")
        return redirect(url_for("sucursales.inicio"))

    form = SucursalForm()

    if form.validate_on_submit():
        uid = usuario_sesion_id()
        try:
            direccion = Direccion(
                fk_estado=form.fk_estado.data,
                fk_municipio=form.fk_municipio.data,
                codigo_postal=form.codigo_postal.data.strip(),
                colonia=form.colonia.data.strip(),
                calle=form.calle.data.strip(),
                num_interior=(form.num_interior.data or "").strip() or None,
                num_exterior=form.num_exterior.data.strip(),
                estatus=form.estatus.data,
                usuario_creacion=uid,
                usuario_movimiento=uid,
            )
            db.session.add(direccion)
            db.session.flush()

            sucursal = Sucursal(
                fk_direccion=direccion.id,
                nombre=form.nombre.data.strip(),
                telefono=form.telefono.data.strip(),
                estatus=form.estatus.data,
                usuario_creacion=uid,
                usuario_movimiento=uid,
            )
            db.session.add(sucursal)
            db.session.commit()
            flash("Sucursal creada correctamente.", "success")
            return redirect(url_for("sucursales.inicio"))
        except Exception as exc:
            db.session.rollback()
            flash(f"No se pudo crear la sucursal: {exc}", "danger")

    return render_template("sucursales/agregar.html", form=form, module=MODULE, action_label="Agregar")


@sucursales.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    sucursal = Sucursal.query.get_or_404(id)
    direccion = sucursal.direccion
    form = SucursalForm()
    form.sucursal_id = sucursal.id

    if request.method == "GET":
        form.nombre.data = sucursal.nombre
        form.telefono.data = sucursal.telefono
        form.fk_estado.data = direccion.fk_estado if direccion else None
        form = SucursalForm(formdata=None, obj=None)
        form.sucursal_id = sucursal.id
        form.nombre.data = sucursal.nombre
        form.telefono.data = sucursal.telefono
        form.fk_estado.data = direccion.fk_estado if direccion else (form.fk_estado.choices[0][0] if form.fk_estado.choices else None)
        estado_id = form.fk_estado.data
        municipios = Municipio.query.filter_by(fk_estado=estado_id, estatus="ACTIVO").order_by(Municipio.nombre.asc()).all() if estado_id else []
        form.fk_municipio.choices = [(municipio.id, municipio.nombre) for municipio in municipios]
        form.fk_municipio.data = direccion.fk_municipio if direccion else None
        form.calle.data = direccion.calle if direccion else ""
        form.colonia.data = direccion.colonia if direccion else ""
        form.codigo_postal.data = direccion.codigo_postal if direccion else ""
        form.num_exterior.data = direccion.num_exterior if direccion else ""
        form.num_interior.data = direccion.num_interior if direccion else ""
        form.estatus.data = sucursal.estatus

    if form.validate_on_submit():
        uid = usuario_sesion_id()
        try:
            if direccion:
                direccion.fk_estado = form.fk_estado.data
                direccion.fk_municipio = form.fk_municipio.data
                direccion.codigo_postal = form.codigo_postal.data.strip()
                direccion.colonia = form.colonia.data.strip()
                direccion.calle = form.calle.data.strip()
                direccion.num_exterior = form.num_exterior.data.strip()
                direccion.num_interior = (form.num_interior.data or "").strip() or None
                direccion.estatus = form.estatus.data
                direccion.usuario_movimiento = uid

            sucursal.nombre = form.nombre.data.strip()
            sucursal.telefono = form.telefono.data.strip()
            sucursal.estatus = form.estatus.data
            sucursal.usuario_movimiento = uid
            db.session.commit()
            flash("Sucursal actualizada correctamente.", "success")
            return redirect(url_for("sucursales.inicio"))
        except Exception as exc:
            db.session.rollback()
            flash(f"No se pudo actualizar la sucursal: {exc}", "danger")

    return render_template("sucursales/editar.html", form=form, module=MODULE, action_label="Editar", sucursal=sucursal)


@sucursales.route("/detalle/<int:id>")
def detalle(id):
    sucursal = Sucursal.query.get_or_404(id)
    return render_template(
        "sucursales/detalle.html",
        module=MODULE,
        sucursal=sucursal,
        direccion_texto=direccion_completa(sucursal.direccion),
    )


@sucursales.route("/eliminar/<int:id>")
def eliminar(id):
    sucursal = Sucursal.query.get_or_404(id)
    if (
        InventarioInsumo.query.filter_by(fk_sucursal=sucursal.id).count() > 0
        or InventarioProducto.query.filter_by(fk_sucursal=sucursal.id).count() > 0
        or Pedido.query.filter_by(fk_sucursal=sucursal.id).count() > 0
        or Venta.query.filter_by(fk_sucursal=sucursal.id).count() > 0
        or Produccion.query.filter_by(fk_sucursal=sucursal.id).count() > 0
        or Caja.query.filter_by(fk_sucursal=sucursal.id).count() > 0
    ):
        flash("No se puede eliminar la sucursal porque tiene registros relacionados (inventario, pedidos, ventas, producción o caja).", "danger")
        return redirect(url_for("sucursales.inicio"))

    uid = usuario_sesion_id()
    sucursal.estatus = "INACTIVO" if sucursal.estatus == "ACTIVO" else "ACTIVO"
    sucursal.usuario_movimiento = uid
    if sucursal.direccion:
        sucursal.direccion.estatus = sucursal.estatus
        sucursal.direccion.usuario_movimiento = uid
    db.session.commit()
    flash(f"Sucursal marcada como {sucursal.estatus}.", "warning")
    return redirect(url_for("sucursales.inicio"))


@sucursales.route("/municipios/<int:estado_id>")
def municipios_por_estado(estado_id):
    municipios = (
        Municipio.query.filter_by(fk_estado=estado_id, estatus="ACTIVO")
        .order_by(Municipio.nombre.asc())
        .all()
    )
    return jsonify({"municipios": [{"id": m.id, "nombre": m.nombre} for m in municipios]})
