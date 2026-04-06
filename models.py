from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_rol = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    nick = db.Column(db.String(254), unique=True, nullable=False)
    clave = db.Column(db.String(255), nullable=False)
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta = db.Column(db.DateTime)
    ultimo_login = db.Column(db.DateTime)
    fecha_cambio_clave = db.Column(db.DateTime)
    forzar_cambio_clave = db.Column(db.Integer, default=0)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Rol(db.Model):
    __tablename__ = 'rol'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class CategoriaProducto(db.Model):
    __tablename__ = 'categoria_producto'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(65), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    foto = db.Column(db.LargeBinary)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Producto(db.Model):
    __tablename__ = 'producto'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_categoria = db.Column(db.Integer, db.ForeignKey('categoria_producto.id'), nullable=False)
    nombre = db.Column(db.String(65), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    costo_produccion = db.Column(db.Numeric(10, 2), default=0.00)
    foto = db.Column(db.LargeBinary)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Relationships
    categoria = db.relationship('CategoriaProducto', backref='productos')


class CategoriaInsumo(db.Model):
    __tablename__ = 'categoria_insumo'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(65), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Insumo(db.Model):
    __tablename__ = 'insumo'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_categoria = db.Column(db.Integer, db.ForeignKey('categoria_insumo.id'), nullable=False)
    nombre = db.Column(db.String(65), nullable=False, unique=True)
    porcentaje_merma = db.Column(db.Numeric(5, 2), default=0.00)
    foto = db.Column(db.LargeBinary)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Relationships
    categoria = db.relationship('CategoriaInsumo', backref='insumos')


class Receta(db.Model):
    __tablename__ = 'receta'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_producto = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class UnidadMedida(db.Model):
    __tablename__ = 'unidad_medida'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    factor_conversion = db.Column(db.Numeric(15, 5), default=1.00000)
    fk_unidad_base = db.Column(db.Integer, db.ForeignKey('unidad_medida.id'))
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Cliente(db.Model):
    __tablename__ = 'cliente'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_persona = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    persona = db.relationship('Persona')


class Persona(db.Model):
    __tablename__ = 'persona'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    fk_direccion = db.Column(db.Integer, db.ForeignKey('direccion.id'))
    nombre = db.Column(db.String(65), nullable=False)
    apellido_uno = db.Column(db.String(65), nullable=False)
    apellido_dos = db.Column(db.String(65))
    telefono = db.Column(db.String(15), unique=True)
    correo = db.Column(db.String(254), unique=True)
    foto = db.Column(db.LargeBinary)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Direccion(db.Model):
    __tablename__ = 'direccion'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_estado = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)
    fk_municipio = db.Column(db.Integer, db.ForeignKey('municipio.id'), nullable=False)
    codigo_postal = db.Column(db.String(20), nullable=False)
    colonia = db.Column(db.String(65), nullable=False)
    calle = db.Column(db.String(65), nullable=False)
    num_interior = db.Column(db.String(20))
    num_exterior = db.Column(db.String(20), nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Estado(db.Model):
    __tablename__ = 'estado'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Municipio(db.Model):
    __tablename__ = 'municipio'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_estado = db.Column(db.Integer, db.ForeignKey('estado.id'), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Proveedor(db.Model):
    __tablename__ = 'proveedor'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_direccion = db.Column(db.Integer, db.ForeignKey('direccion.id'), nullable=False)
    nombre_comercial = db.Column(db.String(65), nullable=False)
    razon_social = db.Column(db.String(65), nullable=False)
    correo = db.Column(db.String(254), nullable=False, unique=True)
    telefono = db.Column(db.String(15), nullable=False, unique=True)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Puesto(db.Model):
    __tablename__ = 'puesto'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(65), nullable=False, unique=True)
    descripcion = db.Column(db.Text, nullable=False)
    sueldo = db.Column(db.Numeric(10, 2), nullable=False)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Empleado(db.Model):
    __tablename__ = 'empleado'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_puesto = db.Column(db.Integer, db.ForeignKey('puesto.id'), nullable=False)
    fk_persona = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    num_empleado = db.Column(db.String(50), nullable=False, unique=True)
    fecha_contratacion = db.Column(db.DateTime, default=datetime.utcnow)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class Sucursal(db.Model):
    __tablename__ = 'sucursal'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_direccion = db.Column(db.Integer, db.ForeignKey('direccion.id'), nullable=False)
    nombre = db.Column(db.String(65), nullable=False)
    telefono = db.Column(db.String(15), nullable=False, unique=True)
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class InventarioProducto(db.Model):
    __tablename__ = 'inventario_producto'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_producto = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    fk_sucursal = db.Column(db.Integer, db.ForeignKey('sucursal.id'), nullable=False)
    cantidad_producto = db.Column(db.Numeric(10, 2), nullable=False)
    fecha_caducidad = db.Column(db.DateTime, nullable=False)
    estado = db.Column(db.Enum('EXISTENCIA', 'AGOTADO'), default='EXISTENCIA')
    estatus = db.Column(db.Enum('ACTIVO', 'INACTIVO'), default='ACTIVO')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    producto = db.relationship('Producto')
    sucursal = db.relationship('Sucursal')
    
class InventarioProductoMovimiento(db.Model):
    __tablename__ = 'inventario_producto_movimiento'

    id = db.Column(db.Integer, primary_key=True)
    fk_inventario_producto = db.Column(db.Integer, db.ForeignKey('inventario_producto.id'), nullable=False)
    cantidad_anterior = db.Column(db.Numeric(10,2), nullable=False)
    cantidad_nueva = db.Column(db.Numeric(10,2), nullable=False)
    motivo = db.Column(db.String(255), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)


class SolicitudProduccion(db.Model):
    __tablename__ = 'solicitud_produccion'
    
    id = db.Column(db.Integer, primary_key=True)
    fk_producto = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    fk_empleado = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=False)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.Enum('PENDIENTE', 'APROBADA', 'RECHAZADA', 'EN_PRODUCCION', 'TERMINADA'), default='PENDIENTE')
    observaciones = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Relationships
    producto = db.relationship('Producto', backref='solicitudes_produccion')
    empleado = db.relationship('Empleado', backref='solicitudes_produccion')
    usuario_creador = db.relationship('Usuario', foreign_keys=[usuario_creacion], backref='solicitudes_creadas')
    usuario_editor = db.relationship('Usuario', foreign_keys=[usuario_movimiento], backref='solicitudes_editadas')
    
    
