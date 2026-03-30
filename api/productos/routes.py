import base64

from flask import render_template, request, redirect, url_for, flash
from api.common import create_module_blueprint
from models import db, Producto, CategoriaProducto
from forms import ProductoForm, EditProductoForm, BuscarProductoForm, ConfirmarEliminacionProductoForm
from werkzeug.utils import secure_filename
import os
from datetime import datetime

productos = create_module_blueprint("productos")


def get_user_id():
    """Obtener el ID del usuario actual (por ahora retorna 1)"""
    # TODO: Implementar autenticación real
    return 1


@productos.route('/', methods=['GET'])
def inicio():
    """Listar todos los productos activos"""
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
    
    # Preparar datos para el template
    productos_data = []
    for producto in productos_list.items:
        productos_data.append({
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'costo': float(producto.costo_produccion),
            'categoria': producto.categoria.nombre,
            'imagen': f"data:image/png;base64,{base64.b64encode(producto.foto).decode('utf-8')}" if producto.foto else url_for('static', filename='img/placeholder.png')    
            }
        )
    
    # Obtener categorías para el filtro
    categorias = CategoriaProducto.query.filter_by(estatus='ACTIVO').all()
    
    return render_template(
        'productos/inicio.html',
        productos=productos_data,
        categorias=categorias,
        buscar=buscar,
        categoria_id=categoria_id,
        pagination=productos_list,
        page=page
    )


@productos.route('/agregar', methods=['GET', 'POST'])
def agregar():
    form = ProductoForm()

    if form.validate_on_submit():
        print("FORM VALIDO")

        try:
            # Validar categoría
            categoria = CategoriaProducto.query.get(form.fk_categoria.data)
            if not categoria or categoria.estatus != 'ACTIVO':
                flash('Categoría inválida o inactiva', 'error')
                return redirect(url_for('productos.agregar'))

            
            # Manejar la carga de imagen
            foto = None
            if form.foto.data:
                
                try:
                    file = form.foto.data
                    file.seek(0, os.SEEK_END)
                    size = file.tell()
                    file.seek(0)

                    if size > 2 * 1024 * 1024:
                        flash("La imagen es muy grande (máx 2MB)", "error")
                    filename = secure_filename(file.filename)
                    # Guardar archivo temporalmente para luego convertir a bytes
                    foto = file.read()
                except Exception as e:
                    flash(f'Error al procesar la imagen: {str(e)}', 'error')
                    return redirect(url_for('productos.agregar'))
            
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
    
    return render_template('productos/agregar.html', form=form)


@productos.route('/detalle/<int:id>', methods=['GET'])
def detalle(id):
    """Ver detalle de un producto"""
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
        'imagen': f"data:image/png;base64,{base64.b64encode(producto.foto).decode('utf-8')}" if producto.foto else url_for('static', filename='img/placeholder.png')    }
    
    return render_template('productos/detalle.html', producto=producto_data)


@productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Editar un producto existente"""
    producto = Producto.query.get_or_404(id)
    
    if producto.estatus != 'ACTIVO':
        flash('No puedes editar un producto inactivo', 'warning')
        return redirect(url_for('productos.inicio'))
    
    form = EditProductoForm()
    form.producto_id = id
    
    if form.validate_on_submit():
        try:
            # Validar que la categoría existe
            categoria = CategoriaProducto.query.get(form.fk_categoria.data)
            if not categoria or categoria.estatus != 'ACTIVO':
                flash('Categoría inválida o inactiva', 'error')
                return redirect(url_for('productos.editar', id=id))
            
            # Actualizar datos
            producto.nombre = form.nombre.data
            producto.fk_categoria = form.fk_categoria.data
            producto.precio = form.precio.data
            
            # Manejar la carga de nueva imagen
            if form.foto.data:
                try:
                    file = form.foto.data
                    producto.foto = file.read()
                except Exception as e:
                    flash(f'Error al procesar la imagen: {str(e)}', 'error')
                    return redirect(url_for('productos.editar', id=id))
            
            # No permitir edición del costo (RNF)
            # El costo se actualiza automáticamente desde recetas
            
            producto.usuario_movimiento = get_user_id()
            producto.fecha_movimiento = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
            return redirect(url_for('productos.detalle', id=producto.id))
            
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
        'imagen': f"data:image/png;base64,{base64.b64encode(producto.foto).decode('utf-8')}" if producto.foto else url_for('static', filename='img/placeholder.png')    }
    
    return render_template('productos/editar.html', form=form, producto=producto_data)


@productos.route('/eliminar/<int:id>', methods=['GET', 'POST'])
def eliminar(id):
    """Desactivar un producto (soft delete)"""
    producto = Producto.query.get_or_404(id)
    
    if producto.estatus != 'ACTIVO':
        flash('El producto ya está inactivo', 'info')
        return redirect(url_for('productos.inicio'))
    
    form = ConfirmarEliminacionProductoForm()
    
    if form.validate_on_submit():
        if form.confirm.data:
            try:
                # Realizar soft delete
                producto.estatus = 'INACTIVO'
                producto.usuario_movimiento = get_user_id()
                producto.fecha_movimiento = datetime.utcnow()
                
                db.session.commit()
                
                flash(f'Producto "{producto.nombre}" desactivado exitosamente', 'success')
                return redirect(url_for('productos.inicio'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al desactivar el producto: {str(e)}', 'error')
                return redirect(url_for('productos.eliminar', id=id))
        
        elif form.cancel.data:
            return redirect(url_for('productos.inicio'))
    
    producto_data = {
        'id': producto.id,
        'nombre': producto.nombre,
        'precio': float(producto.precio),
        'costo': float(producto.costo_produccion),
        'categoria': producto.categoria.nombre,
    }
    
    return render_template('productos/eliminar.html', form=form, producto=producto_data)


@productos.errorhandler(404)
def not_found(error):
    """Manejar errores 404"""
    flash('El producto solicitado no existe', 'error')
    return redirect(url_for('productos.inicio')), 404
