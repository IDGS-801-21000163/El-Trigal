from flask import Blueprint

dashboard_reportes = Blueprint(
    "dashboard_reportes",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes
