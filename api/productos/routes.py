import base64

from flask import render_template, request, redirect, url_for, flash
from utils.modules import create_module_blueprint
from models import (
    PedidoDetalle,
    ProduccionDetalle,
    Producto,
    Receta,
    SolicitudProduccion,
    VentaDetalle,
    db,
    CategoriaProducto,
)
from forms import ProductoForm, EditProductoForm, BuscarProductoForm, ConfirmarEliminacionProductoForm
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from models import InventarioProducto, InventarioProductoMovimiento
from utils.session import get_current_user_id

productos = create_module_blueprint("productos")

MODULE = {
    "name": "Productos",
    "slug": "productos",
    "description": "Gestión de productos del sistema",
}


def get_user_id():
    return get_current_user_id()


def _read_image_base64(file_storage):
    if not file_storage:
        return None
    raw = file_storage.read()
    if not raw:
        return None
    return base64.b64encode(raw).decode("utf-8")


def _format_image(foto):
    if not foto:
        return url_for("static", filename="img/defecto.jpg")
    if isinstance(foto, (bytes, bytearray)):
        encoded = base64.b64encode(foto).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    if isinstance(foto, str):
        if foto.startswith("data:image"):
            return foto
        return f"data:image/png;base64,{foto}"
    return url_for("static", filename="img/defecto.jpg")


@productos.route('/', methods=['GET'])
def inicio():
    page = request.args.get('page', 1, type=int)
    buscar = request.args.get('buscar', '', type=str)
    categoria_id = request.args.get('categoria', 0, type=int)

    query = Producto.query.filter_by(estatus='ACTIVO')

    # Filtrar por búsqueda
    if buscar:
        query = query.filter(Producto.nombre.ilike(f'%{buscar}%'))

    # Filtrar por categoría
    if categoria_id > 0:
        query = query.filter_by(fk_categoria=categoria_id)

    # Paginar resultados
    productos_list = query.paginate(page=page, per_page=12)

    # Construir lista de datos para el template
    productos_data = []
    for producto in productos_list.items:

        # Verificar si el producto tiene inventario activo con existencia
        tiene_inventario = InventarioProducto.query.filter(
            InventarioProducto.fk_producto == producto.id,
            InventarioProducto.estatus == 'ACTIVO',
            InventarioProducto.cantidad_producto > 0
        ).first() is not None

        productos_data.append({
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'costo': float(producto.costo_produccion),
            'categoria': producto.categoria.nombre,
            'imagen': _format_image(producto.foto),
            'tiene_inventario': tiene_inventario
        })

    # Obtener categorías para el filtro
    categorias = CategoriaProducto.query.filter_by(estatus='ACTIVO').all()
    form_eliminar = ConfirmarEliminacionProductoForm()

    return render_template(
        'productos/inicio.html',
        module=MODULE,
        productos=productos_data,
        categorias=categorias,
        buscar=buscar,
        categoria_id=categoria_id,
        pagination=productos_list,
        page=page,
        form_eliminar=form_eliminar
    )


