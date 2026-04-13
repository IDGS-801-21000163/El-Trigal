from . import pos
from flask import render_template, request, redirect, url_for, flash, session
from models import db, Producto, Venta, VentaDetalle, VentaPago, MetodoPago, Caja, CajaDetalle, Cliente, \
    Persona, InventarioProducto, Pedido, SolicitudProduccion, UnidadMedida
from decimal import Decimal
import datetime
from utils.session import (
    get_current_employee_id,
    get_current_user_id,
    get_default_payment_method_id,
    get_default_sucursal_id,
)


def get_carrito():
    if "carrito" not in session:
        session["carrito"] = []
    return session["carrito"]


def calcular_totales(carrito):
    subtotal = sum(Decimal(item["precio"]) * item["cantidad"] for item in carrito)
    total = subtotal
    return subtotal, total


def caja_abierta_actual():
    return Caja.query.filter_by(estatus="ABIERTA").first()


def get_default_unit_id():
    unidad = UnidadMedida.query.filter_by(estatus="ACTIVO").order_by(UnidadMedida.id.asc()).first()
    return unidad.id if unidad else None


def normalize_payment_method_label(nombre):
    nombre_limpio = (nombre or "").strip()
    if nombre_limpio.lower() == "tarjeta guardada":
        return "Tarjeta"
    return nombre_limpio


def _resolve_cliente_id(raw_cliente_id, usuario_id):
    """Venta.fk_cliente es NOT NULL. Asegura un cliente válido para ventas de mostrador."""
    try:
        candidato = int(raw_cliente_id) if raw_cliente_id not in (None, "", "0") else None
    except (TypeError, ValueError):
        candidato = None

    if candidato:
        cliente = Cliente.query.filter_by(id=candidato, estatus="ACTIVO").first()
        if cliente:
            return cliente.id

    cliente = Cliente.query.filter_by(estatus="ACTIVO").order_by(Cliente.id.asc()).first()
    if cliente:
        return cliente.id

    # No hay clientes: crea uno genérico.
    now = datetime.datetime.now()
    persona = Persona(
        fk_usuario=None,
        fk_direccion=None,
        nombre="Publico",
        apellido_uno="General",
        apellido_dos=None,
        telefono=None,
        correo=None,
        estatus="ACTIVO",
        usuario_creacion=usuario_id,
        usuario_movimiento=usuario_id,
        fecha_creacion=now,
        fecha_movimiento=now,
    )
    db.session.add(persona)
    db.session.flush()

    cliente = Cliente(
        fk_persona=persona.id,
        estatus="ACTIVO",
        usuario_creacion=usuario_id,
        usuario_movimiento=usuario_id,
        fecha_creacion=now,
        fecha_movimiento=now,
    )
    db.session.add(cliente)
    db.session.flush()
    return cliente.id


