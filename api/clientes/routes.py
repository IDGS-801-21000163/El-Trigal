from flask import render_template, request, redirect, url_for, flash, Response
from models import db, Cliente, Persona
from api.common import create_module_blueprint
from forms import ClienteForm, EditClienteForm, BuscarClienteForm, ConfirmarEliminacionClienteForm
from datetime import datetime
import base64
import os

clientes = create_module_blueprint("clientes")


def get_user_id():
    return 1


def obtener_imagen(foto):
    """Convierte bytes a base64 para mostrar en template, igual que categorías"""
    if foto:
        return f"data:image/jpeg;base64,{base64.b64encode(foto).decode('utf-8')}"
    return url_for('static', filename='img/defecto.jpg')


def foto_defecto():
    """Lee la imagen por defecto desde disco"""
    ruta = os.path.join('static', 'img', 'defecto.jpg')
    with open(ruta, 'rb') as f:
        return f.read()


# ==========================
# LISTADO
# ==========================
@clientes.route("/")
def inicio():
    buscar = request.args.get('buscar', '', type=str)

    query = Cliente.query.join(Persona).filter(Cliente.estatus == 'ACTIVO')

    if buscar:
        query = query.filter(
            Persona.nombre.ilike(f'%{buscar}%') |
            Persona.apellido_uno.ilike(f'%{buscar}%')
        )

    clientes_list = query.all()

    # Construir lista de dicts igual que categorías
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

    # Form solo para el CSRF del modal eliminar
    form_eliminar = ConfirmarEliminacionClienteForm()

    return render_template(
        'clientes/inicio.html',
        clientes=clientes_data,
        buscar=buscar,
        form_eliminar=form_eliminar
    )


# ==========================
# AGREGAR
# ==========================
@clientes.route("/agregar", methods=["GET", "POST"])
def agregar():
    form = ClienteForm()

    if form.validate_on_submit():
        try:
            # Validar correo único
            existe = Persona.query.filter_by(correo=form.correo.data).first()
            if existe:
                flash("El correo ya está registrado", "error")
                return redirect(url_for('clientes.agregar'))

            # Foto
            if form.foto.data and form.foto.data.filename:
                foto_bytes = form.foto.data.read()
            else:
                foto_bytes = foto_defecto()

            persona = Persona(
                nombre=form.nombre.data,
                apellido_uno=form.apellido_paterno.data,
                apellido_dos=form.apellido_materno.data or None,
                telefono=form.telefono.data,
                correo=form.correo.data,
                foto=foto_bytes,
                estatus='ACTIVO',
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id()
            )
            db.session.add(persona)
            db.session.flush()

            cliente = Cliente(
                fk_persona=persona.id,
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id()
            )
            db.session.add(cliente)
            db.session.commit()

            flash(f'Cliente "{persona.nombre}" agregado correctamente', 'success')
            return redirect(url_for('clientes.agregar'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar cliente: {str(e)}', 'error')
            return redirect(url_for('clientes.agregar'))

    return render_template("clientes/agregar_presencial.html", form=form)


# ==========================
# EDITAR
# ==========================
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
            persona.nombre        = form.nombre.data
            persona.apellido_uno  = form.apellido_paterno.data
            persona.apellido_dos  = form.apellido_materno.data or None
            persona.telefono      = form.telefono.data
            persona.correo        = form.correo.data
            persona.usuario_movimiento = get_user_id()
            persona.fecha_movimiento   = datetime.utcnow()

            if form.foto.data and form.foto.data.filename:
                persona.foto = form.foto.data.read()

            db.session.commit()
            flash(f'Cliente "{persona.nombre}" actualizado correctamente', 'success')
            return redirect(url_for('clientes.editar', id=id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar: {str(e)}', 'error')
            return redirect(url_for('clientes.editar', id=id))

    elif request.method == 'GET':
        form.nombre.data           = persona.nombre
        form.apellido_paterno.data = persona.apellido_uno
        form.apellido_materno.data = persona.apellido_dos
        form.telefono.data         = persona.telefono
        form.correo.data           = persona.correo

    imagen = obtener_imagen(persona.foto)

    return render_template("clientes/editar.html", form=form, imagen=imagen, cliente_id=id)


# ==========================
# ELIMINAR (soft delete)
# ==========================
@clientes.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    form = ConfirmarEliminacionClienteForm()

    if form.validate_on_submit():
        cliente = Cliente.query.get_or_404(id)

        if cliente.estatus != 'ACTIVO':
            flash('El cliente ya está inactivo', 'warning')
            return redirect(url_for('clientes.inicio'))

        try:
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