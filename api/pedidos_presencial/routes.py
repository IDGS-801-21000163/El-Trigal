from __future__ import annotations

import math
from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func

from models import (
    Cliente,
    InventarioProducto,
    MetodoPago,
    Pedido,
    PedidoAnticipo,
    PedidoDetalle,
    Producto,
    SolicitudProduccion,
    db,
)
from utils.session import get_current_employee_id, get_current_user_id, get_default_sucursal_id

from . import pedidos_presencial


MODULE = {
    "name": "Pedidos presencial",
    "slug": "pedidos-presencial",
    "description": "Pedidos presenciales con anticipo, entrega y solicitud a produccion por charolas.",
}


def _fmt_cliente(cliente: Cliente) -> str:
    if not cliente or not cliente.persona:
        return "Cliente"
    persona = cliente.persona
    return " ".join([p for p in [persona.nombre, persona.apellido_uno, persona.apellido_dos] if p])


def _stock_producto(fk_producto: int, fk_sucursal: int) -> float:
    # Stock total de lotes vigentes; no considera merma ni caducados.
    now = datetime.now()
    qty = (
        db.session.query(func.coalesce(func.sum(InventarioProducto.cantidad_producto), 0))
        .filter(
            InventarioProducto.fk_producto == fk_producto,
            InventarioProducto.fk_sucursal == fk_sucursal,
            InventarioProducto.estatus == "ACTIVO",
            InventarioProducto.es_merma == 0,
            InventarioProducto.cantidad_producto > 0,
            InventarioProducto.fecha_caducidad >= now,
        )
        .scalar()
    )
    return float(qty or 0)


@pedidos_presencial.route("/")
def inicio():
    buscar = (request.args.get("buscar") or "").strip()
    estado = (request.args.get("estado") or "0").strip()

    q = (
        Pedido.query.join(Cliente, Cliente.id == Pedido.fk_cliente)
        .join(Cliente.persona)
        .filter(Pedido.tipo_pedido == "PRESENCIAL")
        .order_by(Pedido.id.desc())
    )

    if estado and estado != "0":
        q = q.filter(Pedido.estado == estado)

    if buscar:
        if buscar.isdigit():
            q = q.filter(Pedido.id == int(buscar))
        else:
            like = f"%{buscar}%"
            q = q.filter(
                func.concat(
                    Cliente.persona.nombre,
                    " ",
                    Cliente.persona.apellido_uno,
                    " ",
                    func.coalesce(Cliente.persona.apellido_dos, ""),
                ).ilike(like)
            )

    pedidos_list = q.limit(300).all()

    return render_template(
        "pedidos-presencial/inicio.html",
        module=MODULE,
        current_action="inicio",
        pedidos=pedidos_list,
        buscar=buscar,
        estado=estado,
    )