@pos.route("/", methods=["GET", "POST"])
def inicio():
    carrito = get_carrito()
    accion = request.form.get("accion")
    sucursal_id = get_default_sucursal_id()
    usuario_id = get_current_user_id()
    empleado_id = get_current_employee_id()

    pedidos_listos = Pedido.query.filter(
        Pedido.estado == "LISTO"
    ).all()

    productos = db.session.query(
        Producto,
        InventarioProducto.cantidad_producto
    ).join(
        InventarioProducto,
        Producto.id == InventarioProducto.fk_producto
    ).filter(
        Producto.estatus == "ACTIVO",
        InventarioProducto.fk_sucursal == sucursal_id
    ).all()

    clientes = Cliente.query.filter_by(estatus="ACTIVO").all()
    metodos_pago = MetodoPago.query.filter_by(estatus="ACTIVO").order_by(MetodoPago.id.asc()).all()
    payment_method_options = [
        {
            "id": metodo.id,
            "nombre": normalize_payment_method_label(metodo.nombre),
            "clave": (metodo.nombre or "").strip().lower(),
        }
        for metodo in metodos_pago
    ]

    cambio = None

    metodo_id = int(request.form.get("metodo_pago") or (get_default_payment_method_id() or 0))
    metodo = MetodoPago.query.get(metodo_id)

    if not metodo:
        metodo_id = get_default_payment_method_id() or 0
        metodo = MetodoPago.query.get(metodo_id) if metodo_id else None

    if not metodo:
        flash("No hay metodos de pago activos configurados.", "error")
        return render_template(
            "pos/inicio.html",
            productos=productos,
            carrito=carrito,
            clientes=clientes,
            metodos_pago=[],
            payment_method_options=[],
            subtotal=0,
            total=0,
            cambio=None,
            metodo_seleccionado="",
            metodo_id=0,
            caja_abierta=caja_abierta_actual() is not None,
            pedidos_listos=pedidos_listos,
            pedido=None,
            anticipo=0
        )

    metodo_seleccionado = metodo.nombre.strip().lower()

    pedido_id = session.get("pedido_id")
    pedido = Pedido.query.get(pedido_id) if pedido_id else None

    subtotal, total = calcular_totales(carrito)

    anticipo = 0
    if pedido and pedido.anticipos:
        anticipo = sum(a.monto for a in pedido.anticipos)

    total = float(subtotal) - float(anticipo)

    if total < 0:
        total = 0

    # =========================
    # 📦 CARGAR PEDIDO
    # =========================
    if accion == "cargar_pedido":

        pedido_id = request.form.get("pedido_id")

        if not pedido_id:
            flash("Pedido inválido", "error")
            return redirect(url_for("pos.inicio"))

        pedido = Pedido.query.get_or_404(int(pedido_id))

        carrito.clear()

        for d in pedido.detalles:
            carrito.append({
                "id": d.fk_producto,
                "nombre": d.producto.nombre,
                "precio": float(d.precio_unitario),
                "cantidad": d.cantidad_producto
            })

        session["pedido_id"] = pedido.id
        session.modified = True

        flash(f"Pedido #{pedido.id} cargado al carrito", "success")
        return redirect(url_for("pos.inicio"))

    if accion == "abrir_caja":

        if caja_abierta_actual():
            flash("Ya hay una caja abierta", "warning")
            return redirect(url_for("pos.inicio"))

        monto_inicial = request.form.get("monto_inicial")

        try:
            monto_inicial = float(monto_inicial or 0)
        except:
            monto_inicial = 0

        nueva_caja = Caja(
            fk_sucursal=sucursal_id,
            fk_empleado_apertura=empleado_id,
            monto_inicial=monto_inicial,
            estatus="ABIERTA",
            fecha_apertura=datetime.datetime.now(),
            usuario_creacion=usuario_id,
            usuario_movimiento=usuario_id
        )

        db.session.add(nueva_caja)
        db.session.commit()

        flash("Caja abierta correctamente", "success")
        return redirect(url_for("pos.inicio"))

    if accion == "agregar_producto":

        if session.get("pedido_id"):
            flash("No puedes modificar un pedido cargado", "error")
            return redirect(url_for("pos.inicio"))

        if not caja_abierta_actual():
            flash("Debe abrir caja primero", "error")
            return redirect(url_for("pos.inicio"))

        producto_id = int(request.form.get("producto_id"))

        inventario = InventarioProducto.query.filter_by(
            fk_producto=producto_id,
            fk_sucursal=sucursal_id
        ).first()

        if not inventario or inventario.cantidad_producto <= 0:

            solicitud_existente = SolicitudProduccion.query.filter(
                SolicitudProduccion.fk_producto == producto_id,
                SolicitudProduccion.estado.in_(["PENDIENTE", "EN_PRODUCCION"])
            ).first()

            if solicitud_existente:
                flash("Este producto ya está en producción", "warning")
            else:
                solicitud = SolicitudProduccion(
                    fk_producto=producto_id,
                    fk_empleado=empleado_id,
                    cantidad_solicitada=1,
                    estado="PENDIENTE",
                    usuario_creacion=usuario_id,
                    usuario_movimiento=usuario_id
                )
                db.session.add(solicitud)
                db.session.commit()

                flash("Sin stock. Se envió a producción", "warning")

            return redirect(url_for("pos.inicio"))

        producto = Producto.query.get(producto_id)

        for item in carrito:
            if item["id"] == producto_id:
                item["cantidad"] += 1
                session.modified = True
                return redirect(url_for("pos.inicio"))

        carrito.append({
            "id": producto.id,
            "nombre": producto.nombre,
            "precio": float(producto.precio),
            "cantidad": 1
        })

        session.modified = True
        return redirect(url_for("pos.inicio"))

    # =========================
    # ➕ ➖ ❌
    # =========================
    if accion and accion.startswith(("sumar_", "restar_", "eliminar_")):

        if session.get("pedido_id"):
            flash("No puedes modificar un pedido cargado", "error")
            return redirect(url_for("pos.inicio"))

        id_producto = int(accion.split("_")[1])

        for item in carrito:
            if item["id"] == id_producto:

                if "sumar_" in accion:

                    inventario = InventarioProducto.query.filter_by(
                        fk_producto=id_producto,
                        fk_sucursal=sucursal_id
                    ).first()

                    if not inventario:
                        flash("No hay inventario registrado", "error")
                        return redirect(url_for("pos.inicio"))

                    if item["cantidad"] >= inventario.cantidad_producto:
                        flash("No hay más stock disponible", "error")
                        return redirect(url_for("pos.inicio"))

                    item["cantidad"] += 1

                elif "restar_" in accion:
                    item["cantidad"] -= 1
                    if item["cantidad"] <= 0:
                        carrito.remove(item)

                elif "eliminar_" in accion:
                    carrito.remove(item)

                break

        session.modified = True
        return redirect(url_for("pos.inicio"))

    # =========================
    # 💾 COBRAR
    # =========================
    if accion == "cobrar":

        if not carrito:
            flash("El carrito está vacío", "error")
            return redirect(url_for("pos.inicio"))

        caja = caja_abierta_actual()

        if not caja:
            flash("Debe abrir caja primero", "error")
            return redirect(url_for("pos.inicio"))

        cliente_id = _resolve_cliente_id(request.form.get("cliente_id"), usuario_id)
        metodo_id = int(request.form.get("metodo_pago") or 1)

        metodo = MetodoPago.query.get(metodo_id)
        metodo_seleccionado = metodo.nombre.lower()

        monto_recibido = request.form.get("monto_recibido")

        if metodo_seleccionado == "efectivo":

            if not monto_recibido:
                flash("Debe ingresar monto recibido", "error")
                return redirect(url_for("pos.inicio"))

            monto_recibido = float(monto_recibido)

            if monto_recibido < float(total):
                flash("Monto insuficiente", "error")
                return redirect(url_for("pos.inicio"))

            cambio = monto_recibido - float(total)

        else:
            cambio = 0
            monto_recibido = total

        # 🔥 VALIDAR STOCK
        for item in carrito:
            inventario = InventarioProducto.query.filter_by(
                fk_producto=item["id"],
                fk_sucursal=sucursal_id
            ).first()

            if not inventario or inventario.cantidad_producto < item["cantidad"]:
                flash(f"Stock insuficiente para {item['nombre']}", "error")
                return redirect(url_for("pos.inicio"))

        unidad_id = get_default_unit_id()
        if not unidad_id:
            flash("No hay una unidad de medida activa para registrar la venta.", "error")
            return redirect(url_for("pos.inicio"))

        # 🔥 CREAR VENTA
        now = datetime.datetime.now()
        venta = Venta(
            fk_sucursal=sucursal_id,
            fk_empleado=empleado_id,
            fk_cliente=cliente_id,
            folio_ticket=int(datetime.datetime.now().timestamp()),
            total=total,
            usuario_creacion=usuario_id,
            usuario_movimiento=usuario_id,
            fecha_creacion=now,
            fecha_movimiento=now,
        )

        db.session.add(venta)
        db.session.commit()

        # 🔥 DETALLES
        for item in carrito:
            db.session.add(VentaDetalle(
                fk_venta=venta.id,
                fk_producto=item["id"],
                fk_unidad=unidad_id,
                cantidad_producto=item["cantidad"],
                precio_unitario=item["precio"],
                subtotal=item["cantidad"] * item["precio"],
                usuario_creacion=usuario_id,
                usuario_movimiento=usuario_id,
                fecha_creacion=now,
                fecha_movimiento=now,
            ))

        # 🔥 PAGO
        db.session.add(VentaPago(
            fk_venta=venta.id,
            fk_metodopago=metodo_id,
            monto_pagado=total,
            usuario_creacion=usuario_id,
            usuario_movimiento=usuario_id,
            fecha_creacion=now,
            fecha_movimiento=now,
        ))

        # 🔥 CAJA
        db.session.add(CajaDetalle(
            fk_caja=caja.id,
            fk_venta=venta.id,
            usuario_creacion=usuario_id,
            usuario_movimiento=usuario_id,
            fecha_creacion=now,
            fecha_movimiento=now,
        ))

        db.session.commit()

        # 🔥 INVENTARIO
        for item in carrito:
            inventario = InventarioProducto.query.filter_by(
                fk_producto=item["id"],
                fk_sucursal=sucursal_id
            ).first()

            if inventario:
                inventario.cantidad_producto -= item["cantidad"]

                if inventario.cantidad_producto <= 0:
                    inventario.estado = "AGOTADO"

        db.session.commit()

        session.pop("carrito", None)
        session.pop("pedido_id", None)

        flash("Venta realizada correctamente", "success")

        return redirect(url_for(
            "pos.ticket",
            venta_id=venta.id,
            cambio=cambio,
            recibido=monto_recibido
        ))

    return render_template(
        "pos/inicio.html",
        productos=productos,
        carrito=carrito,
        clientes=clientes,
        metodos_pago=payment_method_options,
        subtotal=subtotal,
        total=total,
        cambio=cambio,
        metodo_seleccionado=metodo_seleccionado,
        metodo_id=metodo_id,
        caja_abierta=caja_abierta_actual() is not None,
        pedidos_listos=pedidos_listos,
        pedido=pedido,
        anticipo=anticipo
    )


