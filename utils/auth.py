import datetime
import secrets
import smtplib
from email.message import EmailMessage

from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from models import Cliente, Persona, Rol, Usuario, UsuarioOtp, db


PASSWORD_HASH_METHOD = "scrypt"
ROL_ADMIN = "Administrador"
ROL_EMPLEADO = "Empleado"
ROL_CLIENTE = "Cliente"
OTP_LENGTH = 5


def hash_password(password):
    return generate_password_hash(password, method=PASSWORD_HASH_METHOD)


def verify_password(password_hash, password):
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)


def generate_temp_password(length=10):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_otp(length=OTP_LENGTH):
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def mask_email(email):
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        local_masked = local[0] + "*"
    else:
        local_masked = local[0] + ("*" * (len(local) - 2)) + local[-1]
    return f"{local_masked}@{domain}"


def send_email(app, to_email, subject, text_body, html_body=None):
    server = app.config.get("MAIL_SERVER")
    port = int(app.config.get("MAIL_PORT", 587))
    username = app.config.get("MAIL_USERNAME")
    password = app.config.get("MAIL_PASSWORD")
    sender = app.config.get("MAIL_DEFAULT_SENDER") or username
    use_tls = bool(app.config.get("MAIL_USE_TLS", True))
    use_ssl = bool(app.config.get("MAIL_USE_SSL", False))
    redirect_domain = (app.config.get("MAIL_REDIRECT_DOMAIN") or "").strip().lower()
    redirect_to = (app.config.get("MAIL_REDIRECT_TO") or "").strip()

    if not server or not sender:
        raise RuntimeError("La configuracion SMTP no esta completa.")

    original_to = to_email
    if redirect_domain and redirect_to and isinstance(to_email, str) and "@" in to_email:
        _, domain = to_email.rsplit("@", 1)
        if domain.strip().lower() == redirect_domain:
            to_email = redirect_to

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    if original_to != to_email:
        message["X-Original-To"] = original_to
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

    with smtp_class(server, port, timeout=20) as smtp:
        if not use_ssl and use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def ensure_roles():
    primer_usuario = Usuario.query.order_by(Usuario.id.asc()).first()
    if not primer_usuario:
        return

    existentes = {
        rol.nombre: rol
        for rol in Rol.query.filter(Rol.nombre.in_([ROL_ADMIN, ROL_EMPLEADO, ROL_CLIENTE])).all()
    }

    created = False

    if ROL_ADMIN not in existentes:
        db.session.add(
            Rol(
                nombre=ROL_ADMIN,
                descripcion="Administrador del sistema",
                estatus="ACTIVO",
                usuario_creacion=primer_usuario.id,
                usuario_movimiento=primer_usuario.id,
            )
        )
        created = True

    if ROL_EMPLEADO not in existentes:
        db.session.add(
            Rol(
                nombre=ROL_EMPLEADO,
                descripcion="Empleado del sistema",
                estatus="ACTIVO",
                usuario_creacion=primer_usuario.id,
                usuario_movimiento=primer_usuario.id,
            )
        )
        created = True

    if ROL_CLIENTE not in existentes:
        db.session.add(
            Rol(
                nombre=ROL_CLIENTE,
                descripcion="Cliente con acceso al modulo de pedidos",
                estatus="ACTIVO",
                usuario_creacion=primer_usuario.id,
                usuario_movimiento=primer_usuario.id,
            )
        )
        created = True

    if created:
        db.session.commit()


