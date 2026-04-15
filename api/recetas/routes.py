from . import recetas
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from models import db, Receta, RecetaDetalle, Producto, UnidadMedida, Insumo
from models import CompraDetalle
import forms
import base64
from decimal import Decimal


def _format_insumo_image(foto):
    if not foto:
        return None
    if isinstance(foto, (bytes, bytearray)):
        return f"data:image/png;base64,{base64.b64encode(foto).decode('utf-8')}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/png;base64,{foto}"
    return None


def cargar_choices(form):
    form.fk_producto.choices = [(p.id, p.nombre) for p in Producto.query.filter_by(estatus="ACTIVO").order_by(Producto.nombre).all()]

    for d in form.detalles:
        d.fk_insumo.choices = [(i.id, i.nombre) for i in Insumo.query.filter_by(estatus="ACTIVO").order_by(Insumo.nombre).all()]
        d.fk_unidad.choices = [(u.id, u.nombre) for u in UnidadMedida.query.filter_by(estatus="ACTIVO").order_by(UnidadMedida.nombre).all()]


def obtener_imagenes(form):
    imagenes_insumos = {}

    for i, d in enumerate(form.detalles):

        insumo_id = d.fk_insumo.data

        if insumo_id:
            insumo = Insumo.query.get(insumo_id)

            if insumo and insumo.foto:
                imagenes_insumos[i] = {
                    "nombre": insumo.nombre,
                    "imagen": _format_insumo_image(insumo.foto)
                }
            else:
                imagenes_insumos[i] = None
        else:
            imagenes_insumos[i] = None

    return imagenes_insumos


def _factor_unidad_base(unidad):
    if not unidad:
        return Decimal("1")
    factor = Decimal(str(unidad.factor_conversion or 1))
    actual = unidad.unidad_base
    while actual:
        factor *= Decimal(str(actual.factor_conversion or 1))
        actual = actual.unidad_base
    return factor


def _recalcular_costo_produccion(producto_id):
    receta = Receta.query.filter_by(fk_producto=producto_id, estatus="ACTIVO").first()
    if not receta:
        return

    total = Decimal("0")
    for det in RecetaDetalle.query.filter_by(fk_receta=receta.id, estatus="ACTIVO").all():
        # Tomar el último costo registrado de compra para ese insumo.
        compra = (
            CompraDetalle.query.filter_by(fk_insumo=det.fk_insumo, estatus="ACTIVO")
            .order_by(CompraDetalle.id.desc())
            .first()
        )
        if not compra or not compra.unidad:
            continue

        factor_compra = _factor_unidad_base(compra.unidad)  # unidad compra -> unidad base
        if factor_compra <= 0:
            continue

        # costo por unidad de compra (según UI: costo unitario)
        costo_compra = Decimal(str(compra.costo or 0))
        costo_base = (costo_compra / factor_compra)  # costo por unidad base (gramo/ml/pieza)

        # En el formulario la receta captura cantidad con una unidad seleccionada,
        # así que convertimos a unidad base para costear.
        unidad_receta = UnidadMedida.query.get(det.fk_unidad) if det.fk_unidad else None
        factor_receta = _factor_unidad_base(unidad_receta)
        if factor_receta <= 0:
            continue

        cantidad = Decimal(str(det.cantidad_insumo or 0))
        cantidad_base = cantidad * factor_receta
        total += cantidad_base * costo_base

    producto = Producto.query.get(producto_id)
    if not producto:
        return
    producto.costo_produccion = total.quantize(Decimal("0.01"))
    db.session.commit()