@pos.route("/cerrar_caja")
def cerrar_caja():
    caja = caja_abierta_actual()

    if not caja:
        flash("No hay caja abierta", "error")
        return redirect(url_for("pos.inicio"))

    caja.estatus = "CERRADA"
    caja.fecha_cierre = datetime.datetime.now()

    db.session.commit()

    flash("Caja cerrada correctamente", "success")
    return redirect(url_for("pos.inicio"))


@pos.route("/corte_caja")
def corte_caja():
    caja = caja_abierta_actual()
    modo_consulta = False

    if not caja:
        caja = Caja.query.filter_by(estatus="CERRADA").order_by(Caja.id.desc()).first()
        modo_consulta = True

    if not caja:
        flash("No hay cajas registradas", "error")
        return redirect(url_for("pos.inicio"))

    # 🔥 OBTENER VENTAS POR FECHA DE CAJA
    ventas = Venta.query.filter(
        Venta.fecha_creacion >= caja.fecha_apertura
    )

    if caja.fecha_cierre:
        ventas = ventas.filter(Venta.fecha_creacion <= caja.fecha_cierre)

    ventas = ventas.all()

    total_ventas = Decimal(0)
    total_efectivo = Decimal(0)
    total_tarjeta = Decimal(0)
    total_transfer = Decimal(0)
    sales_rows = []

    for venta in ventas:
        total_ventas += venta.total
        sale_payment_labels = []
        sale_items = []

        for pago in venta.pagos:
            metodo = MetodoPago.query.get(pago.fk_metodopago)
            metodo_nombre = normalize_payment_method_label(metodo.nombre if metodo else "Otro")
            sale_payment_labels.append(metodo_nombre)

            if metodo and metodo.nombre.lower() == "efectivo":
                total_efectivo += pago.monto_pagado
            elif metodo and metodo.nombre.lower() in {"tarjeta", "tarjeta guardada"}:
                total_tarjeta += pago.monto_pagado
            else:
                total_transfer += pago.monto_pagado

        for detalle in venta.detalles:
            sale_items.append({
                "nombre": detalle.producto.nombre if detalle.producto else "Producto",
                "cantidad": detalle.cantidad_producto,
            })

        sales_rows.append({
            "folio": venta.folio_ticket,
            "fecha": venta.fecha_creacion,
            "total": venta.total,
            "items": sale_items,
            "payments": sale_payment_labels,
        })

    return render_template(
        "pos/corte_caja.html",
        caja=caja,
        total_ventas=total_ventas,
        efectivo=total_efectivo,
        tarjeta=total_tarjeta,
        transferencia=total_transfer,
        ventas=sales_rows,
        modo_consulta=modo_consulta
    )


@pos.route("/ticket/<int:venta_id>")
def ticket(venta_id):
    venta = Venta.query.get_or_404(venta_id)

    detalles = venta.detalles
    pagos = venta.pagos

    return render_template(
        "pos/ticket.html",
        venta=venta,
        detalles=detalles,
        cambio=request.args.get("cambio"),
        recibido=request.args.get("recibido"),
        pagos=pagos
    )