class Produccion(db.Model):
    __tablename__ = "produccion"

    id = db.Column(db.Integer, primary_key=True)
    fk_empleado = db.Column(db.Integer, db.ForeignKey("empleado.id"))
    fk_sucursal = db.Column(db.Integer, db.ForeignKey("sucursal.id"))

    estado = db.Column(db.Enum(
        "PENDIENTE", "EN PROCESO", "TERMINADO", "CANCELADO"
    ), default="PENDIENTE")

    estatus = db.Column(db.Enum("ACTIVO", "INACTIVO"), default="ACTIVO")

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_creacion = db.Column(db.Integer)
    usuario_movimiento = db.Column(db.Integer)


class ProduccionDetalle(db.Model):
    __tablename__ = 'produccion_detalle'

    id = db.Column(db.Integer, primary_key=True)
    fk_produccion = db.Column(db.Integer, nullable=False)
    fk_producto = db.Column(db.Integer, nullable=False)
    fk_solicitud = db.Column(db.Integer)

    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    cantidad_producto = db.Column(db.Integer, nullable=False)
    cantidad_merma = db.Column(db.Integer)

    origen = db.Column(db.String(50), nullable=False)

    usuario_creacion = db.Column(db.Integer, nullable=False)
    usuario_movimiento = db.Column(db.Integer, nullable=False)
    
class RecetaDetalle(db.Model):
    __tablename__ = "receta_detalle"

    id = db.Column(db.Integer, primary_key=True)
    fk_receta = db.Column(db.Integer, db.ForeignKey("receta.id"))
    fk_insumo = db.Column(db.Integer)
    fk_unidad = db.Column(db.Integer)
    cantidad_insumo = db.Column(db.Float)
    estatus = db.Column(db.String(10))