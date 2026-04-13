from datetime import datetime
from decimal import Decimal
from html import escape
import json
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from flask import Response, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from utils.modules import create_module_blueprint
from models import (
    InventarioInsumo,
    InventarioProducto,
    Producto,
    Produccion,
    ProduccionDetalle,
    ProduccionInsumo,
    Receta,
    RecetaDetalle,
    SolicitudProduccion,
    UnidadMedida,
    db,
)
from utils.session import get_current_employee_id, get_current_user_id


produccion = create_module_blueprint("produccion")


def get_user_id():
    return get_current_user_id()


def get_empleado_id():
    return get_current_employee_id()


def get_sucursal_id():
    return 1


def _azure_realtime_ready():
    config = current_app.config
    return all(
        [
            config.get("AZURE_OPENAI_ENDPOINT"),
            config.get("AZURE_OPENAI_API_KEY"),
            config.get("AZURE_OPENAI_REALTIME_DEPLOYMENT"),
        ]
    )


def _azure_assistant_ready():
    config = current_app.config
    return all(
        [
            config.get("AZURE_OPENAI_ENDPOINT"),
            config.get("AZURE_OPENAI_API_KEY"),
            config.get("AZURE_OPENAI_ASSISTANT_DEPLOYMENT") or config.get("AZURE_OPENAI_VISION_DEPLOYMENT"),
        ]
    )


def _azure_vision_ready():
    config = current_app.config
    return all(
        [
            config.get("AZURE_OPENAI_ENDPOINT"),
            config.get("AZURE_OPENAI_API_KEY"),
            config.get("AZURE_OPENAI_VISION_DEPLOYMENT"),
        ]
    )


def _azure_speech_ready():
    config = current_app.config
    return all(
        [
            config.get("AZURE_SPEECH_KEY"),
            config.get("AZURE_SPEECH_REGION"),
            config.get("AZURE_SPEECH_VOICE"),
        ]
    )


def _azure_post_json(url, payload, accept="application/json"):
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", accept)
    req.add_header("api-key", current_app.config["AZURE_OPENAI_API_KEY"])

    try:
        with urllib_request.urlopen(req, timeout=45) as response:
            raw = response.read()
            return response.status, raw.decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or str(exc)) from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _azure_speech_synthesize(text):
    voice = current_app.config["AZURE_SPEECH_VOICE"]
    region = current_app.config["AZURE_SPEECH_REGION"]
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    safe_text = escape(text or "")
    ssml = f"""
    <speak version="1.0" xml:lang="es-MX">
      <voice name="{voice}">
        <prosody rate="0%" pitch="0%">{safe_text}</prosody>
      </voice>
    </speak>
    """.strip()
    body = ssml.encode("utf-8")

    req = urllib_request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/ssml+xml")
    req.add_header("X-Microsoft-OutputFormat", "audio-24khz-48kbitrate-mono-mp3")
    req.add_header("Ocp-Apim-Subscription-Key", current_app.config["AZURE_SPEECH_KEY"])
    req.add_header("Ocp-Apim-Subscription-Region", current_app.config["AZURE_SPEECH_REGION"])
    req.add_header("User-Agent", "Panaderia/1.0")

    try:
        with urllib_request.urlopen(req, timeout=45) as response:
            return response.read()
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or str(exc)) from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def _obtener_detalle_produccion(produccion_id):
    return ProduccionDetalle.query.filter_by(fk_produccion=produccion_id).first()


def _obtener_contexto_produccion(produccion_id):
    prod = Produccion.query.get_or_404(produccion_id)
    detalle = _obtener_detalle_produccion(produccion_id)
    if not detalle:
        raise ValueError("La producción no tiene detalle asociado.")

    producto = Producto.query.get_or_404(detalle.fk_producto)
    receta = Receta.query.filter_by(fk_producto=producto.id, estatus="ACTIVO").first()
    receta_detalles = []
    if receta:
        receta_detalles = (
            RecetaDetalle.query.filter_by(fk_receta=receta.id, estatus="ACTIVO")
            .order_by(RecetaDetalle.id.asc())
            .all()
        )

    return prod, detalle, producto, receta, receta_detalles


