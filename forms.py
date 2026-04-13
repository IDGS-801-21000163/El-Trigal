from flask_wtf import FlaskForm
from wtforms import (
    Form,
    StringField,
    PasswordField,
    IntegerField,
    FloatField,
    DecimalField,
    TextAreaField,
    SelectField,
    DateField,
    FileField,
    SubmitField,
    FieldList,
    FormField,
)

from wtforms import validators
from wtforms.validators import (
    DataRequired,
    Email,
    Optional,
    Length,
    Regexp,
    NumberRange,
    EqualTo,
    ValidationError
)
from wtforms.fields import DateTimeLocalField

from flask_wtf.file import FileAllowed
from models import (
    CategoriaInsumo,
    CategoriaProducto,
    Estado,
    InventarioProducto,
    Municipio,
    Producto,
    Sucursal,
)


class LoginForm(FlaskForm):
    usuario = StringField(
        "Usuario",
        validators=[
            DataRequired(message="El usuario es obligatorio"),
            Length(min=3, max=254, message="El usuario debe tener entre 3 y 254 caracteres")
        ]
    )

    contrasena = PasswordField(
        "Contrasena",
        validators=[
            DataRequired(message="La contrasena es obligatoria"),
            Length(min=8, max=128, message="La contrasena debe tener entre 8 y 128 caracteres")
        ]
    )

    submit = SubmitField("Entrar")


class RecetaDetalleForm(Form):
    fk_insumo = SelectField(
        "Insumo",
        coerce=int,
        validators=[DataRequired(message="Selecciona un insumo")],
    )

    fk_unidad = SelectField(
        "Unidad",
        coerce=int,
        validators=[DataRequired(message="Selecciona una unidad")],
    )

    cantidad_insumo = FloatField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es obligatoria"),
            NumberRange(min=0.01, message="La cantidad debe ser mayor a 0"),
        ],
    )


class RecetaForm(Form):
    id = IntegerField("ID")
    fk_producto = SelectField("Producto", coerce=int)
    descripcion = StringField(
        "Descripcion",
        validators=[
            DataRequired(message="El campo es obligatorio"),
            Length(min=20, message="Requiere un minimo de 20 caracteres"),
        ],
    )
    estatus = SelectField(
        "Estatus",
        choices=[("ACTIVO", "ACTIVO"), ("INACTIVO", "INACTIVO")],
        default="ACTIVO",
        validators=[Optional()],
    )
    detalles = FieldList(FormField(RecetaDetalleForm), min_entries=1)


class PedidoDetalleForm(Form):
    fk_producto = SelectField(
        "Producto",
        coerce=int,
        validators=[DataRequired(message="Selecciona un producto")],
    )

    cantidad = IntegerField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es obligatoria"),
            NumberRange(min=1, message="La cantidad debe ser mayor a 0"),
        ],
    )


class PedidoForm(Form):
    fk_cliente = SelectField(
        "Cliente",
        coerce=int,
        validators=[DataRequired(message="Selecciona un cliente")],
    )

    fecha_entrega = DateField(
        "Fecha Entrega",
        validators=[DataRequired(message="La fecha de entrega es obligatoria")],
    )

    notas = StringField(
        "Notas",
        validators=[Optional(), Length(max=255)],
    )

    anticipo = FloatField(
        "Anticipo",
        validators=[Optional(), NumberRange(min=0, message="El anticipo no puede ser negativo")],
    )

    fk_metodopago = SelectField("Metodo Pago", coerce=int)
    detalles = FieldList(FormField(PedidoDetalleForm), min_entries=1)


class RegistroForm(FlaskForm):
    nombre = StringField(
        "Nombre(s)",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=2, max=65, message="El nombre debe tener entre 2 y 65 caracteres")
        ]
    )

    apellido_uno = StringField(
        "Apellido paterno",
        validators=[
            DataRequired(message="El apellido paterno es obligatorio"),
            Length(min=2, max=65, message="El apellido paterno debe tener entre 2 y 65 caracteres")
        ]
    )

    apellido_dos = StringField(
        "Apellido materno",
        validators=[
            Optional(),
            Length(max=65, message="El apellido materno no debe exceder 65 caracteres")
        ]
    )

    telefono = StringField(
        "Telefono",
        validators=[
            DataRequired(message="El telefono es obligatorio"),
            Regexp(r'^\d{10}$', message="El telefono debe tener 10 digitos")
        ]
    )

    correo = StringField(
        "Correo electronico",
        validators=[
            DataRequired(message="El correo es obligatorio"),
            Email(message="Correo electronico invalido"),
            Length(max=254, message="El correo no debe exceder 254 caracteres")
        ]
    )

    submit = SubmitField("Crear cuenta")


