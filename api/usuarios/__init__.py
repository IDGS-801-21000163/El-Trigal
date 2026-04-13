from flask import Blueprint

usuarios = Blueprint(
    "usuarios",
    __name__,
    template_folder= 'templates',
    static_folder= 'static'
)

from . import routes