from flask import render_template, request, redirect, url_for, flash, session
from sqlalchemy import or_
from . import compras
from models import (
    db,
    Compra,
    CompraDetalle,
    CompraPago,
    Proveedor,
    Insumo,
    UnidadMedida,
    InventarioInsumo,
    InventarioInsumoMovimiento,
    MetodoPago,
    Empleado,
    Persona,
)
import datetime
from decimal import Decimal
from utils.session import get_current_employee_id, get_current_user_id, get_default_sucursal_id


def _parse_number(value, field_name):
    """Parse numeric form inputs allowing commas as decimal separator."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError(f"El campo {field_name} es obligatorio.")
    try:
        return float(raw.replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"El campo {field_name} no es un número válido.") from exc


@compras.route("/")
@compras.route("/inicio")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip()

    query = (
        Compra.query.join(Proveedor, Compra.fk_proveedor == Proveedor.id)
        .join(Empleado, Compra.fk_empleado == Empleado.id)
        .join(Persona, Empleado.fk_persona == Persona.id)
        .order_by(Compra.id.desc())
    )

    if buscar:
        like = f"%{buscar}%"
        query = query.filter(
            or_(
                Proveedor.nombre_comercial.ilike(like),
                Proveedor.razon_social.ilike(like),
                Persona.nombre.ilike(like),
                Persona.apellido_uno.ilike(like),
                Persona.apellido_dos.ilike(like),
            )
        )

    compras_list = query.all()
    return render_template("compras/inicio.html", compras=compras_list, buscar=buscar)


@compras.route("/agregar", methods=["GET", "POST"])
def agregar():
    proveedores = Proveedor.query.filter_by(estatus="ACTIVO").all()
    insumos = Insumo.query.filter_by(estatus="ACTIVO").all()
    unidades = UnidadMedida.query.filter_by(estatus="ACTIVO").all()
    metodos = MetodoPago.query.filter_by(estatus="ACTIVO").all()
    empleados = Empleado.query.filter_by(estatus="ACTIVO").all()
    sucursal_id = get_default_sucursal_id(default=None)

    if not proveedores:
        flash("No hay proveedores registrados. No se puede continuar con el alta de compras.", "warning")
        return redirect(url_for("proveedores.inicio"))
    if not insumos:
        flash("No hay insumos registrados. No se puede continuar con el alta de compras.", "warning")
        return redirect(url_for("insumos.inicio"))
    if not unidades:
        flash("No hay unidades de medida registradas. No se puede continuar con el alta de compras.", "warning")
        return redirect(url_for("compras.inicio"))
    if not metodos:
        flash("No hay métodos de pago registrados. No se puede continuar con el alta de compras.", "warning")
        return redirect(url_for("compras.inicio"))
    if not empleados:
        flash("No hay empleados registrados. No se puede continuar con el alta de compras.", "warning")
        return redirect(url_for("empleados.inicio"))
    if not sucursal_id:
        flash("No hay una sucursal activa configurada para registrar inventario. No se puede continuar.", "warning")
        return redirect(url_for("sucursales.inicio"))

    if "carrito_compra" not in session:
        session["carrito_compra"] = []

    if "compra_data" not in session:
        session["compra_data"] = {}

    carrito = session["carrito_compra"]
    compra_data = session["compra_data"]

    total = sum([item["subtotal"] for item in carrito])

    if request.method == "POST":

        accion = request.form.get("accion")

        if accion == "agregar":

            try:
                fk_insumo = int(request.form.get("fk_insumo"))
                fk_unidad = int(request.form.get("fk_unidad"))
            except (TypeError, ValueError):
                flash("Selecciona un insumo y una unidad válidos.", "warning")
                return redirect(url_for("compras.agregar"))

            try:
                cantidad = _parse_number(request.form.get("cantidad"), "Cantidad")
                costo = _parse_number(request.form.get("costo"), "Costo unitario")
            except ValueError as exc:
                flash(str(exc), "warning")
                return redirect(url_for("compras.agregar"))

            fecha_cad = (request.form.get("fecha_caducidad") or "").strip()

            if cantidad <= 0 or costo <= 0:
                flash("Cantidad y costo deben ser mayores a 0.", "warning")
                return redirect(url_for("compras.agregar"))

            if not fecha_cad:
                flash("La fecha de caducidad es obligatoria.", "warning")
                return redirect(url_for("compras.agregar"))

            if not compra_data:
                session["compra_data"] = {
                    "fk_proveedor": request.form.get("fk_proveedor"),
                    "fk_empleado": request.form.get("fk_empleado"),
                    "metodo_pago": request.form.get("metodo_pago")
                }

            insumo = Insumo.query.get(fk_insumo)
            unidad = UnidadMedida.query.get(fk_unidad)
            if not insumo or insumo.estatus != "ACTIVO":
                flash("El insumo seleccionado ya no está disponible.", "warning")
                return redirect(url_for("compras.agregar"))
            if not unidad or unidad.estatus != "ACTIVO":
                flash("La unidad seleccionada ya no está disponible.", "warning")
                return redirect(url_for("compras.agregar"))

            item = {
                "id": fk_insumo,
                "nombre": insumo.nombre,
                "cantidad": cantidad,
                "unidad": unidad.nombre,
                "fk_unidad": fk_unidad,
                "costo": costo,
                "fecha_caducidad": fecha_cad,
                "subtotal": cantidad * costo
            }

            carrito.append(item)
            session["carrito_compra"] = carrito
            session.modified = True
            flash(f"{insumo.nombre} se agregó al carrito.", "success")

            return redirect(url_for("compras.agregar"))


        elif accion.startswith("eliminar_"):

            id_insumo = int(accion.split("_")[1])
            carrito = [i for i in carrito if i["id"] != id_insumo]
            session["carrito_compra"] = carrito

            if not carrito:
                session.pop("compra_data", None)

            return redirect(url_for("compras.agregar"))


        elif accion == "cancelar":

            session.pop("carrito_compra", None)
            session.pop("compra_data", None)

            return redirect(url_for("compras.inicio"))


        elif accion == "confirmar":

            if not carrito:
                flash("Agrega al menos un insumo al carrito antes de confirmar la compra.", "warning")
                return redirect(url_for("compras.agregar"))

            try:
                fk_proveedor = int(compra_data.get("fk_proveedor"))
                fk_empleado = int(compra_data.get("fk_empleado"))
                metodo_pago = int(compra_data.get("metodo_pago"))
                usuario_id = get_current_user_id()
                if not sucursal_id:
                    flash("No hay una sucursal activa para registrar inventario.", "error")
                    return redirect(url_for("compras.agregar"))

                compra = Compra(
                    fk_proveedor=fk_proveedor,
                    fk_empleado=fk_empleado or get_current_employee_id(),
                    monto_total=total,
                )

                db.session.add(compra)
                db.session.flush()

                for item in carrito:
                    unidad = UnidadMedida.query.get(item["fk_unidad"])
                    cantidad_comprada = Decimal(str(item["cantidad"]))
                    factor_conversion = Decimal(str(unidad.factor_conversion or 1))
                    cantidad_convertida = cantidad_comprada * factor_conversion
                    fecha_caducidad = datetime.datetime.strptime(item["fecha_caducidad"], "%Y-%m-%d")

                    detalle = CompraDetalle(
                        fk_compra=compra.id,
                        fk_insumo=item["id"],
                        fk_unidad=item["fk_unidad"],
                        cantidad_comprada=cantidad_comprada,
                        cantidad_convertida=cantidad_convertida,
                        costo=item["costo"],
                        fecha_caducidad=fecha_caducidad,
                    )

                    db.session.add(detalle)

                    inventario = InventarioInsumo.query.filter_by(
                        fk_insumo=item["id"],
                        fk_sucursal=sucursal_id,
                    ).first()

                    if inventario:
                        cantidad_anterior = Decimal(str(inventario.cantidad or 0))
                        cantidad_nueva = cantidad_anterior + cantidad_convertida
                        inventario.cantidad = cantidad_nueva
                        inventario.fk_unidad = item["fk_unidad"]
                        inventario.estatus = "DISPONIBLE"
                        if not inventario.fecha_caducidad or fecha_caducidad < inventario.fecha_caducidad:
                            inventario.fecha_caducidad = fecha_caducidad
                        inventario.usuario_movimiento = usuario_id
                    else:
                        cantidad_anterior = Decimal("0")
                        cantidad_nueva = cantidad_convertida
                        inventario = InventarioInsumo(
                            fk_sucursal=sucursal_id,
                            fk_insumo=item["id"],
                            fk_unidad=item["fk_unidad"],
                            cantidad=cantidad_nueva,
                            fecha_caducidad=fecha_caducidad,
                            estatus="DISPONIBLE",
                            usuario_creacion=usuario_id,
                            usuario_movimiento=usuario_id,
                        )
                        db.session.add(inventario)
                        db.session.flush()

                    movimiento = InventarioInsumoMovimiento(
                        fk_inventario_insumo=inventario.id,
                        tipo_movimiento="AUDITORIA",
                        cantidad_anterior=cantidad_anterior,
                        cantidad_nueva=cantidad_nueva,
                        diferencia=cantidad_convertida,
                        motivo=f"Entrada por compra #{compra.id}",
                        usuario_movimiento=usuario_id,
                    )
                    db.session.add(movimiento)

                pago = CompraPago(
                    fk_compra=compra.id,
                    fk_metodopago=metodo_pago,
                    monto=total,
                )

                db.session.add(pago)
                db.session.commit()

                session.pop("carrito_compra", None)
                session.pop("compra_data", None)

                flash("Compra registrada", "success")
                return redirect(url_for("compras.inicio"))

            except Exception as e:
                print(e)
                db.session.rollback()
                flash("Error al guardar", "error")
        else:
            flash("Acción inválida. Intenta de nuevo.", "warning")

    return render_template(
        "compras/agregar.html",
        proveedores=proveedores,
        insumos=insumos,
        unidades=unidades,
        metodos_pago=metodos,
        empleados=empleados,
        carrito=carrito,
        total=total,
        compra_data=compra_data
    )


@compras.route("/detalle/<int:id>")
def detalle(id):
    compra = Compra.query.get_or_404(id)
    return render_template("compras/detalle.html", compra=compra)