class OtpForm(FlaskForm):
    digito_1 = StringField("Digito 1", validators=[DataRequired(), Length(min=1, max=1), Regexp(r'^\d$')])
    digito_2 = StringField("Digito 2", validators=[DataRequired(), Length(min=1, max=1), Regexp(r'^\d$')])
    digito_3 = StringField("Digito 3", validators=[DataRequired(), Length(min=1, max=1), Regexp(r'^\d$')])
    digito_4 = StringField("Digito 4", validators=[DataRequired(), Length(min=1, max=1), Regexp(r'^\d$')])
    digito_5 = StringField("Digito 5", validators=[DataRequired(), Length(min=1, max=1), Regexp(r'^\d$')])

    submit = SubmitField("Verificar")


class RecuperarForm(FlaskForm):
    correo = StringField(
        "Correo electronico",
        validators=[
            DataRequired(message="El correo es obligatorio"),
            Email(message="Correo electronico invalido"),
            Length(max=254, message="El correo no debe exceder 254 caracteres"),
        ],
    )
    submit = SubmitField("Enviar solicitud")


class EmpleadoForm(FlaskForm):

    # ==========================
    # PERSONA
    # ==========================

    nombre = StringField(
        "Nombre",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=2, max=50, message="Debe tener entre 2 y 50 caracteres")
        ]
    )

    apellido_uno = StringField(
        "Apellido paterno",
        validators=[
            DataRequired(message="El apellido paterno es obligatorio"),
            Length(min=2, max=50)
        ]
    )

    apellido_dos = StringField(
        "Apellido materno",
        validators=[
            Optional(),
            Length(max=50)
        ]
    )

    telefono = StringField(
        "Teléfono",
        validators=[
            Optional(),
            Regexp(r'^\d{10}$',  message="El teléfono debe tener 10 dígitos")
        ]
    )

    correo = StringField(
        "Correo",
        validators=[
            Optional(),
            Email(message="Correo electrónico inválido"),
            Length(max=120)
        ]
    )

    # ==========================
    # DIRECCION
    # ==========================

    fk_estado = SelectField(
        "Estado",
        coerce=int,
        validators=[DataRequired(message="Seleccione un estado")]
    )

    fk_municipio = SelectField(
        "Municipio",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Seleccione un municipio")]
    )

    calle = StringField(
        "Calle",
        validators=[
            DataRequired(message="La calle es obligatoria"),
            Length(max=100)
        ]
    )

    colonia = StringField(
        "Colonia",
        validators=[
            DataRequired(message="La colonia es obligatoria"),
            Length(max=100)
        ]
    )

    codigo_postal = StringField(
        "Código postal",
        validators=[
            DataRequired(message="El código postal es obligatorio"),
            Regexp(r'^[0-9]{5}$', message="El código postal debe tener 5 dígitos")
        ]
    )

    num_exterior = StringField(
        "Número exterior",
        validators=[
            DataRequired(message="El número exterior es obligatorio"),
            Length(max=10)
        ]
    )

    num_interior = StringField(
        "Número interior",
        validators=[
            Optional(),
            Length(max=10)
        ]
    )

    # ==========================
    # EMPLEADO
    # ==========================

    num_empleado = StringField(
        "Número de empleado",
        validators=[
            DataRequired(message="El número de empleado es obligatorio"),
            Length(min=1, max=50)
        ]
    )

    fk_puesto = SelectField(
        "Puesto",
        coerce=int,
        validators=[DataRequired(message="Seleccione un puesto")]
    )

    fecha_contratacion = DateField(
        "Fecha contratación",
        format="%Y-%m-%d",
        validators=[
            DataRequired(message="Ingrese la fecha de contratación")
        ]
    )

    estatus = SelectField(
        "Estatus",
        choices=[
            ("ACTIVO", "ACTIVO"),
            ("INACTIVO", "INACTIVO")
        ]
    )

    imagen = FileField(
        "Imagen",
        validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Solo imágenes JPG o PNG')]
    )

    submit = SubmitField("Guardar")
    