@recetas.route("/")
@recetas.route("/inicio")
def inicio():
    create_form = forms.RecetaForm(request.form)

    buscar = request.args.get("buscar", "", type=str).strip()
    producto_id = request.args.get("producto", 0, type=int)
    estatus = request.args.get("estatus", "ACTIVO", type=str).strip().upper()

    query = Receta.query
    if estatus in {"ACTIVO", "INACTIVO"}:
        query = query.filter(Receta.estatus == estatus)
    # 🔍 filtro por texto
    if buscar:
        like = f"%{buscar}%"
        query = query.join(Producto).outerjoin(RecetaDetalle).outerjoin(Insumo).filter(
            or_(
                Producto.nombre.ilike(like),
                Insumo.nombre.ilike(like),
            )
        )

    if producto_id:
        query = query.filter(Receta.fk_producto == producto_id)

    recetas = query.all()

    productos = Producto.query.filter_by(estatus="ACTIVO").order_by(Producto.nombre).all()

    return render_template(
        "recetas/inicio.html",
        form=create_form,
        receta=recetas,
        productos=productos,
        buscar=buscar,
        producto_id=producto_id,
        estatus=estatus,
    )


@recetas.route('/detalleR', methods=['GET'])
def detalleReceta():
    id = request.args.get('id')

    receta = db.session.query(Receta).filter(Receta.id == id).first()

    if not receta:
        flash("Receta no encontrada", "error")
        return redirect(url_for('recetas.inicio'))

    producto = receta.producto
    detalles = receta.detalles
    imagenes_detalles = {
        d.id: _format_insumo_image(d.insumo.foto) if d.insumo and d.insumo.foto else None
        for d in detalles
    }

    return render_template(
        'recetas/detalle.html',
        receta=receta,
        producto=producto,
        detalles=detalles,
        imagenes_detalles=imagenes_detalles,
    )


@recetas.route("/agregarR", methods=['GET', 'POST'])
def agregarReceta():
    if Producto.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay productos registrados. No se puede crear una receta sin productos.", "warning")
        return redirect(url_for("productos.inicio"))
    if Insumo.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay insumos registrados. No se puede crear una receta sin insumos.", "warning")
        return redirect(url_for("insumos.inicio"))
    if UnidadMedida.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay unidades de medida registradas. No se puede crear una receta.", "warning")
        return redirect(url_for("recetas.inicio"))

    form = forms.RecetaForm(request.form)
    accion = request.form.get("accion")

    total = 0
    while f"detalles-{total}-fk_insumo" in request.form:
        total += 1

    while len(form.detalles) < total:
        form.detalles.append_entry()

    cargar_choices(form)

    if accion == "agregar":
        form.detalles.append_entry()
        cargar_choices(form)

        imagenes_insumos = obtener_imagenes(form)

        return render_template(
            "recetas/agregar.html",
            form=form,
            duplicados=[],
            imagenes_insumos=imagenes_insumos
        )

    if accion and accion.startswith("quitar_"):

        index = int(accion.split("_")[1])

        nuevos = []

        for i, d in enumerate(form.detalles.entries):
            if i != index:
                nuevos.append(d.data)

        form.detalles.entries = []

        for d in nuevos:
            form.detalles.append_entry(d)

        cargar_choices(form)

        imagenes_insumos = obtener_imagenes(form)

        return render_template(
            "recetas/agregar.html",
            form=form,
            duplicados=[],
            imagenes_insumos=imagenes_insumos
        )

    if request.method == 'POST':

        valid = True
        duplicados = []

        if not form.validate():
            valid = False

        #  validar receta duplicada
        existe = Receta.query.filter_by(fk_producto=form.fk_producto.data).first()
        if existe:
            form.fk_producto.errors.append("Ya existe una receta para este producto")
            valid = False

        #  validar insumos duplicados
        insumos = {}
        for i, d in enumerate(form.detalles.data):

            insumo = d.get('fk_insumo')

            if not insumo:
                continue

            if insumo in insumos:
                duplicados.append(i)
                duplicados.append(insumos[insumo])

                form.detalles[i].form.fk_insumo.errors.append("Insumo duplicado")
                form.detalles[insumos[insumo]].form.fk_insumo.errors.append("Insumo duplicado")

                valid = False
            else:
                insumos[insumo] = i

            insumos_validos = [
                d for d in form.detalles.data if d.get('fk_insumo')
            ]

            if len(insumos_validos) < 3:
                flash("Debe agregar al menos 3 insumos", "error")
                valid = False

        if not valid:
            flash("Corrige los errores del formulario", "error")

            imagenes_insumos = obtener_imagenes(form)

            return render_template(
                "recetas/agregar.html",
                form=form,
                duplicados=duplicados,
                imagenes_insumos=imagenes_insumos
            )

        receta = Receta(
            fk_producto=form.fk_producto.data,
            descripcion=form.descripcion.data,
        )

        db.session.add(receta)
        db.session.commit()

        for d in form.detalles.data:

            if not d['fk_insumo']:
                continue

            detalle = RecetaDetalle(
                fk_receta=receta.id,
                fk_insumo=d['fk_insumo'],
                fk_unidad=d['fk_unidad'],
                cantidad_insumo=d['cantidad_insumo'],
            )

            db.session.add(detalle)

        db.session.commit()

        flash("Receta agregada correctamente", "success")

        # Actualizar costo de producción del producto desde la receta.
        _recalcular_costo_produccion(form.fk_producto.data)
        return render_template(
            "recetas/agregar.html",
            form=form,
            duplicados=[],
            imagenes_insumos=obtener_imagenes(form),
            redirect_url=url_for('recetas.inicio')
        )

    imagenes_insumos = obtener_imagenes(form)

    return render_template(
        "recetas/agregar.html",
        form=form,
        duplicados=[],
        imagenes_insumos=imagenes_insumos
    )


