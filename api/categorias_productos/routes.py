from flask import render_template, request, redirect, url_for, flash
from api.common import create_module_blueprint
from models import db, CategoriaProducto
from forms import CategoriaProductoForm, EditCategoriaProductoForm, BuscarCategoriaForm, ConfirmarEliminacionCategoriaForm
from datetime import datetime
from models import db, CategoriaProducto, Producto
from models import Producto  
import base64

categorias_productos = create_module_blueprint("categorias-productos")


def get_user_id():
    """Obtener el ID del usuario actual (por ahora retorna 1)"""
    # TODO: Implementar autenticación real
    return 1


@categorias_productos.route('/inicio', methods=['GET'])
def inicio():
    """Listar todas las categorías activas"""
    buscar = request.args.get('buscar', '', type=str)
    
    query = CategoriaProducto.query.filter_by(estatus='ACTIVO')
    
    # Filtrar por búsqueda
    if buscar:
        query = query.filter(CategoriaProducto.nombre.ilike(f'%{buscar}%'))
    
    categorias_list = query.all() 

    categorias_data = []
    for categoria in categorias_list:
        categorias_data.append({
            'id': categoria.id,
            'nombre': categoria.nombre,
            'descripcion': categoria.descripcion,
            'foto': obtener_imagen(categoria.foto)
        })
    
    return render_template(
        'categorias-productos/inicio.html',
        categorias=categorias_data,
        buscar=buscar
    )


@categorias_productos.route('/agregar', methods=['GET', 'POST'])
def agregar():
    """Crear una nueva categoría"""
    form = CategoriaProductoForm()
    
    if form.validate_on_submit():
        try:
            if form.validate_on_submit():
                nueva_categoria = CategoriaProducto(
                    nombre=form.nombre.data,
                    descripcion=form.descripcion.data,
                    usuario_creacion=1,
                    usuario_movimiento=1
                )

                if form.foto.data:
                    try:
                        file = form.foto.data
                        nueva_categoria.foto = file.read()
                    except Exception as e:
                        flash(f'Error al procesar la imagen: {str(e)}', 'error')
                        return redirect(url_for('categorias_productos.agregar'))
                else:
                    with open('static/img/defecto.jpg', 'rb') as f:
                        nueva_categoria.foto = f.read()

                db.session.add(nueva_categoria)
                db.session.commit()
            
            flash(f'Categoría "{nueva_categoria.nombre}" creada exitosamente', 'success')
            return redirect(url_for('categorias_productos.agregar'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la categoría: {str(e)}', 'error')
            return redirect(url_for('categorias_productos.agregar'))
    
    return render_template('categorias-productos/agregar.html', form=form)


@categorias_productos.route('/detalle/<int:id>', methods=['GET'])
def detalle(id):
    """Ver detalle de una categoría"""
    categoria = CategoriaProducto.query.get_or_404(id)
    
    if categoria.estatus != 'ACTIVO':
        flash('La categoría no está disponible', 'warning')
        return redirect(url_for('categorias_productos.inicio'))
    
    categoria_data = {
        'id': categoria.id,
        'nombre': categoria.nombre,
        'descripcion': categoria.descripcion,
    }
    
    return render_template('categorias-productos/detalle.html', categoria=categoria_data)


@categorias_productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    """Editar una categoría existente"""
    categoria = CategoriaProducto.query.get_or_404(id)
    
    if categoria.estatus != 'ACTIVO':
        flash('No puedes editar una categoría inactiva', 'warning')
        return redirect(url_for('categorias_productos.inicio'))
    
    form = EditCategoriaProductoForm()
    form.categoria_id = id
    
    if form.validate_on_submit():
        try:
            # Actualizar datos
            categoria.nombre = form.nombre.data
            categoria.descripcion = form.descripcion.data
            if form.foto.data:
                categoria.foto = form.foto.data.read()
            categoria.usuario_movimiento = get_user_id()
            categoria.fecha_movimiento = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Categoría "{categoria.nombre}" actualizada exitosamente', 'success')
            return redirect(url_for('categorias_productos.editar', id=id))            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la categoría: {str(e)}', 'error')
            return redirect(url_for('categorias_productos.editar', id=id))
    
    elif request.method == 'GET':
        # Pre-cargar datos del formulario
        form.nombre.data = categoria.nombre
        form.descripcion.data = categoria.descripcion
    
    categoria_data = {
        'id': categoria.id,
        'nombre': categoria.nombre,
        'descripcion': categoria.descripcion,
    }
    imagen = obtener_imagen(categoria.foto)
    return render_template('categorias-productos/editar.html',form=form,categoria=categoria_data,imagen=imagen)


@categorias_productos.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    """Desactivar una categoría (soft delete con validación)"""
    categoria = CategoriaProducto.query.get_or_404(id)

    # Validar si ya está inactiva
    if categoria.estatus != 'ACTIVO':
        flash('La categoría ya está inactiva', 'warning')
        return redirect(url_for('categorias_productos.inicio'))

    try:
        # VALIDAR PRODUCTOS ACTIVOS 
        productos_activos = Producto.query.filter_by(
            fk_categoria=id,
            estatus='ACTIVO'
        ).count()

        if productos_activos > 0:
            flash(
                'No se puede desactivar la categoría porque tiene productos activos asociados',
                'error'
            )
            return redirect(url_for('categorias_productos.inicio'))

        # ✅ SOFT DELETE
        categoria.estatus = 'INACTIVO'
        categoria.usuario_movimiento = get_user_id()
        categoria.fecha_movimiento = datetime.utcnow()

        db.session.commit()

        flash(f'Categoría "{categoria.nombre}" desactivada correctamente', 'success')
        return redirect(url_for('categorias_productos.inicio'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al desactivar la categoría: {str(e)}', 'error')
        return redirect(url_for('categorias_productos.inicio'))

@categorias_productos.errorhandler(404)
def not_found(error):
    """Manejar errores 404"""
    flash('La categoría solicitada no existe', 'error')
    return redirect(url_for('categorias_productos.inicio')), 404

def obtener_imagen(foto):
    if foto:
        return f"data:image/png;base64,{base64.b64encode(foto).decode('utf-8')}"
    return url_for('static', filename='img/defecto.jpg')