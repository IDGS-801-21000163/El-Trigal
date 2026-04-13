from flask import Blueprint

costo_producto = Blueprint(
    "costo_producto",
    __name__,
    template_folder= 'templates',
    static_folder= 'static'
)

from . import routes