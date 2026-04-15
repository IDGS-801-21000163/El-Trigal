from flask import render_template, redirect, url_for, flash, request, session
from sqlalchemy import or_
from . import inventario_insumos
from models import db, InventarioInsumo, InventarioInsumoMovimiento, Insumo, Sucursal, UnidadMedida
from forms import InventarioInsumoForm
from datetime import datetime
import base64
from decimal import Decimal

MODULE = {
    "name": "Inventario de Insumos",
    "slug": "inventario_insumos",
    "description": "Gestión de inventario de insumos"
}

def usuario_sesion_id():
    return session.get("usuario_id") or 1


def _format_cantidad(cantidad, unidad: UnidadMedida | None):
    """Mostrar bonito: si está en base (g/ml), convertir a kg/L cuando aplique."""
    try:
        qty = Decimal(str(cantidad or 0))
    except Exception:
        qty = Decimal("0")

    nombre = (unidad.nombre if unidad else "").strip()
    if not nombre:
        return float(qty), ""

    q5 = Decimal("0.00001")

    def as_float(d: Decimal) -> float:
        # quantize a 5 decimales para evitar strings enormes, luego convertir a float.
        try:
            return float(d.quantize(q5))
        except Exception:
            return float(d)

    if nombre.lower() == "gramo" and qty >= Decimal("1000"):
        return as_float(qty / Decimal("1000")), "Kilogramo"

    if nombre.lower() == "mililitro" and qty >= Decimal("1000"):
        return as_float(qty / Decimal("1000")), "Litro"

    return as_float(qty), nombre


# ==========================
# LISTAR
# ==========================
@inventario_insumos.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()
    now = datetime.now()

    query = (
        InventarioInsumo.query.join(Insumo, InventarioInsumo.fk_insumo == Insumo.id)
        .join(UnidadMedida, InventarioInsumo.fk_unidad == UnidadMedida.id)
        .filter(InventarioInsumo.estatus != "INACTIVO")
    )
    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            or_(
                Insumo.nombre.ilike(like),
                UnidadMedida.nombre.ilike(like),
            )
        )

    inventario = query.all()
    touched = False
    for item in inventario:
        # Normalizar estatus por caducidad/cantidad (para que no se quede "DISPONIBLE" si ya venció).
        try:
            qty_raw = Decimal(str(item.cantidad or 0))
        except Exception:
            qty_raw = Decimal("0")

        if qty_raw <= 0:
            if item.estatus != "NO DISPONIBLE":
                item.estatus = "NO DISPONIBLE"
                touched = True
        elif item.fecha_caducidad and item.fecha_caducidad < now:
            if item.estatus != "CADUCADO":
                item.estatus = "CADUCADO"
                touched = True
        else:
            if item.estatus not in ("DISPONIBLE",):
                item.estatus = "DISPONIBLE"
                touched = True

        qty, unidad_nombre = _format_cantidad(item.cantidad, item.unidad)
        item.cantidad_display = qty
        item.unidad_display = unidad_nombre

    if touched:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    module = MODULE.copy()
    module["items"] = inventario
    return render_template("inventario-insumos/inicio.html", module=module, buscar=buscar)


# ==========================
# EDITAR CANTIDAD
# ==========================
@inventario_insumos.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    inventario = InventarioInsumo.query.get_or_404(id)
    form = InventarioInsumoForm()
    imagen = None
    if inventario.insumo and inventario.insumo.foto:
        foto = inventario.insumo.foto
        if isinstance(foto, (bytes, bytearray)):
            imagen = f"data:image/png;base64,{base64.b64encode(foto).decode('utf-8')}"
        elif isinstance(foto, str):
            imagen = foto if foto.startswith("data:image") else f"data:image/png;base64,{foto}"

    if request.method == "GET":
        try:
            form.cantidad.data = float(inventario.cantidad or 0)
        except (TypeError, ValueError):
            form.cantidad.data = 0

    if form.validate_on_submit():
        uid = usuario_sesion_id()

        cantidad_anterior = inventario.cantidad
        cantidad_nueva    = form.cantidad.data
        diferencia        = cantidad_nueva - cantidad_anterior

        # MOVIMIENTO
        movimiento = InventarioInsumoMovimiento(
            fk_inventario_insumo=inventario.id,
            tipo_movimiento=form.tipo_movimiento.data,
            cantidad_anterior=cantidad_anterior,
            cantidad_nueva=cantidad_nueva,
            diferencia=diferencia,
            motivo=form.motivo.data,
            usuario_movimiento=uid
        )
        db.session.add(movimiento)

        # ACTUALIZAR INVENTARIO
        inventario.cantidad          = cantidad_nueva
        inventario.usuario_movimiento = uid

        # ACTUALIZAR ESTADO
        if cantidad_nueva <= 0:
            inventario.estatus = "NO DISPONIBLE"
        # `datetime` aquí es la clase importada, no el módulo. Usar datetime.now() evita
        # el error: "datetime.datetime has no attribute datetime".
        elif inventario.fecha_caducidad and inventario.fecha_caducidad < datetime.now():
            inventario.estatus = "CADUCADO"
        else:
            inventario.estatus = "DISPONIBLE"

        db.session.commit()

        flash("Inventario actualizado correctamente.", "success")
        return redirect(url_for("inventario_insumos.inicio"))

    return render_template(
        "inventario-insumos/editar.html",
        form=form,
        inventario=inventario,
        imagen=imagen,
        module=MODULE,
        action_label="Editar"
    )