class PuestoForm(FlaskForm):

    # ==========================
    # DATOS DEL PUESTO
    # ==========================

    nombre = StringField(
        "Nombre del puesto",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=3, max=65, message="Debe tener entre 3 y 65 caracteres")
        ]
    )

    descripcion = TextAreaField(
        "Descripción",
        validators=[
            DataRequired(message="La descripción es obligatoria"),
            Length(max=500)
        ]
    )

    sueldo = DecimalField(
        "Sueldo Semanal",
        places=2,
        validators=[
            DataRequired(message="El sueldo es obligatorio"),
            NumberRange(min=0, message="El sueldo no puede ser negativo")
        ]
    )

    estatus = SelectField(
        "Estatus",
        choices=[
            ("ACTIVO", "ACTIVO"),
            ("INACTIVO", "INACTIVO")
        ],
        default="ACTIVO",
        validators=[DataRequired()]
    )

    # ==========================
    # SUBMIT
    # ==========================
    submit = SubmitField("Guardar")

class ProveedorForm(FlaskForm):
    # ==========================
    # DATOS DEL PROVEEDOR
    # ==========================
    nombre_comercial = StringField(
        "Nombre comercial",
        validators=[
            DataRequired(message="El nombre comercial es obligatorio"),
            Length(min=3, max=150, message="Debe tener entre 3 y 150 caracteres")
        ]
    )

    razon_social = StringField(
        "Razón social",
        validators=[
            Optional(),
            Length(max=150)
        ]
    )

    telefono = StringField(
        "Teléfono",
        validators=[
            Optional(),
            Regexp(r'^[0-9]{10}$', message="El teléfono debe tener 10 dígitos")
        ]
    )

    correo = StringField(
        "Correo electrónico",
        validators=[
            Optional(),
            Email(message="Correo electrónico inválido"),
            Length(max=120)
        ]
    )

    # ==========================
    # DIRECCIÓN
    # ==========================
    fk_estado = SelectField(
        "Estado",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Seleccione un estado")]
    )

    fk_municipio = SelectField(
        "Municipio",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Seleccione un municipio")]
    )

    calle = StringField(
        "Calle",
        validators=[DataRequired(message="La calle es obligatoria"), Length(max=120)]
    )

    colonia = StringField(
        "Colonia",
        validators=[DataRequired(message="La colonia es obligatoria"), Length(max=120)]
    )

    codigo_postal = StringField(
        "Código postal",
        validators=[DataRequired(message="El código postal es obligatorio"),
                    Regexp(r'^[0-9]{5}$', message="El código postal debe tener 5 dígitos")]
    )

    num_exterior = StringField(
        "Número exterior",
        validators=[DataRequired(message="El número exterior es obligatorio"), Length(max=10)]
    )

    num_interior = StringField(
        "Número interior",
        validators=[Optional(), Length(max=10)]
    )

    # ==========================
    # ESTATUS
    # ==========================
    estatus = SelectField(
        "Estatus",
        choices=[("ACTIVO", "ACTIVO"), ("INACTIVO", "INACTIVO")],
        default="ACTIVO"
    )

    # ==========================
    # SUBMIT
    # ==========================
    submit = SubmitField("Guardar")


