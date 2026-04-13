from flask import Blueprint

ventas = Blueprint(
    "ventas",
    __name__,
    template_folder="templates",
)

from . import routes
