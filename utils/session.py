from flask import has_request_context, session

from models import Cliente, Empleado, MetodoPago, Persona, Sucursal


def get_current_user_id(default=1):
    if has_request_context():
        return session.get("usuario_id") or default
    return default


def get_current_employee_id(default=1):
    if has_request_context() and session.get("empleado_id"):
        return session["empleado_id"]

    user_id = get_current_user_id(default=None)
    if not user_id:
        return default

    empleado = (
        Empleado.query.join(Persona, Empleado.fk_persona == Persona.id)
        .filter(Persona.fk_usuario == user_id, Empleado.estatus == "ACTIVO")
        .first()
    )

    if empleado and has_request_context():
        session["empleado_id"] = empleado.id
        return empleado.id

    return default


def get_current_client_id(default=None):
    if has_request_context() and session.get("cliente_id"):
        return session["cliente_id"]

    user_id = get_current_user_id(default=None)
    if not user_id:
        return default

    cliente = (
        Cliente.query.join(Persona, Cliente.fk_persona == Persona.id)
        .filter(Persona.fk_usuario == user_id, Cliente.estatus == "ACTIVO")
        .first()
    )

    if cliente and has_request_context():
        session["cliente_id"] = cliente.id
        return cliente.id

    return default


def get_default_sucursal_id(default=1):
    sucursal = Sucursal.query.filter_by(estatus="ACTIVO").order_by(Sucursal.id.asc()).first()
    return sucursal.id if sucursal else default


def get_default_payment_method_id(default=None):
    metodo = MetodoPago.query.filter_by(estatus="ACTIVO").order_by(MetodoPago.id.asc()).first()
    return metodo.id if metodo else default


def get_default_employee_id(default=1):
    empleado = Empleado.query.filter_by(estatus="ACTIVO").order_by(Empleado.id.asc()).first()
    return empleado.id if empleado else default


def get_session_user_summary():
    if not has_request_context() or not session.get("usuario_id"):
        return None

    return {
        "id": session.get("usuario_id"),
        "rol_id": session.get("rol_id"),
        "nick": session.get("usuario_nick"),
        "nombre": session.get("usuario_nombre"),
        "correo": session.get("usuario_correo"),
        "rol": session.get("usuario_rol"),
    }
