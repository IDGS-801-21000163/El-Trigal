from flask import Blueprint


sucursales = Blueprint(
    "sucursales",
    __name__,
    template_folder="templates",
    static_folder="static",
)


from . import routes
