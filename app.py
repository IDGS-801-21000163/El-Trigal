import base64
import datetime
import uuid

from flask import Flask, current_app, flash, has_request_context, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session
from flask_wtf.csrf import CSRFProtect
from flask_wtf.csrf import CSRFError

from api import ALL_BLUEPRINTS
from utils.auth import (
    ROL_CLIENTE,
    bootstrap_first_account,
    create_login_otp,
    create_user_account,
    ensure_roles,
    generate_temp_password,
    get_valid_otp,
    hash_password,
    mask_email,
    send_email,
    verify_password,
)
from utils.modules import ACTIONS, ensure_module_catalog, get_first_allowed_module, get_nav_modules_for_role, role_has_module_access
from config import DevelopmentConfig
from forms import LoginForm, OtpForm, RecuperarForm, RegistroForm
from models import (
    CategoriaProducto,
    Pedido,
    PedidoDetalle,
    Persona,
    Producto,
    Rol,
    Usuario,
    db,
)
from utils.session import (
    get_current_client_id,
    get_current_user_id,
    get_default_employee_id,
    get_default_sucursal_id,
    get_session_user_summary,
)
from utils.mongo_logger import SENSITIVE_FIELDS, configure_mongo_logging, write_audit_event, _serialize_value


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
app.permanent_session_lifetime = datetime.timedelta(hours=8)
configure_mongo_logging(app)

csrf = CSRFProtect()
csrf.init_app(app)
db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    db.create_all()
    ensure_roles()
    ensure_module_catalog()

@event.listens_for(Session, "before_flush")
def stamp_audit_fields(session_obj, flush_context, instances):
    if not has_request_context():
        return

    user_id = get_current_user_id(default=None)
    if not user_id:
        return

    now = datetime.datetime.now()

    for obj in session_obj.new:
        if hasattr(obj, "usuario_creacion"):
            obj.usuario_creacion = user_id
        if hasattr(obj, "usuario_movimiento"):
            obj.usuario_movimiento = user_id
        if hasattr(obj, "fecha_movimiento"):
            obj.fecha_movimiento = now

    for obj in session_obj.dirty:
        if not session_obj.is_modified(obj, include_collections=False):
            continue
        if hasattr(obj, "usuario_movimiento"):
            obj.usuario_movimiento = user_id
        if hasattr(obj, "fecha_movimiento"):
            obj.fecha_movimiento = now


def _build_audit_context():
    if not has_request_context():
        return {}
    return {
        "user_id": session.get("usuario_id"),
        "role_id": session.get("rol_id"),
        "path": request.path,
        "method": request.method,
        "endpoint": request.endpoint,
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent"),
        "session_id": session.get("session_id") or session.get("_id"),
    }


def _safe_column_value(value):
    return _serialize_value(value)


@event.listens_for(Session, "after_flush")
def audit_model_changes(session_obj, flush_context):
    if not has_request_context():
        return

    context = _build_audit_context()

    def snapshot(obj):
        state = sa_inspect(obj)
        data = {}
        for col in state.mapper.column_attrs:
            key = col.key
            if key in SENSITIVE_FIELDS:
                continue
            value = getattr(obj, key, None)
            data[key] = _safe_column_value(value)
        return data

    for obj in session_obj.new:
        state = sa_inspect(obj)
        entity = state.mapper.class_.__name__
        entity_id = state.identity[0] if state.identity else getattr(obj, "id", None)
        payload = {
            "event": "create",
            "entity": entity,
            "entity_id": entity_id,
            "data": snapshot(obj),
            "context": context,
        }
        write_audit_event(current_app, payload)

    for obj in session_obj.deleted:
        state = sa_inspect(obj)
        entity = state.mapper.class_.__name__
        entity_id = state.identity[0] if state.identity else getattr(obj, "id", None)
        payload = {
            "event": "delete",
            "entity": entity,
            "entity_id": entity_id,
            "data": snapshot(obj),
            "context": context,
        }
        write_audit_event(current_app, payload)

    for obj in session_obj.dirty:
        if not session_obj.is_modified(obj, include_collections=False):
            continue
        state = sa_inspect(obj)
        entity = state.mapper.class_.__name__
        entity_id = state.identity[0] if state.identity else getattr(obj, "id", None)
        changes = {}
        for attr in state.attrs:
            if attr.key in SENSITIVE_FIELDS:
                continue
            hist = attr.history
            if not hist.has_changes():
                continue
            old_val = hist.deleted[0] if hist.deleted else None
            new_val = hist.added[0] if hist.added else getattr(obj, attr.key, None)
            changes[attr.key] = {
                "old": _safe_column_value(old_val),
                "new": _safe_column_value(new_val),
            }

        if not changes:
            continue

        action = "update"
        if "estatus" in changes:
            new_status = changes["estatus"]["new"]
            if new_status == "INACTIVO":
                action = "deactivate"
            elif new_status == "ACTIVO":
                action = "activate"

        payload = {
            "event": action,
            "entity": entity,
            "entity_id": entity_id,
            "changes": changes,
            "context": context,
        }
        write_audit_event(current_app, payload)


