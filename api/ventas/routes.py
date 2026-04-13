from flask import redirect, url_for

from . import ventas


@ventas.route("/")
@ventas.route("/inicio")
def inicio():
    return redirect(url_for("pos.inicio"))
