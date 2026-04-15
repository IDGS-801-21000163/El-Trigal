import base64
from decimal import Decimal

from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from . import insumos
from forms import EditInsumoForm, InsumoForm
from models import (
    CategoriaInsumo,
    CompraDetalle,
    Insumo,
    InventarioInsumo,
    ProduccionInsumo,
    RecetaDetalle,
    db,
)


MODULE = {
    "name": "Gestion de insumos",
    "slug": "insumos",
    "description": "Registro, actualizacion, consulta y control de existencia de insumos.",
}


def usuario_sesion_id():
    return session.get("usuario_id") or 1


def imagen_insumo(insumo):
    if not insumo.foto:
        return None
    if isinstance(insumo.foto, (bytes, bytearray)):
        encoded = base64.b64encode(insumo.foto).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    if isinstance(insumo.foto, str):
        if insumo.foto.startswith("data:image"):
            return insumo.foto
        return f"data:image/png;base64,{insumo.foto}"
    return None


def _read_image_bytes(file_storage):
    if not file_storage:
        return None
    # WTForms/Werkzeug may leave the stream cursor at the end depending on previous access.
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    raw = file_storage.read()
    if not raw:
        return None
    return raw


def resumen_existencia(insumo_id):
    inventarios = InventarioInsumo.query.filter_by(fk_insumo=insumo_id).all()
    total = float(sum((item.cantidad or 0) for item in inventarios))
    proximidad = sorted(
        [item.fecha_caducidad for item in inventarios if item.fecha_caducidad],
        key=lambda fecha: fecha,
    )
    estado = "SIN REGISTRO"
    if inventarios:
        if any(item.estatus == "CADUCADO" for item in inventarios):
            estado = "CADUCADO"
        elif total <= 0:
            estado = "SIN EXISTENCIA"
        elif total <= 10:
            estado = "STOCK BAJO"
        else:
            estado = "DISPONIBLE"

    return {
        "total": total,
        "estado": estado,
        "proxima_caducidad": proximidad[0] if proximidad else None,
        "registros": inventarios,
    }


def _format_cantidad(cantidad, unidad_nombre: str | None):
    try:
        qty = Decimal(str(cantidad or 0))
    except Exception:
        qty = Decimal("0")
    name = (unidad_nombre or "").strip().lower()
    if name == "gramo" and qty >= Decimal("1000"):
        try:
            return float((qty / Decimal("1000")).quantize(Decimal("0.00001"))), "Kilogramo"
        except Exception:
            return float(qty / Decimal("1000")), "Kilogramo"
    if name == "mililitro" and qty >= Decimal("1000"):
        try:
            return float((qty / Decimal("1000")).quantize(Decimal("0.00001"))), "Litro"
        except Exception:
            return float(qty / Decimal("1000")), "Litro"
    if unidad_nombre:
        try:
            return float(qty.quantize(Decimal("0.00001"))), unidad_nombre
        except Exception:
            return float(qty), unidad_nombre
    return float(qty), ""


@insumos.route("/")
def inicio():
    busqueda = request.args.get("buscar", "", type=str).strip()
    categoria_id = request.args.get("categoria", 0, type=int)
    estado_stock = request.args.get("stock", "", type=str).strip().upper()

    query = Insumo.query.order_by(Insumo.nombre.asc())

    if busqueda:
        query = query.filter(Insumo.nombre.ilike(f"%{busqueda}%"))

    if categoria_id > 0:
        query = query.filter(Insumo.fk_categoria == categoria_id)

    insumos_lista = query.all()
    insumos_data = []
    for insumo_item in insumos_lista:
        existencia = resumen_existencia(insumo_item.id)
        if estado_stock and existencia["estado"] != estado_stock:
            continue
        insumos_data.append(
            {
                "insumo": insumo_item,
                "imagen": imagen_insumo(insumo_item),
                "existencia": existencia,
                "recetas": RecetaDetalle.query.filter_by(fk_insumo=insumo_item.id).count(),
                "compras": CompraDetalle.query.filter_by(fk_insumo=insumo_item.id).count(),
            }
        )

    resumen = {
        "total": Insumo.query.count(),
        "activos": Insumo.query.filter_by(estatus="ACTIVO").count(),
        "stock_bajo": sum(1 for item in insumos_data if item["existencia"]["estado"] == "STOCK BAJO"),
        "sin_existencia": sum(1 for item in insumos_data if item["existencia"]["estado"] == "SIN EXISTENCIA"),
    }

    categorias = CategoriaInsumo.query.order_by(CategoriaInsumo.nombre.asc()).all()
    return render_template(
        "insumos/inicio.html",
        module=MODULE,
        current_action="inicio",
        insumos_data=insumos_data,
        categorias=categorias,
        resumen=resumen,
        buscar=busqueda,
        categoria_id=categoria_id,
        estado_stock=estado_stock,
    )


