from flask import Blueprint

categorias_insumos = Blueprint(
    "categorias_insumos",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes
