import csv
import io
from datetime import date, datetime, timedelta

from flask import make_response, render_template, request
from sqlalchemy import func

from . import reportes
from models import Cliente, Persona, Producto, Venta, VentaDetalle


MODULE = {
    "name": "Reportes",
    "slug": "reportes",
    "description": "Descarga de reportes operativos y comerciales.",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _default_range(periodo: str):
    hoy = datetime.now().date()
    if periodo == "hoy":
        return hoy, hoy
    if periodo == "7d":
        return hoy - timedelta(days=6), hoy
    if periodo == "30d":
        return hoy - timedelta(days=29), hoy
    return hoy - timedelta(days=29), hoy


def _date_filters(desde: date, hasta: date):
    # Inclusivo por día; fecha_creacion es DATETIME.
    start_dt = datetime.combine(desde, datetime.min.time())
    end_dt = datetime.combine(hasta, datetime.max.time())
    return start_dt, end_dt


def _csv_response(rows: list[dict], filename: str):
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("sin_datos\n")

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@reportes.route("/")
def inicio():
    tipo = request.args.get("tipo", "ventas", type=str)
    periodo = request.args.get("periodo", "30d", type=str)
    desde_qs = _parse_date(request.args.get("desde"))
    hasta_qs = _parse_date(request.args.get("hasta"))
    # UI: si el usuario usa "Personalizado" mandamos periodo=custom.
    periodo_for_range = periodo if periodo != "custom" else "30d"
    if desde_qs and hasta_qs:
        desde, hasta = desde_qs, hasta_qs
    else:
        desde, hasta = _default_range(periodo_for_range)

    return render_template(
        "reportes/inicio.html",
        module=MODULE,
        current_action="inicio",
        filtros={"tipo": tipo, "periodo": periodo, "desde": desde.isoformat(), "hasta": hasta.isoformat()},
    )


@reportes.route("/exportar")
def exportar():
    tipo = request.args.get("tipo", "ventas", type=str)
    periodo = request.args.get("periodo", "30d", type=str)
    desde_qs = _parse_date(request.args.get("desde"))
    hasta_qs = _parse_date(request.args.get("hasta"))
    periodo_for_range = periodo if periodo != "custom" else "30d"
    if desde_qs and hasta_qs:
        desde, hasta = desde_qs, hasta_qs
    else:
        desde, hasta = _default_range(periodo_for_range)

    start_dt, end_dt = _date_filters(desde, hasta)

    if tipo == "top_productos":
        rows_db = (
            VentaDetalle.query.join(Producto, Producto.id == VentaDetalle.fk_producto)
            .join(Venta, Venta.id == VentaDetalle.fk_venta)
            .filter(Venta.fecha_creacion >= start_dt, Venta.fecha_creacion <= end_dt, Venta.estatus == "ACTIVO")
            .with_entities(
                Producto.nombre.label("producto"),
                func.sum(VentaDetalle.cantidad_producto).label("cantidad"),
                func.sum(VentaDetalle.subtotal).label("ingreso"),
            )
            .group_by(Producto.nombre)
            .order_by(func.sum(VentaDetalle.cantidad_producto).desc())
            .limit(25)
            .all()
        )
        rows = [
            {
                "producto": item.producto,
                "cantidad": float(item.cantidad or 0),
                "ingreso": round(float(item.ingreso or 0), 2),
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
            }
            for item in rows_db
        ]
        return _csv_response(rows, f"top-productos-{desde.isoformat()}-{hasta.isoformat()}.csv")

    if tipo == "menos_productos":
        # Incluye productos con 0 ventas en el rango (LEFT JOIN al agregado).
        ventas_agg = (
            VentaDetalle.query.join(Venta, Venta.id == VentaDetalle.fk_venta)
            .filter(Venta.fecha_creacion >= start_dt, Venta.fecha_creacion <= end_dt, Venta.estatus == "ACTIVO")
            .with_entities(
                VentaDetalle.fk_producto.label("fk_producto"),
                func.sum(VentaDetalle.cantidad_producto).label("cantidad"),
                func.sum(VentaDetalle.subtotal).label("ingreso"),
            )
            .group_by(VentaDetalle.fk_producto)
            .subquery()
        )

        rows_db = (
            Producto.query.outerjoin(ventas_agg, ventas_agg.c.fk_producto == Producto.id)
            .filter(Producto.estatus == "ACTIVO")
            .with_entities(
                Producto.nombre.label("producto"),
                func.coalesce(ventas_agg.c.cantidad, 0).label("cantidad"),
                func.coalesce(ventas_agg.c.ingreso, 0).label("ingreso"),
            )
            .order_by(func.coalesce(ventas_agg.c.cantidad, 0).asc(), Producto.nombre.asc())
            .limit(25)
            .all()
        )
        rows = [
            {
                "producto": item.producto,
                "cantidad": float(item.cantidad or 0),
                "ingreso": round(float(item.ingreso or 0), 2),
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
            }
            for item in rows_db
        ]
        return _csv_response(rows, f"menos-vendidos-{desde.isoformat()}-{hasta.isoformat()}.csv")

    if tipo == "top_clientes":
        rows_db = (
            Venta.query.join(Cliente, Cliente.id == Venta.fk_cliente)
            .join(Persona, Persona.id == Cliente.fk_persona)
            .filter(Venta.fecha_creacion >= start_dt, Venta.fecha_creacion <= end_dt, Venta.estatus == "ACTIVO")
            .with_entities(
                Persona.nombre.label("nombre"),
                Persona.apellido_uno.label("apellido_uno"),
                Persona.apellido_dos.label("apellido_dos"),
                Persona.correo.label("correo"),
                func.count(Venta.id).label("compras"),
                func.sum(Venta.total).label("total"),
            )
            .group_by(Persona.id)
            .order_by(func.sum(Venta.total).desc())
            .limit(50)
            .all()
        )
        rows = [
            {
                "cliente": " ".join([p for p in [item.nombre, item.apellido_uno, item.apellido_dos] if p]),
                "correo": item.correo or "",
                "compras": int(item.compras or 0),
                "total": round(float(item.total or 0), 2),
                "desde": desde.isoformat(),
                "hasta": hasta.isoformat(),
            }
            for item in rows_db
        ]
        return _csv_response(rows, f"top-clientes-{desde.isoformat()}-{hasta.isoformat()}.csv")

    # Default: ventas
    ventas = (
        Venta.query.filter(
            Venta.fecha_creacion >= start_dt,
            Venta.fecha_creacion <= end_dt,
        )
        .order_by(Venta.fecha_creacion.desc())
        .limit(5000)
        .all()
    )
    rows = [
        {
            "ticket": venta.folio_ticket,
            "cliente": (
                venta.cliente.persona.nombre
                if venta.cliente and venta.cliente.persona
                else "N/A"
            ),
            "total": round(float(venta.total or 0), 2),
            "fecha": venta.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if venta.fecha_creacion else "",
            "estatus": venta.estatus,
        }
        for venta in ventas
    ]
    return _csv_response(rows, f"ventas-{desde.isoformat()}-{hasta.isoformat()}.csv")
