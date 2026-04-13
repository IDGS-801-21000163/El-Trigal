import base64
import datetime
from decimal import Decimal

from flask import current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from utils.modules import create_module_blueprint, get_module_config
from models import (
    CategoriaProducto,
    Cliente,
    InventarioProducto,
    InventarioProductoMovimiento,
    Pedido,
    PedidoAnticipo,
    PedidoDetalle,
    Producto,
    db,
)
from utils.auth import send_email
from utils.session import (
    get_current_client_id,
    get_current_employee_id,
    get_current_user_id,
    get_default_employee_id,
    get_default_payment_method_id,
    get_default_sucursal_id,
)


pedidos = create_module_blueprint("pedidos")
MODULE = get_module_config("pedidos")
CARD_PROFILE = {
    "brand": "Visa",
    "holder": "Cliente El Trigal",
    "masked_number": "**** **** **** 4821",
    "expires": "09/29",
}


def _format_image(foto):
    if not foto:
        return url_for("static", filename="img/defecto.jpg")
    if isinstance(foto, (bytes, bytearray)):
        encoded = base64.b64encode(foto).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/jpeg;base64,{foto}"
    return url_for("static", filename="img/defecto.jpg")


def _get_cart():
    return session.get("pedido_cart", [])


def _save_cart(cart):
    session["pedido_cart"] = cart
    session.modified = True


def _clear_cart():
    session.pop("pedido_cart", None)
    session.modified = True


def _get_product_stock(producto_id, sucursal_id=None):
    sucursal_id = sucursal_id or get_default_sucursal_id(default=None)
    if not sucursal_id:
        return 0.0

    stock = (
        db.session.query(func.coalesce(func.sum(InventarioProducto.cantidad_producto), 0))
        .filter(
            InventarioProducto.fk_producto == producto_id,
            InventarioProducto.fk_sucursal == sucursal_id,
            InventarioProducto.estatus == "ACTIVO",
        )
        .scalar()
    )
    return float(stock or 0)


def _build_catalog(buscar="", categoria_id=0):
    query = Producto.query.filter_by(estatus="ACTIVO")
    if buscar:
        query = query.filter(Producto.nombre.ilike(f"%{buscar}%"))
    if categoria_id:
        query = query.filter_by(fk_categoria=categoria_id)

    productos = []
    for producto in query.order_by(Producto.nombre.asc()).all():
        stock = _get_product_stock(producto.id)
        productos.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "categoria": producto.categoria.nombre if producto.categoria else "Sin categoria",
                "precio": float(producto.precio or 0),
                "imagen": _format_image(producto.foto),
                "stock": float(stock or 0),
                "stock_label": "Disponible" if stock and float(stock) > 0 else "Bajo pedido",
            }
        )
    return productos


def _build_cart_detail():
    cart = _get_cart()
    if not cart:
        return [], {"items": 0, "subtotal": 0.0, "service": 0.0, "total": 0.0}

    product_ids = [item["producto_id"] for item in cart]
    productos = {producto.id: producto for producto in Producto.query.filter(Producto.id.in_(product_ids)).all()}

    detail = []
    subtotal = Decimal("0.00")
    total_items = 0

    for item in cart:
        producto = productos.get(item["producto_id"])
        if not producto:
            continue

        cantidad = int(item["cantidad"])
        unit_price = Decimal(str(producto.precio or 0))
        line_total = unit_price * Decimal(str(cantidad))
        subtotal += line_total
        total_items += cantidad

        detail.append(
            {
                "producto_id": producto.id,
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "precio": float(unit_price),
                "subtotal": float(line_total),
                "imagen": _format_image(producto.foto),
                "stock": _get_product_stock(producto.id),
            }
        )

    service = subtotal * Decimal("0.05")
    total = subtotal + service

    return detail, {
        "items": total_items,
        "subtotal": float(subtotal),
        "service": float(service),
        "total": float(total),
    }


def _get_cliente_actual():
    client_id = get_current_client_id()
    if not client_id:
        return None
    return Cliente.query.get(client_id)


