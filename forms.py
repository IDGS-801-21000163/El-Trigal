from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    DecimalField,
    TextAreaField,
    SelectField,
    DateField,
    FileField,
    SubmitField
)

from wtforms import validators
from wtforms.validators import (
    DataRequired,
    Email,
    Optional,
    Length,
    Regexp,
    NumberRange
)

from flask_wtf.file import FileAllowed


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
        "Sueldo",
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

from wtforms import SelectField

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