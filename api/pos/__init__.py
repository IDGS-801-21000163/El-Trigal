
from flask import Blueprint

pos=Blueprint(
    'pos',
    __name__,
    template_folder='templates'
)
from . import routes