from api.clientes import clientes
from api.compras import compras
from api.categorias_insumos import categorias_insumos
from api.costo_producto import costo_producto
from api.categorias_productos import categorias_productos
from api.empleados import empleados
from api.insumos import insumos
from api.inventario_insumos import inventario_insumos
from api.inventario_productos import inventario_productos
from api.pedidos import pedidos
from api.pedidos_presencial import pedidos_presencial
from api.pos import pos
from api.productos import productos
from api.produccion import produccion
from api.proveedores import proveedores
from api.puestos import puestos
from api.recetas import recetas
from api.sucursales import sucursales
from api.usuarios import usuarios
from api.ventas import ventas
from api.solicitud_produccion import solicitud_produccion
from api.dashboard import dashboard
from api.reportes import reportes
from api.dashboard_reportes import dashboard_reportes


ALL_BLUEPRINTS = [
    dashboard,
    reportes,
    dashboard_reportes,
    usuarios,
    puestos,
    empleados,
    proveedores,
    sucursales,
    categorias_insumos,
    insumos,
    compras,
    inventario_insumos,
    categorias_productos,
    recetas,
    productos,
    inventario_productos,
    produccion,
    pedidos,
    pedidos_presencial,
    ventas,
    pos,
    solicitud_produccion,
    clientes,
    costo_producto,
]