for blueprint in ALL_BLUEPRINTS:
    app.register_blueprint(blueprint, url_prefix=f"/{blueprint.name.replace('_', '-')}")


def completar_login(usuario):
    usuario.intentos_fallidos = 0
    usuario.ultimo_login = datetime.datetime.now()
    usuario.usuario_movimiento = usuario.id
    db.session.commit()

    write_audit_event(
        current_app,
        {
            "event": "auth_login_success",
            "entity": "Usuario",
            "entity_id": usuario.id,
            "context": _build_audit_context(),
        },
    )

    session.clear()
    session.permanent = True
    session["session_id"] = str(uuid.uuid4())
    persona = usuario.persona
    session["usuario_id"] = usuario.id
    session["rol_id"] = usuario.fk_rol
    session["usuario_nick"] = usuario.nick
    session["usuario_rol"] = usuario.rol.nombre if usuario.rol else None
    session["usuario_nombre"] = persona.nombre if persona else usuario.nick
    session["usuario_correo"] = persona.correo if persona and persona.correo else usuario.nick
    if persona and persona.empleado:
        session["empleado_id"] = persona.empleado.id
    if persona and persona.cliente:
        session["cliente_id"] = persona.cliente.id
    session["login_at"] = datetime.datetime.now().isoformat()


def hydrate_session_user():
    user_id = session.get("usuario_id")
    if not user_id:
        return None

    usuario = Usuario.query.get(user_id)
    if not usuario or usuario.estatus != "ACTIVO":
        session.clear()
        return None

    persona = usuario.persona
    session["rol_id"] = usuario.fk_rol
    session["usuario_nick"] = usuario.nick
    session["usuario_rol"] = usuario.rol.nombre if usuario.rol else None
    session["usuario_nombre"] = persona.nombre if persona else usuario.nick
    session["usuario_correo"] = persona.correo if persona and persona.correo else usuario.nick

    if persona and persona.empleado:
        session["empleado_id"] = persona.empleado.id
    else:
        session.pop("empleado_id", None)

    if persona and persona.cliente:
        session["cliente_id"] = persona.cliente.id
    else:
        session.pop("cliente_id", None)

    return usuario


def enviar_codigo_acceso(usuario):
    persona = usuario.persona
    target_email = None
    if persona and persona.correo:
        target_email = persona.correo
    elif usuario and isinstance(usuario.nick, str) and "@" in usuario.nick:
        # Compat: algunas cuentas usan el correo como nick y no tienen Persona vinculada.
        target_email = usuario.nick.strip().lower()

    if not target_email:
        raise RuntimeError("Tu cuenta no tiene un correo asociado para enviar el codigo.")

    otp = create_login_otp(usuario, current_app.config["OTP_EXPIRATION_MINUTES"])

    write_audit_event(
        current_app,
        {
            "event": "auth_otp_sent",
            "entity": "Usuario",
            "entity_id": usuario.id,
            "context": _build_audit_context(),
        },
    )

    send_email(
        current_app,
        target_email,
        "Codigo de verificacion - El Trigal",
        (
            f"Hola {(persona.nombre if persona and persona.nombre else 'usuario')},\n\n"
            f"Tu codigo de verificacion para iniciar sesion es: {otp.token}\n"
            f"Este codigo vence en {current_app.config['OTP_EXPIRATION_MINUTES']} minutos.\n\n"
            "Si no intentaste iniciar sesion, ignora este mensaje."
        ),
    )

    session.clear()
    session["pending_user_id"] = usuario.id
    session["pending_email"] = target_email


