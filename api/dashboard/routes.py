from datetime import datetime, timedelta

from flask import render_template, request
from sqlalchemy import func

from . import dashboard
from models import (
    CategoriaInsumo,
    Compra,
    Insumo,
    Pedido,
    Produccion,
    Producto,
    Venta,
    VentaDetalle,
)


MODULE = {
    "name": "Dashboard",
    "slug": "dashboard",
    "description": "Indicadores operativos de ventas, producción e inventarios.",
}


def _fecha_inicio(periodo: str) -> datetime:
    ahora = datetime.now()
    if periodo == "7d":
        return ahora - timedelta(days=7)
    if periodo == "30d":
        return ahora - timedelta(days=30)
    if periodo == "90d":
        return ahora - timedelta(days=90)
    return ahora - timedelta(days=30)


def _dashboard_data(periodo: str):
    desde = _fecha_inicio(periodo)
    ventas_periodo = Venta.query.filter(Venta.fecha_creacion >= desde).all()
    compras_periodo = Compra.query.filter(Compra.fecha_creacion >= desde).all()
    produccion_periodo = Produccion.query.filter(Produccion.fecha_creacion >= desde).all()
    pedidos_periodo = Pedido.query.filter(Pedido.fecha_creacion >= desde).all()

    total_ventas = round(sum(float(item.total or 0) for item in ventas_periodo), 2)
    total_compras = round(sum(float(item.monto_total or 0) for item in compras_periodo), 2)
    total_produccion = len(produccion_periodo)
    pedidos_pendientes = sum(1 for item in pedidos_periodo if item.estado not in {"ENTREGADO", "CANCELADO"})

    insumos_criticos = []
    for insumo in Insumo.query.order_by(Insumo.nombre.asc()).all():
        total = sum(float(item.cantidad or 0) for item in insumo.inventarios)
        caducidad = sorted([item.fecha_caducidad for item in insumo.inventarios if item.fecha_caducidad])
        estado = "DISPONIBLE"
        if not insumo.inventarios or total <= 0:
            estado = "SIN EXISTENCIA"
        elif total <= 10:
            estado = "STOCK BAJO"
        elif any(item.estatus == "CADUCADO" for item in insumo.inventarios):
            estado = "CADUCADO"
        if estado != "DISPONIBLE":
            insumos_criticos.append(
                {
                    "nombre": insumo.nombre,
                    "categoria": insumo.categoria.nombre if insumo.categoria else "Sin categoria",
                    "cantidad": total,
                    "estado": estado,
                    "caducidad": caducidad[0] if caducidad else None,
                }
            )

    top_productos_query = (
        VentaDetalle.query.join(Producto, Producto.id == VentaDetalle.fk_producto)
        .with_entities(
            Producto.nombre.label("producto"),
            func.sum(VentaDetalle.cantidad_producto).label("cantidad"),
            func.sum(VentaDetalle.subtotal).label("ingreso"),
        )
        .join(Venta, Venta.id == VentaDetalle.fk_venta)
        .filter(Venta.fecha_creacion >= desde)
        .group_by(Producto.nombre)
        .order_by(func.sum(VentaDetalle.cantidad_producto).desc())
        .limit(5)
        .all()
    )

    top_productos = [
        {
            "producto": item.producto,
            "cantidad": float(item.cantidad or 0),
            "ingreso": round(float(item.ingreso or 0), 2),
        }
        for item in top_productos_query
    ]

    produccion_estados = [
        {
            "estado": estado,
            "total": Produccion.query.filter(
                Produccion.fecha_creacion >= desde,
                Produccion.estado == estado,
            ).count(),
        }
        for estado in ["PENDIENTE", "EN PROCESO", "TERMINADO", "CANCELADO"]
    ]

    pedidos_estados = [
        {
            "estado": estado,
            "total": Pedido.query.filter(
                Pedido.fecha_creacion >= desde,
                Pedido.estado == estado,
            ).count(),
        }
        for estado in ["ESPERANDO", "EN PRODUCCIÓN", "LISTO", "ENTREGADO", "CANCELADO"]
    ]

    categoria_insumos = (
        CategoriaInsumo.query.join(Insumo, Insumo.fk_categoria == CategoriaInsumo.id)
        .with_entities(CategoriaInsumo.nombre, func.count(Insumo.id))
        .group_by(CategoriaInsumo.nombre)
        .order_by(func.count(Insumo.id).desc())
        .all()
    )

    ventas_recientes = Venta.query.order_by(Venta.fecha_creacion.desc()).limit(8).all()

    dias = 7 if periodo == "7d" else 6 if periodo == "30d" else 8
    paso = 1 if periodo == "7d" else 5 if periodo == "30d" else 10
    ventas_series = []
    for indice in range(dias - 1, -1, -1):
        inicio_dia = datetime.now() - timedelta(days=indice * paso)
        fin_dia = inicio_dia + timedelta(days=paso)
        total_dia = sum(
            float(venta.total or 0)
            for venta in ventas_periodo
            if inicio_dia <= venta.fecha_creacion < fin_dia
        )
        ventas_series.append({"label": inicio_dia.strftime("%d/%m"), "total": round(total_dia, 2)})

    max_ventas_series = max((item["total"] for item in ventas_series), default=0)
    for item in ventas_series:
        item["height"] = 18 if max_ventas_series <= 0 else max(18, round((item["total"] / max_ventas_series) * 100))

    total_insumos = Insumo.query.count() or 1
    stock_bajo = sum(1 for item in insumos_criticos if item["estado"] == "STOCK BAJO")
    sin_existencia = sum(1 for item in insumos_criticos if item["estado"] == "SIN EXISTENCIA")
    caducado = sum(1 for item in insumos_criticos if item["estado"] == "CADUCADO")
    saludables = max(total_insumos - stock_bajo - sin_existencia - caducado, 0)

    salud_inventario = [
        {"label": "Saludable", "count": saludables, "color": "#6f8f5f"},
        {"label": "Stock bajo", "count": stock_bajo, "color": "#d29a34"},
        {"label": "Sin existencia", "count": sin_existencia, "color": "#bf6a45"},
        {"label": "Caducado", "count": caducado, "color": "#874a3a"},
    ]
    for item in salud_inventario:
        item["percent"] = round((item["count"] / total_insumos) * 100)

    max_top_cantidad = max((item["cantidad"] for item in top_productos), default=0)
    for item in top_productos:
        item["width"] = 16 if max_top_cantidad <= 0 else max(16, round((item["cantidad"] / max_top_cantidad) * 100))

    max_categoria_total = max((item[1] for item in categoria_insumos), default=0)
    categoria_insumos_data = []
    for nombre, total in categoria_insumos:
        categoria_insumos_data.append(
            {
                "categoria": nombre,
                "total": total,
                "width": 16 if max_categoria_total <= 0 else max(16, round((total / max_categoria_total) * 100)),
            }
        )

    produccion_total = sum(item["total"] for item in produccion_estados) or 1
    for item in produccion_estados:
        item["percent"] = round((item["total"] / produccion_total) * 100)

    pedidos_total = sum(item["total"] for item in pedidos_estados) or 1
    for item in pedidos_estados:
        item["percent"] = round((item["total"] / pedidos_total) * 100)

    balance_operativo = round(total_ventas - total_compras, 2)
    eficiencia_abasto = round((saludables / total_insumos) * 100)

    return {
        "periodo": periodo,
        "desde": desde,
        "kpis": {
            "ventas": total_ventas,
            "compras": total_compras,
            "produccion": total_produccion,
            "pedidos_pendientes": pedidos_pendientes,
            "insumos_criticos": len(insumos_criticos),
            "productos_activos": Producto.query.filter_by(estatus="ACTIVO").count(),
            "balance_operativo": balance_operativo,
            "eficiencia_abasto": eficiencia_abasto,
        },
        "insumos_criticos": insumos_criticos[:8],
        "top_productos": top_productos,
        "produccion_estados": produccion_estados,
        "pedidos_estados": pedidos_estados,
        "categoria_insumos": categoria_insumos_data,
        "ventas_recientes": ventas_recientes,
        "ventas_series": ventas_series,
        "salud_inventario": salud_inventario,
    }


@dashboard.route("/")
def inicio():
    periodo = request.args.get("periodo", "30d", type=str)
    data = _dashboard_data(periodo)
    return render_template(
        "dashboard/inicio.html",
        module=MODULE,
        current_action="inicio",
        dashboard=data,
    )