@productos.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if CategoriaProducto.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay categorías de productos registradas. Primero crea una categoría para poder dar de alta un producto.", "warning")
        return redirect(url_for("categorias_productos.inicio"))

    form = ProductoForm()

    if form.validate_on_submit():
        print("FORM VALIDO")

        try:
            # Validar categoría activa
            categoria = CategoriaProducto.query.get(form.fk_categoria.data)
            if not categoria or categoria.estatus != 'ACTIVO':
                flash('Categoría inválida o inactiva', 'error')
                return redirect(url_for('productos.agregar'))

            # Leer y validar imagen subida
            if form.foto.data:
                try:
                    file = form.foto.data
                    file.seek(0, os.SEEK_END)
                    size = file.tell()
                    file.seek(0)

                    if size > 2 * 1024 * 1024:
                        flash("La imagen es muy grande (máx 2MB)", "error")
                        return redirect(url_for('productos.agregar'))

                    foto = _read_image_base64(file)
                except Exception as e:
                    flash(f'Error al procesar la imagen: {str(e)}', 'error')
                    return redirect(url_for('productos.agregar'))
            else:
                foto = None

            # Crear nuevo producto
            nuevo_producto = Producto(
                fk_categoria=form.fk_categoria.data,
                nombre=form.nombre.data,
                precio=form.precio.data,
                costo_produccion=form.costo_produccion.data or 0,
                foto=foto,
                estatus='ACTIVO',
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id()
            )

            db.session.add(nuevo_producto)
            db.session.commit()

            flash(f'Producto "{nuevo_producto.nombre}" creado exitosamente', 'success')
            return redirect(url_for('productos.inicio'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el producto: {str(e)}', 'error')
            return redirect(url_for('productos.agregar'))

    return render_template('productos/agregar.html', form=form, module=MODULE)


@productos.route('/detalle/<int:id>', methods=['GET'])
def detalle(id):
    producto = Producto.query.get_or_404(id)

    if producto.estatus != 'ACTIVO':
        flash('El producto no está disponible', 'warning')
        return redirect(url_for('productos.inicio'))

    producto_data = {
        'id': producto.id,
        'nombre': producto.nombre,
        'precio': float(producto.precio),
        'costo': float(producto.costo_produccion),
        'categoria': producto.categoria.nombre,
        'imagen': _format_image(producto.foto)
    }

    return render_template('productos/detalle.html', producto=producto_data, module=MODULE)


@productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    producto = Producto.query.get_or_404(id)

    if producto.estatus != 'ACTIVO':
        flash('No puedes editar un producto inactivo', 'warning')
        return redirect(url_for('productos.inicio'))

    form = EditProductoForm()
    form.producto_id = id

    if form.validate_on_submit():
        try:
            # Validar que la categoría existe y está activa
            categoria = CategoriaProducto.query.get(form.fk_categoria.data)
            if not categoria or categoria.estatus != 'ACTIVO':
                flash('Categoría inválida o inactiva', 'error')
                return redirect(url_for('productos.editar', id=id))

            # Actualizar datos
            producto.nombre = form.nombre.data
            producto.fk_categoria = form.fk_categoria.data
            producto.precio = form.precio.data

            if form.foto.data:
                try:
                    producto.foto = _read_image_base64(form.foto.data)
                except Exception as e:
                    flash(f'Error al procesar la imagen: {str(e)}', 'error')
                    return redirect(url_for('productos.editar', id=id))

            # El costo se actualiza automáticamente desde recetas
            producto.usuario_movimiento = get_user_id()
            producto.fecha_movimiento = datetime.utcnow()

            db.session.commit()

            flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
            return redirect(url_for('productos.inicio'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
            return redirect(url_for('productos.editar', id=id))

    elif request.method == 'GET':
        # Pre-cargar datos del formulario
        form.nombre.data = producto.nombre
        form.fk_categoria.data = producto.fk_categoria
        form.precio.data = producto.precio
        form.costo_produccion.data = producto.costo_produccion

    producto_data = {
        'id': producto.id,
        'nombre': producto.nombre,
        'precio': float(producto.precio),
        'costo': float(producto.costo_produccion),
        'categoria': producto.categoria.nombre,
        'imagen': _format_image(producto.foto)
    }

    return render_template(
        'productos/editar.html',
        form=form,
        producto=producto_data,
        imagen=producto_data['imagen'],
        module=MODULE,
    )


@productos.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    form = ConfirmarEliminacionProductoForm()

    if form.validate_on_submit():
        try:
            if (
                PedidoDetalle.query.filter_by(fk_producto=producto.id).count() > 0
                or VentaDetalle.query.filter_by(fk_producto=producto.id).count() > 0
                or Receta.query.filter_by(fk_producto=producto.id).count() > 0
                or SolicitudProduccion.query.filter_by(fk_producto=producto.id).count() > 0
                or ProduccionDetalle.query.filter_by(fk_producto=producto.id).count() > 0
            ):
                flash("No se puede eliminar el producto porque tiene registros relacionados (pedidos, ventas, recetas o producción).", "error")
                return redirect(url_for("productos.inicio"))

            # Bloquear si tiene inventario activo
            inventario = InventarioProducto.query.filter_by(
                fk_producto=producto.id,
                estatus='ACTIVO'
            ).first()

            if inventario:
                flash('No puedes eliminar este producto porque tiene inventario activo', 'error')
                return redirect(url_for('productos.inicio'))

            # Soft delete
            producto.estatus = 'INACTIVO'
            producto.usuario_movimiento = get_user_id()
            producto.fecha_movimiento = datetime.utcnow()

            db.session.commit()

            flash(f'Producto "{producto.nombre}" eliminado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar el producto: {str(e)}', 'error')
    else:
        flash("Error CSRF o formulario inválido", "error")

    return redirect(url_for('productos.inicio'))


@productos.errorhandler(404)
def not_found(error):
    flash('El producto solicitado no existe', 'error')
    return redirect(url_for('productos.inicio')), 404