@app.context_processor
def inject_navigation():
    role_id = session.get("rol_id")
    return {
        "nav_modules": get_nav_modules_for_role(role_id),
        "actions": ACTIONS,
        "usuario_sesion": get_session_user_summary(),
    }


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash("La solicitud expiró o el token de seguridad no es válido. Intenta de nuevo.", "warning")
    return redirect(request.referrer or url_for("acceso"))


@app.before_request
def guard_module_access():
    public_endpoints = {
        "static",
        "landing",
        "acceso",
        "index",
        "registro",
        "verificacion",
        "cancelar_verificacion",
        "recuperar",
        "logout",
    }

    if request.endpoint != "static":
        now = datetime.datetime.now()
        inactivity_minutes = int(current_app.config.get("SESSION_INACTIVITY_MINUTES", 10))
        last_activity_raw = session.get("last_activity_at")

        if session.get("usuario_id") and last_activity_raw:
            try:
                last_activity = datetime.datetime.fromisoformat(last_activity_raw)
                if now - last_activity > datetime.timedelta(minutes=inactivity_minutes):
                    write_audit_event(
                        current_app,
                        {
                            "event": "auth_session_expired",
                            "context": _build_audit_context(),
                        },
                    )
                    session.clear()
                    flash("Tu sesión expiró por inactividad. Vuelve a iniciar sesión.", "warning")
                    return redirect(url_for("acceso"))
            except ValueError:
                session.pop("last_activity_at", None)

        session["last_activity_at"] = now.isoformat()

    if request.endpoint in public_endpoints:
        return None

    if not session.get("usuario_id"):
        flash("Debes iniciar sesion para continuar.", "warning")
        return redirect(url_for("acceso"))

    usuario = hydrate_session_user()
    if not usuario:
        flash("Tu sesion ya no es valida. Vuelve a iniciar sesion.", "warning")
        return redirect(url_for("acceso"))

    if not request.blueprint:
        return None

    module_slug = request.blueprint.replace("_", "-")
    role_id = session.get("rol_id")
    if role_id and role_has_module_access(role_id, module_slug):
        return None


@app.after_request
def log_request(response):
    if request.endpoint != "static":
        user_id = session.get("usuario_id")
        app.logger.info(
            "HTTP %s %s %s user=%s session=%s",
            request.method,
            request.path,
            response.status_code,
            user_id if user_id is not None else "-",
            session.get("session_id") or "-",
        )
    return response

    flash("No tienes permiso para entrar a este modulo.", "warning")
    return redirect(url_for("panel"))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


def _landing_image(foto):
    if not foto:
        return None
    if isinstance(foto, bytes):
        encoded = base64.b64encode(foto).decode("utf-8")
    elif isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        encoded = foto
    else:
        return None
    return f"data:image/png;base64,{encoded}"


def _get_landing_cart():
    return session.get("landing_cart", {})


def _set_landing_cart(cart):
    session["landing_cart"] = cart


def _build_cart_items():
    cart = _get_landing_cart()
    if not cart:
        return []
    keys = [int(k) for k in cart.keys()]
    productos = Producto.query.filter(Producto.id.in_(keys)).all()
    items = []
    for producto in productos:
        qty = int(cart.get(str(producto.id)) or cart.get(producto.id) or 0)
        if qty <= 0:
            continue
        items.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "precio": float(producto.precio),
                "cantidad": qty,
                "imagen": _landing_image(producto.foto),
                "subtotal": float(producto.precio) * qty,
            }
        )
    return items


@app.route("/")
def landing():
    if session.get("usuario_id"):
        usuario = hydrate_session_user()
        first_module = get_first_allowed_module(session.get("rol_id")) if usuario else None
        if first_module:
            return redirect(url_for("panel"))
        session.clear()
        flash("Tu cuenta no tiene módulos asignados todavía. Inicia sesión de nuevo.", "warning")
    categorias = (
        CategoriaProducto.query.filter(CategoriaProducto.estatus == "ACTIVO")
        .order_by(CategoriaProducto.nombre.asc())
        .all()
    )
    productos = (
        Producto.query.filter(Producto.estatus == "ACTIVO")
        .order_by(Producto.id.desc())
        .limit(12)
        .all()
    )
    productos_cards = [
        {
            "id": item.id,
            "nombre": item.nombre,
            "precio": float(item.precio),
            "imagen": _landing_image(item.foto),
        }
        for item in productos
    ]
    categorias_cards = [item.nombre for item in categorias]
    return render_template(
        "landing.html",
        productos=productos_cards,
        categorias=categorias_cards,
    )