@pedidos_presencial.route("/agregar", methods=["GET", "POST"])
def agregar():
    productos = Producto.query.filter_by(estatus="ACTIVO").order_by(Producto.nombre.asc()).all()
    clientes = (
        Cliente.query.join(Cliente.persona)
        .filter(Cliente.estatus == "ACTIVO")
        .order_by(Cliente.id.desc())
        .all()
    )
    metodos = MetodoPago.query.filter_by(estatus="ACTIVO").order_by(MetodoPago.id.asc()).all()

    subtotal = 0.0
    anticipo = float(request.form.get("anticipo") or 0)
    saldo = 0.0

    if request.method == "POST":
        errores: list[str] = []
        # cantidades guarda piezas (charolas * 10), pero la UI captura charolas.
        cantidades: dict[int, int] = {}

        fk_cliente = request.form.get("fk_cliente", type=int)
        fecha_entrega = request.form.get("fecha_entrega") or ""
        notas = (request.form.get("notas") or "").strip()
        metodo_pago = request.form.get("metodo_pago", type=int)

        if not fk_cliente:
            errores.append("Selecciona un cliente.")

        if not metodo_pago:
            errores.append("Selecciona un metodo de pago.")

        # Validar y calcular subtotal
        for p in productos:
            raw = (request.form.get(f"cantidad_{p.id}") or "0").strip()

            if raw == "":
                raw = "0"

            if not raw.isdigit():
                errores.append(f"Cantidad de charolas invalida en {p.nombre}.")
                continue

            if raw.startswith("0") and raw != "0":
                errores.append(f"No se permiten ceros a la izquierda en {p.nombre}.")
                continue

            charolas = int(raw)
            piezas = charolas * 10
            cantidades[p.id] = piezas

            if piezas > 0:
                subtotal += piezas * float(p.precio)

        saldo = subtotal - anticipo

        if subtotal <= 0:
            errores.append("Debes seleccionar al menos un producto con cantidad mayor a 0.")

        if not fecha_entrega:
            errores.append("Debes seleccionar una fecha de entrega.")
            fecha_entrega_dt = None
        else:
            try:
                fecha_entrega_dt = datetime.strptime(fecha_entrega, "%Y-%m-%d")
                if fecha_entrega_dt.date() <= date.today():
                    errores.append("La fecha de entrega debe ser mayor a hoy.")
            except ValueError:
                fecha_entrega_dt = None
                errores.append("Formato de fecha invalido.")

        if subtotal > 0:
            minimo = subtotal * 0.2
            if anticipo < minimo:
                errores.append(f"El anticipo debe ser minimo el 20% del total (${minimo:.2f}).")

        if anticipo > subtotal:
            errores.append(f"El anticipo (${anticipo:.2f}) no puede ser mayor al total (${subtotal:.2f}).")

        if errores:
            for e in errores:
                flash(e, "error")

            return render_template(
                "pedidos-presencial/agregar.html",
                module=MODULE,
                current_action="agregar",
                productos=productos,
                clientes=clientes,
                metodos_pago=metodos,
                subtotal=subtotal,
                anticipo=anticipo,
                saldo=saldo,
                valores={
                    "fk_cliente": fk_cliente or 0,
                    "fecha_entrega": fecha_entrega,
                    "notas": notas,
                    "metodo_pago": metodo_pago or 0,
                    "cantidades": cantidades,
                },
            )

        # Crear pedido
        try:
            user_id = get_current_user_id()
            empleado_id = get_current_employee_id()
            sucursal_id = get_default_sucursal_id()

            pedido = Pedido(
                fk_cliente=int(fk_cliente),
                fk_empleado=int(empleado_id),
                fk_sucursal=int(sucursal_id),
                tipo_pedido="PRESENCIAL",
                notas=notas or None,
                fecha_entrega=fecha_entrega_dt,
                estado="EN PRODUCCION",
                usuario_creacion=user_id,
                usuario_movimiento=user_id,
            )

            db.session.add(pedido)
            db.session.flush()  # obtener pedido.id sin commit parcial

            # Detalles + solicitudes a producción (por charolas de 10)
            for p in productos:
                piezas = int(cantidades.get(p.id, 0) or 0)
                if piezas <= 0:
                    continue

                db.session.add(
                    PedidoDetalle(
                        fk_pedido=pedido.id,
                        fk_producto=p.id,
                        cantidad_producto=piezas,
                        precio_unitario=p.precio,
                        subtotal=piezas * float(p.precio),
                        usuario_creacion=user_id,
                        usuario_movimiento=user_id,
                    )
                )

                # Pedidos presenciales no descuentan inventario: siempre generan solicitud de producción.
                db.session.add(
                    SolicitudProduccion(
                        fk_producto=p.id,
                        fk_empleado=empleado_id,
                        cantidad_solicitada=piezas,
                        estado="PENDIENTE",
                        observaciones=f"Pedido presencial #{pedido.id}",
                        usuario_creacion=user_id,
                        usuario_movimiento=user_id,
                    )
                )
                flash(f"{p.nombre}: se envió a producción ({piezas} pzas).", "warning")

            if anticipo > 0:
                db.session.add(
                    PedidoAnticipo(
                        fk_pedido=pedido.id,
                        fk_metodopago=int(metodo_pago),
                        monto=anticipo,
                        usuario_creacion=user_id,
                        usuario_movimiento=user_id,
                    )
                )

            db.session.commit()
            flash("Pedido presencial creado correctamente.", "success")
            return redirect(url_for("pedidos_presencial.inicio"))

        except Exception:
            db.session.rollback()
            flash("Ocurrio un error al guardar el pedido.", "error")

    return render_template(
        "pedidos-presencial/agregar.html",
        module=MODULE,
        current_action="agregar",
        productos=productos,
        clientes=clientes,
        metodos_pago=metodos,
        subtotal=subtotal,
        anticipo=anticipo,
        saldo=saldo,
        valores={
            "fk_cliente": request.form.get("fk_cliente", type=int) or 0,
            "fecha_entrega": request.form.get("fecha_entrega") or "",
            "notas": request.form.get("notas") or "",
            "metodo_pago": request.form.get("metodo_pago", type=int) or 0,
            "cantidades": {},
        },
    )


@pedidos_presencial.route("/detalle/<int:pedido_id>")
def detalle(pedido_id: int):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo_pedido != "PRESENCIAL":
        return redirect(url_for("pedidos_presencial.inicio"))

    total = float(sum([float(d.subtotal or 0) for d in (pedido.detalles or [])]) or 0)
    anticipo = float(sum([float(a.monto or 0) for a in (pedido.anticipos or [])]) or 0)
    saldo = total - anticipo

    return render_template(
        "pedidos-presencial/detalle.html",
        module=MODULE,
        current_action="detalle",
        pedido=pedido,
        total=total,
        anticipo=anticipo,
        saldo=saldo,
    )


@pedidos_presencial.route("/cambiar-estado/<int:pedido_id>", methods=["POST"])
def cambiar_estado(pedido_id: int):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo_pedido != "PRESENCIAL":
        return redirect(url_for("pedidos_presencial.inicio"))

    nuevo_estado = (request.form.get("estado") or "").strip()
    estado_actual = pedido.estado

    if estado_actual in ["ENTREGADO", "CANCELADO"]:
        flash(f"El pedido ya está {estado_actual} y no se puede modificar.", "error")
        return redirect(url_for("pedidos_presencial.inicio"))

    flujo = {
        "ESPERANDO": ["EN PRODUCCION", "CANCELADO"],
        "EN PRODUCCION": ["LISTO"],
        "LISTO": [],
    }

    if nuevo_estado == "ENTREGADO":
        flash("El estado ENTREGADO se genera al registrar la venta.", "error")
        return redirect(url_for("pedidos_presencial.detalle", pedido_id=pedido.id))

    if nuevo_estado not in flujo.get(estado_actual, []):
        flash(f"No puedes pasar de {estado_actual} a {nuevo_estado}.", "error")
        return redirect(url_for("pedidos_presencial.detalle", pedido_id=pedido.id))

    pedido.estado = nuevo_estado
    pedido.usuario_movimiento = get_current_user_id()
    db.session.commit()

    flash(f"Pedido actualizado a {nuevo_estado}.", "success")
    return redirect(url_for("pedidos_presencial.detalle", pedido_id=pedido.id))