def _get_order_history(cliente):
    if not cliente:
        return []

    orders = (
        Pedido.query.filter_by(fk_cliente=cliente.id)
        .order_by(Pedido.fecha_creacion.desc())
        .limit(6)
        .all()
    )

    history = []
    for order in orders:
        total = sum(float(detalle.subtotal or 0) for detalle in order.detalles if detalle.estatus == "ACTIVO")
        history.append(
            {
                "id": order.id,
                "estado": order.estado,
                "fecha": order.fecha_pedido.strftime("%d/%m/%Y"),
                "entrega": order.fecha_entrega.strftime("%d/%m/%Y"),
                "total": total,
                "items": sum(int(det.cantidad_producto or 0) for det in order.detalles if det.estatus == "ACTIVO"),
            }
        )
    return history


def _resolve_checkout_context():
    empleado_id = get_current_employee_id(default=None) or get_default_employee_id(default=None)
    sucursal_id = get_default_sucursal_id(default=None)
    metodo_pago_id = get_default_payment_method_id(default=None)
    return empleado_id, sucursal_id, metodo_pago_id


def _build_order_confirmation_email(pedido, cliente, detalles, total):
    nombre_cliente = "Cliente El Trigal"
    correo = None
    if cliente and cliente.persona:
        nombre_cliente = f"{cliente.persona.nombre} {cliente.persona.apellido_uno or ''}".strip()
        correo = cliente.persona.correo

    entrega = pedido.fecha_entrega.strftime("%d/%m/%Y")
    fecha_pedido = pedido.fecha_pedido.strftime("%d/%m/%Y %H:%M")
    notas = pedido.notas or "Sin notas adicionales."
    items_html = "".join(
        [
            f"""
            <tr>
                <td style="padding:12px 0;border-bottom:1px dashed #e9d6ba;color:#6f4d2f;">{item['nombre']}</td>
                <td style="padding:12px 0;border-bottom:1px dashed #e9d6ba;color:#8a6946;text-align:center;">{item['cantidad']}</td>
                <td style="padding:12px 0;border-bottom:1px dashed #e9d6ba;color:#6f4d2f;text-align:right;">${item['subtotal']:.2f}</td>
            </tr>
            """
            for item in detalles
        ]
    )

    text_body = (
        f"Hola {nombre_cliente},\n\n"
        f"Tu pedido #{pedido.id} fue confirmado correctamente.\n"
        f"Fecha del pedido: {fecha_pedido}\n"
        f"Entrega programada: {entrega}\n"
        f"Estado: {pedido.estado}\n"
        f"Total: ${total:.2f}\n\n"
        "Productos:\n"
        + "\n".join([f"- {item['nombre']} x{item['cantidad']} - ${item['subtotal']:.2f}" for item in detalles])
        + f"\n\nNotas: {notas}\n\nGracias por comprar en El Trigal."
    )

    html_body = f"""
    <html>
    <body style="margin:0;padding:0;background:#f7efe1;font-family:Georgia,'Times New Roman',serif;color:#6b4a2d;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 0;background:#f7efe1;">
            <tr>
                <td align="center">
                    <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;background:#fffaf2;border-radius:28px;overflow:hidden;border:1px solid #ead8bd;box-shadow:0 16px 40px rgba(112,78,44,0.10);">
                        <tr>
                            <td style="padding:30px 34px;background:linear-gradient(135deg,#fff6e6,#f2dfc0);border-bottom:1px solid #ebd8bc;">
                                <table width="100%" role="presentation">
                                    <tr>
                                        <td>
                                            <div style="font-size:14px;letter-spacing:.22em;text-transform:uppercase;color:#b07b3c;">Confirmación de pedido</div>
                                            <h1 style="margin:8px 0 6px;font-size:36px;line-height:1;color:#6b4a2d;">Ticket #{pedido.id}</h1>
                                            <p style="margin:0;color:#8a6946;font-size:16px;">Gracias por comprar en El Trigal, {nombre_cliente}.</p>
                                        </td>
                                        <td align="right" style="font-size:14px;color:#8a6946;">
                                            <strong style="display:block;font-size:16px;color:#6b4a2d;">Estado</strong>
                                            {pedido.estado}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:28px 34px;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
                                    <tr>
                                        <td style="padding:0 16px 16px 0;">
                                            <div style="padding:18px 20px;border:1px solid #ebd8bc;border-radius:18px;background:#fffdf8;">
                                                <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#b07b3c;">Fecha del pedido</div>
                                                <strong style="display:block;margin-top:6px;font-size:20px;color:#6b4a2d;">{fecha_pedido}</strong>
                                            </div>
                                        </td>
                                        <td style="padding:0 16px 16px 0;">
                                            <div style="padding:18px 20px;border:1px solid #ebd8bc;border-radius:18px;background:#fffdf8;">
                                                <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#b07b3c;">Entrega</div>
                                                <strong style="display:block;margin-top:6px;font-size:20px;color:#6b4a2d;">{entrega}</strong>
                                            </div>
                                        </td>
                                        <td style="padding:0 0 16px 0;">
                                            <div style="padding:18px 20px;border:1px solid #ebd8bc;border-radius:18px;background:#fffdf8;">
                                                <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#b07b3c;">Total</div>
                                                <strong style="display:block;margin-top:6px;font-size:20px;color:#6b4a2d;">${total:.2f}</strong>
                                            </div>
                                        </td>
                                    </tr>
                                </table>

                                <div style="padding:22px 24px;border-radius:22px;background:#fffdf8;border:1px solid #ebd8bc;">
                                    <h2 style="margin:0 0 14px;font-size:26px;color:#6b4a2d;">Resumen del pedido</h2>
                                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                        <thead>
                                            <tr>
                                                <th align="left" style="padding:0 0 10px;color:#b07b3c;font-size:13px;letter-spacing:.12em;text-transform:uppercase;">Producto</th>
                                                <th align="center" style="padding:0 0 10px;color:#b07b3c;font-size:13px;letter-spacing:.12em;text-transform:uppercase;">Cant.</th>
                                                <th align="right" style="padding:0 0 10px;color:#b07b3c;font-size:13px;letter-spacing:.12em;text-transform:uppercase;">Importe</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {items_html}
                                        </tbody>
                                    </table>
                                </div>

                                <div style="margin-top:18px;padding:18px 20px;border-radius:18px;background:#f9f2e7;border:1px solid #ebd8bc;">
                                    <div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#b07b3c;">Notas</div>
                                    <p style="margin:8px 0 0;color:#6f4d2f;line-height:1.6;">{notas}</p>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:20px 34px 30px;background:#fff6e8;border-top:1px solid #ebd8bc;color:#8a6946;font-size:14px;">
                                <strong style="display:block;color:#6b4a2d;font-size:16px;margin-bottom:6px;">El Trigal</strong>
                                Este correo es una confirmación automática de tu pedido.
                                {f"<br>Se envió a: {correo}" if correo else ""}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """.strip()

    return text_body, html_body


