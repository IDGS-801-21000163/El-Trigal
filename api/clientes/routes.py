from flask import render_template, request, redirect, url_for, flash, Response, session
from sqlalchemy.exc import IntegrityError

from models import db, Cliente, Pedido, Persona, Venta, Rol, Usuario
from utils.modules import create_module_blueprint
from forms import ClienteForm, EditClienteForm, BuscarClienteForm, ConfirmarEliminacionClienteForm
from datetime import datetime
import base64
import os
from utils.session import get_current_user_id
from utils.auth import hash_password, generate_temp_password, ROL_CLIENTE

clientes = create_module_blueprint("clientes")


def get_user_id():
    return get_current_user_id()


def obtener_imagen(foto):
    if foto:
        return f"data:image/jpeg;base64,{base64.b64encode(foto).decode('utf-8')}"
    return url_for('static', filename='img/defecto.jpg')


def foto_defecto():
    # Leer imagen por defecto desde disco
    ruta = os.path.join('static', 'img', 'defecto.jpg')
    with open(ruta, 'rb') as f:
        return f.read()


def _friendly_duplicate_message(exc: Exception) -> str:
    raw = str(exc) or ""
    lowered = raw.lower()
    if "persona.telefono" in lowered or "telefono" in lowered:
        return "El teléfono ya está registrado."
    if "persona.correo" in lowered or "correo" in lowered:
        return "El correo ya está registrado."
    if "usuario.nick" in lowered or "nick" in lowered:
        return "Ya existe una cuenta con ese correo."
    return "No se pudo guardar porque hay datos duplicados."


@clientes.route("/")
def inicio():
    buscar = request.args.get('buscar', '', type=str)
    estatus = request.args.get("estatus", "ACTIVO", type=str).strip().upper()

    query = Cliente.query.join(Persona)
    if estatus in {"ACTIVO", "INACTIVO"}:
        query = query.filter(Cliente.estatus == estatus)

    # Filtrar por nombre o apellido
    if buscar:
        query = query.filter(
            Persona.nombre.ilike(f'%{buscar}%') |
            Persona.apellido_uno.ilike(f'%{buscar}%')
        )

    clientes_list = query.all()

    # Construir lista de datos para el template
    clientes_data = []
    for c in clientes_list:
        clientes_data.append({
            'id': c.id,
            'persona_id': c.persona.id,
            'nombre': c.persona.nombre,
            'apellido_uno': c.persona.apellido_uno,
            'apellido_dos': c.persona.apellido_dos or '',
            'telefono': c.persona.telefono,
            'correo': c.persona.correo,
            'foto': obtener_imagen(c.persona.foto)
        })

    # Form para el CSRF del modal eliminar
    form_eliminar = ConfirmarEliminacionClienteForm()

    return render_template(
        'clientes/inicio.html',
        clientes=clientes_data,
        buscar=buscar,
        estatus=estatus,
        form_eliminar=form_eliminar
    )


@clientes.route("/agregar", methods=["GET", "POST"])
def agregar():
    form = ClienteForm()

    if form.validate_on_submit():
        try:
            correo = (form.correo.data or "").strip().lower()
            telefono = (form.telefono.data or "").strip()

            if not telefono:
                form.telefono.errors.append("El teléfono es requerido.")
            if not correo:
                form.correo.errors.append("El correo es requerido.")
            if form.telefono.errors or form.correo.errors:
                return render_template("clientes/agregar_presencial.html", form=form)

            if Persona.query.filter_by(telefono=telefono).first():
                form.telefono.errors.append("Este teléfono ya está en uso.")
            if Persona.query.filter_by(correo=correo).first():
                form.correo.errors.append("Este correo ya está en uso.")
            if Usuario.query.filter_by(nick=correo).first():
                form.correo.errors.append("Ya existe una cuenta con este correo.")
            if form.telefono.errors or form.correo.errors:
                return render_template("clientes/agregar_presencial.html", form=form)

            rol = Rol.query.filter_by(nombre=ROL_CLIENTE).first()
            if not rol:
                flash("No existe el rol Cliente. No se puede crear el usuario.", "error")
                return render_template("clientes/agregar_presencial.html", form=form)

            # Leer imagen subida o usar imagen por defecto
            if form.foto.data and form.foto.data.filename:
                foto_bytes = form.foto.data.read()
            else:
                foto_bytes = foto_defecto()

            uid = get_user_id()
            temp_password = generate_temp_password()
            usuario = Usuario(
                fk_rol=rol.id,
                nick=correo,
                clave=hash_password(temp_password),
                forzar_cambio_clave=1,
                estatus='ACTIVO',
                usuario_creacion=uid,
                usuario_movimiento=uid
            )
            db.session.add(usuario)
            db.session.flush()

            persona = Persona(
                nombre=form.nombre.data,
                apellido_uno=form.apellido_paterno.data,
                apellido_dos=form.apellido_materno.data or None,
                telefono=telefono,
                correo=correo,
                foto=foto_bytes,
                fk_usuario=usuario.id,
                estatus='ACTIVO',
                usuario_creacion=uid,
                usuario_movimiento=uid
            )
            db.session.add(persona)
            db.session.flush()

            cliente = Cliente(
                fk_persona=persona.id,
                estatus='ACTIVO',
                usuario_creacion=uid,
                usuario_movimiento=uid
            )
            db.session.add(cliente)
            db.session.commit()

            session["alert_cliente_user"] = correo
            session["alert_cliente_password"] = temp_password

            flash(f'Cliente "{persona.nombre}" agregado correctamente', 'success')
            return redirect(url_for('clientes.inicio'))

        except IntegrityError as e:
            db.session.rollback()
            flash(_friendly_duplicate_message(e), 'error')
            return render_template("clientes/agregar_presencial.html", form=form)
        except Exception:
            db.session.rollback()
            flash('Error al agregar cliente. Verifica los datos e intenta de nuevo.', 'error')
            return render_template("clientes/agregar_presencial.html", form=form)

    return render_template("clientes/agregar_presencial.html", form=form)


