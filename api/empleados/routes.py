import base64
import random
import string

from flask import render_template, redirect, url_for, flash, request, jsonify, session
from sqlalchemy import or_
from werkzeug.security import generate_password_hash

from . import empleados
from models import (
    Caja,
    Compra,
    Direccion,
    Empleado,
    Estado,
    Municipio,
    Pedido,
    Persona,
    Produccion,
    Puesto,
    Rol,
    SolicitudProduccion,
    Usuario,
    Venta,
    db,
)
from forms import EmpleadoForm
from utils.auth import ROL_EMPLEADO


# ==========================
# HELPERS
# ==========================
def generar_password(longitud=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))

def usuario_sesion_id():
    return session.get("usuario_id") or 1

def validate_fk_estado(self, field):
    if field.data == 0:
        raise ValidationError("Seleccione un estado válido")

def validate_fk_municipio(self, field):
    if field.data == 0:
        raise ValidationError("Seleccione un municipio válido")
# ==========================
# CONFIG MODULO
# ==========================
MODULE = {
    "name": "Empleados",
    "slug": "empleados",
    "description": "Gestión de empleados del sistema"
}


# ==========================
# LISTA
# ==========================
@empleados.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()

    query = (
        Empleado.query.join(Persona, Empleado.fk_persona == Persona.id)
        .outerjoin(Puesto, Empleado.fk_puesto == Puesto.id)
        .outerjoin(Usuario, Persona.fk_usuario == Usuario.id)
        .filter(Empleado.estatus == "ACTIVO")
    )

    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            or_(
                Empleado.num_empleado.ilike(like),
                Persona.nombre.ilike(like),
                Persona.apellido_uno.ilike(like),
                Persona.apellido_dos.ilike(like),
                Persona.telefono.ilike(like),
                Persona.correo.ilike(like),
                Puesto.nombre.ilike(like),
                Usuario.nick.ilike(like),
            )
        )

    empleados_lista = query.all()

    for emp in empleados_lista:
        if emp.persona and emp.persona.foto:
            if isinstance(emp.persona.foto, bytes):
                emp.persona.foto = emp.persona.foto.decode('utf-8')

   

    module = MODULE.copy()
    module["items"] = empleados_lista

    return render_template("empleados/inicio.html", module=module, buscar=buscar)


# ==========================
# DETALLE
# ==========================
@empleados.route("/detalle/<int:id>")
def detalle(id):
    empleado = Empleado.query.get_or_404(id)
    if empleado.persona and empleado.persona.foto:
        if isinstance(empleado.persona.foto, bytes):
            empleado.persona.foto = empleado.persona.foto.decode('utf-8')
    return render_template(
        "empleados/detalle.html",
        empleado=empleado,
        module=MODULE,
        temp_user=session.pop("alert_user", None),
        temp_password=session.pop("alert_password", None)
    )


# ==========================
# AGREGAR
# ==========================
@empleados.route("/agregar", methods=["GET", "POST"])
def agregar():

    form = EmpleadoForm()

    if Puesto.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay puestos registrados. Primero crea un puesto para poder dar de alta un empleado.", "warning")
        return redirect(url_for("puestos.inicio"))

    if Estado.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay estados registrados. No se puede continuar con el alta de empleados.", "warning")
        return redirect(url_for("empleados.inicio"))

    # Quitar estatus en alta
    if 'estatus' in form._fields:
        del form._fields['estatus']

    # PUESTOS
    form.fk_puesto.choices = [
        (p.id, p.nombre)
        for p in Puesto.query.filter_by(estatus="ACTIVO").all()
    ]

    # ESTADOS
    form.fk_estado.choices = [(0, "Seleccione un estado")] + [
        (e.id, e.nombre)
        for e in Estado.query.filter_by(estatus="ACTIVO").order_by(Estado.nombre)
]
    


    # MUNICIPIOS
    estado_id = request.form.get("fk_estado", type=int)

    form.fk_municipio.choices = []

    if estado_id:
        form.fk_municipio.choices = [
            (m.id, m.nombre)
            for m in Municipio.query
            .filter_by(fk_estado=estado_id)
            .order_by(Municipio.nombre)
    ]

    # VALIDAR
    if form.validate_on_submit():
                # ==========================