@pedidos.route("/", methods=["GET"])
def inicio():
    buscar = request.args.get("buscar", "", type=str)
    categoria_id = request.args.get("categoria", 0, type=int)
    categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").order_by(CategoriaProducto.nombre.asc()).all()
    cliente = _get_cliente_actual()
    cart_items, cart_summary = _build_cart_detail()

    return render_template(
        "pedidos/inicio.html",
        module=MODULE,
        current_action="inicio",
        productos=_build_catalog(buscar=buscar, categoria_id=categoria_id),
        categorias=categorias,
        buscar=buscar,
        categoria_id=categoria_id,
        cliente=cliente,
        cart_items=cart_items,
        cart_summary=cart_summary,
        card_profile=CARD_PROFILE,
        order_history=_get_order_history(cliente),
        today=datetime.date.today().strftime("%Y-%m-%d"),
    )


@pedidos.route("/carrito/agregar", methods=["POST"])
def agregar_al_carrito():
    producto_id = request.form.get("producto_id", type=int)
    cantidad = max(request.form.get("cantidad", type=int, default=1), 1)
    producto = Producto.query.filter_by(id=producto_id, estatus="ACTIVO").first()

    if not producto:
        flash("El producto seleccionado ya no esta disponible.", "warning")
        return redirect(url_for("pedidos.inicio"))

    stock_disponible = _get_product_stock(producto_id)
    if stock_disponible <= 0:
        flash(f"{producto.nombre} no tiene existencias disponibles.", "warning")
        return redirect(url_for("pedidos.inicio"))

    cart = _get_cart()
    existing = next((item for item in cart if item["producto_id"] == producto_id), None)
    if existing:
        nueva_cantidad = existing["cantidad"] + cantidad
        if nueva_cantidad > stock_disponible:
            flash(f"No puedes agregar más de {int(stock_disponible)} unidad(es) de {producto.nombre}.", "warning")
            return redirect(url_for("pedidos.inicio"))
        existing["cantidad"] = nueva_cantidad
    else:
        if cantidad > stock_disponible:
            flash(f"Solo hay {int(stock_disponible)} unidad(es) disponibles de {producto.nombre}.", "warning")
            return redirect(url_for("pedidos.inicio"))
        cart.append({"producto_id": producto_id, "cantidad": cantidad})

    _save_cart(cart)
    flash(f"{producto.nombre} se agrego al carrito.", "success")
    return redirect(url_for("pedidos.inicio"))


