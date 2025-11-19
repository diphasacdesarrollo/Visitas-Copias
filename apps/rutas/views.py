# apps/rutas/views.py
from datetime import date
import time, logging

from django.template.loader import render_to_string
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.timezone import localdate

from apps.doctores.models import Doctor
from apps.ubicaciones.models import Departamento, Distrito, Provincia
from apps.usuarios.models import Usuario
from .models import Ruta

logger = logging.getLogger(__name__)


@login_required
def crear_ruta(request):
    """Vista principal para crear rutas médicas."""
    t0_total = time.perf_counter()

    # ---------------------- parámetros GET ----------------------
    departamento_id = request.GET.get("departamento")
    provincia_id    = request.GET.get("provincia")
    distrito_id     = request.GET.get("distrito")
    busqueda        = (request.GET.get("busqueda") or "").strip()
    visitador_filtro_id = request.GET.get("visitador_id")
    page_num        = request.GET.get("page") or 1

    # ---------------------- queryset base -----------------------
    doctores_qs = Doctor.objects.all()

    # --- Filtro por rol (supervisor/admin pueden ver otros visitadores)
    if request.user.is_superuser or getattr(request.user, "rol", "") == "supervisor":
        if visitador_filtro_id:
            doctores_qs = doctores_qs.filter(visitador_id=visitador_filtro_id)
        visitadores = Usuario.objects.filter(rol="visitador")
        visitador_objetivo = int(visitador_filtro_id) if visitador_filtro_id else int(request.user.id)
    else:
        doctores_qs = doctores_qs.filter(visitador_id=request.user.id)
        visitadores = []
        visitador_objetivo = int(request.user.id)

    # ---------------------- FILTROS GEOGRÁFICOS -----------------
    if distrito_id:
        doctores_qs = doctores_qs.filter(ubigeo_id=distrito_id)
    elif provincia_id:
        distritos = Distrito.objects.filter(provincia_id=provincia_id)
        doctores_qs = doctores_qs.filter(ubigeo__in=distritos)
    elif departamento_id:
        provincias = Provincia.objects.filter(departamento_id=departamento_id)
        distritos = Distrito.objects.filter(provincia__in=provincias)
        doctores_qs = doctores_qs.filter(ubigeo__in=distritos)

    # ---------------------- BÚSQUEDA ----------------------------
    if busqueda:
        doctores_qs = doctores_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(cmp__icontains=busqueda)
        )

    # ---------------------- OPTIMIZACIÓN ------------------------
    doctores_qs = (
        doctores_qs
        .select_related("ubigeo__provincia__departamento")
        .only(
            "id", "cmp", "nombre", "especialidad", "direccion", "ubigeo",
            "ubigeo__nombre", "ubigeo__provincia__nombre", "ubigeo__provincia__departamento__nombre"
        )
        .order_by("id")
    )

    # ---------------------- CREAR RUTA (POST) -------------------
    if request.method == "POST":
        doctor_id    = request.POST.get("doctor_id")
        fecha_visita = (request.POST.get("fecha_visita") or "").strip()

        # Validaciones
        if request.user.is_superuser or getattr(request.user, "rol", "") == "supervisor":
            usuario_id = request.POST.get("visitador_id")
            if not usuario_id:
                messages.error(request, "Debes seleccionar un visitador.")
                return redirect("crear_ruta")
            if not Doctor.objects.filter(id=doctor_id, visitador_id=usuario_id).exists():
                messages.error(request, "El doctor seleccionado no pertenece al visitador elegido.")
                return redirect("crear_ruta")
        else:
            usuario_id = request.user.id
            if not Doctor.objects.filter(id=doctor_id, visitador_id=usuario_id).exists():
                messages.error(request, "No tienes permiso para programar rutas con este doctor.")
                return redirect("crear_ruta")

        if not doctor_id or not fecha_visita:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("crear_ruta")

        try:
            fecha_seleccionada = date.fromisoformat(fecha_visita)
        except ValueError:
            messages.error(request, "La fecha de visita no es válida (usa formato YYYY-MM-DD).")
            return redirect("crear_ruta")

        hoy = localdate()
        estado = "pendiente" if fecha_seleccionada >= hoy else "retraso"

        # Evitar duplicados
        existe = Ruta.objects.filter(
            usuario_id=usuario_id,
            doctor_id=doctor_id,
            fecha_visita=fecha_seleccionada
        ).exists()
        if existe:
            messages.warning(request, "Ya existe una ruta programada para ese médico en esa fecha.")
            return redirect("crear_ruta")

        Ruta.objects.create(
            doctor_id=doctor_id,
            usuario_id=usuario_id,
            fecha_visita=fecha_seleccionada,
            estatus=estado,
        )
        messages.success(request, "Ruta registrada exitosamente.")
        return redirect(request.get_full_path())

    # ---------------------- CATÁLOGOS ---------------------------
    departamentos = Departamento.objects.order_by("nombre")
    provincias    = Provincia.objects.filter(departamento_id=departamento_id).order_by("nombre") if departamento_id else []
    distritos     = Distrito.objects.filter(provincia_id=provincia_id).order_by("nombre") if provincia_id else []

    # ---------------------- PAGINACIÓN --------------------------
    paginator = Paginator(doctores_qs, 30)
    doctores_page = paginator.get_page(page_num)
    doctor_ids = [d.id for d in doctores_page.object_list]

    # ---------------------- ESTADOS REALES (desde BD) ----------- #
    hoy = localdate()

    # Última ruta (más reciente por doctor)
    ultimas = (
        Ruta.objects
        .filter(usuario_id=visitador_objetivo, doctor_id__in=doctor_ids)
        .order_by("doctor_id", "-fecha_visita")
        .distinct("doctor_id")
        .values("doctor_id", "estatus", "fecha_visita")
    )
    estado_por_doctor = {r["doctor_id"]: r for r in ultimas}

    # Próxima ruta futura no completada
    proximas = (
        Ruta.objects
        .filter(
            usuario_id=visitador_objetivo,
            doctor_id__in=doctor_ids,
            fecha_visita__gte=hoy
        )
        .exclude(estatus="completado")
        .order_by("doctor_id", "fecha_visita")
        .distinct("doctor_id")
        .values("doctor_id", "fecha_visita")
    )
    prox_por_doctor = {r["doctor_id"]: r["fecha_visita"] for r in proximas}

    # Inyección de datos a los objetos renderizados
    for d in doctores_page.object_list:
        info = estado_por_doctor.get(d.id)
        d.ultimo_estatus    = (info or {}).get("estatus")          # ← estado real de rutas_ruta
        d.fecha_ultima_ruta = (info or {}).get("fecha_visita")
        d.fecha_prox_ruta   = prox_por_doctor.get(d.id)

    # ---------------------- RENDER -------------------------------
    context = {
        "doctores": doctores_page,
        "departamentos": departamentos,
        "provincias": provincias,
        "distritos": distritos,
        "visitadores": visitadores,
        "departamento_actual": int(departamento_id) if departamento_id else None,
        "provincia_actual": int(provincia_id) if provincia_id else None,
        "distrito_actual": int(distrito_id) if distrito_id else None,
        "busqueda": busqueda,
        "visitador_actual": int(visitador_filtro_id) if visitador_filtro_id else None,
        "hoy": hoy,
    }

    # Parcial para AJAX
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string("rutas/tabla_doctores.html", context, request=request)
        return JsonResponse({"html": html})

    resp = render(request, "rutas/crear_ruta.html", context)

    # Log de performance
    t_total = (time.perf_counter() - t0_total) * 1000
    logger.warning("[PERF_VIEW] crear_ruta total %.1f ms (page %s, doctores %d)",
                   t_total, page_num, len(doctor_ids))
    return resp