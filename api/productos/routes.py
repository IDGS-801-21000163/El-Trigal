import base64
import binascii
from decimal import Decimal

from flask import render_template, request, redirect, url_for, flash
from utils.modules import create_module_blueprint
from models import (
    PedidoDetalle,
    ProduccionDetalle,
    Producto,
    Receta,
    RecetaDetalle,
    SolicitudProduccion,
    VentaDetalle,
    db,
    CategoriaProducto,
    CompraDetalle,
    UnidadMedida,
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


def _read_image_bytes(file_storage):
    if not file_storage:
        return None
    # Compat: si por alguna razón llega un base64 string (datos legacy), convertir a bytes.
    if isinstance(file_storage, str):
        return _coerce_blob(file_storage)
    try:
        file_storage.stream.seek(0)
    except Exception:
        try:
            file_storage.seek(0)
        except Exception:
            pass
    raw = file_storage.read()
    if not raw:
        return None
    return raw


def _coerce_blob(value):
    """Asegura bytes para columnas BLOB, aceptando strings base64 legacy."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.startswith("data:") and "base64," in s:
            s = s.split("base64,", 1)[1]
        try:
            return base64.b64decode(s, validate=False)
        except (binascii.Error, ValueError):
            return None
    return None


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


def _factor_unidad_base(unidad: UnidadMedida | None) -> Decimal:
    if not unidad:
        return Decimal("1")
    factor = Decimal(str(unidad.factor_conversion or 1))
    actual = unidad.unidad_base
    while actual:
        factor *= Decimal(str(actual.factor_conversion or 1))
        actual = actual.unidad_base
    return factor


def _calcular_costo_desde_receta(producto_id: int) -> Decimal | None:
    receta = Receta.query.filter_by(fk_producto=producto_id, estatus="ACTIVO").first()
    if not receta:
        return None

    total = Decimal("0")
    detalles = RecetaDetalle.query.filter_by(fk_receta=receta.id, estatus="ACTIVO").all()
    if not detalles:
        return Decimal("0")

    for det in detalles:
        compra = (
            CompraDetalle.query.filter_by(fk_insumo=det.fk_insumo, estatus="ACTIVO")
            .order_by(CompraDetalle.id.desc())
            .first()
        )
        if not compra or not compra.unidad:
            continue

        factor_compra = _factor_unidad_base(compra.unidad)
        if factor_compra <= 0:
            continue

        costo_compra = Decimal(str(compra.costo or 0))
        costo_base = costo_compra / factor_compra

        unidad_receta = UnidadMedida.query.get(det.fk_unidad) if det.fk_unidad else None
        factor_receta = _factor_unidad_base(unidad_receta)
        if factor_receta <= 0:
            continue

        cantidad = Decimal(str(det.cantidad_insumo or 0))
        cantidad_base = cantidad * factor_receta
        total += cantidad_base * costo_base

    return total.quantize(Decimal("0.01"))


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
        # Refrescar costo si existe receta y el costo quedó en 0 (legacy).
        if float(producto.costo_produccion or 0) <= 0:
            costo_calc = _calcular_costo_desde_receta(producto.id)
            if costo_calc is not None and costo_calc > 0:
                producto.costo_produccion = costo_calc
                producto.usuario_movimiento = get_user_id()
                db.session.add(producto)

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

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

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
        try:
            # Validar categoría activa
            categoria = CategoriaProducto.query.get(form.fk_categoria.data)
            if not categoria or categoria.estatus != 'ACTIVO':
                flash('Categoría inválida o inactiva', 'error')
                return redirect(url_for('productos.agregar'))

            # Leer y validar imagen subida
            foto = None
            if form.foto.data:
                raw = _read_image_bytes(form.foto.data)
                if raw:
                    if len(raw) > 2 * 1024 * 1024:
                        flash("La imagen es muy grande (máx 2MB)", "error")
                        return render_template('productos/agregar.html', form=form, module=MODULE)
                    foto = _coerce_blob(raw) or raw

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

        except Exception:
            db.session.rollback()
            flash('Error al crear el producto. Verifica los datos e intenta de nuevo.', 'error')
            return render_template('productos/agregar.html', form=form, module=MODULE)

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
                    raw = _read_image_bytes(form.foto.data)
                    if raw and len(raw) > 2 * 1024 * 1024:
                        flash("La imagen es muy grande (máx 2MB)", "error")
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
                    producto.foto = _coerce_blob(raw) or raw
                except Exception as e:
                    flash(f'Error al procesar la imagen: {str(e)}', 'error')
                    return redirect(url_for('productos.editar', id=id))

            # El costo se actualiza automáticamente desde recetas
            producto.usuario_movimiento = get_user_id()
            producto.fecha_movimiento = datetime.utcnow()

            db.session.commit()

            flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
            return redirect(url_for('productos.inicio'))

        except Exception:
            db.session.rollback()
            flash('Error al actualizar el producto. Verifica los datos e intenta de nuevo.', 'error')
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