@pedidos.route("/carrito/actualizar", methods=["POST"])
def actualizar_carrito():
    producto_id = request.form.get("producto_id", type=int)
    cantidad = request.form.get("cantidad", type=int, default=1)
    cart = _get_cart()
    producto = Producto.query.filter_by(id=producto_id, estatus="ACTIVO").first()
    stock_disponible = _get_product_stock(producto_id)

    for item in cart:
        if item["producto_id"] == producto_id:
            if cantidad <= 0:
                cart = [row for row in cart if row["producto_id"] != producto_id]
                flash("Producto eliminado del carrito.", "warning")
            else:
                if cantidad > stock_disponible:
                    flash(
                        f"Solo hay {int(stock_disponible)} unidad(es) disponibles"
                        + (f" de {producto.nombre}" if producto else "."),
                        "warning",
                    )
                    return redirect(url_for("pedidos.inicio"))
                item["cantidad"] = cantidad
                flash("Cantidad actualizada.", "success")
            break

    _save_cart(cart)
    return redirect(url_for("pedidos.inicio"))


@pedidos.route("/carrito/eliminar", methods=["POST"])
def eliminar_del_carrito():
    producto_id = request.form.get("producto_id", type=int)
    cart = [item for item in _get_cart() if item["producto_id"] != producto_id]
    _save_cart(cart)
    flash("Producto eliminado del carrito.", "warning")
    return redirect(url_for("pedidos.inicio"))


