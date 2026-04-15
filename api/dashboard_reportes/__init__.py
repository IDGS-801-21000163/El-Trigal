from flask import Blueprint, redirect, url_for

# Compat: antes existía el módulo "dashboard-reportes". Ahora son 2 módulos:
# /dashboard y /reportes. Dejamos este blueprint solo para redirecciones.
dashboard_reportes = Blueprint("dashboard_reportes", __name__)


@dashboard_reportes.route("/")
def inicio():
    return redirect(url_for("dashboard.inicio"))


@dashboard_reportes.route("/exportar")
def exportar():
    return redirect(url_for("reportes.inicio"))