@recetas.route("/editarR", methods=['GET', 'POST'])
def editarReceta():
    id = request.args.get("id")
    receta = Receta.query.filter_by(id=id, estatus="ACTIVO").first_or_404()

    form = forms.RecetaForm(request.form)
    accion = request.form.get("accion")

    total = 0
    while f"detalles-{total}-fk_insumo" in request.form:
        total += 1

    while len(form.detalles) < total:
        form.detalles.append_entry()

    if request.method == "GET":

        form.fk_producto.data = receta.fk_producto
        form.descripcion.data = receta.descripcion

        form.detalles.entries = []

        # Si quedaron duplicados ACTIVO por ediciones previas, colapsarlos para que el form
        # refleje una sola fila por insumo y puedas guardar para limpiar.
        agregados = {}
        duplicados_activos = False
        for d in receta.detalles:
            if getattr(d, "estatus", None) != "ACTIVO":
                continue
            key = d.fk_insumo
            cantidad = float(d.cantidad_insumo or 0)
            if key in agregados:
                duplicados_activos = True
                agregados[key]["cantidad_insumo"] = float(agregados[key]["cantidad_insumo"] or 0) + cantidad
                continue
            agregados[key] = {
                "fk_insumo": d.fk_insumo,
                "fk_unidad": d.fk_unidad,
                "cantidad_insumo": float(d.cantidad_insumo or 0),
            }

        if duplicados_activos:
            flash(
                "Esta receta tenía insumos duplicados (por ediciones anteriores). "
                "Se consolidaron en el formulario; guarda para limpiar la receta.",
                "warning",
            )

        for row in agregados.values():
            form.detalles.append_entry(row)

    cargar_choices(form)

    if accion == "agregar":
        form.detalles.append_entry()
        cargar_choices(form)

        return render_template(
            "recetas/editar.html",
            form=form,
            imagenes_insumos=obtener_imagenes(form)
        )

    if accion and accion.startswith("quitar_"):

        # 🚫 no permitir menos de 3
        if len(form.detalles.entries) <= 3:
            flash("Debe haber mínimo 3 insumos", "error")

            return render_template(
                "recetas/editar.html",
                form=form,
                imagenes_insumos=obtener_imagenes(form)
            )

        index = int(accion.split("_")[1])

        nuevos = []

        for i, d in enumerate(form.detalles.entries):
            if i != index:
                nuevos.append(d.data)

        form.detalles.entries = []

        for d in nuevos:
            form.detalles.append_entry(d)

        cargar_choices(form)

        return render_template(
            "recetas/editar.html",
            form=form,
            imagenes_insumos=obtener_imagenes(form)
        )

    if request.method == "POST":

        valid = True
        duplicados = []

        if not form.validate():
            valid = False

        existe = Receta.query.filter(
            Receta.fk_producto == form.fk_producto.data,
            Receta.id != receta.id
        ).first()

        if existe:
            form.fk_producto.errors.append("Ya existe una receta para este producto")
            valid = False

        insumos = {}
        for i, d in enumerate(form.detalles.data):

            insumo = d.get('fk_insumo')

            if not insumo:
                continue

            if insumo in insumos:
                duplicados.append(i)
                duplicados.append(insumos[insumo])

                form.detalles[i].form.fk_insumo.errors.append("Insumo duplicado")
                form.detalles[insumos[insumo]].form.fk_insumo.errors.append("Insumo duplicado")

                valid = False
            else:
                insumos[insumo] = i

        #  mínimo 3 insumos
        insumos_validos = [
            d for d in form.detalles.data if d.get('fk_insumo')
        ]

        if len(insumos_validos) < 3:
            flash("Debe agregar al menos 3 insumos", "error")
            valid = False

        if not valid:
            flash("Corrige los errores del formulario", "error")

            return render_template(
                "recetas/editar.html",
                form=form,
                duplicados=duplicados,
                imagenes_insumos=obtener_imagenes(form)
            )

        receta.fk_producto = form.fk_producto.data
        receta.descripcion = form.descripcion.data

        for detalle_existente in receta.detalles:
            if getattr(detalle_existente, "estatus", None) == "ACTIVO":
                detalle_existente.estatus = "INACTIVO"

        for d in form.detalles.data:

            if not d['fk_insumo']:
                continue

            nuevo = RecetaDetalle(
                fk_receta=receta.id,
                fk_insumo=d['fk_insumo'],
                fk_unidad=d['fk_unidad'],
                cantidad_insumo=d['cantidad_insumo'],
            )

            db.session.add(nuevo)

        db.session.commit()

        flash("Receta actualizada correctamente", "success")

        # Actualizar costo de producción del producto desde la receta.
        _recalcular_costo_produccion(receta.fk_producto)

        return render_template(
            "recetas/editar.html",
            form=form,
            imagenes_insumos=obtener_imagenes(form),
            redirect_url=url_for('recetas.inicio')
        )

    return render_template(
        "recetas/editar.html",
        form=form,
        duplicados=[],
        imagenes_insumos=obtener_imagenes(form)
    )


@recetas.route("/eliminarR", methods=["POST"])
def eliminarReceta():
    id = request.form.get("id")
    receta = Receta.query.get_or_404(id)

    receta.estatus = 'INACTIVO'  # eliminación lógica
    for detalle in receta.detalles:
        detalle.estatus = "INACTIVO"
    db.session.commit()

    flash("Receta eliminada correctamente", "success")
    return redirect(url_for("recetas.inicio"))


@recetas.route("/activarR", methods=["POST"])
def activarReceta():
    id = request.form.get("id")
    receta = Receta.query.get_or_404(id)

    if receta.estatus == "ACTIVO":
        flash("La receta ya está activa", "warning")
        return redirect(url_for("recetas.inicio"))

    receta.estatus = "ACTIVO"
    # Reactivar detalles (si existen) como ACTIVO.
    for detalle in receta.detalles:
        detalle.estatus = "ACTIVO"
    db.session.commit()

    flash("Receta activada correctamente", "success")
    return redirect(url_for("recetas.inicio", estatus="INACTIVO"))