@pedidos.route("/checkout", methods=["POST"])
def checkout():
    cliente = _get_cliente_actual()
    if not cliente:
        flash("Tu cuenta no tiene un perfil de cliente enlazado para generar pedidos.", "danger")
        return redirect(url_for("pedidos.inicio"))

    cart_items, cart_summary = _build_cart_detail()
    if not cart_items:
        flash("Agrega productos al carrito antes de confirmar el pedido.", "warning")
        return redirect(url_for("pedidos.inicio"))

    empleado_id, sucursal_id, metodo_pago_id = _resolve_checkout_context()
    if not empleado_id or not sucursal_id or not metodo_pago_id:
        flash("Falta configuracion base del sistema para registrar pedidos en linea.", "danger")
        return redirect(url_for("pedidos.inicio"))

    fecha_entrega_raw = request.form.get("fecha_entrega", "").strip()
    notas = request.form.get("notas", "").strip() or None

    try:
        fecha_entrega = datetime.datetime.strptime(fecha_entrega_raw, "%Y-%m-%d")
        fecha_entrega = fecha_entrega.replace(hour=18, minute=0, second=0)
    except ValueError:
        flash("Selecciona una fecha de entrega valida.", "warning")
        return redirect(url_for("pedidos.inicio"))

    if fecha_entrega.date() < datetime.date.today():
        flash("La fecha de entrega no puede ser anterior a hoy.", "warning")
        return redirect(url_for("pedidos.inicio"))

    user_id = get_current_user_id()

    try:
        inventarios = {}
        for item in cart_items:
            inventario = InventarioProducto.query.filter_by(
                fk_producto=item["producto_id"],
                fk_sucursal=sucursal_id,
                estatus="ACTIVO",
            ).first()

            if not inventario or float(inventario.cantidad_producto or 0) < item["cantidad"]:
                producto_nombre = item["nombre"]
                flash(f"No hay existencias suficientes para {producto_nombre}.", "warning")
                return redirect(url_for("pedidos.inicio"))

            inventarios[item["producto_id"]] = inventario

        pedido = Pedido(
            fk_cliente=cliente.id,
            fk_empleado=empleado_id,
            fk_sucursal=sucursal_id,
            tipo_pedido="EN_LINEA",
            notas=notas,
            fecha_entrega=fecha_entrega,
            estado="ESPERANDO",
            estatus="ACTIVO",
            usuario_creacion=user_id,
            usuario_movimiento=user_id,
        )
        db.session.add(pedido)
        db.session.flush()

        for item in cart_items:
            db.session.add(
                PedidoDetalle(
                    fk_pedido=pedido.id,
                    fk_producto=item["producto_id"],
                    cantidad_producto=item["cantidad"],
                    precio_unitario=Decimal(str(item["precio"])),
                    subtotal=Decimal(str(item["subtotal"])),
                    estatus="ACTIVO",
                    usuario_creacion=user_id,
                    usuario_movimiento=user_id,
                )
            )

        db.session.add(
            PedidoAnticipo(
                fk_pedido=pedido.id,
                fk_metodopago=metodo_pago_id,
                monto=Decimal(str(cart_summary["total"])),
                estatus="ACTIVO",
                usuario_creacion=user_id,
                usuario_movimiento=user_id,
            )
        )

        for item in cart_items:
            inventario = inventarios[item["producto_id"]]
            cantidad_anterior = Decimal(str(inventario.cantidad_producto or 0))
            cantidad_nueva = cantidad_anterior - Decimal(str(item["cantidad"]))

            inventario.cantidad_producto = cantidad_nueva
            inventario.estado = "EXISTENCIA" if cantidad_nueva > 0 else "AGOTADO"
            inventario.usuario_movimiento = user_id

            db.session.add(
                InventarioProductoMovimiento(
                    fk_inventario_producto=inventario.id,
                    tipo_movimiento="AUDITORIA",
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=cantidad_nueva,
                    diferencia=Decimal(str(item["cantidad"])) * Decimal("-1"),
                    motivo=f"Salida por pedido en linea #{pedido.id}",
                    usuario_movimiento=user_id,
                )
            )

        db.session.commit()
        _clear_cart()
    except Exception as exc:
        db.session.rollback()
        flash(f"No se pudo registrar el pedido: {exc}", "danger")
        return redirect(url_for("pedidos.inicio"))

    correo_cliente = cliente.persona.correo if cliente and cliente.persona else None
    if correo_cliente:
        try:
            text_body, html_body = _build_order_confirmation_email(pedido, cliente, cart_items, cart_summary["total"])
            send_email(
                current_app,
                correo_cliente,
                f"El Trigal | Confirmacion de pedido #{pedido.id}",
                text_body,
                html_body=html_body,
            )
        except Exception as exc:
            flash(f"El pedido se registró, pero no se pudo enviar el correo de confirmación: {exc}", "warning")

    flash("Pedido confirmado y pago simulado con tu tarjeta guardada.", "success")
    return redirect(url_for("pedidos.detalle", id=pedido.id))


@pedidos.route("/detalle/<int:id>", methods=["GET"])
def detalle(id):
    pedido = Pedido.query.get_or_404(id)
    cliente_actual = _get_cliente_actual()

    if cliente_actual and pedido.fk_cliente != cliente_actual.id:
        flash("No puedes consultar pedidos de otro cliente.", "warning")
        return redirect(url_for("pedidos.inicio"))

    detalles = [
        {
            "nombre": detalle.producto.nombre if detalle.producto else "Producto eliminado",
            "cantidad": detalle.cantidad_producto,
            "precio_unitario": float(detalle.precio_unitario or 0),
            "subtotal": float(detalle.subtotal or 0),
        }
        for detalle in pedido.detalles
        if detalle.estatus == "ACTIVO"
    ]

    total = sum(item["subtotal"] for item in detalles)

    return render_template(
        "pedidos/detalle.html",
        module=MODULE,
        pedido=pedido,
        detalles=detalles,
        total=total,
        current_action="detalle",
    )
