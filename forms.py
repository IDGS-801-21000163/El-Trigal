from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, DecimalField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from models import Producto, CategoriaProducto


class ProductoForm(FlaskForm):
    """Formulario para crear y editar productos"""
    
    nombre = StringField(
        'Nombre del Producto',
        validators=[
            DataRequired(message='El nombre es requerido'),
            Length(min=3, max=65, message='El nombre debe tener entre 3 y 65 caracteres')
        ],
        render_kw={"placeholder": "Nombre del producto"}
    )
    
    fk_categoria = SelectField(
        'Categoría',
        validators=[DataRequired(message='La categoría es requerida')],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )
    
    precio = DecimalField(
        'Precio de Venta',
        validators=[
            DataRequired(message='El precio es requerido'),
            NumberRange(min=0.01, message='El precio debe ser mayor a 0')
        ],
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "min": "0"}
    )
    
    costo_produccion = DecimalField(
        'Costo de Producción',
        validators=[
            NumberRange(min=0, message='El costo no puede ser negativo')
        ],
        default=0.00,
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "disabled": "disabled"}
    )
    
    foto = FileField(
        'Imagen del Producto',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Solo se permiten imágenes (jpg, jpeg, png, gif)')
        ],
        render_kw={"accept": ".jpg,.jpeg,.png,.gif"}
    )
    
    submit = SubmitField('Guardar')
    
    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        # Cargar las categorías activas
        categorias = CategoriaProducto.query.filter_by(estatus='ACTIVO').all()
        self.fk_categoria.choices = [
            (cat.id, cat.nombre) for cat in categorias
        ]
        if not self.fk_categoria.choices:
            self.fk_categoria.choices = [(0, 'No hay categorías disponibles')]
    
    def validate_nombre(self, field):
        """Validar que el nombre sea único (excepto en edición del mismo producto)"""
        # En creación, verificar que no exista
        producto = Producto.query.filter_by(nombre=field.data).first()
        if producto:
            raise ValidationError('Ya existe un producto con este nombre')


class EditProductoForm(ProductoForm):
    """Formulario específico para editar productos"""
    
    def validate_nombre(self, field):
        """Permitir el mismo nombre si es el mismo producto"""
        # Si es el mismo producto, permitir
        if hasattr(self, 'producto_id') and self.producto_id:
            producto = Producto.query.get(self.producto_id)
            if producto and producto.nombre == field.data:
                return
        
        # Sino, verificar que no exista otro con ese nombre
        producto = Producto.query.filter_by(nombre=field.data).first()
        if producto:
            raise ValidationError('Ya existe otro producto con este nombre')


class BuscarProductoForm(FlaskForm):
    """Formulario para buscar productos"""
    
    buscar = StringField(
        'Buscar producto',
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre..."}
    )
    
    categoria = SelectField(
        'Categoría',
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )
    
    submit = SubmitField('Buscar')
    
    def __init__(self, *args, **kwargs):
        super(BuscarProductoForm, self).__init__(*args, **kwargs)
        # Cargar las categorías activas con opción de todas
        categorias = CategoriaProducto.query.filter_by(estatus='ACTIVO').all()
        self.categoria.choices = [(0, 'Todas las categorías')] + [
            (cat.id, cat.nombre) for cat in categorias
        ]


class ConfirmarEliminacionProductoForm(FlaskForm):
    """Formulario para confirmar eliminación de producto"""
    
    confirm = SubmitField('Sí, desactivar')
    cancel = SubmitField('Cancelar')