def _build_steps(producto, detalle, receta_detalles):
    cantidad_objetivo = detalle.cantidad_solicitada or 0
    insumos = []
    for item in receta_detalles:
        nombre_insumo = item.insumo.nombre if item.insumo else "Insumo no disponible"
        unidad_nombre = item.unidad.nombre if item.unidad else ""
        merma = round(float(item.insumo.porcentaje_merma or 0), 2) if item.insumo else 0
        requerido = Decimal(str(item.cantidad_insumo or 0)) * Decimal(str(cantidad_objetivo))
        insumos.append(
            {
                "insumo": nombre_insumo,
                "unidad": unidad_nombre,
                "requerido": round(float(requerido), 2),
                "merma": merma,
            }
        )

    return [
        {
            "title": "Preparar estación",
            "description": f"Confirma el área de trabajo, utensilios y horno para {producto.nombre}.",
            "items": [
                "Sanitizar mesa y equipo.",
                "Verificar horno, charolas y recipientes.",
                f"Confirmar meta de producción: {cantidad_objetivo} piezas.",
            ],
        },
        {
            "title": "Reunir insumos",
            "description": "Surtir la materia prima requerida según la receta activa.",
            "items": [
                f"{insumo['insumo']} - {insumo['requerido']} {insumo['unidad']} (merma {insumo['merma']}%)"
                for insumo in insumos
            ] or ["Este producto aún no tiene insumos registrados en receta."],
        },
        {
            "title": "Preparación guiada",
            "description": f"Ejecuta la preparación base de {producto.nombre} siguiendo la receta activa.",
            "items": [
                "Pesar y validar cada insumo antes de mezclar.",
                "Preparar la mezcla o masa base.",
                "Mantener consistencia y tiempos definidos por el encargado.",
            ],
        },
        {
            "title": "Horneado y control",
            "description": "Supervisa cocción, textura, color y mermas durante el proceso.",
            "items": [
                "Registrar piezas rechazadas o merma detectada.",
                "Validar cocción uniforme y presentación.",
                "Corregir lote o escalar al supervisor si hay desviaciones.",
            ],
        },
        {
            "title": "Cerrar producción",
            "description": "Captura el resultado final y mueve existencias al inventario del producto.",
            "items": [
                "Registrar piezas correctas.",
                "Capturar merma final del lote.",
                "Definir fecha de caducidad del producto terminado.",
            ],
        },
    ]


def _build_help_prompt(produccion_id, producto, detalle, receta, receta_detalles, steps, state):
    current_index = min(state.get("current", 0), max(len(steps) - 1, 0))
    current_step = steps[current_index] if steps else {"title": "Sin paso", "description": "", "items": []}
    ingredientes = []
    for item in receta_detalles:
        if item.estatus != "ACTIVO":
            continue
        nombre_insumo = item.insumo.nombre if item.insumo else "Insumo no disponible"
        unidad_nombre = item.unidad.nombre if item.unidad else ""
        ingredientes.append(f"- {nombre_insumo}: {item.cantidad_insumo} {unidad_nombre}".strip())

    descripcion = receta.descripcion.strip() if receta and receta.descripcion else "No hay descripción textual de receta."
    checklist = "\n".join([f"- {point}" for point in current_step.get("items", [])]) or "- Sin checklist disponible."
    ingredientes_texto = "\n".join(ingredientes) or "- No hay insumos activos cargados."

    return f"""
Eres Maestro Trigal, un panadero experto que acompaña por voz al personal durante la producción.
Responde siempre en español.
Mantente estrictamente dentro del contexto del producto, la receta, el paso actual, higiene, tiempos, temperatura, textura, merma, horneado y cierre del lote.
No hables de temas ajenos al proceso productivo. Si el usuario pregunta algo fuera de contexto, redirígelo con cortesía al producto o al paso actual.
Habla como una persona experta, breve, clara y accionable.
Cuando no tengas certeza, dilo y sugiere una verificación práctica.
No inventes ingredientes ni cantidades que no aparezcan en el contexto.

CONTEXTO ACTUAL
- Lote: {produccion_id}
- Producto: {producto.nombre}
- Meta de producción: {detalle.cantidad_solicitada} piezas
- Paso actual: {current_index + 1} de {len(steps)}
- Título del paso actual: {current_step.get("title", "")}
- Objetivo del paso: {current_step.get("description", "")}

CHECKLIST DEL PASO
{checklist}

RECETA BASE
{descripcion}

INSUMOS DE LA RECETA
{ingredientes_texto}

FORMA DE AYUDAR
- Responde como si estuvieras en videollamada con el empleado.
- Primero orienta con el siguiente paso concreto.
- Si piden ayuda por error, explica cómo corregirlo.
- Si notas un riesgo de seguridad o calidad, dilo de inmediato.
- Si el empleado pregunta por cantidades, tiempos o consistencias, respóndelas usando el contexto disponible.
""".strip()