class SucursalForm(FlaskForm):
    nombre = StringField(
        "Nombre de la sucursal",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=3, max=65, message="Debe tener entre 3 y 65 caracteres"),
        ],
    )

    telefono = StringField(
        "Teléfono",
        validators=[
            DataRequired(message="El teléfono es obligatorio"),
            Regexp(r'^[0-9]{10}$', message="El teléfono debe tener 10 dígitos"),
        ],
    )

    fk_estado = SelectField(
        "Estado",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Seleccione un estado")],
    )

    fk_municipio = SelectField(
        "Municipio",
        coerce=int,
        choices=[],
        validators=[DataRequired(message="Seleccione un municipio")],
    )

    calle = StringField(
        "Calle",
        validators=[DataRequired(message="La calle es obligatoria"), Length(max=120)],
    )

    colonia = StringField(
        "Colonia",
        validators=[DataRequired(message="La colonia es obligatoria"), Length(max=120)],
    )

    codigo_postal = StringField(
        "Código postal",
        validators=[
            DataRequired(message="El código postal es obligatorio"),
            Regexp(r'^[0-9]{5}$', message="El código postal debe tener 5 dígitos"),
        ],
    )

    num_exterior = StringField(
        "Número exterior",
        validators=[DataRequired(message="El número exterior es obligatorio"), Length(max=10)],
    )

    num_interior = StringField(
        "Número interior",
        validators=[Optional(), Length(max=10)],
    )

    estatus = SelectField(
        "Estatus",
        choices=[("ACTIVO", "ACTIVO"), ("INACTIVO", "INACTIVO")],
        default="ACTIVO",
    )

    submit = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estados = Estado.query.filter_by(estatus="ACTIVO").order_by(Estado.nombre.asc()).all()
        self.fk_estado.choices = [(estado.id, estado.nombre) for estado in estados]
        estado_id = self.fk_estado.data or (self.fk_estado.choices[0][0] if self.fk_estado.choices else None)
        municipios = []
        if estado_id:
            municipios = (
                Municipio.query.filter_by(fk_estado=estado_id, estatus="ACTIVO")
                .order_by(Municipio.nombre.asc())
                .all()
            )
        self.fk_municipio.choices = [(municipio.id, municipio.nombre) for municipio in municipios]

    def validate_nombre(self, field):
        sucursal = Sucursal.query.filter_by(nombre=field.data.strip()).first()
        if sucursal and getattr(self, "sucursal_id", None) != sucursal.id:
            raise ValidationError("Ya existe una sucursal con este nombre")

    def validate_telefono(self, field):
        sucursal = Sucursal.query.filter_by(telefono=field.data.strip()).first()
        if sucursal and getattr(self, "sucursal_id", None) != sucursal.id:
            raise ValidationError("Ya existe una sucursal con este teléfono")

class InventarioInsumoForm(FlaskForm):
    cantidad = IntegerField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es obligatoria"),
            NumberRange(min=0, message="La cantidad no puede ser negativa")
        ]
    )
    tipo_movimiento = SelectField(
        "Tipo de movimiento",
        choices=[
            ("MERMA", "Merma"),
            ("ERROR", "Error"),
            ("AUDITORIA", "Auditoría")
        ],
        validators=[DataRequired()]
    )
    motivo = TextAreaField(
        "Motivo",
        validators=[
            DataRequired(message="El motivo es obligatorio"),
            Length(max=500)
        ]
    )
    submit = SubmitField("Guardar")


class CategoriaInsumoForm(FlaskForm):
    nombre = StringField(
        "Nombre de la categoria",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=3, max=65, message="Debe tener entre 3 y 65 caracteres"),
        ],
    )

    descripcion = TextAreaField(
        "Descripcion",
        validators=[
            DataRequired(message="La descripcion es obligatoria"),
            Length(min=5, max=500, message="Debe tener entre 5 y 500 caracteres"),
        ],
    )

    estatus = SelectField(
        "Estatus",
        choices=[("ACTIVO", "ACTIVO"), ("INACTIVO", "INACTIVO")],
        default="ACTIVO",
        validators=[DataRequired()],
    )

    submit = SubmitField("Guardar")

    def validate_nombre(self, field):
        categoria = CategoriaInsumo.query.filter_by(nombre=field.data.strip()).first()
        if categoria:
            raise ValidationError("Ya existe una categoria con este nombre")


class EditCategoriaInsumoForm(CategoriaInsumoForm):
    def validate_nombre(self, field):
        if hasattr(self, "categoria_id") and self.categoria_id:
            categoria = CategoriaInsumo.query.get(self.categoria_id)
            if categoria and categoria.nombre == field.data.strip():
                return

        categoria = CategoriaInsumo.query.filter_by(nombre=field.data.strip()).first()
        if categoria:
            raise ValidationError("Ya existe otra categoria con este nombre")


