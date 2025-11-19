# apps/visitas/draft.py
from django.utils import timezone

SESSION_KEY = "visita_borrador"

# Estados que consideramos "pendientes" para emparejar ruta
RUTA_PENDIENTES = {"pendiente", "planificado", "planificada", "atrasado", "atrasada"}

def get_draft(request) -> dict | None:
    return request.session.get(SESSION_KEY)

def save_draft(request, draft: dict) -> None:
    request.session[SESSION_KEY] = draft
    request.session.modified = True

def clear_draft(request) -> None:
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True

def _now_iso() -> str:
    # Mantiene el formato original (ISO 8601 con tz)
    return timezone.now().isoformat()

def _normaliza_estado(valor: str) -> str:
    if not valor:
        return ""
    v = valor.strip().lower()
    if v in {"pendiente", "planificado", "planificada", "atrasado", "atrasada"}:
        return "pendiente"
    if v in {"completado", "completada", "cubierto", "cubierta", "hecho"}:
        return "completado"
    return v

def new_draft(
    *,
    usuario_id: int,
    doctor_id: int,
    ruta_id: int | None,
    ubicacion_inicio: str,
    origen: str | None = None,          # "rutas" o "buscador" (opcional)
    auto_match: bool = True             # intentar sugerir ruta si no hay ruta_id
) -> dict:
    """
    Crea un borrador de visita. Si no viene ruta_id y auto_match=True,
    intenta calcular una ruta sugerida (`ruta_sugerida_id`) para este doctor.
    Esto permite que, aunque el usuario inicie desde "Buscar Médicos",
    podamos completar la ruta programada más coherente al finalizar.
    """
    draft = {
        "usuario_id": usuario_id,
        "doctor_id": doctor_id,
        "ruta_id": ruta_id,                 # puede venir en None si no inició desde Rutas
        "ubicacion_inicio": ubicacion_inicio or "",
        "fecha_inicio_iso": _now_iso(),
        "productos_presentados": [],
        "entregas": [],
        "comentarios": "",
        "origen": (origen or "").strip().lower(),  # "rutas" | "buscador" | ""
        "ruta_sugerida_id": None,           # nueva: ruta candidata a cubrir
    }

    # Si no se inició desde una ruta concreta, calculamos una sugerencia
    if draft["ruta_id"] is None and auto_match:
        try:
            ruta_candidata_id = _resolver_ruta_sugerida(
                usuario_id=usuario_id,
                doctor_id=doctor_id,
                fecha_iso=draft["fecha_inicio_iso"],
            )
            draft["ruta_sugerida_id"] = ruta_candidata_id
        except Exception:
            # Nunca romper por la sugerencia
            draft["ruta_sugerida_id"] = None

    return draft

# ---------- Helpers para leer/escribir atributos del draft ----------

def set_ruta_id(request, ruta_id: int | None) -> None:
    """Permite fijar/actualizar ruta_id durante el flujo (por ejemplo, si el usuario cambia)."""
    d = get_draft(request) or {}
    d["ruta_id"] = ruta_id
    save_draft(request, d)

def get_ruta_id(request) -> int | None:
    d = get_draft(request) or {}
    return d.get("ruta_id") or d.get("ruta_sugerida_id")

def get_doctor_id(request) -> int | None:
    d = get_draft(request) or {}
    return d.get("doctor_id")

def get_origen(request) -> str:
    d = get_draft(request) or {}
    return (d.get("origen") or "").strip().lower()

def get_fecha_inicio_iso(request) -> str | None:
    d = get_draft(request) or {}
    return d.get("fecha_inicio_iso")

# ---------- Emparejamiento de ruta sugerida (lazy import para evitar ciclos) ----------

def _resolver_ruta_sugerida(*, usuario_id: int, doctor_id: int, fecha_iso: str) -> int | None:
    """
    Busca la mejor ruta 'pendiente/planificado/atrasado' para este doctor.
    Criterio:
      1) primero en el MISMO mes/año de la fecha de inicio del draft, por fecha asc,
      2) si no hay, la más cercana posterior,
      3) si no hay posterior, la más cercana anterior.
    Devuelve el ID (int) o None.
    """
    # Import local para evitar dependencias circulares
    from datetime import datetime
    from django.db.models import Q
    from rutas.models import Ruta

    # Parse de la fecha ISO
    try:
        # timezone-aware ISO → usar fromisoformat
        fecha_dt = datetime.fromisoformat(fecha_iso)
        fecha_base = fecha_dt.date()
        y, m = fecha_base.year, fecha_base.month
    except Exception:
        # Fallback: ahora
        ahora = timezone.now()
        fecha_base = ahora.date()
        y, m = fecha_base.year, fecha_base.month

    # Filtro estados pendientes
    q_estado = Q()
    for campo in ("estado", "estatus", "status"):
        q_estado |= Q(**{f"{campo}__in": list(RUTA_PENDIENTES)})

    base = (Ruta.objects
            .filter(usuario_id=usuario_id, doctor_id=doctor_id)
            .filter(q_estado))

    # 1) mismo mes
    en_mes = (base.filter(fecha_visita__year=y, fecha_visita__month=m)
                   .order_by("fecha_visita")
                   .values_list("id", flat=True)
                   .first())
    if en_mes:
        return int(en_mes)

    # 2) la más cercana futura
    futura = (base.filter(fecha_visita__gte=fecha_base)
                   .order_by("fecha_visita")
                   .values_list("id", flat=True)
                   .first())
    if futura:
        return int(futura)

    # 3) la más cercana pasada
    pasada = (base.filter(fecha_visita__lt=fecha_base)
                  .order_by("-fecha_visita")
                  .values_list("id", flat=True)
                  .first())
    if pasada:
        return int(pasada)

    return None