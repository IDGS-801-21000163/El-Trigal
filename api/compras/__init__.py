
from flask import Blueprint
compras = Blueprint(
    'compras',
    __name__,
    template_folder='templates'
)


from .routes import compras
