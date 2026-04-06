from flask import Blueprint

puestos = Blueprint(
    "puestos",
    __name__,
    template_folder= 'templates',
    static_folder= 'static'
)

from . import routes