class InsumoForm(FlaskForm):
    fk_categoria = SelectField(
        "Categoria",
        coerce=int,
        validators=[DataRequired(message="Selecciona una categoria")],
    )

    nombre = StringField(
        "Nombre del insumo",
        validators=[
            DataRequired(message="El nombre es obligatorio"),
            Length(min=3, max=65, message="Debe tener entre 3 y 65 caracteres"),
        ],
    )

    porcentaje_merma = DecimalField(
        "Porcentaje de merma",
        places=2,
        validators=[
            DataRequired(message="El porcentaje de merma es obligatorio"),
            NumberRange(min=0, max=100, message="Debe estar entre 0 y 100"),
        ],
        default=0,
    )

    foto = FileField(
        "Imagen del insumo",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Solo se permiten imagenes JPG o PNG")],
    )

    estatus = SelectField(
        "Estatus",
        choices=[("ACTIVO", "ACTIVO"), ("INACTIVO", "INACTIVO")],
        default="ACTIVO",
        validators=[DataRequired()],
    )

    submit = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = CategoriaInsumo.query.order_by(CategoriaInsumo.nombre.asc()).all()
        self.fk_categoria.choices = [(categoria.id, categoria.nombre) for categoria in categorias]
        if not self.fk_categoria.choices:
            self.fk_categoria.choices = [(0, "No hay categorias disponibles")]

    def validate_nombre(self, field):
        from models import Insumo

        existente = Insumo.query.filter_by(nombre=field.data.strip()).first()
        if existente:
            raise ValidationError("Ya existe un insumo con este nombre")


class EditInsumoForm(InsumoForm):
    def validate_nombre(self, field):
        nombre = field.data.strip()
        from models import Insumo

        if hasattr(self, "insumo_id") and self.insumo_id:
            insumo = Insumo.query.get(self.insumo_id)
            if insumo and insumo.nombre == nombre:
                return

        existente = Insumo.query.filter_by(nombre=nombre).first()
        if existente:
            raise ValidationError("Ya existe otro insumo con este nombre")


class ProductoForm(FlaskForm):
    nombre = StringField(
        "Nombre del Producto",
        validators=[
            DataRequired(message="El nombre es requerido"),
            Length(min=3, max=65, message="El nombre debe tener entre 3 y 65 caracteres")
        ],
        render_kw={"placeholder": "Nombre del producto"}
    )

    fk_categoria = SelectField(
        "Categoria",
        validators=[DataRequired(message="La categoria es requerida")],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )

    precio = DecimalField(
        "Precio de Venta",
        validators=[
            DataRequired(message="El precio es requerido"),
            NumberRange(min=1, message="El precio debe ser mayor a 0")
        ],
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "min": "1"}
    )

    costo_produccion = DecimalField(
        "Costo de Produccion",
        validators=[NumberRange(min=0, message="El costo no puede ser negativo")],
        default=0.00,
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "disabled": "disabled"}
    )

    foto = FileField(
        "Imagen del Producto",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Solo se permiten imagenes (jpg, jpeg, png)")],
        render_kw={"accept": ".jpg,.jpeg,.png"}
    )

    submit = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").all()
        self.fk_categoria.choices = [(cat.id, cat.nombre) for cat in categorias]
        if not self.fk_categoria.choices:
            self.fk_categoria.choices = [(0, "No hay categorias disponibles")]

    def validate_nombre(self, field):
        producto = Producto.query.filter_by(nombre=field.data).first()
        if producto:
            raise ValidationError("Ya existe un producto con este nombre")


class EditProductoForm(ProductoForm):
    def validate_nombre(self, field):
        if hasattr(self, "producto_id") and self.producto_id:
            producto = Producto.query.get(self.producto_id)
            if producto and producto.nombre == field.data:
                return

        producto = Producto.query.filter_by(nombre=field.data).first()
        if producto:
            raise ValidationError("Ya existe otro producto con este nombre")


