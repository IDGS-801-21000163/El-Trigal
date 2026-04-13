from flask import Blueprint

inventario_insumos = Blueprint(
    "inventario_insumos",
    __name__,
    template_folder= 'templates',
    static_folder= 'static'
)

from . import routes