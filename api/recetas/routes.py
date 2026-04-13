from . import recetas
from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from models import db, Receta, RecetaDetalle, Producto, UnidadMedida, Insumo
import forms


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
                    "imagen": insumo.foto
                }
            else:
                imagenes_insumos[i] = None
        else:
            imagenes_insumos[i] = None

    return imagenes_insumos


@recetas.route("/")
@recetas.route("/inicio")
def inicio():
    create_form = forms.RecetaForm(request.form)

    buscar = request.args.get("buscar", "", type=str).strip()
    producto_id = request.args.get("producto", 0, type=int)

    query = Receta.query.filter(Receta.estatus == 'ACTIVO')
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
    )


@recetas.route('/detalleR', methods=['GET'])
def detalleReceta():
    id = request.args.get('id')

    receta = db.session.query(Receta).filter(Receta.id == id, Receta.estatus == "ACTIVO").first()

    if not receta:
        flash("Receta no encontrada", "error")
        return redirect(url_for('recetas.inicio'))

    producto = receta.producto
    detalles = receta.detalles

    return render_template(
        'recetas/detalle.html',
        receta=receta,
        producto=producto,
        detalles=detalles
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
