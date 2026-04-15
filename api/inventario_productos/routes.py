import base64

from flask import render_template, request, redirect, url_for, flash
from utils.modules import create_module_blueprint
from models import db, InventarioProducto, Producto, Sucursal, InventarioProductoMovimiento
from sqlalchemy import func
from forms import (
    InventarioProductoForm, EditInventarioProductoForm,
    BuscarInventarioForm, ConfirmarEliminacionInventarioForm
)
from datetime import datetime
from utils.session import get_current_user_id

inventario_productos = create_module_blueprint("inventario-productos")


def get_user_id():
    return get_current_user_id()


def _format_image(foto):
    if not foto:
        return url_for('static', filename='img/defecto.jpg')
    if isinstance(foto, (bytes, bytearray)):
        encoded = base64.b64encode(foto).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/png;base64,{foto}"
    return url_for('static', filename='img/defecto.jpg')


@inventario_productos.route('/', methods=['GET'])
def inicio():
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '', type=str)
    estado_filter = request.args.get('estado', '', type=str)
    lote_filter = request.args.get('lote', 'vigente', type=str)

    form = ConfirmarEliminacionInventarioForm()

    query = InventarioProducto.query.filter_by(estatus='ACTIVO')
    today = datetime.now().date()

    if lote_filter == "vigente":
        query = query.filter(func.date(InventarioProducto.fecha_caducidad) >= today)
    elif lote_filter == "caducado":
        query = query.filter(func.date(InventarioProducto.fecha_caducidad) < today)

    # Filtrar por nombre de producto
    if buscar:
        query = query.join(Producto).filter(Producto.nombre.ilike(f'%{buscar}%'))

    # Filtrar por "estado" derivado de existencia (la tabla no tiene columna `estado`)
    if estado_filter == 'EXISTENCIA':
        query = query.filter(InventarioProducto.cantidad_producto > 0)
    elif estado_filter == 'AGOTADO':
        query = query.filter(InventarioProducto.cantidad_producto <= 0)

    # Paginar resultados
    inventarios_list = query.paginate(page=page, per_page=12)

    inventarios_data = []

    for inv in inventarios_list.items:
        try:
            cantidad_val = float(inv.cantidad_producto or 0)
        except (TypeError, ValueError):
            cantidad_val = 0

        dias_restantes = None
        por_caducar = False
        caducado = False

        # Calcular días restantes para caducidad
        if inv.fecha_caducidad:
            dias_restantes = (inv.fecha_caducidad.date() - today).days

            if dias_restantes < 0 and inv.cantidad_producto > 0:
                caducado = True
            elif dias_restantes <= 3:
                por_caducar = True

        # Determinar badge de estado (derivado)
        if cantidad_val <= 0:
            estado_clase = 'danger'
            estado_display = 'Agotado'

        elif caducado:
            estado_clase = 'danger'
            estado_display = f'Caducado ({abs(dias_restantes)} días vencido)'

        elif por_caducar:
            estado_clase = 'warning'
            estado_display = f'Por caducar ({dias_restantes} días)'

        else:
            estado_clase = 'active'
            estado_display = 'Disponible'

        producto = inv.producto

        inventarios_data.append({
            'id': inv.id,
            'producto_id': inv.fk_producto,
            'producto_nombre': producto.nombre if producto else 'N/A',
            'categoria': producto.categoria.nombre if producto and producto.categoria else 'N/A',
            'cantidad': int(cantidad_val),
            'fecha_caducidad': inv.fecha_caducidad.strftime('%Y-%m-%d'),
            'estado_display': estado_display,
            'estado_clase': estado_clase,
            'imagen': _format_image(producto.foto if producto else None)
        })

    # Alertas globales de caducidad
    hay_alerta = any("caducar" in inv["estado_display"] for inv in inventarios_data)
    hay_alerta_roja = any("Caducado" in inv["estado_display"] for inv in inventarios_data)

    buscar_form = BuscarInventarioForm(request.args)

    return render_template(
        'inventario-productos/inicio.html',
        inventarios=inventarios_data,
        pagination=inventarios_list,
        form=form,
        hay_alerta=hay_alerta,
        hay_alerta_roja=hay_alerta_roja,
        buscar=buscar,
        estado=estado_filter,
        lote=lote_filter,
    )