# VALIDAR CAMPOS OBLIGATORIOS
# ==========================

        if not form.correo.data:
            flash("El correo es obligatorio.", "danger")
            return render_template(
        "empleados/agregar.html",
        form=form,
        module=MODULE,
        action_label="Agregar"
    )

        if not form.telefono.data:
            flash("El teléfono es obligatorio.", "danger")
            return render_template(
        "empleados/agregar.html",
        form=form,
        module=MODULE,
        action_label="Agregar"
    )
        
        uid = usuario_sesion_id()

        # ROL
        rol = Rol.query.filter_by(nombre=ROL_EMPLEADO).first()
        if not rol:
            flash("No existe el rol EMPLEADO en el sistema. No se puede continuar.", "danger")
            return redirect(url_for("empleados.inicio"))
        # ==========================
# VALIDACIONES DE DUPLICADOS
# ==========================

        # NUM EMPLEADO
        existe_num = Empleado.query.filter_by(
            num_empleado=form.num_empleado.data
        ).first()

        if existe_num:
            flash("El número de empleado ya está registrado.", "danger")
            return render_template("empleados/agregar.html", form=form, module=MODULE, action_label="Agregar")


        # CORREO
        if form.correo.data:
            existe_correo = Persona.query.filter_by(
                correo=form.correo.data
            ).first()

            if existe_correo:
                flash("El correo ya está registrado.", "danger")
                return render_template("empleados/agregar.html", form=form, module=MODULE, action_label="Agregar")


        # TELEFONO
        if form.telefono.data:
            existe_tel = Persona.query.filter_by(
                telefono=form.telefono.data
            ).first()

            if existe_tel:
                flash("El teléfono ya está registrado.", "danger")
                return render_template("empleados/agregar.html", form=form, module=MODULE, action_label="Agregar")
            # DIRECCION
        direccion = Direccion(
            fk_estado=form.fk_estado.data,
            fk_municipio=form.fk_municipio.data,
            calle=form.calle.data,
            colonia=form.colonia.data,
            codigo_postal=form.codigo_postal.data,
            num_exterior=form.num_exterior.data,
            num_interior=form.num_interior.data,
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(direccion)
        db.session.flush()

        # PERSONA
        persona = Persona(
            nombre=form.nombre.data,
            apellido_uno=form.apellido_uno.data,
            apellido_dos=form.apellido_dos.data,
            telefono=form.telefono.data,
            correo=form.correo.data,
            fk_direccion=direccion.id,
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(persona)
        db.session.flush()

        # FOTO → se guarda en Persona
        archivo = form.imagen.data
        if archivo and hasattr(archivo, 'read') and archivo.filename:
            contenido = archivo.read()
            if contenido:
                persona.foto = f"data:{archivo.mimetype};base64,{base64.b64encode(contenido).decode('utf-8')}"

        # EMPLEADO
        empleado = Empleado(
            fk_persona=persona.id,
            fk_puesto=form.fk_puesto.data,
            num_empleado=form.num_empleado.data,
            fecha_contratacion=form.fecha_contratacion.data,
            estatus="ACTIVO",
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(empleado)
        db.session.flush()

        # USUARIO — generar nick único
        primer_nombre = persona.nombre.split()[0].lower()
        base_nick = primer_nombre + str(form.num_empleado.data)
        nick = base_nick
        contador = 1
        while Usuario.query.filter_by(nick=nick).first():
            nick = f"{base_nick}{contador}"
            contador += 1

        password_plano = generar_password()

        usuario = Usuario(
            fk_rol=rol.id,
            nick=nick,
            clave=generate_password_hash(password_plano, method="scrypt"),
            usuario_creacion=uid,
            usuario_movimiento=uid
        )
        db.session.add(usuario)
        db.session.flush()

        # VINCULAR usuario → persona
        persona.fk_usuario = usuario.id

        db.session.commit()

        # GUARDAR CREDENCIALES TEMPORALES EN SESIÓN
        session["alert_user"] = nick
        session["alert_password"] = password_plano

        flash("Empleado registrado correctamente.", "success")
        return redirect(url_for("empleados.detalle", id=empleado.id))

    return render_template(
        "empleados/agregar.html",
        form=form,
        module=MODULE,
        action_label="Agregar"
    )


# ==========================
# EDITAR
# ==========================
@empleados.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    empleado  = Empleado.query.get_or_404(id)
    persona   = empleado.persona
    if not persona:
        flash("El empleado no tiene una persona asociada. Corrige los datos antes de editarlo.", "danger")
        return redirect(url_for("empleados.inicio"))

    direccion = persona.direccion
    if not direccion:
        flash("El empleado no tiene dirección asociada. Corrige los datos antes de editarlo.", "danger")
        return redirect(url_for("empleados.inicio"))

    form = EmpleadoForm()

    # PUESTOS
    form.fk_puesto.choices = [
        (p.id, p.nombre)
        for p in Puesto.query.order_by(Puesto.nombre)
    ]

    # ESTADOS
    form.fk_estado.choices = [
        (e.id, e.nombre)
        for e in Estado.query.order_by(Estado.nombre)
    ]

    # MUNICIPIOS
    if request.method == "POST":
        estado_id = request.form.get("fk_estado", type=int) or direccion.fk_estado
        municipio_id = request.form.get("fk_municipio", type=int)
    else:
        estado_id = direccion.fk_estado
        municipio_id = direccion.fk_municipio

    form.fk_municipio.choices = [
        (m.id, m.nombre)
        for m in Municipio.query
        .filter_by(fk_estado=estado_id)
        .order_by(Municipio.nombre)
    ]

    # ESTATUS — forzar valor actual en POST si no viene en el form
    if request.method == "POST" and not request.form.get("estatus"):
        form.estatus.data = empleado.estatus

    # CARGAR DATOS EN GET
    if request.method == "GET":
        form.nombre.data             = persona.nombre
        form.apellido_uno.data       = persona.apellido_uno
        form.apellido_dos.data       = persona.apellido_dos
        form.telefono.data           = persona.telefono
        form.correo.data             = persona.correo

        form.calle.data              = direccion.calle
        form.colonia.data            = direccion.colonia
        form.codigo_postal.data      = direccion.codigo_postal
        form.num_exterior.data       = direccion.num_exterior
        form.num_interior.data       = direccion.num_interior
        form.fk_estado.data          = direccion.fk_estado
        form.fk_municipio.data       = direccion.fk_municipio

        form.num_empleado.data       = empleado.num_empleado
        form.fk_puesto.data          = empleado.fk_puesto
        form.fecha_contratacion.data = empleado.fecha_contratacion
        form.estatus.data            = empleado.estatus

    # GUARDAR EN POST
    if form.validate_on_submit():
        
        # ==========================
# VALIDAR CAMPOS OBLIGATORIOS
# ==========================

        if not form.correo.data:
            flash("El correo es obligatorio.", "danger")
            return redirect(request.url)

        if not form.telefono.data:
            flash("El teléfono es obligatorio.", "danger")
            return redirect(request.url)
        uid = usuario_sesion_id()

        # ==========================
        # VALIDACIONES EDITAR
        # ==========================

        # CORREO (excluyendo el actual)
        if form.correo.data:
            existe_correo = Persona.query.filter(
                Persona.correo == form.correo.data,
                Persona.id != persona.id
            ).first()

            if existe_correo:
                flash("El correo ya está en uso.", "danger")
                return redirect(request.url)


        # TELEFONO (excluyendo el actual)
        if form.telefono.data:
            existe_tel = Persona.query.filter(
                Persona.telefono == form.telefono.data,
                Persona.id != persona.id
            ).first()

            if existe_tel:
                flash("El teléfono ya está en uso.", "danger")
                return redirect(request.url)


        persona.nombre             = form.nombre.data
        persona.apellido_uno       = form.apellido_uno.data
        persona.apellido_dos       = form.apellido_dos.data
        persona.telefono           = form.telefono.data
        persona.correo             = form.correo.data
        persona.usuario_movimiento = uid

        direccion.calle              = form.calle.data
        direccion.colonia            = form.colonia.data
        direccion.codigo_postal      = form.codigo_postal.data
        direccion.num_exterior       = form.num_exterior.data
        direccion.num_interior       = form.num_interior.data
        direccion.fk_estado          = form.fk_estado.data
        direccion.fk_municipio       = form.fk_municipio.data
        direccion.usuario_movimiento = uid

        empleado.num_empleado          = form.num_empleado.data
        empleado.fk_puesto             = form.fk_puesto.data
        empleado.fecha_contratacion    = form.fecha_contratacion.data
        empleado.estatus               = form.estatus.data
        empleado.usuario_movimiento    = uid

        # FOTO → se guarda en Persona
        archivo = form.imagen.data
        if archivo and hasattr(archivo, 'read') and archivo.filename:
            contenido = archivo.read()
            if contenido:
                persona.foto = f"data:{archivo.mimetype};base64,{base64.b64encode(contenido).decode('utf-8')}"

        db.session.commit()

        flash("Empleado actualizado correctamente.", "success")
        return redirect(url_for("empleados.inicio"))
    if persona and persona.foto:
            if isinstance(persona.foto, bytes):
                persona.foto = persona.foto.decode('utf-8')
    return render_template(
        "empleados/editar.html",
        form=form,
        empleado=empleado,
        module=MODULE,
        action_label="Editar"
    )

# ==========================
# ELIMINAR
# ==========================
@empleados.route("/eliminar/<int:id>")
def eliminar(id):

    empleado  = Empleado.query.get_or_404(id)
    if (
        Compra.query.filter_by(fk_empleado=empleado.id).count() > 0
        or Pedido.query.filter_by(fk_empleado=empleado.id).count() > 0
        or Venta.query.filter_by(fk_empleado=empleado.id).count() > 0
        or Produccion.query.filter_by(fk_empleado=empleado.id).count() > 0
        or SolicitudProduccion.query.filter_by(fk_empleado=empleado.id).count() > 0
        or Caja.query.filter_by(fk_empleado_apertura=empleado.id).count() > 0
    ):
        flash("No se puede eliminar el empleado porque tiene registros relacionados (compras, pedidos, ventas, producción o caja).", "danger")
        return redirect(url_for("empleados.inicio"))

    persona   = empleado.persona
    if not persona:
        flash("El empleado no tiene una persona asociada. No se puede eliminar correctamente.", "danger")
        return redirect(url_for("empleados.inicio"))

    usuario   = persona.usuario if persona else None

    uid = usuario_sesion_id()

    empleado.estatus = "INACTIVO"
    empleado.usuario_movimiento = uid

    persona.estatus = "INACTIVO"
    persona.usuario_movimiento = uid

    if usuario:
        usuario.estatus = "INACTIVO"
        usuario.usuario_movimiento = uid

    db.session.commit()

    flash("Empleado dado de baja correctamente.", "warning")
    return redirect(url_for("empleados.inicio"))


# ==========================
# MUNICIPIOS (AJAX)
# ==========================
@empleados.route("/municipios/<int:estado_id>")
def municipios_por_estado(estado_id):

    municipios = Municipio.query \
        .filter_by(fk_estado=estado_id) \
        .order_by(Municipio.nombre) \
        .all()

    return jsonify({
        "municipios": [{"id": m.id, "nombre": m.nombre} for m in municipios]
    })