from flask import render_template, redirect, url_for, flash, request, session
from . import usuarios
from models import Usuario, Rol, Empleado, db
from werkzeug.security import generate_password_hash
import secrets

MODULE = {
    "name": "Usuarios",
    "slug": "usuarios",
    "description": "Gestión de usuarios del sistema"
}

@usuarios.route("/")
def inicio():
    usuarios_lista = Usuario.query.all()
    module = MODULE.copy()
    module["items"] = usuarios_lista
    actions = []
    return render_template(
        "usuarios/inicio.html",
        module=module,
        actions=actions
    )

@usuarios.route("/agregar", methods=["GET", "POST"])
def agregar():
    return render_template(
        "empleados/agregar.html",
        module=MODULE
    )

@usuarios.route("/detalle/<int:id>")
def detalle(id):
    usuario = Usuario.query.get_or_404(id)
    password_temp = session.get("password_temp")  # Cambio: usar get para no eliminar de sesión
    roles = Rol.query.all()
    return render_template(
        "usuarios/detalle.html",
        usuario=usuario,
        module=MODULE,
        password_temp=password_temp,
        roles=roles
    )

@usuarios.route("/detalle/<int:id>/mostrar_password")
def mostrar_password(id):
    usuario = Usuario.query.get_or_404(id)
    password_temp = session.pop("password_temp", None)  # Cambio: pop para mostrar solo 1 vez
    roles = Rol.query.all()
    return render_template(
        "usuarios/detalle.html",
        usuario=usuario,
        module=MODULE,
        password_temp=password_temp,
        roles=roles
    )

@usuarios.route("/editar/<int:id>", methods=["POST"])
def editar(id):
    usuario = Usuario.query.get_or_404(id)
    rol_id = request.form.get("rol_id")

    if rol_id:
        usuario.fk_rol = int(rol_id)
        db.session.commit()
        flash("Rol de usuario actualizado correctamente.", "success")
    else:
        flash("No se seleccionó un rol válido.", "warning")

    return redirect(url_for("usuarios.inicio"))

def crear_usuario_para_empleado(empleado):
    temp_password = secrets.token_urlsafe(8)  # Cambio: genera contraseña temporal
    hashed_password = generate_password_hash(temp_password, method="scrypt")
    usuario = Usuario(
        fk_rol=empleado.rol.id,
        nick=empleado.nombre.lower() + "001",
        clave=hashed_password,
        empleado=empleado
    )
    db.session.add(usuario)
    db.session.commit()
    session['password_temp'] = temp_password  # Cambio: guardar contraseña en sesión
    return usuario