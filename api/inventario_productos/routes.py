import base64

from flask import render_template, request, redirect, url_for, flash
from api.common import create_module_blueprint
from models import db, InventarioProducto, Producto, Sucursal, InventarioProductoMovimiento
from forms import (
    InventarioProductoForm, EditInventarioProductoForm, 
    BuscarInventarioForm, ConfirmarEliminacionInventarioForm
)
from datetime import datetime

inventario_productos = create_module_blueprint("inventario-productos")


def get_user_id():
    """Obtener el ID del usuario actual (por ahora retorna 1)"""
    # TODO: Implementar autenticación real
    return 1


@inventario_productos.route('/', methods=['GET'])
def inicio():
    """Listar todos los registros de inventario activos"""
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '', type=str)
    estado_filter = request.args.get('estado', '', type=str)

    form = ConfirmarEliminacionInventarioForm()

    query = InventarioProducto.query.filter_by(estatus='ACTIVO')
    
    # FILTRO POR PRODUCTO
    if buscar:
        query = query.join(Producto).filter(Producto.nombre.ilike(f'%{buscar}%'))
    
    # FILTRO POR ESTADO
    if estado_filter in ['EXISTENCIA', 'AGOTADO']:
        query = query.filter_by(estado=estado_filter)
    
    # PAGINACIÓN
    inventarios_list = query.paginate(page=page, per_page=12)
    
    inventarios_data = []

    # LOOP CORRECTO
    import base64

    for inv in inventarios_list.items:

        dias_restantes = None
        por_caducar = False
        caducado = False

        if inv.fecha_caducidad:
            dias_restantes = (inv.fecha_caducidad - datetime.now()).days

            if dias_restantes < 0 and inv.cantidad_producto > 0:
                caducado = True
            elif dias_restantes <= 3:
                por_caducar = True 

        # BADGES
        if inv.estado == 'AGOTADO':
            estado_color = 'bg-red-500 text-white'
            estado_display = 'Agotado'

        elif caducado:
            estado_color = 'bg-red-500 text-white'
            estado_display = f'Caducado ({abs(dias_restantes)} días vencido)'

        elif por_caducar:
            estado_color = 'bg-yellow-400 text-black'
            estado_display = f'Por caducar ({dias_restantes} días)'

        else:
            estado_color = 'bg-green-500 text-white'
            estado_display = 'Disponible'

        producto = inv.producto

        inventarios_data.append({
            'id': inv.id,
            'producto_id': inv.fk_producto,
            'producto_nombre': producto.nombre if producto else 'N/A',
            'categoria': producto.categoria.nombre if producto and producto.categoria else 'N/A',
            'cantidad': int(inv.cantidad_producto),
            'fecha_caducidad': inv.fecha_caducidad.strftime('%Y-%m-%d'),
            'estado_display': estado_display,
            'estado_color': estado_color,

            # FOTO
            'imagen': f"data:image/png;base64,{base64.b64encode(producto.foto).decode('utf-8')}"
            if producto and producto.foto
            else url_for('static', filename='img/placeholder.png')
        })

    # ALERTA GLOBAL (AQUÍ VA)
    hay_alerta = any("caducar" in inv["estado_display"] for inv in inventarios_data)
    hay_alerta_roja = any("Caducado" in inv["estado_display"] for inv in inventarios_data)

    # FORM DE BÚSQUEDA (si lo usas)
    buscar_form = BuscarInventarioForm(request.args)

    return render_template(
        'inventario-productos/inicio.html',
        inventarios=inventarios_data,
        pagination=inventarios_list,
        form=form,
        hay_alerta=hay_alerta,
        hay_alerta_roja=hay_alerta_roja
    )

@inventario_productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    inventario = InventarioProducto.query.get_or_404(id)
    form = EditInventarioProductoForm()

    if form.validate_on_submit():
        try:
            cantidad_restar = form.cantidad_producto.data
            cantidad_actual = inventario.cantidad_producto
            tipo = form.tipo_movimiento.data
            obs = form.observaciones.data

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

            # ACTUALIZAR INVENTARIO
            inventario.cantidad_producto = nueva_cantidad
            inventario.estado = 'EXISTENCIA' if nueva_cantidad > 0 else 'AGOTADO'
            inventario.usuario_movimiento = get_user_id()

            # GUARDAR MOVIMIENTO
            movimiento = InventarioProductoMovimiento(
            fk_inventario_producto=id,
            cantidad_anterior=cantidad_actual,
            cantidad_nueva=nueva_cantidad,
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
        inventario={"producto_nombre": inventario.producto.nombre,"cantidad_actual": inventario.cantidad_producto}
    )

@inventario_productos.route('/eliminar/<int:id>', methods=['GET', 'POST'])
def eliminar(id):
    """Eliminar (desactivar) un registro de inventario"""
    inventario = InventarioProducto.query.get_or_404(id)
    form = ConfirmarEliminacionInventarioForm()
    
    if form.validate_on_submit():
        try:
            #  VALIDACIÓN IMPORTANTE
            if inventario.cantidad_producto > 0:
                flash('No puedes desactivar un producto con existencia en inventario', 'error')
                return redirect(url_for('inventario_productos.inicio'))

            #  SI ESTÁ EN 0, SÍ PERMITE
            inventario.estatus = 'INACTIVO'
            inventario.usuario_movimiento = get_user_id()

            db.session.commit()

            flash('Inventario desactivado correctamente', 'success')
            return redirect(url_for('inventario_productos.inicio'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al desactivar el inventario: {str(e)}', 'error')
            return redirect(url_for('inventario_productos.inicio'))
        
    data = {
        'id': inventario.id,
        'producto_nombre': inventario.producto.nombre if inventario.producto else 'N/A',
        'sucursal_nombre': inventario.sucursal.nombre if inventario.sucursal else 'N/A',
    }
    
    return render_template('inventario-productos/eliminar.html', form=form, inventario=data)


@inventario_productos.errorhandler(404)
def not_found(error):
    """Manejar errores 404 en el módulo"""
    flash('El registro de inventario no fue encontrado', 'error')
    return redirect(url_for('inventario_productos.inicio')), 404
