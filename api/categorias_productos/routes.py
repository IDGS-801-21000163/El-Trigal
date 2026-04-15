from flask import render_template, request, redirect, url_for, flash
from utils.modules import create_module_blueprint
from models import db, CategoriaProducto
from forms import CategoriaProductoForm, EditCategoriaProductoForm, BuscarCategoriaForm, ConfirmarEliminacionCategoriaForm
from datetime import datetime
from models import db, CategoriaProducto, Producto
from models import Producto
from utils.session import get_current_user_id

categorias_productos = create_module_blueprint("categorias-productos")

MODULE = {
    "name": "Categorías de productos",
    "slug": "categorias-productos",
    "description": "Gestión de categorías comerciales para los productos del sistema",
}


def get_user_id():
    return get_current_user_id()


@categorias_productos.route('/', methods=['GET'])
@categorias_productos.route('/inicio', methods=['GET'])
def inicio():
    buscar = request.args.get('buscar', '', type=str)
    estatus = request.args.get("estatus", "ACTIVO", type=str).strip().upper()
    
    query = CategoriaProducto.query
    if estatus in {"ACTIVO", "INACTIVO"}:
        query = query.filter_by(estatus=estatus)
    
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
        })
    
    return render_template(
        'categorias-productos/inicio.html',
        module=MODULE,
        categorias=categorias_data,
        buscar=buscar,
        estatus=estatus,
    )


@categorias_productos.route('/agregar', methods=['GET', 'POST'])
def agregar():
    form = CategoriaProductoForm()
    
    if form.validate_on_submit():
        try:
            if form.validate_on_submit():
                nueva_categoria = CategoriaProducto(
                    nombre=form.nombre.data,
                    descripcion=form.descripcion.data,
                    usuario_creacion=get_user_id(),
                    usuario_movimiento=get_user_id()
                )

                db.session.add(nueva_categoria)
                db.session.commit()
            
            flash(f'Categoría "{nueva_categoria.nombre}" creada exitosamente', 'success')
            return redirect(url_for('categorias_productos.inicio'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la categoría: {str(e)}', 'error')
            return redirect(url_for('categorias_productos.agregar'))
    
    return render_template('categorias-productos/agregar.html', form=form, module=MODULE)


@categorias_productos.route('/detalle/<int:id>', methods=['GET'])
def detalle(id):
    categoria = CategoriaProducto.query.get_or_404(id)
    
    categoria_data = {
        'id': categoria.id,
        'nombre': categoria.nombre,
        'descripcion': categoria.descripcion,
        'estatus': categoria.estatus,
    }
    
    return render_template('categorias-productos/detalle.html', categoria=categoria_data, module=MODULE)


@categorias_productos.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    categoria = CategoriaProducto.query.get_or_404(id)
    
    if categoria.estatus != 'ACTIVO':
        flash('No puedes editar una categoría inactiva', 'warning')
        return redirect(url_for('categorias_productos.inicio', estatus="INACTIVO"))
    
    form = EditCategoriaProductoForm()
    form.categoria_id = id
    
    if form.validate_on_submit():
        try:
            # Actualizar datos
            categoria.nombre = form.nombre.data
            categoria.descripcion = form.descripcion.data
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
    return render_template(
        'categorias-productos/editar.html',
        form=form,
        categoria=categoria_data,
        module=MODULE,
    )


@categorias_productos.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    categoria = CategoriaProducto.query.get_or_404(id)

    # Validar si ya está inactiva
    if categoria.estatus != 'ACTIVO':
        flash('La categoría ya está inactiva', 'warning')
        return redirect(url_for('categorias_productos.inicio'))

    try:
        # Bloquear si tiene productos asociados (dependencia)
        productos_relacionados = Producto.query.filter_by(fk_categoria=id).count()

        if productos_relacionados > 0:
            flash(
                'No se puede eliminar la categoría porque tiene productos asociados',
                'error'
            )
            return redirect(url_for('categorias_productos.inicio'))

        # Eliminacion logica
        categoria.estatus = 'INACTIVO'
        categoria.usuario_movimiento = get_user_id()
        categoria.fecha_movimiento = datetime.utcnow()

        db.session.commit()

        flash(f'Categoría "{categoria.nombre}" eliminada correctamente', 'success')
        return redirect(url_for('categorias_productos.inicio'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la categoría: {str(e)}', 'error')
        return redirect(url_for('categorias_productos.inicio'))


@categorias_productos.errorhandler(404)
def not_found(error):
    flash('La categoría solicitada no existe', 'error')
    return redirect(url_for('categorias_productos.inicio')), 404


@categorias_productos.route('/activar/<int:id>', methods=['POST'])
def activar(id):
    categoria = CategoriaProducto.query.get_or_404(id)

    if categoria.estatus == 'ACTIVO':
        flash('La categoría ya está activa', 'warning')
        return redirect(url_for('categorias_productos.inicio'))

    categoria.estatus = 'ACTIVO'
    categoria.usuario_movimiento = get_user_id()
    categoria.fecha_movimiento = datetime.utcnow()
    db.session.commit()

    flash(f'Categoría "{categoria.nombre}" activada correctamente', 'success')
    return redirect(url_for('categorias_productos.inicio', estatus="INACTIVO"))