@insumos.route("/detalle/<int:id>")
def detalle(id):
    insumo_item = Insumo.query.get_or_404(id)
    existencia = resumen_existencia(insumo_item.id)
    # Decorar registros para mostrar conversiones amigables.
    for inv in existencia["registros"]:
        unidad_nombre = inv.unidad.nombre if getattr(inv, "unidad", None) else None
        qty, unidad_show = _format_cantidad(inv.cantidad, unidad_nombre)
        inv.cantidad_display = qty
        inv.unidad_display = unidad_show
    metricas = {
        "compras": CompraDetalle.query.filter_by(fk_insumo=id).count(),
        "recetas": RecetaDetalle.query.filter_by(fk_insumo=id).count(),
        "produccion": ProduccionInsumo.query.filter_by(fk_insumo=id).count(),
    }
    return render_template(
        "insumos/detalle.html",
        module=MODULE,
        current_action="detalle",
        insumo=insumo_item,
        imagen=imagen_insumo(insumo_item),
        existencia=existencia,
        metricas=metricas,
    )


@insumos.route("/agregar", methods=["GET", "POST"])
def agregar():
    if CategoriaInsumo.query.count() == 0:
        flash("No hay categorías de insumos registradas. Primero crea una categoría para poder dar de alta un insumo.", "warning")
        return redirect(url_for("categorias_insumos.inicio"))

    form = InsumoForm()
    if form.validate_on_submit():
        if not CategoriaInsumo.query.get(form.fk_categoria.data):
            flash("La categoria seleccionada no existe.", "warning")
            return render_template(
                "insumos/agregar.html",
                module=MODULE,
                current_action="agregar",
                form=form,
                action_label="Agregar",
            )

        uid = usuario_sesion_id()
        foto = _read_image_bytes(form.foto.data)
        nuevo_insumo = Insumo(
            fk_categoria=form.fk_categoria.data,
            nombre=form.nombre.data.strip(),
            foto=foto,
            estatus=form.estatus.data,
            usuario_creacion=uid,
            usuario_movimiento=uid,
        )
        db.session.add(nuevo_insumo)
        db.session.commit()
        flash("Insumo creado correctamente.", "success")
        return redirect(url_for("insumos.inicio"))

    return render_template(
        "insumos/agregar.html",
        module=MODULE,
        current_action="agregar",
        form=form,
        action_label="Agregar",
    )


@insumos.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    insumo_item = Insumo.query.get_or_404(id)
    form = EditInsumoForm(obj=insumo_item)
    form.insumo_id = id

    if request.method == "GET":
        form.fk_categoria.data = insumo_item.fk_categoria

    if form.validate_on_submit():
        insumo_item.fk_categoria = form.fk_categoria.data
        insumo_item.nombre = form.nombre.data.strip()
        insumo_item.estatus = form.estatus.data
        insumo_item.usuario_movimiento = usuario_sesion_id()
        if form.foto.data and getattr(form.foto.data, "filename", ""):
            nueva_foto = _read_image_bytes(form.foto.data)
            if nueva_foto:
                insumo_item.foto = nueva_foto
        db.session.commit()
        flash("Insumo actualizado correctamente.", "success")
        return redirect(url_for("insumos.inicio"))

    return render_template(
        "insumos/editar.html",
        module=MODULE,
        current_action="editar",
        form=form,
        insumo=insumo_item,
        imagen=imagen_insumo(insumo_item),
        action_label="Editar",
    )


@insumos.route("/eliminar/<int:id>")
def eliminar(id):
    insumo_item = Insumo.query.get_or_404(id)

    if (
        CompraDetalle.query.filter_by(fk_insumo=insumo_item.id).count() > 0
        or InventarioInsumo.query.filter_by(fk_insumo=insumo_item.id).count() > 0
        or RecetaDetalle.query.filter_by(fk_insumo=insumo_item.id).count() > 0
        or ProduccionInsumo.query.filter_by(fk_insumo=insumo_item.id).count() > 0
    ):
        flash("No se puede eliminar el insumo porque tiene registros relacionados (compras, inventario, recetas o producción).", "danger")
        return redirect(url_for("insumos.inicio"))

    insumo_item.estatus = "INACTIVO" if insumo_item.estatus == "ACTIVO" else "ACTIVO"
    insumo_item.usuario_movimiento = usuario_sesion_id()
    db.session.commit()
    flash(f"Insumo marcado como {insumo_item.estatus}.", "warning")
    return redirect(url_for("insumos.inicio"))
