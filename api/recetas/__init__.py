from flask import Blueprint

recetas=Blueprint(
    'recetas',
    __name__,
    template_folder='templates'
)
from . import routes