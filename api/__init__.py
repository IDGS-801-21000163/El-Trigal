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
from api.productos import productos
from api.produccion import produccion
from api.proveedores import proveedores
from api.puestos import puestos
from api.recetas import recetas
from api.sucursales import sucursales
from api.usuarios import usuarios
from api.ventas import ventas


ALL_BLUEPRINTS = [
    usuarios,
    puestos,
    empleados,
    proveedores,
    costo_producto,
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
    ventas,
    clientes,
]