def _extract_output_text(payload):
    if not isinstance(payload, dict):
        return ""

    if payload.get("output_text"):
        return payload["output_text"]

    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                return text
    return ""


def _step_state(produccion_id, total_steps):
    all_state = session.setdefault("produccion_step_state", {})
    state = all_state.get(str(produccion_id), {"current": 0, "completed": []})
    state["current"] = max(0, min(state.get("current", 0), total_steps - 1))
    state["completed"] = [index for index in state.get("completed", []) if 0 <= index < total_steps]
    all_state[str(produccion_id)] = state
    session.modified = True
    return state


def _guardar_step_state(produccion_id, state):
    all_state = session.setdefault("produccion_step_state", {})
    all_state[str(produccion_id)] = state
    session.modified = True


def _preparar_insumos_produccion(produccion_id, detalle, receta_detalles):
    existentes = ProduccionInsumo.query.filter_by(fk_produccion=produccion_id).count()
    if existentes:
        return

    for item in receta_detalles:
        if not item.insumo:
            continue
        requerida = Decimal(str(item.cantidad_insumo or 0)) * Decimal(str(detalle.cantidad_solicitada or 0))
        db.session.add(
            ProduccionInsumo(
                fk_produccion=produccion_id,
                fk_insumo=item.fk_insumo,
                cantidad_requerida=requerida,
                cantidad_consumida=requerida,
                cantidad_merma_real=Decimal("0.00"),
                observacion=f"Generado desde receta activa de {item.insumo.nombre}",
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id(),
            )
        )


def _factor_unidad_base(unidad):
    if not unidad:
        return Decimal("1")

    factor = Decimal(str(unidad.factor_conversion or 1))
    actual = unidad.unidad_base
    while actual:
        factor *= Decimal(str(actual.factor_conversion or 1))
        actual = actual.unidad_base
    return factor


