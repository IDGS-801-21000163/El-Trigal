from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()


# =====================================================
# ROL Y USUARIO
# =====================================================

class Rol(db.Model):
    __tablename__ = 'rol'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(50), nullable=False, unique=True)
    descripcion        = db.Column(db.Text,       nullable=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    usuarios        = db.relationship('Usuario',   backref='rol', lazy=True, foreign_keys='Usuario.fk_rol')
    permisos_modulo = db.relationship('RolModulo', backref='rol', lazy=True, cascade='all, delete-orphan')


class Modulo(db.Model):
    __tablename__ = 'modulo'

    id     = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    ruta   = db.Column(db.String(80), nullable=False, unique=True)

    permisos_rol = db.relationship('RolModulo', backref='modulo', lazy=True, cascade='all, delete-orphan')


class RolModulo(db.Model):
    __tablename__ = 'rol_modulo'

    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_rol    = db.Column(db.Integer, db.ForeignKey('rol.id'),    nullable=False)
    fk_modulo = db.Column(db.Integer, db.ForeignKey('modulo.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('fk_rol', 'fk_modulo', name='uq_rol_modulo'),
    )


class Usuario(db.Model):
    __tablename__ = 'usuario'

    id                  = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    fk_rol              = db.Column(db.Integer,      db.ForeignKey('rol.id'), nullable=False)
    nick                = db.Column(db.String(254),  nullable=False, unique=True)
    clave               = db.Column(db.String(255),  nullable=False)
    intentos_fallidos   = db.Column(db.SmallInteger, nullable=False, default=0)
    bloqueado_hasta     = db.Column(db.DateTime,     nullable=True)
    ultimo_login        = db.Column(db.DateTime,     nullable=True)
    fecha_cambio_clave  = db.Column(db.DateTime,     nullable=True)
    forzar_cambio_clave = db.Column(db.SmallInteger, nullable=False, default=0)
    estatus             = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion      = db.Column(db.DateTime,     nullable=False, default=datetime.datetime.now)
    usuario_creacion    = db.Column(db.Integer,      db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento    = db.Column(db.DateTime,     nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento  = db.Column(db.Integer,      db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    otps = db.relationship('UsuarioOtp', backref='usuario', lazy=True)


class UsuarioOtp(db.Model):
    __tablename__ = 'usuario_otp'

    id             = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    fk_usuario     = db.Column(db.Integer,      db.ForeignKey('usuario.id'), nullable=False)
    token          = db.Column(db.String(10),   nullable=False)
    expiracion     = db.Column(db.DateTime,     nullable=False)
    utilizado      = db.Column(db.SmallInteger, nullable=False, default=0)
    fecha_creacion = db.Column(db.DateTime,     nullable=False, default=datetime.datetime.now)


# =====================================================
# CATÁLOGOS GEOGRÁFICOS
# =====================================================

class Estado(db.Model):
    __tablename__ = 'estado'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(50), nullable=False, unique=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    municipios  = db.relationship('Municipio', backref='estado', lazy=True)
    direcciones = db.relationship('Direccion', backref='estado', lazy=True)


class Municipio(db.Model):
    __tablename__ = 'municipio'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_estado          = db.Column(db.Integer,    db.ForeignKey('estado.id'), nullable=False)
    nombre             = db.Column(db.String(50), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    direcciones = db.relationship('Direccion', backref='municipio', lazy=True)


class Direccion(db.Model):
    __tablename__ = 'direccion'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_estado          = db.Column(db.Integer,    db.ForeignKey('estado.id'),    nullable=False)
    fk_municipio       = db.Column(db.Integer,    db.ForeignKey('municipio.id'), nullable=False)
    codigo_postal      = db.Column(db.String(20), nullable=False)
    colonia            = db.Column(db.String(65), nullable=False)
    calle              = db.Column(db.String(65), nullable=False)
    num_interior       = db.Column(db.String(20), nullable=True)
    num_exterior       = db.Column(db.String(20), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    personas    = db.relationship('Persona',   backref='direccion', lazy=True)
    sucursales  = db.relationship('Sucursal',  backref='direccion', lazy=True)
    proveedores = db.relationship('Proveedor', backref='direccion', lazy=True)


# =====================================================
# PERSONAS, PUESTOS, SUCURSALES, EMPLEADOS
# =====================================================

class Persona(db.Model):
    __tablename__ = 'persona'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_usuario         = db.Column(db.Integer,    db.ForeignKey('usuario.id'),   nullable=True)
    fk_direccion       = db.Column(db.Integer,    db.ForeignKey('direccion.id'), nullable=True)
    nombre             = db.Column(db.String(65), nullable=False)
    apellido_uno       = db.Column(db.String(65), nullable=False)
    apellido_dos       = db.Column(db.String(65), nullable=True)
    telefono           = db.Column(db.String(15), nullable=True,  unique=True)
    correo             = db.Column(db.String(254),nullable=True,  unique=True)
    foto               = db.Column(db.LargeBinary(length=2**32 - 1), nullable=True)  # BLOB/LONGBLOB
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    empleado = db.relationship('Empleado', backref='persona', uselist=False, lazy=True)
    usuario  = db.relationship('Usuario',  foreign_keys=[fk_usuario], backref=db.backref('persona', uselist=False))
    cliente  = db.relationship('Cliente',  backref='persona', uselist=False, lazy=True)


class Puesto(db.Model):
    __tablename__ = 'puesto'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(65),    nullable=False, unique=True)
    descripcion        = db.Column(db.Text,          nullable=False)
    sueldo             = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    empleados = db.relationship('Empleado', backref='puesto', lazy=True)


class Sucursal(db.Model):
    __tablename__ = 'sucursal'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_direccion       = db.Column(db.Integer,    db.ForeignKey('direccion.id'), nullable=False)
    nombre             = db.Column(db.String(65), nullable=False)
    telefono           = db.Column(db.String(15), nullable=False, unique=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    producciones         = db.relationship('Produccion',         backref='sucursal', lazy=True)
    inventarios_insumo   = db.relationship('InventarioInsumo',   backref='sucursal', lazy=True)
    inventarios_producto = db.relationship('InventarioProducto', backref='sucursal', lazy=True)
    pedidos              = db.relationship('Pedido',             backref='sucursal', lazy=True)
    ventas               = db.relationship('Venta',              backref='sucursal', lazy=True)
    cajas                = db.relationship('Caja',               backref='sucursal', lazy=True)


class Empleado(db.Model):
    __tablename__ = 'empleado'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_puesto          = db.Column(db.Integer,    db.ForeignKey('puesto.id'),  nullable=False)
    fk_persona         = db.Column(db.Integer,    db.ForeignKey('persona.id'), nullable=False)
    num_empleado       = db.Column(db.String(50), nullable=False, unique=True)
    fecha_contratacion = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    compras      = db.relationship('Compra',              backref='empleado', lazy=True)
    producciones = db.relationship('Produccion',          backref='empleado', lazy=True)
    pedidos      = db.relationship('Pedido',              backref='empleado', lazy=True)
    ventas       = db.relationship('Venta',               backref='empleado', lazy=True)
    solicitudes  = db.relationship('SolicitudProduccion', backref='empleado', lazy=True)


# =====================================================
# PROVEEDORES E INSUMOS
# =====================================================

class Proveedor(db.Model):
    __tablename__ = 'proveedor'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    fk_direccion       = db.Column(db.Integer,    db.ForeignKey('direccion.id'), nullable=False)
    nombre_comercial   = db.Column(db.String(65), nullable=False)
    razon_social       = db.Column(db.String(65), nullable=False)
    correo             = db.Column(db.String(254),nullable=False, unique=True)
    telefono           = db.Column(db.String(15), nullable=False, unique=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    compras = db.relationship('Compra', backref='proveedor', lazy=True)


class CategoriaInsumo(db.Model):
    __tablename__ = 'categoria_insumo'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(65), nullable=False, unique=True)
    descripcion        = db.Column(db.Text,       nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    insumos = db.relationship('Insumo', backref='categoria', lazy=True)


class Insumo(db.Model):
    __tablename__ = 'insumo'

    id                 = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    fk_categoria       = db.Column(db.Integer,      db.ForeignKey('categoria_insumo.id'), nullable=False)
    nombre             = db.Column(db.String(65),   nullable=False, unique=True)
    porcentaje_merma   = db.Column(db.Numeric(5,2), nullable=False, default=0.00)
    # En BD normalmente es BLOB/LONGBLOB. Conservamos compat: el runtime tambien soporta strings base64 viejos.
    foto               = db.Column(db.LargeBinary(length=2**32 - 1), nullable=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,     nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,      db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,     nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,      db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    compra_detalles    = db.relationship('CompraDetalle',    backref='insumo', lazy=True)
    inventarios        = db.relationship('InventarioInsumo', backref='insumo', lazy=True)
    receta_detalles    = db.relationship('RecetaDetalle',    backref='insumo', lazy=True)
    produccion_insumos = db.relationship('ProduccionInsumo', backref='insumo', lazy=True)


# =====================================================
# MÉTODOS DE PAGO
# =====================================================

class MetodoPago(db.Model):
    __tablename__ = 'metodo_pago'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(65), nullable=False, unique=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    compra_pagos     = db.relationship('CompraPago',     backref='metodo_pago', lazy=True)
    pedido_anticipos = db.relationship('PedidoAnticipo', backref='metodo_pago', lazy=True)
    venta_pagos      = db.relationship('VentaPago',      backref='metodo_pago', lazy=True)


# =====================================================
# COMPRAS
# =====================================================

class Compra(db.Model):
    __tablename__ = 'compra'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_proveedor       = db.Column(db.Integer,       db.ForeignKey('proveedor.id'), nullable=False)
    fk_empleado        = db.Column(db.Integer,       db.ForeignKey('empleado.id'),  nullable=False)
    monto_total        = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    detalles = db.relationship('CompraDetalle', backref='compra', lazy=True)
    pagos    = db.relationship('CompraPago',    backref='compra', lazy=True)


class CompraDetalle(db.Model):
    __tablename__ = 'compra_detalle'

    id                  = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_compra           = db.Column(db.Integer,       db.ForeignKey('compra.id'),       nullable=False)
    fk_insumo           = db.Column(db.Integer,       db.ForeignKey('insumo.id'),        nullable=False)
    fk_unidad           = db.Column(db.Integer,       db.ForeignKey('unidad_medida.id'), nullable=False)
    cantidad_comprada   = db.Column(db.Numeric(15,5), nullable=False)
    cantidad_convertida = db.Column(db.Numeric(15,5), nullable=False)
    costo               = db.Column(db.Numeric(10,2), nullable=False)
    fecha_caducidad     = db.Column(db.Date,          nullable=False)
    estatus             = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion      = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion    = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento    = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento  = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    unidad             = db.relationship('UnidadMedida',    foreign_keys=[fk_unidad])
    inventarios_insumo = db.relationship('InventarioInsumo', backref='compra_detalle', lazy=True)


class CompraPago(db.Model):
    __tablename__ = 'compra_pago'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_compra          = db.Column(db.Integer,       db.ForeignKey('compra.id'),      nullable=False)
    fk_metodopago      = db.Column(db.Integer,       db.ForeignKey('metodo_pago.id'), nullable=False)
    monto              = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


# =====================================================
# UNIDAD DE MEDIDA
# =====================================================

class UnidadMedida(db.Model):
    __tablename__ = 'unidad_medida'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(50),    nullable=False, unique=True)
    factor_conversion  = db.Column(db.Numeric(15,5), nullable=False, default=1.00000)
    fk_unidad_base     = db.Column(db.Integer,       db.ForeignKey('unidad_medida.id'), nullable=True)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Auto-referencia
    unidad_base      = db.relationship('UnidadMedida', remote_side='UnidadMedida.id', backref='unidades_derivadas')


# =====================================================
# INVENTARIO DE INSUMOS
# =====================================================

class InventarioInsumo(db.Model):
    __tablename__ = 'inventario_insumo'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_sucursal        = db.Column(db.Integer,       db.ForeignKey('sucursal.id'),      nullable=False)
    fk_insumo          = db.Column(db.Integer,       db.ForeignKey('insumo.id'),         nullable=False)
    fk_unidad          = db.Column(db.Integer,       db.ForeignKey('unidad_medida.id'),  nullable=False)
    cantidad           = db.Column(db.Numeric(15,5), nullable=False)
    fecha_caducidad    = db.Column(db.DateTime,      nullable=True)
    # ── V8: manejo por lotes ──────────────────────────────────────────────────
    lote               = db.Column(db.String(50),    nullable=True)
    fk_compra_detalle  = db.Column(db.Integer,       db.ForeignKey('compra_detalle.id'), nullable=True)
    # ─────────────────────────────────────────────────────────────────────────
    estatus            = db.Column(db.Enum('DISPONIBLE', 'CADUCADO', 'NO DISPONIBLE'), nullable=True)
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    unidad      = db.relationship('UnidadMedida', foreign_keys=[fk_unidad])
    movimientos = db.relationship('InventarioInsumoMovimiento', backref='inventario_insumo', lazy=True)


class InventarioInsumoMovimiento(db.Model):
    __tablename__ = 'inventario_insumo_movimiento'

    id                   = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_inventario_insumo = db.Column(db.Integer,       db.ForeignKey('inventario_insumo.id'), nullable=False)
    tipo_movimiento      = db.Column(db.Enum('MERMA', 'ERROR', 'AUDITORIA'), nullable=False)
    cantidad_anterior    = db.Column(db.Numeric(15,5), nullable=False)
    cantidad_nueva       = db.Column(db.Numeric(15,5), nullable=False)
    diferencia           = db.Column(db.Numeric(15,5), nullable=False)
    motivo               = db.Column(db.String(255),   nullable=False)
    fecha_movimiento     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_movimiento   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


# =====================================================
# PRODUCTOS Y RECETAS
# =====================================================

class CategoriaProducto(db.Model):
    __tablename__ = 'categoria_producto'

    id                 = db.Column(db.Integer,    primary_key=True, autoincrement=True)
    nombre             = db.Column(db.String(65), nullable=False)
    descripcion        = db.Column(db.Text,       nullable=False)
    # ── V6/V8: foto agregada ──────────────────────────────────────────────────
    foto               = db.Column(db.LargeBinary(length=2**32 - 1), nullable=True)  # LONGBLOB
    # ─────────────────────────────────────────────────────────────────────────
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,   nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,    db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    productos = db.relationship('Producto', backref='categoria', lazy=True)


class Producto(db.Model):
    __tablename__ = 'producto'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_categoria       = db.Column(db.Integer,       db.ForeignKey('categoria_producto.id'), nullable=False)
    nombre             = db.Column(db.String(65),    nullable=False)
    precio             = db.Column(db.Numeric(10,2), nullable=False)
    costo_produccion   = db.Column(db.Numeric(10,2), nullable=False, default=0.00)
    # ── V8: control de producción por lotes ──────────────────────────────────
    cantidad_por_lote  = db.Column(db.Integer,       nullable=True, default=10)
    # ─────────────────────────────────────────────────────────────────────────
    foto               = db.Column(db.LargeBinary(length=2**32 - 1), nullable=True)  # LONGBLOB
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    receta              = db.relationship('Receta',              backref='producto', uselist=False, lazy=True)
    inventarios         = db.relationship('InventarioProducto',  backref='producto', lazy=True)
    solicitudes         = db.relationship('SolicitudProduccion', backref='producto', lazy=True)
    produccion_detalles = db.relationship('ProduccionDetalle',   backref='producto', lazy=True)


class Receta(db.Model):
    __tablename__ = 'receta'

    id                 = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_producto        = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    descripcion        = db.Column(db.Text,    nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    detalles = db.relationship('RecetaDetalle', backref='receta', lazy=True)


class RecetaDetalle(db.Model):
    __tablename__ = 'receta_detalle'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_receta          = db.Column(db.Integer,       db.ForeignKey('receta.id'),        nullable=False)
    fk_insumo          = db.Column(db.Integer,       db.ForeignKey('insumo.id'),         nullable=False)
    fk_unidad          = db.Column(db.Integer,       db.ForeignKey('unidad_medida.id'),  nullable=False)
    cantidad_insumo    = db.Column(db.Numeric(15,5), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    unidad = db.relationship('UnidadMedida', foreign_keys=[fk_unidad])


# =====================================================
# INVENTARIO DE PRODUCTOS
# =====================================================

class InventarioProducto(db.Model):
    __tablename__ = 'inventario_producto'

    id                    = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_producto           = db.Column(db.Integer,       db.ForeignKey('producto.id'),           nullable=False)
    fk_sucursal           = db.Column(db.Integer,       db.ForeignKey('sucursal.id'),            nullable=False)
    cantidad_producto     = db.Column(db.Numeric(10,2), nullable=False)
    fecha_caducidad       = db.Column(db.DateTime,      nullable=False)
    # ── V8: trazabilidad y merma ──────────────────────────────────────────────
    fk_produccion_detalle = db.Column(db.Integer,       db.ForeignKey('produccion_detalle.id'),  nullable=True)
    es_merma              = db.Column(db.Boolean,       nullable=False, default=False)
    # ─────────────────────────────────────────────────────────────────────────
    estatus               = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion        = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion      = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento      = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento    = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    produccion_detalle = db.relationship('ProduccionDetalle', foreign_keys=[fk_produccion_detalle],
                                         backref='inventarios_producto', lazy=True)
    movimientos        = db.relationship('InventarioProductoMovimiento', backref='inventario_producto', lazy=True)
    venta_detalle_lotes = db.relationship('VentaDetalleLote', backref='inventario_producto', lazy=True)


class InventarioProductoMovimiento(db.Model):
    __tablename__ = 'inventario_producto_movimiento'

    id                     = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_inventario_producto = db.Column(db.Integer,       db.ForeignKey('inventario_producto.id'), nullable=False)
    tipo_movimiento        = db.Column(db.Enum('MERMA', 'ERROR', 'AUDITORIA'), nullable=False)
    cantidad_anterior      = db.Column(db.Numeric(10,2), nullable=False)
    cantidad_nueva         = db.Column(db.Numeric(10,2), nullable=False)
    diferencia             = db.Column(db.Numeric(10,2), nullable=False)
    motivo                 = db.Column(db.String(255),   nullable=False)
    fecha_movimiento       = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_movimiento     = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


# =====================================================
# PRODUCCIÓN
# =====================================================

class Produccion(db.Model):
    __tablename__ = 'produccion'

    id                 = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_empleado        = db.Column(db.Integer, db.ForeignKey('empleado.id'), nullable=False)
    fk_sucursal        = db.Column(db.Integer, db.ForeignKey('sucursal.id'), nullable=False)
    estado             = db.Column(db.Enum('PENDIENTE', 'EN PROCESO', 'TERMINADO', 'CANCELADO'), default='PENDIENTE')
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    insumos  = db.relationship('ProduccionInsumo',  backref='produccion', lazy=True)
    detalles = db.relationship('ProduccionDetalle', backref='produccion', lazy=True)


class ProduccionInsumo(db.Model):
    __tablename__ = 'produccion_insumo'

    id                  = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_produccion       = db.Column(db.Integer,       db.ForeignKey('produccion.id'), nullable=False)
    fk_insumo           = db.Column(db.Integer,       db.ForeignKey('insumo.id'),     nullable=False)
    cantidad_requerida  = db.Column(db.Numeric(15,5), nullable=False)
    cantidad_consumida  = db.Column(db.Numeric(15,5), nullable=False)
    cantidad_merma_real = db.Column(db.Numeric(15,5), nullable=False, default=0.00)
    observacion         = db.Column(db.String(255),   nullable=True)
    estatus             = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion      = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion    = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento    = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento  = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


class ProduccionDetalle(db.Model):
    __tablename__ = 'produccion_detalle'

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_produccion       = db.Column(db.Integer, db.ForeignKey('produccion.id'),           nullable=False)
    fk_producto         = db.Column(db.Integer, db.ForeignKey('producto.id'),              nullable=False)
    # ── V8: relación con solicitud de ventas ──────────────────────────────────
    fk_solicitud        = db.Column(db.Integer, db.ForeignKey('solicitud_produccion.id'),  nullable=True)
    # ─────────────────────────────────────────────────────────────────────────
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    cantidad_producto   = db.Column(db.Integer, nullable=False)
    cantidad_merma      = db.Column(db.Integer, nullable=True)
    origen              = db.Column(db.Enum('INTERNO', 'SOLICITUD_VENTAS'), nullable=False, default='INTERNO')
    estatus             = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion      = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion    = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento    = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    solicitud = db.relationship('SolicitudProduccion', foreign_keys=[fk_solicitud])


class SolicitudProduccion(db.Model):
    __tablename__ = 'solicitud_produccion'

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_producto         = db.Column(db.Integer, db.ForeignKey('producto.id'),  nullable=False)
    fk_empleado         = db.Column(db.Integer, db.ForeignKey('empleado.id'),  nullable=False)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    estado              = db.Column(db.Enum('PENDIENTE', 'APROBADA', 'RECHAZADA', 'EN_PRODUCCION', 'TERMINADA'),
                                    default='PENDIENTE')
    observaciones       = db.Column(db.Text,    nullable=True)
    fecha_creacion      = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion    = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento    = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    produccion_detalles = db.relationship('ProduccionDetalle', backref='solicitud_produccion',
                                          foreign_keys='ProduccionDetalle.fk_solicitud', lazy=True)


# =====================================================
# CLIENTES
# =====================================================

class Cliente(db.Model):
    __tablename__ = 'cliente'

    id                 = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_persona         = db.Column(db.Integer, db.ForeignKey('persona.id'), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)
    ventas  = db.relationship('Venta',  backref='cliente', lazy=True)


# =====================================================
# PEDIDOS
# =====================================================

class Pedido(db.Model):
    __tablename__ = 'pedido'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_cliente         = db.Column(db.Integer,       db.ForeignKey('cliente.id'),  nullable=False)
    fk_empleado        = db.Column(db.Integer,       db.ForeignKey('empleado.id'), nullable=False)
    fk_sucursal        = db.Column(db.Integer,       db.ForeignKey('sucursal.id'), nullable=False)
    tipo_pedido        = db.Column(db.Enum('PRESENCIAL', 'EN_LINEA'), nullable=False, default='PRESENCIAL')
    notas              = db.Column(db.Text,          nullable=True)
    fecha_pedido       = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    fecha_entrega      = db.Column(db.DateTime,      nullable=False)
    # ── V8: campos financieros ────────────────────────────────────────────────
    subtotal           = db.Column(db.Numeric(10,2), nullable=True,  default=0)
    descuento          = db.Column(db.Numeric(10,2), nullable=True,  default=0)
    total              = db.Column(db.Numeric(10,2), nullable=True,  default=0)
    total_pagado       = db.Column(db.Numeric(10,2), nullable=True,  default=0)
    # ─────────────────────────────────────────────────────────────────────────
    # ── V8: estado NO_RECOGIDO agregado ──────────────────────────────────────
    estado             = db.Column(db.Enum('ESPERANDO', 'EN PRODUCCION', 'LISTO',
                                           'ENTREGADO', 'NO_RECOGIDO', 'CANCELADO'),
                                   nullable=False, default='ESPERANDO')
    # ─────────────────────────────────────────────────────────────────────────
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    detalles  = db.relationship('PedidoDetalle',  backref='pedido', lazy=True)
    anticipos = db.relationship('PedidoAnticipo', backref='pedido', lazy=True)
    ventas    = db.relationship('Venta',          backref='pedido', lazy=True)


class PedidoDetalle(db.Model):
    __tablename__ = 'pedido_detalle'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_pedido          = db.Column(db.Integer,       db.ForeignKey('pedido.id'),   nullable=False)
    fk_producto        = db.Column(db.Integer,       db.ForeignKey('producto.id'), nullable=False)
    cantidad_producto  = db.Column(db.Integer,       nullable=False)
    precio_unitario    = db.Column(db.Numeric(10,2), nullable=False, default=0.00)
    subtotal           = db.Column(db.Numeric(10,2), nullable=False, default=0.00)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    producto = db.relationship('Producto', foreign_keys=[fk_producto])


class PedidoAnticipo(db.Model):
    __tablename__ = 'pedido_anticipo'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_pedido          = db.Column(db.Integer,       db.ForeignKey('pedido.id'),      nullable=False)
    fk_metodopago      = db.Column(db.Integer,       db.ForeignKey('metodo_pago.id'), nullable=False)
    monto              = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


# =====================================================
# VENTAS Y CAJA
# =====================================================

class Venta(db.Model):
    __tablename__ = 'venta'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_sucursal        = db.Column(db.Integer,       db.ForeignKey('sucursal.id'),  nullable=False)
    fk_empleado        = db.Column(db.Integer,       db.ForeignKey('empleado.id'),  nullable=False)
    fk_pedido          = db.Column(db.Integer,       db.ForeignKey('pedido.id'),    nullable=True)
    fk_cliente         = db.Column(db.Integer,       db.ForeignKey('cliente.id'),   nullable=False)
    folio_ticket       = db.Column(db.Integer,       nullable=False, unique=True)
    total              = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO', 'CANCELADO'), default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    detalles      = db.relationship('VentaDetalle', backref='venta', lazy=True)
    pagos         = db.relationship('VentaPago',    backref='venta', lazy=True)
    caja_detalles = db.relationship('CajaDetalle',  backref='venta', lazy=True)


class VentaDetalle(db.Model):
    __tablename__ = 'venta_detalle'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_venta           = db.Column(db.Integer,       db.ForeignKey('venta.id'),        nullable=False)
    fk_producto        = db.Column(db.Integer,       db.ForeignKey('producto.id'),      nullable=False)
    fk_unidad          = db.Column(db.Integer,       db.ForeignKey('unidad_medida.id'), nullable=False)
    cantidad_producto  = db.Column(db.Numeric(10,2), nullable=False)
    precio_unitario    = db.Column(db.Numeric(10,2), nullable=False)
    subtotal           = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    producto    = db.relationship('Producto',     foreign_keys=[fk_producto])
    unidad      = db.relationship('UnidadMedida', foreign_keys=[fk_unidad])
    # ── V8: trazabilidad de lotes en ventas ───────────────────────────────────
    lotes       = db.relationship('VentaDetalleLote', backref='venta_detalle', lazy=True)


# ── V8: tabla nueva — de qué lote de inventario proviene cada línea de venta ──
class VentaDetalleLote(db.Model):
    __tablename__ = 'venta_detalle_lote'

    id                     = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_venta_detalle       = db.Column(db.Integer,       db.ForeignKey('venta_detalle.id'),       nullable=False)
    fk_inventario_producto = db.Column(db.Integer,       db.ForeignKey('inventario_producto.id'), nullable=False)
    cantidad               = db.Column(db.Numeric(10,2), nullable=False)


class VentaPago(db.Model):
    __tablename__ = 'venta_pago'

    id                 = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_venta           = db.Column(db.Integer,       db.ForeignKey('venta.id'),       nullable=False)
    fk_metodopago      = db.Column(db.Integer,       db.ForeignKey('metodo_pago.id'), nullable=False)
    monto_pagado       = db.Column(db.Numeric(10,2), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)


class Caja(db.Model):
    __tablename__ = 'caja'

    id                   = db.Column(db.Integer,       primary_key=True, autoincrement=True)
    fk_sucursal          = db.Column(db.Integer,       db.ForeignKey('sucursal.id'), nullable=False)
    fk_empleado_apertura = db.Column(db.Integer,       db.ForeignKey('empleado.id'), nullable=False)
    monto_inicial        = db.Column(db.Numeric(10,2), nullable=False)
    monto_final          = db.Column(db.Numeric(10,2), nullable=True)
    fecha_apertura       = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    fecha_cierre         = db.Column(db.DateTime,      nullable=True)
    estatus              = db.Column(db.Enum('ABIERTA', 'CERRADA'), nullable=False, default='ABIERTA')
    fecha_creacion       = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now)
    usuario_creacion     = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento     = db.Column(db.DateTime,      nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento   = db.Column(db.Integer,       db.ForeignKey('usuario.id'), nullable=False)

    # Relaciones
    empleado_apertura = db.relationship('Empleado',    foreign_keys=[fk_empleado_apertura])
    detalles          = db.relationship('CajaDetalle', backref='caja', lazy=True)


class CajaDetalle(db.Model):
    __tablename__ = 'caja_detalle'

    id                 = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fk_caja            = db.Column(db.Integer, db.ForeignKey('caja.id'),  nullable=False)
    fk_venta           = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False)
    estatus            = db.Column(db.Enum('ACTIVO', 'INACTIVO'), nullable=False, default='ACTIVO')
    fecha_creacion     = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now)
    usuario_creacion   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_movimiento   = db.Column(db.DateTime,nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    usuario_movimiento = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