@inventario_productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    inventario = InventarioProducto.query.get_or_404(id)
    form = EditInventarioProductoForm()

    if form.validate_on_submit():
        try:
            cantidad_restar = form.cantidad_producto.data
            cantidad_actual = inventario.cantidad_producto
            tipo = form.tipo_movimiento.data or "AUDITORIA"
            obs = form.observaciones.data

            # Construir motivo del movimiento
            if obs:
                motivo = f"{tipo} - {obs}"
            else:
                motivo = tipo

            if cantidad_restar is None or cantidad_restar <= 0:
                flash('La cantidad a restar debe ser mayor a 0', 'error')
                return redirect(url_for('inventario_productos.editar', id=id))

            if cantidad_restar > cantidad_actual:
                flash('No puedes restar más de lo disponible en inventario', 'error')
                return redirect(url_for('inventario_productos.editar', id=id))

            nueva_cantidad = cantidad_actual - cantidad_restar

            # Actualizar inventario
            inventario.cantidad_producto = nueva_cantidad
            inventario.usuario_movimiento = get_user_id()

            # Registrar movimiento
            movimiento = InventarioProductoMovimiento(
                fk_inventario_producto=id,
                tipo_movimiento=tipo,
                cantidad_anterior=cantidad_actual,
                cantidad_nueva=nueva_cantidad,
                diferencia=nueva_cantidad - cantidad_actual,
                motivo=motivo,
                usuario_movimiento=get_user_id()
            )

            db.session.add(movimiento)
            db.session.commit()

            flash('Inventario actualizado correctamente', 'success')
            return redirect(url_for('inventario_productos.inicio'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')

    form.cantidad_producto.data = inventario.cantidad_producto

    return render_template(
        'inventario-productos/editar.html',
        form=form,
        inventario={
            "producto_nombre": inventario.producto.nombre,
            "cantidad_actual": inventario.cantidad_producto
        }
    )


@inventario_productos.route('/eliminar/<int:id>', methods=['GET', 'POST'])
def eliminar(id):
    inventario = InventarioProducto.query.get_or_404(id)
    form = ConfirmarEliminacionInventarioForm()

    if form.validate_on_submit():
        try:
            # Bloquear si aún tiene existencia
            if inventario.cantidad_producto > 0:
                flash('No puedes eliminar un producto con existencia en inventario', 'error')
                return redirect(url_for('inventario_productos.inicio'))

            # Soft delete
            inventario.estatus = 'INACTIVO'
            inventario.usuario_movimiento = get_user_id()

            db.session.commit()

            flash('Inventario eliminado correctamente', 'success')
            return redirect(url_for('inventario_productos.inicio'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar el inventario: {str(e)}', 'error')
            return redirect(url_for('inventario_productos.inicio'))

    data = {
        'id': inventario.id,
        'producto_nombre': inventario.producto.nombre if inventario.producto else 'N/A',
        'sucursal_nombre': inventario.sucursal.nombre if inventario.sucursal else 'N/A',
    }

    return render_template('inventario-productos/eliminar.html', form=form, inventario=data)


@inventario_productos.errorhandler(404)
def not_found(error):
    flash('El registro de inventario no fue encontrado', 'error')
    return redirect(url_for('inventario_productos.inicio')), 404


@inventario_productos.route('/merma/<int:id>', methods=['POST'])
def marcar_merma(id):
    inventario = InventarioProducto.query.get_or_404(id)

    if inventario.es_merma:
        flash("Este lote ya está marcado como merma.", "warning")
        return redirect(url_for("inventario_productos.inicio"))

    inventario.es_merma = True
    inventario.usuario_movimiento = get_user_id()
    db.session.commit()

    flash("Lote marcado como merma.", "success")
    return redirect(url_for("inventario_productos.inicio", lote="caducado"))