@clientes.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    cliente = Cliente.query.get_or_404(id)
    persona = cliente.persona

    if cliente.estatus != 'ACTIVO':
        flash('No puedes editar un cliente inactivo', 'warning')
        return redirect(url_for('clientes.inicio'))

    form = EditClienteForm(persona_id=persona.id)

    if form.validate_on_submit():
        try:
            correo = (form.correo.data or "").strip().lower()
            telefono = (form.telefono.data or "").strip()
            if not telefono:
                form.telefono.errors.append("El teléfono es requerido.")
            if not correo:
                form.correo.errors.append("El correo es requerido.")
            if form.telefono.errors or form.correo.errors:
                imagen = obtener_imagen(persona.foto)
                return render_template("clientes/editar.html", form=form, imagen=imagen, cliente_id=id)

            # Actualizar datos
            persona.nombre        = form.nombre.data
            persona.apellido_uno  = form.apellido_paterno.data
            persona.apellido_dos  = form.apellido_materno.data or None
            persona.telefono      = telefono
            persona.correo        = correo
            persona.usuario_movimiento = get_user_id()
            persona.fecha_movimiento   = datetime.utcnow()

            if form.foto.data and form.foto.data.filename:
                persona.foto = form.foto.data.read()

            if persona.usuario:
                persona.usuario.nick = correo
                persona.usuario.usuario_movimiento = get_user_id()

            db.session.commit()
            flash(f'Cliente "{persona.nombre}" actualizado correctamente', 'success')
            return redirect(url_for('clientes.editar', id=id))

        except IntegrityError as e:
            db.session.rollback()
            flash(_friendly_duplicate_message(e), 'error')
            imagen = obtener_imagen(persona.foto)
            return render_template("clientes/editar.html", form=form, imagen=imagen, cliente_id=id)
        except Exception:
            db.session.rollback()
            flash('Error al actualizar. Verifica los datos e intenta de nuevo.', 'error')
            imagen = obtener_imagen(persona.foto)
            return render_template("clientes/editar.html", form=form, imagen=imagen, cliente_id=id)

    elif request.method == 'GET':
        # Pre-cargar datos del formulario
        form.nombre.data           = persona.nombre
        form.apellido_paterno.data = persona.apellido_uno
        form.apellido_materno.data = persona.apellido_dos
        form.telefono.data         = persona.telefono
        form.correo.data           = persona.correo

    imagen = obtener_imagen(persona.foto)

    return render_template("clientes/editar.html", form=form, imagen=imagen, cliente_id=id)


@clientes.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    form = ConfirmarEliminacionClienteForm()

    if form.validate_on_submit():
        cliente = Cliente.query.get_or_404(id)

        if cliente.estatus != 'ACTIVO':
            flash('El cliente ya está inactivo', 'warning')
            return redirect(url_for('clientes.inicio'))

        try:
            if Pedido.query.filter_by(fk_cliente=cliente.id).count() > 0 or Venta.query.filter_by(fk_cliente=cliente.id).count() > 0:
                flash("No se puede eliminar el cliente porque tiene pedidos o ventas relacionadas.", "error")
                return redirect(url_for("clientes.inicio"))

            # Soft delete en cliente y persona
            cliente.estatus                    = 'INACTIVO'
            cliente.persona.estatus            = 'INACTIVO'
            cliente.usuario_movimiento         = get_user_id()
            cliente.persona.usuario_movimiento = get_user_id()
            cliente.persona.fecha_movimiento   = datetime.utcnow()

            db.session.commit()
            flash('Cliente eliminado correctamente', 'warning')

        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar: {str(e)}', 'error')
    else:
        flash('Token de seguridad inválido', 'error')

    return redirect(url_for('clientes.inicio'))


@clientes.route("/activar/<int:id>", methods=["POST"])
def activar(id):
    form = ConfirmarEliminacionClienteForm()
    if not form.validate_on_submit():
        flash('Token de seguridad inválido', 'error')
        return redirect(url_for('clientes.inicio', estatus="INACTIVO"))

    cliente = Cliente.query.get_or_404(id)
    uid = get_user_id()

    cliente.estatus = "ACTIVO"
    cliente.usuario_movimiento = uid
    if cliente.persona:
        cliente.persona.estatus = "ACTIVO"
        cliente.persona.usuario_movimiento = uid
        cliente.persona.fecha_movimiento = datetime.utcnow()
        if cliente.persona.usuario:
            cliente.persona.usuario.estatus = "ACTIVO"
            cliente.persona.usuario.usuario_movimiento = uid

    db.session.commit()
    flash('Cliente reactivado correctamente', 'success')
    return redirect(url_for('clientes.inicio', estatus="INACTIVO"))