class BuscarProductoForm(FlaskForm):
    buscar = StringField(
        "Buscar producto",
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre..."}
    )

    categoria = SelectField(
        "Categoria",
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )

    submit = SubmitField("Buscar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categorias = CategoriaProducto.query.filter_by(estatus="ACTIVO").all()
        self.categoria.choices = [(0, "Todas las categorias")] + [(cat.id, cat.nombre) for cat in categorias]


class ConfirmarEliminacionProductoForm(FlaskForm):
    confirm = SubmitField("Si, eliminar")
    cancel = SubmitField("Cancelar")


class CategoriaProductoForm(FlaskForm):
    nombre = StringField(
        "Nombre de la Categoria",
        validators=[
            DataRequired(message="El nombre es requerido"),
            Length(min=3, max=65, message="El nombre debe tener entre 3 y 65 caracteres")
        ],
        render_kw={"placeholder": "Nombre de la categoria"}
    )

    descripcion = TextAreaField(
        "Descripcion",
        validators=[
            DataRequired(message="La descripcion es requerida"),
            Length(min=5, max=500, message="La descripcion debe tener entre 5 y 500 caracteres")
        ],
        render_kw={"placeholder": "Descripcion de la categoria", "rows": 4}
    )

    foto = FileField(
        "Imagen de la Categoria",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Solo se permiten imagenes (jpg, jpeg, png)")],
        render_kw={"accept": ".jpg,.jpeg,.png"}
    )

    submit = SubmitField("Guardar")

    def validate_nombre(self, field):
        categoria = CategoriaProducto.query.filter_by(nombre=field.data).first()
        if categoria:
            raise ValidationError("Ya existe una categoria con este nombre")


class EditCategoriaProductoForm(CategoriaProductoForm):
    def validate_nombre(self, field):
        if hasattr(self, "categoria_id") and self.categoria_id:
            categoria = CategoriaProducto.query.get(self.categoria_id)
            if categoria and categoria.nombre == field.data:
                return

        categoria = CategoriaProducto.query.filter_by(nombre=field.data).first()
        if categoria:
            raise ValidationError("Ya existe otra categoria con este nombre")


class BuscarCategoriaForm(FlaskForm):
    buscar = StringField(
        "Buscar categoria",
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre..."}
    )

    submit = SubmitField("Buscar")


class ConfirmarEliminacionCategoriaForm(FlaskForm):
    confirm = SubmitField("Si, eliminar")
    cancel = SubmitField("Cancelar")


class InventarioProductoForm(FlaskForm):
    fk_producto = SelectField(
        "Producto",
        validators=[DataRequired(message="El producto es requerido")],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )

    fk_sucursal = SelectField(
        "Sucursal",
        validators=[DataRequired(message="La sucursal es requerida")],
        coerce=int,
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )

    cantidad_producto = DecimalField(
        "Cantidad",
        validators=[
            DataRequired(message="La cantidad es requerida"),
            NumberRange(min=0.01, message="La cantidad debe ser mayor a 0")
        ],
        places=2,
        render_kw={"placeholder": "0.00", "step": "0.01", "min": "0"}
    )

    fecha_caducidad = StringField(
        "Fecha de Caducidad",
        validators=[DataRequired(message="La fecha de caducidad es requerida")],
        render_kw={"type": "datetime-local", "placeholder": "YYYY-MM-DD HH:MM"}
    )

    submit = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fk_producto.choices = [(p.id, p.nombre) for p in Producto.query.filter_by(estatus="ACTIVO").all()]
        self.fk_sucursal.choices = [(s.id, s.nombre) for s in Sucursal.query.filter_by(estatus="ACTIVO").all()]


class EditInventarioProductoForm(FlaskForm):
    cantidad_producto = IntegerField(
        "Cantidad a Descontar",
        validators=[
            DataRequired(message="La cantidad es requerida o invalida"),
            NumberRange(min=1, message="No puede ser negativa")
        ],
        render_kw={"placeholder": "0", "min": "1", "step": "1"}
    )

    tipo_movimiento = SelectField(
        "Motivo",
        choices=[("MERMA", "Merma"), ("AUDITORIA", "Auditoria")],
        validators=[DataRequired(message="El motivo es obligatorio")]
    )

    observaciones = TextAreaField(
        "Observaciones",
        validators=[
            DataRequired(message="Las observaciones son obligatorias"),
            Length(max=255, message="Maximo 255 caracteres")
        ],
        render_kw={"placeholder": "Describe el motivo..."}
    )

    submit = SubmitField("Guardar")


class BuscarInventarioForm(FlaskForm):
    buscar = StringField(
        "Buscar producto",
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre del producto..."}
    )

    estado_filter = SelectField(
        "Estado del Inventario",
        choices=[("", "Todos"), ("EXISTENCIA", "Con existencia"), ("AGOTADO", "Agotado")],
        render_kw={"class": "border px-3 py-2 rounded-lg"}
    )

    submit = SubmitField("Buscar")


class ConfirmarEliminacionInventarioForm(FlaskForm):
    confirm = SubmitField("Si, eliminar")
    cancel = SubmitField("Cancelar")


class ProduccionForm(FlaskForm):
    cantidad = IntegerField(
        "Cantidad",
        validators=[DataRequired(), NumberRange(min=1, message="Debe ser mayor a 0")]
    )
    submit = SubmitField("Iniciar produccion")


class CancelarProduccionForm(FlaskForm):
    cantidad = IntegerField(
        "Cantidad de merma extra",
        validators=[DataRequired(), NumberRange(min=1)]
    )

    observacion = StringField("Observacion", validators=[DataRequired()])
    submit = SubmitField("Guardar")


class TerminarProduccionForm(FlaskForm):
    piezas = IntegerField("Piezas correctas", validators=[DataRequired(), NumberRange(min=1)])
    merma = IntegerField("Merma", validators=[DataRequired(), NumberRange(min=0)])
    fecha_caducidad = DateTimeLocalField("Fecha de caducidad", format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Guardar y cerrar")


class NuevaProduccionForm(FlaskForm):
    producto_id = SelectField("Producto", coerce=int)
    cantidad = IntegerField("Cantidad", validators=[DataRequired(), NumberRange(min=1)])
    empleado = SelectField("Empleado", coerce=int)
    submit = SubmitField("Guardar")


class ClienteForm(FlaskForm):
    nombre = StringField(
        "Nombre",
        validators=[
            DataRequired(message="El nombre es requerido"),
            Length(min=2, max=65, message="Entre 2 y 65 caracteres")
        ],
        render_kw={"placeholder": "Nombre"}
    )

    apellido_paterno = StringField(
        "Apellido Paterno",
        validators=[
            DataRequired(message="El apellido paterno es requerido"),
            Length(min=2, max=65)
        ],
        render_kw={"placeholder": "Apellido paterno"}
    )

    apellido_materno = StringField(
        "Apellido Materno",
        validators=[Optional(), Length(max=65)],
        render_kw={"placeholder": "Apellido materno (opcional)"}
    )

    telefono = StringField(
        "Telefono",
        validators=[
            DataRequired(message="El telefono es requerido"),
            Length(min=10, max=15, message="Entre 10 y 15 caracteres")
        ],
        render_kw={"placeholder": "10 digitos"}
    )

    correo = StringField(
        "Correo electronico",
        validators=[
            DataRequired(message="El correo es requerido"),
            Email(message="Correo no valido"),
            Length(max=254)
        ],
        render_kw={"placeholder": "correo@ejemplo.com"}
    )

    foto = FileField(
        "Foto del cliente",
        validators=[FileAllowed(["jpg", "jpeg", "png"], "Solo imagenes jpg, jpeg, png")],
        render_kw={"accept": ".jpg,.jpeg,.png"}
    )

    submit = SubmitField("Guardar")


class EditClienteForm(ClienteForm):
    def __init__(self, *args, **kwargs):
        self.persona_id = kwargs.pop("persona_id", None)
        super().__init__(*args, **kwargs)

    def validate_correo(self, field):
        from models import Persona

        existe = Persona.query.filter(
            Persona.correo == field.data,
            Persona.id != self.persona_id
        ).first()
        if existe:
            raise ValidationError("Este correo ya esta en uso")

    def validate_telefono(self, field):
        from models import Persona

        existe = Persona.query.filter(
            Persona.telefono == field.data,
            Persona.id != self.persona_id
        ).first()
        if existe:
            raise ValidationError("Este telefono ya esta en uso")


class BuscarClienteForm(FlaskForm):
    buscar = StringField(
        "Buscar cliente",
        validators=[Length(min=0, max=100)],
        render_kw={"placeholder": "Buscar por nombre..."}
    )
    submit = SubmitField("Buscar")


class ConfirmarEliminacionClienteForm(FlaskForm):
    submit = SubmitField("Si, eliminar")