def bootstrap_first_account(nombre, apellido_uno, apellido_dos, telefono, correo):
    now = datetime.datetime.now()
    temp_password = generate_temp_password()
    password_hash = hash_password(temp_password)

    connection = db.session.connection()
    connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

    try:
        connection.execute(
            text(
                """
                INSERT INTO rol (
                    id, nombre, descripcion, estatus,
                    fecha_creacion, usuario_creacion,
                    fecha_movimiento, usuario_movimiento
                ) VALUES
                    (1, :rol_admin, 'Administrador del sistema', 'ACTIVO', :now, 1, :now, 1),
                    (2, :rol_empleado, 'Empleado del sistema', 'ACTIVO', :now, 1, :now, 1),
                    (3, :rol_cliente, 'Cliente con acceso al modulo de pedidos', 'ACTIVO', :now, 1, :now, 1)
                """
            ),
            {
                "rol_admin": ROL_ADMIN,
                "rol_empleado": ROL_EMPLEADO,
                "rol_cliente": ROL_CLIENTE,
                "now": now,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO usuario (
                    id, fk_rol, nick, clave,
                    intentos_fallidos, bloqueado_hasta, ultimo_login,
                    fecha_cambio_clave, forzar_cambio_clave, estatus,
                    fecha_creacion, usuario_creacion,
                    fecha_movimiento, usuario_movimiento
                ) VALUES (
                    1, 1, :nick, :clave,
                    0, NULL, NULL,
                    NULL, 0, 'ACTIVO',
                    :now, 1,
                    :now, 1
                )
                """
            ),
            {
                "nick": correo.strip().lower(),
                "clave": password_hash,
                "now": now,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO persona (
                    fk_usuario, fk_direccion, nombre, apellido_uno, apellido_dos,
                    telefono, correo, foto, estatus,
                    fecha_creacion, usuario_creacion,
                    fecha_movimiento, usuario_movimiento
                ) VALUES (
                    1, NULL, :nombre, :apellido_uno, :apellido_dos,
                    :telefono, :correo, NULL, 'ACTIVO',
                    :now, 1,
                    :now, 1
                )
                """
            ),
            {
                "nombre": nombre,
                "apellido_uno": apellido_uno,
                "apellido_dos": apellido_dos or None,
                "telefono": telefono,
                "correo": correo,
                "now": now,
            },
        )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    return Usuario.query.filter_by(nick=correo.strip().lower()).first(), temp_password


def create_user_account(nombre, apellido_uno, apellido_dos, telefono, correo, creador_id, rol_id):
    username = correo.strip().lower()
    temp_password = generate_temp_password()

    usuario = Usuario(
        fk_rol=rol_id,
        nick=username,
        clave=hash_password(temp_password),
        estatus="ACTIVO",
        usuario_creacion=creador_id,
        usuario_movimiento=creador_id,
    )
    db.session.add(usuario)
    db.session.flush()

    persona = Persona(
        fk_usuario=usuario.id,
        fk_direccion=None,
        nombre=nombre.strip(),
        apellido_uno=apellido_uno.strip(),
        apellido_dos=(apellido_dos or "").strip() or None,
        telefono=telefono.strip(),
        correo=correo.strip().lower(),
        estatus="ACTIVO",
        usuario_creacion=creador_id,
        usuario_movimiento=creador_id,
    )
    db.session.add(persona)
    db.session.flush()

    rol = Rol.query.get(rol_id)
    if rol and rol.nombre == ROL_CLIENTE:
        cliente = Cliente(
            fk_persona=persona.id,
            estatus="ACTIVO",
            usuario_creacion=creador_id,
            usuario_movimiento=creador_id,
        )
        db.session.add(cliente)

    db.session.commit()

    return usuario, temp_password


def create_login_otp(usuario, expires_in_minutes):
    token = generate_otp()
    expiracion = datetime.datetime.now() + datetime.timedelta(minutes=expires_in_minutes)

    UsuarioOtp.query.filter_by(fk_usuario=usuario.id, utilizado=0).update({"utilizado": 1})

    otp = UsuarioOtp(
        fk_usuario=usuario.id,
        token=token,
        expiracion=expiracion,
        utilizado=0,
    )
    db.session.add(otp)
    db.session.commit()

    return otp


def get_valid_otp(usuario_id, token):
    now = datetime.datetime.now()
    return (
        UsuarioOtp.query.filter_by(fk_usuario=usuario_id, token=token, utilizado=0)
        .filter(UsuarioOtp.expiracion >= now)
        .first()
    )
