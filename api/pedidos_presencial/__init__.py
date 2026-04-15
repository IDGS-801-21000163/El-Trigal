from flask import Blueprint

pedidos_presencial = Blueprint(
    "pedidos_presencial",
    __name__,
    template_folder="../../templates",
)

from . import routes  # noqa: E402,F401