@app.route("/catalogo/<int:producto_id>")
def catalogo_detalle(producto_id):
    producto = Producto.query.filter_by(id=producto_id, estatus="ACTIVO").first_or_404()
    detalle = {
        "id": producto.id,
        "nombre": producto.nombre,
        "precio": float(producto.precio),
        "imagen": _landing_image(producto.foto),
        "categoria": producto.categoria.nombre if producto.categoria else "Panadería",
    }
    return render_template("landing_detalle.html", producto=detalle)


@app.route("/carrito")
def carrito():
    items = _build_cart_items()
    total = sum(item["subtotal"] for item in items)
    return render_template("carrito.html", items=items, total=total)


@app.route("/carrito/agregar", methods=["POST"])
def carrito_agregar():
    producto_id = request.form.get("producto_id", type=int)
    cantidad = request.form.get("cantidad", type=int) or 1
    producto = Producto.query.filter_by(id=producto_id, estatus="ACTIVO").first()
    if not producto:
        flash("Producto no disponible.", "danger")
        return redirect(url_for("landing"))
    cart = _get_landing_cart()
    key = str(producto_id)
    cart[key] = int(cart.get(key, 0)) + max(1, cantidad)
    _set_landing_cart(cart)
    flash("Producto agregado al carrito.", "success")
    return redirect(url_for("carrito"))


@app.route("/carrito/remover", methods=["POST"])
def carrito_remover():
    producto_id = request.form.get("producto_id", type=int)
    cart = _get_landing_cart()
    key = str(producto_id)
    if key in cart:
        cart.pop(key)
        _set_landing_cart(cart)
    return redirect(url_for("carrito"))


@app.route("/carrito/checkout", methods=["POST"])
def carrito_checkout():
    items = _build_cart_items()
    if not items:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for("carrito"))

    if not session.get("usuario_id"):
        flash("Inicia sesión para completar la compra.", "warning")
        return redirect(url_for("acceso"))

    cliente_id = get_current_client_id(default=None)
    if not cliente_id:
        flash("Tu cuenta no tiene perfil de cliente activo.", "warning")
        return redirect(url_for("carrito"))

    empleado_id = get_default_employee_id(default=1)
    sucursal_id = get_default_sucursal_id(default=1)
    fecha_entrega_raw = request.form.get("fecha_entrega")
    notas = request.form.get("notas")
    try:
        fecha_entrega = datetime.datetime.strptime(fecha_entrega_raw, "%Y-%m-%d")
    except Exception:
        fecha_entrega = datetime.datetime.now() + datetime.timedelta(days=1)

    pedido = Pedido(
        fk_cliente=cliente_id,
        fk_empleado=empleado_id,
        fk_sucursal=sucursal_id,
        tipo_pedido="EN_LINEA",
        notas=notas,
        fecha_entrega=fecha_entrega,
        estado="ESPERANDO",
        estatus="ACTIVO",
        usuario_creacion=get_current_user_id(default=1),
        usuario_movimiento=get_current_user_id(default=1),
    )
    db.session.add(pedido)
    db.session.flush()

    for item in items:
        detalle = PedidoDetalle(
            fk_pedido=pedido.id,
            fk_producto=item["id"],
            cantidad_producto=item["cantidad"],
            precio_unitario=item["precio"],
            subtotal=item["subtotal"],
            estatus="ACTIVO",
            usuario_creacion=get_current_user_id(default=1),
            usuario_movimiento=get_current_user_id(default=1),
        )
        db.session.add(detalle)

    db.session.commit()
    session.pop("landing_cart", None)
    flash("Pedido registrado. Te esperamos para tu entrega.", "success")
    return redirect(url_for("landing"))


@app.route("/acceso", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def acceso():
    if session.get("usuario_id"):
        usuario = hydrate_session_user()
        if usuario and get_first_allowed_module(session.get("rol_id")):
            return redirect(url_for("panel"))
        session.clear()

    form = LoginForm()

    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(nick=form.usuario.data.strip().lower()).first()

        # Bloqueo por intentos fallidos (A07).
        if usuario and usuario.bloqueado_hasta and datetime.datetime.now() < usuario.bloqueado_hasta:
            flash("Tu cuenta está bloqueada temporalmente por intentos fallidos. Intenta más tarde.", "danger")
            return render_template("index.html", form=form)

        if not usuario or usuario.estatus != "ACTIVO" or not verify_password(usuario.clave, form.contrasena.data):
            if usuario:
                usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
                # Al 3er intento fallido bloquear por 15 minutos.
                if (usuario.intentos_fallidos or 0) >= 3:
                    usuario.bloqueado_hasta = datetime.datetime.now() + datetime.timedelta(minutes=15)
                usuario.usuario_movimiento = usuario.id
                db.session.commit()

            write_audit_event(
                current_app,
                {
                    "event": "auth_login_failed",
                    "entity": "Usuario",
                    "entity_id": usuario.id if usuario else None,
                    "context": {
                        **_build_audit_context(),
                        "login_user": form.usuario.data.strip().lower(),
                    },
                },
            )

            flash("Usuario o contrasena incorrectos.", "danger")
            return render_template("index.html", form=form)

        try:
            enviar_codigo_acceso(usuario)
        except Exception as exc:
            flash(f"No se pudo enviar el codigo de verificacion: {exc}", "danger")
            return render_template("index.html", form=form)

        flash("Te enviamos un codigo de verificacion a tu correo.", "success")
        return redirect(url_for("verificacion"))

    return render_template("index.html", form=form)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if session.get("usuario_id"):
        return redirect(url_for("panel"))

    form = RegistroForm()

    if form.validate_on_submit():
        correo = form.correo.data.strip().lower()
        telefono = form.telefono.data.strip()

        if Usuario.query.filter_by(nick=correo).first():
            flash("Ese correo ya tiene una cuenta registrada.", "warning")
            return render_template("registro.html", form=form)

        persona_existente = Persona.query.filter(
            (Persona.correo == correo) | (Persona.telefono == telefono)
        ).first()
        if persona_existente:
            flash("El correo o telefono ya estan registrados.", "warning")
            return render_template("registro.html", form=form)

        try:
            if Usuario.query.count() == 0:
                usuario, temp_password = bootstrap_first_account(
                    form.nombre.data,
                    form.apellido_uno.data,
                    form.apellido_dos.data,
                    telefono,
                    correo,
                )
            else:
                ensure_roles()
                ensure_module_catalog()
                rol = Rol.query.filter_by(nombre=ROL_CLIENTE).first()
                creador = Usuario.query.order_by(Usuario.id.asc()).first()

                if not rol or not creador:
                    raise RuntimeError("No fue posible inicializar los roles del sistema.")

                usuario, temp_password = create_user_account(
                    form.nombre.data,
                    form.apellido_uno.data,
                    form.apellido_dos.data,
                    telefono,
                    correo,
                    creador.id,
                    rol.id,
                )
        except Exception as exc:
            flash(f"No se pudo completar el registro: {exc}", "danger")
            return render_template("registro.html", form=form)

        ensure_module_catalog()

        try:
            send_email(
                current_app,
                correo,
                "Bienvenido a El Trigal",
                (
                    f"Hola {form.nombre.data.strip()},\n\n"
                    "Tu cuenta fue creada correctamente.\n"
                    f"Usuario: {usuario.nick}\n"
                    f"Contrasena temporal: {temp_password}\n\n"
                    "Cuando inicies sesion te enviaremos un codigo de verificacion a este correo."
                ),
            )
        except Exception as exc:
            flash(
                f"La cuenta fue creada, pero no se pudo enviar el correo con las credenciales: {exc}",
                "warning",
            )
            return redirect(url_for("acceso"))

        write_audit_event(
            current_app,
            {
                "event": "auth_register",
                "entity": "Usuario",
                "entity_id": usuario.id,
                "context": _build_audit_context(),
            },
        )

        flash("Registro completado. Te enviamos tus credenciales al correo.", "success")
        return redirect(url_for("acceso"))

    return render_template("registro.html", form=form)


@app.route("/verificacion", methods=["GET", "POST"])
def verificacion():
    usuario_id = session.get("pending_user_id")
    correo = session.get("pending_email")

    if not usuario_id or not correo:
        flash("Primero inicia sesion para verificar tu identidad.", "warning")
        return redirect(url_for("acceso"))

    form = OtpForm()

    if form.validate_on_submit():
        token = "".join([
            form.digito_1.data,
            form.digito_2.data,
            form.digito_3.data,
            form.digito_4.data,
            form.digito_5.data,
        ])

        otp = get_valid_otp(usuario_id, token)
        if not otp:
            write_audit_event(
                current_app,
                {
                    "event": "auth_otp_invalid",
                    "entity": "Usuario",
                    "entity_id": usuario_id,
                    "context": _build_audit_context(),
                },
            )
            flash("El codigo no es valido o ya vencio.", "danger")
            return render_template("verificacion.html", form=form, correo_mascara=mask_email(correo))

        otp.utilizado = 1
        db.session.commit()

        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            session.clear()
            flash("La cuenta ya no existe.", "danger")
            return redirect(url_for("acceso"))

        completar_login(usuario)
        flash("Verificacion completada. Bienvenido.", "success")
        return redirect(url_for("panel"))

    return render_template("verificacion.html", form=form, correo_mascara=mask_email(correo))


@app.route("/verificacion/cancelar")
def cancelar_verificacion():
    session.clear()
    flash("Se cancelo la verificacion de identidad.", "warning")
    return redirect(url_for("acceso"))


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if session.get("usuario_id"):
        return redirect(url_for("panel"))

    form = RecuperarForm()

    if form.validate_on_submit():
        correo = form.correo.data.strip().lower()

        usuario = Usuario.query.filter_by(nick=correo).first()

        # Siempre respondemos igual para evitar enumeracion de cuentas.
        flash("Si el correo existe, te enviaremos una nueva contraseña temporal.", "success")

        if usuario and usuario.estatus == "ACTIVO":
            temp_password = generate_temp_password()
            usuario.clave = hash_password(temp_password)
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            usuario.fecha_cambio_clave = datetime.datetime.now()
            usuario.forzar_cambio_clave = 1
            usuario.usuario_movimiento = usuario.id
            db.session.commit()

            write_audit_event(
                current_app,
                {
                    "event": "auth_password_reset",
                    "entity": "Usuario",
                    "entity_id": usuario.id,
                    "context": _build_audit_context(),
                },
            )

            try:
                send_email(
                    current_app,
                    correo,
                    "Recuperacion de cuenta - El Trigal",
                    (
                        "Hola,\n\n"
                        "Recibimos una solicitud para restablecer tu contraseña.\n"
                        f"Tu nueva contraseña temporal es: {temp_password}\n\n"
                        "Te recomendamos iniciar sesion y cambiarla lo antes posible.\n"
                        "Si no solicitaste este cambio, ignora este mensaje."
                    ),
                )
            except Exception as exc:
                flash(f"No se pudo enviar el correo de recuperacion: {exc}", "warning")

        return redirect(url_for("acceso"))

    return render_template("recuperar.html", form=form)


@app.route("/panel")
def panel():
    if not session.get("usuario_id"):
        flash("Debes iniciar sesion para entrar al panel.", "warning")
        return redirect(url_for("acceso"))

    usuario = hydrate_session_user()
    if not usuario:
        flash("Tu sesion ya no es valida. Vuelve a iniciar sesion.", "warning")
        return redirect(url_for("acceso"))

    first_module = get_first_allowed_module(session.get("rol_id"))
    if not first_module:
        session.clear()
        flash("Tu cuenta no tiene modulos asignados.", "warning")
        return redirect(url_for("acceso"))

    return redirect(url_for(f"{first_module['slug'].replace('-', '_')}.inicio"))


@app.route("/logout")
def logout():
    write_audit_event(
        current_app,
        {
            "event": "auth_logout",
            "context": _build_audit_context(),
        },
    )
    session.clear()
    flash("Sesion cerrada.", "success")
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(port=4000, debug=True)
