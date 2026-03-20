from flask import Flask, redirect, render_template, url_for

from api import ALL_BLUEPRINTS
from api.common import ACTIONS, MODULES, NAV_MODULES
from config import DevelopmentConfig


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)

for module, blueprint in zip(MODULES, ALL_BLUEPRINTS):
    app.register_blueprint(blueprint, url_prefix=f"/{module['slug']}")


@app.context_processor
def inject_navigation():
    return {
        "nav_modules": NAV_MODULES,
        "actions": ACTIONS,
    }


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/registro")
def registro():
    return render_template("registro.html")


@app.route("/recuperar")
def recuperar():
    return render_template("recuperar.html")


@app.route("/panel")
def panel():
    return redirect(url_for("inventario_productos.inicio"))


if __name__ == "__main__":
    app.run(port=4000, debug=True)
