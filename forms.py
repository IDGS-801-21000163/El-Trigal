from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import IntegerField, StringField, DecimalField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from models import Producto, CategoriaProducto, InventarioProducto, Sucursal
from wtforms import StringField, SelectField, SubmitField, TextAreaField

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


# ============================================================================
# FORMULARIOS PARA CATEGORÍAS DE PRODUCTOS
# ============================================================================

class CategoriaProductoForm(FlaskForm):
    """Formulario para crear y editar categorías de productos"""
    
    nombre = StringField(
        'Nombre de la Categoría',
        validators=[
            DataRequired(message='El nombre es requerido'),
            Length(min=3, max=65, message='El nombre debe tener entre 3 y 65 caracteres')
        ],
        render_kw={"placeholder": "Nombre de la categoría"}
    )
    
    descripcion = TextAreaField(
        'Descripción',
        validators=[
            DataRequired(message='La descripción es requerida'),
            Length(min=5, max=500, message='La descripción debe tener entre 5 y 500 caracteres')
        ],
        render_kw={"placeholder": "Descripción de la categoría", "rows": 4}
    )
    
    submit = SubmitField('Guardar')
    
    def validate_nombre(self, field):
        """Validar que el nombre sea único"""
        categoria = CategoriaProducto.query.filter_by(nombre=field.data).first()
        if categoria:
            raise ValidationError('Ya existe una categoría con este nombre')


class EditCategoriaProductoForm(CategoriaProductoForm):
    """Formulario específico para editar categorías"""
    
    def validate_nombre(self, field):
        """Permitir el mismo nombre si es la misma categoría"""
        # Si es la misma categoría, permitir
        if hasattr(self, 'categoria_id') and self.categoria_id:
            categoria = CategoriaProducto.query.get(self.categoria_id)
            if categoria and categoria.nombre == field.data:
                return
        
        # Sino, verificar que no exista otra con ese nombre
        categoria = CategoriaProducto.query.filter_by(nombre=field.data).first()
        if categoria:
            raise ValidationError('Ya existe otra categoría con este nombre')


class BuscarCategoriaForm(FlaskForm):
    """Formulario para buscar categorías"""
    
    buscar = StringField(
        'Buscar categoría',
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre..."}
    )
    
    submit = SubmitField('Buscar')


class ConfirmarEliminacionCategoriaForm(FlaskForm):
    """Formulario para confirmar eliminación de categoría"""
    
    confirm = SubmitField('Sí, desactivar')
    cancel = SubmitField('Cancelar')


# ============================================================================
# FORMULARIOS PARA INVENTARIO DE PRODUCTOS
# ============================================================================

class InventarioProductoForm(FlaskForm):
    """Formulario para crear y registrar inventario de productos"""
    
    fk_producto = SelectField(
        'Producto',
        validators=[DataRequired(message='El producto es requerido')],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )
    
    fk_sucursal = SelectField(
        'Sucursal',
        validators=[DataRequired(message='La sucursal es requerida')],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )
    
    cantidad_producto = DecimalField(
        'Cantidad',
        validators=[
            DataRequired(message='La cantidad es requerida'),
            NumberRange(min=0.01, message='La cantidad debe ser mayor a 0')
        ],
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "min": "0"}
    )
    
    fecha_caducidad = StringField(
        'Fecha de Caducidad',
        validators=[DataRequired(message='La fecha de caducidad es requerida')],
        render_kw={"type": "datetime-local", "placeholder": "YYYY-MM-DD HH:MM"}
    )
    
    submit = SubmitField('Guardar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar productos activos
        self.fk_producto.choices = [
            (p.id, p.nombre) for p in Producto.query.filter_by(estatus='ACTIVO').all()
        ]
        # Cargar sucursales activas
        self.fk_sucursal.choices = [
            (s.id, s.nombre) for s in Sucursal.query.filter_by(estatus='ACTIVO').all()
        ]


class EditInventarioProductoForm(FlaskForm):
    """Formulario para editar inventario (M14)"""

    cantidad_producto = IntegerField(
    'Cantidad de producto',
    validators=[
        DataRequired(message='La cantidad es requerida'),
        NumberRange(min=0, message='No puede ser negativa')
    ],
    render_kw={
        "placeholder": "0",
        "min": "0",
        "step": "1"
    }
)

    tipo_movimiento = SelectField(
        'Motivo',
        choices=[
            ('MERMA', 'Merma'),
            ('AUDITORIA', 'Auditoría')
        ],
        validators=[DataRequired(message='El motivo es obligatorio')]
    )

    observaciones = TextAreaField(
    'Observaciones',
    validators=[
        DataRequired(message='Las observaciones son obligatorias'),
        Length(max=255, message='Máximo 255 caracteres')
    ],
    render_kw={"placeholder": "Describe el motivo..."}
)

    submit = SubmitField('Guardar')

class BuscarInventarioForm(FlaskForm):
    """Formulario para buscar en inventario"""
    
    buscar = StringField(
        'Buscar producto',
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre del producto..."}
    )
    
    estado_filter = SelectField(
        'Estado del Inventario',
        choices=[('', 'Todos'), ('EXISTENCIA', 'Con existencia'), ('AGOTADO', 'Agotado')],
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )
    
    submit = SubmitField('Buscar')


class ConfirmarEliminacionInventarioForm(FlaskForm):
    """Formulario para confirmar eliminación de inventario"""
    
    confirm = SubmitField('Sí, desactivar')
    cancel = SubmitField('Cancelar')

class ProduccionForm(FlaskForm):
    cantidad = IntegerField(
        "Cantidad",
        validators=[
            DataRequired(),
            NumberRange(min=1, message="Debe ser mayor a 0")
        ]
    )
    submit = SubmitField("Iniciar producción")