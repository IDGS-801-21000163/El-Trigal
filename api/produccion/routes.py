from flask import render_template, request, redirect, url_for, flash
from api.common import create_module_blueprint
from models import db, Produccion, ProduccionDetalle, Producto, Receta, RecetaDetalle, InventarioProducto, SolicitudProduccion
from sqlalchemy import func
from datetime import datetime

produccion = create_module_blueprint("produccion")

def get_user_id():
    return 1

def get_empleado_id():
    return 1

def get_sucursal_id():
    return 1

@produccion.route("/iniciar/<int:id>")
def iniciar(id):
    prod = Produccion.query.get_or_404(id)

    if prod.estado != "PENDIENTE":
        flash("Solo se puede iniciar si está pendiente", "error")
        return redirect(url_for("produccion.inicio"))

    prod.estado = "EN PROCESO"

    detalle = ProduccionDetalle.query.filter_by(fk_produccion=id).first()

    if detalle and detalle.fk_solicitud:
        solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
        if solicitud:
            solicitud.estado = "EN_PRODUCCION"   # ← estado correcto del ENUM

    db.session.commit()

    flash("Producción iniciada", "success")
    return redirect(url_for("produccion.inicio"))

@produccion.route("/")
def inicio():

    estado = request.args.get("estado", "")
    buscar = request.args.get("buscar", "")

    data = []

    # 🔵 1. PRODUCCIÓN INTERNA (M15)
    producciones = Produccion.query.order_by(Produccion.id.desc()).all()

    for p in producciones:

        detalle = ProduccionDetalle.query.filter_by(
            fk_produccion=p.id
        ).first()

        if not detalle:
            continue

        producto = Producto.query.get(detalle.fk_producto)

        data.append({
            "id": p.id,
            "producto": producto.nombre,
            "cantidad": detalle.cantidad_solicitada,
            "estado": p.estado,
            "tipo": "PRODUCCION"  # 🔥 CLAVE
        })

    # 🟡 2. SOLICITUDES (M16)
    solicitudes = SolicitudProduccion.query.order_by(
        SolicitudProduccion.id.desc()
    ).all()

    for s in solicitudes:

        producto = Producto.query.get(s.fk_producto)

        data.append({
            "id": s.id,
            "producto": producto.nombre,
            "cantidad": s.cantidad_solicitada,
            "estado": s.estado,
            "tipo": "SOLICITUD"  # 🔥 CLAVE
        })

    return render_template(
        "produccion/inicio.html",
        ordenes=data,
        estado=estado,
        buscar=buscar
    )
    
@produccion.route("/crear/<int:solicitud_id>")
def crear(solicitud_id):

    solicitud = SolicitudProduccion.query.get_or_404(solicitud_id)

    if solicitud.estado != "PENDIENTE":
        flash("La solicitud ya fue procesada", "error")
        return redirect(url_for("produccion.inicio"))

    nueva_produccion = Produccion(
        fk_empleado=get_empleado_id(),
        fk_sucursal=get_sucursal_id(),
        estado="PENDIENTE",          # ← PENDIENTE, no EN PROCESO
        usuario_creacion=get_user_id(),
        usuario_movimiento=get_user_id()
    )

    db.session.add(nueva_produccion)
    db.session.flush()

    detalle = ProduccionDetalle(
        fk_produccion=nueva_produccion.id,
        fk_producto=solicitud.fk_producto,
        cantidad_solicitada=solicitud.cantidad_solicitada,
        cantidad_producto=0,
        origen="SOLICITUD_VENTAS",
        usuario_creacion=get_user_id(),
        usuario_movimiento=get_user_id(),
        fk_solicitud=solicitud.id
    )

    db.session.add(detalle)

    # Sincronizar M16: marcar como aprobada (no EN_PRODUCCION aún)
    solicitud.estado = "APROBADA"

    db.session.commit()

    flash("Producción creada correctamente. Inicia desde la lista.", "success")
    return redirect(url_for("produccion.inicio"))


@produccion.route("/terminar/<int:id>", methods=["GET", "POST"])
def terminar(id):

    prod = Produccion.query.get_or_404(id)
    detalle = ProduccionDetalle.query.filter_by(fk_produccion=id).first()

    if request.method == "POST":

        piezas = int(request.form.get("piezas"))

        detalle.cantidad_producto = piezas
        prod.estado = "TERMINADO"

        inventario = InventarioProducto.query.filter_by(
            fk_producto=detalle.fk_producto,
            fk_sucursal=get_sucursal_id(),
            estatus="ACTIVO"
        ).first()

        if inventario:
            inventario.cantidad_producto += piezas
        else:
            nuevo = InventarioProducto(
                fk_producto=detalle.fk_producto,
                fk_sucursal=get_sucursal_id(),
                cantidad_producto=piezas,
                estado="EXISTENCIA",
                estatus="ACTIVO",
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id()
            )
            db.session.add(nuevo)

        # ✅ Sincronizar M16 ANTES del commit
        if detalle.fk_solicitud:
            solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
            if solicitud:
                solicitud.estado = "TERMINADA"

        db.session.commit()  # ← UN SOLO commit al final

        flash("Producción terminada", "success")
        return redirect(url_for("produccion.inicio"))

    return render_template("produccion/editar.html", produccion=prod)

@produccion.route("/agregar", methods=["GET", "POST"])
def agregar():

    if request.method == "POST":
        producto_id = request.form.get("producto_id")
        cantidad = int(request.form.get("cantidad"))

        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0", "error")
            return redirect(url_for("produccion.agregar"))

        if not producto_id or not cantidad:
            flash("Datos incompletos", "error")
            return redirect(url_for("produccion.agregar"))

        produccion = Produccion(
            fk_empleado=get_empleado_id(),
            fk_sucursal=get_sucursal_id(),
            estado="PENDIENTE",
            fecha_creacion=datetime.utcnow(),  # 🔥 AQUI
            usuario_creacion=get_user_id(),
            usuario_movimiento=get_user_id()
        )

        db.session.add(produccion)
        db.session.flush()

        detalle = ProduccionDetalle(
            fk_produccion=produccion.id,
            fk_producto=producto_id,
            cantidad_solicitada=cantidad,
            cantidad_producto=0,
            origen="INTERNO",
            usuario_creacion=get_user_id(),       # 🔥
            usuario_movimiento=get_user_id()      # 🔥
        )

        db.session.add(detalle)
        db.session.commit()

        flash("Producción creada", "success")
        return redirect(url_for("produccion.inicio"))

    productos = Producto.query.filter_by(estatus="ACTIVO").all()

    return render_template("produccion/agregar.html", productos=productos)


@produccion.route("/merma/<int:id>", methods=["GET", "POST"])
def merma(id):

    produccion = Produccion.query.get_or_404(id)

    if request.method == "POST":
        cantidad = request.form.get("cantidad")
        observacion = request.form.get("observacion")

        # aquí puedes guardar en tabla merma (si la haces)
        flash("Merma registrada", "success")

        return redirect(url_for("produccion.inicio"))

    return render_template("produccion/eliminar.html", produccion=produccion)


@produccion.route("/cancelar/<int:id>")
def cancelar(id):
    prod = Produccion.query.get_or_404(id)
    prod.estado = "CANCELADO"

    detalle = ProduccionDetalle.query.filter_by(fk_produccion=id).first()

    if detalle and detalle.fk_solicitud:
        solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
        if solicitud:
            solicitud.estado = "RECHAZADA"   # ← RECHAZADA según tu ENUM

    db.session.commit()

    flash("Producción cancelada", "warning")
    return redirect(url_for("produccion.inicio"))