from flask import Blueprint

empleados = Blueprint(
    "empleados",
    __name__,
    template_folder= 'templates',
    static_folder= 'static'
)

from . import routes