def _formatear_decimal(valor):
    numero = Decimal(str(valor or 0)).quantize(Decimal("0.01"))
    texto = format(numero.normalize(), "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"


def _validar_stock_insumos(detalle, receta_detalles, sucursal_id):
    faltantes = []

    for item in receta_detalles:
        if item.estatus != "ACTIVO":
            continue

        if not item.insumo:
            faltantes.append(
                {
                    "insumo": "Insumo no disponible",
                    "motivo": "La receta referencia un insumo eliminado o inválido.",
                }
            )
            continue

        inventario = InventarioInsumo.query.filter(
            InventarioInsumo.fk_insumo == item.fk_insumo,
            InventarioInsumo.fk_sucursal == sucursal_id,
            InventarioInsumo.estatus == "DISPONIBLE",
            InventarioInsumo.cantidad > 0,
        ).first()

        unidad_receta = item.unidad or UnidadMedida.query.get(item.fk_unidad)
        factor_receta = _factor_unidad_base(unidad_receta)
        requerido = Decimal(str(item.cantidad_insumo or 0)) * Decimal(str(detalle.cantidad_solicitada or 0))
        requerido_base = requerido * factor_receta

        if not inventario:
            faltantes.append(
                {
                    "insumo": item.insumo.nombre,
                    "motivo": (
                        f"No hay inventario disponible en sucursal. "
                        f"Se requieren {_formatear_decimal(requerido)} {unidad_receta.nombre if unidad_receta else ''}".strip()
                    ),
                }
            )
            continue

        unidad_inventario = inventario.unidad
        factor_inventario = _factor_unidad_base(unidad_inventario)
        disponible = Decimal(str(inventario.cantidad or 0))
        disponible_base = disponible * factor_inventario

        if disponible_base < requerido_base:
            faltante_base = requerido_base - disponible_base
            faltante_visible = (
                (faltante_base / factor_receta) if factor_receta else faltante_base
            )
            faltantes.append(
                {
                    "insumo": item.insumo.nombre,
                    "motivo": (
                        f"Disponible: {_formatear_decimal(disponible)} {unidad_inventario.nombre if unidad_inventario else ''}. "
                        f"Faltan {_formatear_decimal(faltante_visible)} {unidad_receta.nombre if unidad_receta else ''}".strip()
                    ),
                }
            )

    return faltantes


@produccion.route("/iniciar/<int:id>")
def iniciar(id):
    prod, detalle, producto, receta, receta_detalles = _obtener_contexto_produccion(id)

    if prod.estado != "PENDIENTE":
        flash("Solo se puede iniciar si está pendiente.", "error")
        return redirect(url_for("produccion.inicio"))

    detalles_invalidos = [item for item in receta_detalles if not item.insumo]
    if detalles_invalidos:
        flash(
            "La receta tiene insumos eliminados o inválidos. Corrige la receta antes de iniciar la guía.",
            "error",
        )
        return redirect(url_for("produccion.inicio"))

    faltantes = _validar_stock_insumos(detalle, receta_detalles, prod.fk_sucursal)
    if faltantes:
        resumen = "\n" + "\n".join([f"- {item['insumo']}: {item['motivo']}" for item in faltantes[:4]])
        if len(faltantes) > 4:
            resumen += f"\n- y {len(faltantes) - 4} insumo(s) más."
        flash(
            f"No puedes iniciar la producción porque no hay insumos suficientes. {resumen}",
            "error",
        )
        return redirect(url_for("produccion.inicio"))

    prod.estado = "EN PROCESO"
    _preparar_insumos_produccion(prod.id, detalle, receta_detalles)

    if detalle and detalle.fk_solicitud:
        solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
        if solicitud:
            solicitud.estado = "EN_PRODUCCION"

    db.session.commit()
    flash(f"Producción de {producto.nombre} iniciada.", "success")
    return redirect(url_for("produccion.proceso", id=id))


@produccion.route("/")
def inicio():
    buscar = request.args.get("buscar", "", type=str).strip() if request else ""
    data = []
    producciones = Produccion.query.order_by(Produccion.id.desc()).all()
    for item in producciones:
        detalle = _obtener_detalle_produccion(item.id)
        if not detalle:
            continue
        producto = Producto.query.get(detalle.fk_producto)
        receta = Receta.query.filter_by(fk_producto=detalle.fk_producto, estatus="ACTIVO").first()
        pasos_total = 5
        state = _step_state(item.id, pasos_total)
        data.append(
            {
                "id": item.id,
                "producto": producto.nombre if producto else "Producto eliminado",
                "cantidad": detalle.cantidad_solicitada,
                "estado": item.estado,
                "tipo": "PRODUCCION",
                "origen": detalle.origen if detalle.origen else "INTERNO",
                "fecha": item.fecha_creacion or datetime.min,
                "solicitud_id": detalle.fk_solicitud,
                "receta": bool(receta),
                "paso_actual": state["current"] + 1,
                "pasos_total": pasos_total,
            }
        )

    solicitudes_usadas = {detalle.fk_solicitud for detalle in ProduccionDetalle.query.all() if detalle.fk_solicitud}
    for solicitud in SolicitudProduccion.query.order_by(SolicitudProduccion.id.desc()).all():
        if solicitud.id in solicitudes_usadas:
            continue
        producto = Producto.query.get(solicitud.fk_producto)
        receta = Receta.query.filter_by(fk_producto=solicitud.fk_producto, estatus="ACTIVO").first()
        data.append(
            {
                "id": solicitud.id,
                "producto": producto.nombre if producto else "Producto eliminado",
                "cantidad": solicitud.cantidad_solicitada,
                "estado": solicitud.estado,
                "tipo": "SOLICITUD",
                "origen": "SOLICITUD",
                "fecha": solicitud.fecha_creacion or datetime.min,
                "solicitud_id": solicitud.id,
                "receta": bool(receta),
                "paso_actual": 0,
                "pasos_total": 5,
            }
        )

    data.sort(key=lambda item: (item["fecha"], item["id"]), reverse=True)
    if buscar:
        needle = buscar.lower()
        data = [
            item
            for item in data
            if needle in (item.get("producto") or "").lower()
            or needle in (item.get("estado") or "").lower()
            or needle in (item.get("tipo") or "").lower()
            or needle in (item.get("origen") or "").lower()
        ]

    return render_template("produccion/inicio.html", ordenes=data, buscar=buscar)


@produccion.route("/crear/<int:solicitud_id>")
def crear(solicitud_id):
    solicitud = SolicitudProduccion.query.get_or_404(solicitud_id)
    if solicitud.estado != "PENDIENTE":
        flash("La solicitud ya fue procesada.", "error")
        return redirect(url_for("produccion.inicio"))

    nueva_produccion = Produccion(
        fk_empleado=get_empleado_id(),
        fk_sucursal=get_sucursal_id(),
        estado="PENDIENTE",
        usuario_creacion=get_user_id(),
        usuario_movimiento=get_user_id(),
    )
    db.session.add(nueva_produccion)
    db.session.flush()

    db.session.add(
        ProduccionDetalle(
            fk_produccion=nueva_produccion.id,
            fk_producto=solicitud.fk_producto,
            cantidad_solicitada=solicitud.cantidad_solicitada,
            cantidad_producto=0,
            origen="SOLICITUD_VENTAS",
            usuario_creacion=get_user_id(),
            usuario_movimiento=get_user_id(),
            fk_solicitud=solicitud.id,
        )
    )

    solicitud.estado = "APROBADA"
    db.session.commit()

    flash("Producción creada correctamente. Ahora puedes comenzar la guía.", "success")
    return redirect(url_for("produccion.inicio"))


@produccion.route("/proceso/<int:id>", methods=["GET", "POST"])
def proceso(id):
    prod, detalle, producto, receta, receta_detalles = _obtener_contexto_produccion(id)
    if prod.estado == "PENDIENTE":
        return redirect(url_for("produccion.iniciar", id=id))

    steps = _build_steps(producto, detalle, receta_detalles)
    state = _step_state(id, len(steps))

    if request.method == "POST":
        action = request.form.get("action")
        current = state["current"]

        if action == "next":
            if current not in state["completed"]:
                state["completed"].append(current)
            if current >= len(steps) - 1:
                _guardar_step_state(id, state)
                return redirect(url_for("produccion.terminar", id=id))
            state["current"] = min(current + 1, len(steps) - 1)
        elif action == "prev":
            state["current"] = max(current - 1, 0)

        _guardar_step_state(id, state)
        return redirect(url_for("produccion.proceso", id=id))

    avance = round((len(state["completed"]) / len(steps)) * 100) if steps else 0
    return render_template(
        "produccion/proceso.html",
        produccion=prod,
        detalle=detalle,
        producto=producto,
        receta=receta,
        receta_detalles=receta_detalles,
        steps=steps,
        state=state,
        avance=avance,
        ai_help_configured=_azure_assistant_ready(),
        ai_help_visual=_azure_vision_ready(),
        ai_help_tts=_azure_speech_ready(),
    )


@produccion.route("/ayuda/<int:id>/texto", methods=["POST"])
def ayuda_texto(id):
    if not _azure_assistant_ready():
        return jsonify({"error": "La integración de asistencia no está configurada."}), 503

    prod, detalle, producto, receta, receta_detalles = _obtener_contexto_produccion(id)
    steps = _build_steps(producto, detalle, receta_detalles)
    state = _step_state(id, len(steps))

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    visual_context = (payload.get("visual_context") or "").strip()
    if not message:
        return jsonify({"error": "No se recibió la pregunta del empleado."}), 400

    instructions = _build_help_prompt(prod.id, producto, detalle, receta, receta_detalles, steps, state)
    endpoint = current_app.config["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    model = current_app.config.get("AZURE_OPENAI_ASSISTANT_DEPLOYMENT") or current_app.config.get("AZURE_OPENAI_VISION_DEPLOYMENT")
    url = f"{endpoint}/openai/v1/responses"

    composed_message = message
    if visual_context:
        composed_message += f"\n\nContexto visual observado: {visual_context}"

    request_payload = {
        "model": model,
        "instructions": instructions,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": composed_message,
                    }
                ],
            }
        ],
        "max_output_tokens": 220,
    }

    try:
        _, raw_json = _azure_post_json(url, request_payload)
        data = json.loads(raw_json)
        answer = _extract_output_text(data).strip()
    except RuntimeError as exc:
        return jsonify({"error": f"No se pudo consultar la asistencia en Azure OpenAI: {exc}"}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Azure OpenAI devolvió una respuesta inválida para la asistencia."}), 502

    if not answer:
        answer = "No pude formular una recomendación clara con el contexto actual. Intenta describir mejor el problema."

    return jsonify({"answer": answer})


@produccion.route("/ayuda/<int:id>/tts", methods=["POST"])
def ayuda_tts(id):
    if not _azure_speech_ready():
        return jsonify({"error": "La síntesis de voz de Azure Speech no está configurada."}), 503

    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No se recibió texto para sintetizar."}), 400

    try:
        audio_bytes = _azure_speech_synthesize(text)
    except RuntimeError as exc:
        return jsonify({"error": f"No se pudo sintetizar voz con Azure Speech: {exc}"}), 502

    return Response(audio_bytes, mimetype="audio/mpeg")


@produccion.route("/ayuda/<int:id>/realtime-token", methods=["POST"])
def ayuda_realtime_token(id):
    if not _azure_realtime_ready():
        return jsonify({"error": "La integración con Azure OpenAI no está configurada."}), 503

    prod, detalle, producto, receta, receta_detalles = _obtener_contexto_produccion(id)
    steps = _build_steps(producto, detalle, receta_detalles)
    state = _step_state(id, len(steps))

    instructions = _build_help_prompt(prod.id, producto, detalle, receta, receta_detalles, steps, state)
    endpoint = current_app.config["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    url = f"{endpoint}/openai/v1/realtime/client_secrets"

    session_payload = {
        "session": {
            "type": "realtime",
            "model": current_app.config["AZURE_OPENAI_REALTIME_DEPLOYMENT"],
            "instructions": instructions,
            "audio": {
                "input": {
                    "turn_detection": {
                        "type": "server_vad",
                    }
                },
                "output": {
                    "voice": current_app.config["AZURE_OPENAI_REALTIME_VOICE"],
                },
            },
        }
    }

    try:
        _, raw_json = _azure_post_json(url, session_payload)
        data = json.loads(raw_json)
    except RuntimeError as exc:
        detail = str(exc)
        if "OpperationNotSupported" in detail or "OperationNotSupported" in detail:
            detail = (
                "El deployment configurado no soporta Realtime. "
                "Necesitas un modelo Realtime de Azure, por ejemplo gpt-4o-mini-realtime-preview, "
                "gpt-4o-realtime-preview o gpt-realtime."
            )
        return jsonify({"error": f"No se pudo iniciar la sesión en Azure OpenAI: {detail}"}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Azure OpenAI devolvió una respuesta inválida para el token efímero."}), 502

    ephemeral_token = data.get("value") or data.get("token") or data.get("client_secret", {}).get("value")
    if not ephemeral_token:
        return jsonify({"error": "Azure OpenAI no devolvió un token efímero utilizable."}), 502

    return jsonify(
        {
            "token": ephemeral_token,
            "webrtc_url": f"{endpoint}/openai/v1/realtime/calls?webrtcfilter=on",
        }
    )


@produccion.route("/ayuda/<int:id>/vision-context", methods=["POST"])
def ayuda_vision_context(id):
    if not _azure_vision_ready():
        return jsonify({"error": "El análisis visual no está configurado."}), 503

    prod, detalle, producto, receta, receta_detalles = _obtener_contexto_produccion(id)
    steps = _build_steps(producto, detalle, receta_detalles)
    state = _step_state(id, len(steps))

    payload = request.get_json(silent=True) or {}
    image_url = payload.get("image_url")
    if not image_url:
        return jsonify({"error": "No se recibió imagen para análisis."}), 400

    current_index = min(state.get("current", 0), max(len(steps) - 1, 0))
    current_step = steps[current_index] if steps else {"title": "", "description": ""}
    endpoint = current_app.config["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    model = current_app.config["AZURE_OPENAI_VISION_DEPLOYMENT"]
    url = f"{endpoint}/openai/v1/responses"

    vision_prompt = (
        "Analiza esta imagen como apoyo visual para una producción de panadería. "
        f"Producto: {producto.nombre}. "
        f"Paso actual: {current_step.get('title', '')}. "
        f"Objetivo del paso: {current_step.get('description', '')}. "
        "Responde en español con máximo 2 oraciones. "
        "Describe solo señales visuales útiles para orientar al empleado en la producción, sin salirte del contexto."
    )

    request_payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": vision_prompt},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
        "max_output_tokens": 120,
    }

    try:
        _, raw_json = _azure_post_json(url, request_payload)
        data = json.loads(raw_json)
        summary = _extract_output_text(data).strip()
    except RuntimeError as exc:
        return jsonify({"error": f"No se pudo analizar la imagen con Azure OpenAI: {exc}"}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Azure OpenAI devolvió una respuesta no válida para el análisis visual."}), 502

    if not summary:
        summary = "No se detectó suficiente información visual útil en esta captura."

    return jsonify({"summary": summary})


@produccion.route("/terminar/<int:id>", methods=["GET", "POST"])
def terminar(id):
    prod, detalle, producto, _, _ = _obtener_contexto_produccion(id)
    inventario = InventarioProducto.query.filter_by(
        fk_producto=detalle.fk_producto,
        fk_sucursal=get_sucursal_id(),
        estatus="ACTIVO",
    ).first()

    if request.method == "POST":
        if prod.estado == "TERMINADO":
            flash("Esta producción ya fue cerrada. Solo puedes consultar el resultado.", "warning")
            return redirect(url_for("produccion.terminar", id=id))

        piezas = int(request.form.get("piezas"))
        merma = int(request.form.get("merma"))
        fecha = request.form.get("fecha_caducidad")

        if not fecha:
            flash("La fecha de caducidad es obligatoria.", "error")
            return redirect(url_for("produccion.terminar", id=id))

        fecha = datetime.fromisoformat(fecha)

        if piezas < 0 or merma < 0:
            flash("Las piezas y la merma deben ser valores positivos.", "error")
            return redirect(url_for("produccion.terminar", id=id))

        if piezas + merma > detalle.cantidad_solicitada:
            flash("El total de piezas y merma no puede exceder la cantidad solicitada.", "error")
            return redirect(url_for("produccion.terminar", id=id))
        detalle.cantidad_producto = piezas
        detalle.cantidad_merma = merma
        prod.estado = "TERMINADO"

        if inventario:
            inventario.cantidad_producto += piezas
            inventario.fecha_caducidad = fecha
        else:
            db.session.add(
                InventarioProducto(
                    fk_producto=detalle.fk_producto,
                    fk_sucursal=get_sucursal_id(),
                    cantidad_producto=piezas,
                    fecha_caducidad=fecha,
                    estado="EXISTENCIA",
                    estatus="ACTIVO",
                    usuario_creacion=get_user_id(),
                    usuario_movimiento=get_user_id(),
                )
            )

        if detalle.fk_solicitud:
            solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
            if solicitud:
                solicitud.estado = "TERMINADA"

        db.session.commit()
        flash(f"Producción de {producto.nombre} terminada correctamente.", "success")
        return redirect(url_for("produccion.inicio"))

    return render_template(
        "produccion/editar.html",
        produccion=prod,
        detalle=detalle,
        producto=producto,
        inventario=inventario,
    )


@produccion.route("/agregar", methods=["GET", "POST"])
def agregar():
    if Producto.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay productos registrados. No se puede crear una producción.", "warning")
        return redirect(url_for("productos.inicio"))

    if Receta.query.filter_by(estatus="ACTIVO").count() == 0:
        flash("No hay recetas activas. No se puede crear una producción sin recetas.", "warning")
        return redirect(url_for("recetas.inicio"))

    if request.method == "POST":
        producto_id = request.form.get("producto_id", type=int)
        cantidad = request.form.get("cantidad", type=int)

        if not producto_id or not cantidad:
            flash("Debes seleccionar un producto y una cantidad.", "error")
            return redirect(url_for("produccion.agregar"))

        if cantidad <= 0:
            flash("La cantidad debe ser mayor a 0.", "error")
            return redirect(url_for("produccion.agregar"))

        receta = Receta.query.filter_by(fk_producto=producto_id, estatus="ACTIVO").first()
        if not receta:
            flash("El producto seleccionado no tiene receta activa.", "error")
            return redirect(url_for("produccion.agregar"))

        nueva_produccion = Produccion(
            fk_empleado=get_empleado_id(),
            fk_sucursal=get_sucursal_id(),
            estado="PENDIENTE",
            fecha_creacion=datetime.utcnow(),
            usuario_creacion=get_user_id(),
            usuario_movimiento=get_user_id(),
        )
        db.session.add(nueva_produccion)
        db.session.flush()

        db.session.add(
            ProduccionDetalle(
                fk_produccion=nueva_produccion.id,
                fk_producto=producto_id,
                cantidad_solicitada=cantidad,
                cantidad_producto=0,
                origen="INTERNO",
                usuario_creacion=get_user_id(),
                usuario_movimiento=get_user_id(),
            )
        )

        db.session.commit()
        flash("Producción creada. Ahora puedes comenzar la guía paso a paso.", "success")
        return redirect(url_for("produccion.inicio"))

    productos = (
        Producto.query.filter_by(estatus="ACTIVO")
        .order_by(Producto.nombre.asc())
        .all()
    )
    solicitudes_usadas = {detalle.fk_solicitud for detalle in ProduccionDetalle.query.all() if detalle.fk_solicitud}
    solicitudes_pendientes = []
    for solicitud in (
        SolicitudProduccion.query.filter(
            SolicitudProduccion.estado.in_(["PENDIENTE", "APROBADA"])
        )
        .order_by(SolicitudProduccion.fecha_creacion.desc())
        .all()
    ):
        if solicitud.id in solicitudes_usadas:
            continue
        producto = Producto.query.get(solicitud.fk_producto)
        solicitudes_pendientes.append(
            {
                "id": solicitud.id,
                "producto": producto.nombre if producto else "Producto eliminado",
                "cantidad": solicitud.cantidad_solicitada,
                "estado": solicitud.estado,
                "fecha": solicitud.fecha_creacion,
            }
        )

    return render_template(
        "produccion/agregar.html",
        productos=productos,
        solicitudes_pendientes=solicitudes_pendientes,
    )


@produccion.route("/merma/<int:id>", methods=["GET", "POST"])
def merma(id):
    prod, detalle, producto, _, _ = _obtener_contexto_produccion(id)

    if request.method == "POST":
        cantidad = request.form.get("cantidad", type=int)
        observacion = request.form.get("observacion", type=str)
        if not cantidad or cantidad <= 0 or not observacion:
            flash("Debes indicar cantidad y observación.", "error")
            return redirect(url_for("produccion.merma", id=id))
        flash(f"Merma registrada para {producto.nombre}.", "success")
        return redirect(url_for("produccion.inicio"))

    return render_template("produccion/eliminar.html", produccion=prod, detalle=detalle, producto=producto)


@produccion.route("/cancelar/<int:id>")
def cancelar(id):
    prod = Produccion.query.get_or_404(id)
    prod.estado = "CANCELADO"

    detalle = _obtener_detalle_produccion(id)
    if detalle and detalle.fk_solicitud:
        solicitud = SolicitudProduccion.query.get(detalle.fk_solicitud)
        if solicitud:
            solicitud.estado = "RECHAZADA"

    db.session.commit()
    flash("Producción cancelada.", "warning")
    return redirect(url_for("produccion.inicio"))
