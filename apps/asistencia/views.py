# apps/visitas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.visitas.models import Visita, DetalleVisita, ProductoPresentado
from apps.productos.models import Producto
from apps.rutas.models import Ruta
from apps.doctores.models import Doctor
from django.utils.timezone import now
from django.db.models import Count, Avg, DurationField, ExpressionWrapper, F, OuterRef, Subquery, Exists, Value, CharField, IntegerField, Count, DateTimeField, Case, When, Sum
from django.core.paginator import Paginator
from django.db.models.functions import ExtractIsoWeekDay, TruncWeek, Coalesce
from django.db.models import Exists, OuterRef, Value, CharField, Case, When, IntegerField, BooleanField, Subquery, Count
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
import json
from django.db import transaction
from types import SimpleNamespace
from django.utils.dateparse import parse_datetime


@login_required
def iniciar_visita(request, ruta_id=None, doctor_id=None):
    from .draft import get_draft, save_draft, new_draft
    user = request.user
    ubicacion = request.GET.get('ubicacion', '')
    visita_es_emergencia = False
    ruta = None
    doctor = None

    # Resolver doctor/ruta con las mismas reglas actuales
    if ruta_id:
        ruta = get_object_or_404(Ruta, id=ruta_id, usuario=user)
        doctor = ruta.doctor
    elif doctor_id:
        doctor = get_object_or_404(Doctor, id=doctor_id)
        if not (user.is_superuser or getattr(user, 'rol', '') == 'supervisor'):
            if getattr(doctor, 'visitador_id', None) != user.id:
                messages.error(request, "No tienes permiso para visitar a este doctor.")
                return redirect('visitas:gestionar_visitas_medicas')
        visita_es_emergencia = True
    else:
        return redirect('visitas:gestionar_visitas_medicas')

    # Si ya hay un borrador activo, continuar allí
    from .draft import get_draft
    if get_draft(request):
        messages.info(request, "Tienes un borrador de visita en curso.")
        return redirect('visitas:agregar_productos')

    if request.method == 'POST':
        draft = new_draft(
            usuario_id=user.id,
            doctor_id=doctor.id,
            ruta_id=(ruta.id if ruta else None),
            ubicacion_inicio=request.POST.get('ubicacion', '')
        )
        save_draft(request, draft)
        messages.info(request, "Visita iniciado.")
        return redirect('visitas:agregar_productos')

    return render(request, 'visitas/iniciar_visita.html', {
        'doctor': doctor,
        'ubicacion': ubicacion,
        'visita_es_emergencia': visita_es_emergencia
    })

@login_required
def agregar_productos(request):
    """
    Pantalla de visita comercial en curso.

    - Usa el borrador (draft) guardado en sesión.
    - Permite agregar / eliminar productos (se guardan en draft["entregas"]).
    - Al finalizar, redirige a finalizar_visita, donde se crea Visita + DetalleVisita.
    """
    from .draft import get_draft, save_draft

    draft = get_draft(request)
    if not draft:
        messages.error(request, "No se ha iniciado una visita.")
        return redirect('visitas:gestionar_visitas_medicas')

    # Aseguramos claves básicas en el borrador
    entregas = draft.get("entregas", [])
    comentarios = draft.get("comentarios", "")
    draft.setdefault("productos_presentados", [])  # para compatibilidad con finalizar_visita
    draft["entregas"] = entregas

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # --- 1) Agregar producto como ítem de la visita ---
        if accion == 'agregar_item':
            producto_id = request.POST.get('producto_id')
            cantidad_raw = request.POST.get('cantidad') or "1"

            try:
                pid = int(producto_id) if producto_id else None
                cantidad = int(cantidad_raw)
            except (TypeError, ValueError):
                pid = None
                cantidad = 0

            if pid and cantidad > 0:
                # correlativo interno para poder eliminar después
                next_id = draft.get("next_entrega_id", 1)
                entregas.append({
                    "id": next_id,
                    "producto_id": pid,
                    "cantidad": cantidad,
                    "tipo_entrega": "comercial",  # único tipo en el nuevo flujo
                })
                draft["next_entrega_id"] = next_id + 1
                draft["entregas"] = entregas
                messages.success(request, "Producto agregado a la visita.")
            else:
                messages.warning(request, "Debes seleccionar un producto y una cantidad válida.")

            # Guardar comentario si el usuario escribió algo
            draft["comentarios"] = request.POST.get('comentarios', comentarios)[:5000]
            save_draft(request, draft)
            return redirect('visitas:agregar_productos')

        # --- 2) Eliminar ítem de la visita ---
        elif accion == 'eliminar_item':
            detalle_id = request.POST.get('detalle_id')
            try:
                det_id = int(detalle_id)
                entregas = [e for e in entregas if e.get("id") != det_id]
                draft["entregas"] = entregas
                messages.info(request, "Producto eliminado de la visita.")
            except (TypeError, ValueError):
                messages.warning(request, "No se pudo eliminar el producto seleccionado.")

            draft["comentarios"] = request.POST.get('comentarios', comentarios)[:5000]
            save_draft(request, draft)
            return redirect('visitas:agregar_productos')

        # --- 3) Finalizar visita ---
        elif accion == 'finalizar':
            draft["comentarios"] = request.POST.get('comentarios', comentarios)[:5000]
            save_draft(request, draft)
            return redirect('visitas:finalizar_visita')

    # =======================
    #   GET o POST ya redirigido
    # =======================

    # Productos para el combo (filtro por nombre / línea en el template)
    productos = Producto.objects.all().order_by('nombre')

    # Líneas / categorías distintas para el filtro
    lineas = (
        Producto.objects
        .exclude(categoria__isnull=True)
        .exclude(categoria__exact="")
        .values_list('categoria', flat=True)
        .distinct()
        .order_by('categoria')
    )

    # Construir "detalles" a partir de las entregas del draft
    entrega_ids = [e.get("producto_id") for e in entregas if e.get("producto_id")]
    productos_map = {
        p.id: p for p in Producto.objects.filter(id__in=entrega_ids)
    }

    detalles = []
    for e in entregas:
        prod = productos_map.get(e.get("producto_id"))
        if not prod:
            continue
        detalles.append(
            SimpleNamespace(
                id=e.get("id"),
                producto=prod,
                cantidad=e.get("cantidad"),
            )
        )

    return render(request, 'visitas/agregar_productos.html', {
        "draft": draft,
        "productos": productos,
        "lineas": lineas,
        "detalles": detalles,
        "comentarios": comentarios,
    })

@login_required
def gestionar_visitas_medicas(request):
    user = request.user
    hoy = timezone.localdate()

    # 1) Rutas del visitador (mostrar todas desde hace unos días)
    rutas = (
        Ruta.objects
        .filter(usuario=user)
        .select_related('doctor')
        .annotate(
            # 🟢 Ruta cubierta = existe visita asociada (finalizada)
            cubierta=Exists(
                Visita.objects.filter(ruta_id=OuterRef("pk"), fecha_final__isnull=False)
            )
        )
        .order_by('fecha_visita')
    )

    # 2) Doctores asignados al visitador
    doctores_base = Doctor.objects.filter(visitador_id=user.id)

    # Límites del mes actual
    first_month_day = hoy.replace(day=1)
    next_month = (first_month_day.replace(day=28) + timedelta(days=4)).replace(day=1)

    # Visitas finalizadas por doctor (conteo en el mes)
    visitas_count_sq = (
        Visita.objects
        .filter(
            usuario=user,
            doctor_id=OuterRef('pk'),
            fecha_inicio__gte=first_month_day,
            fecha_inicio__lt=next_month,
            fecha_final__isnull=False
        )
        .values('doctor_id')
        .annotate(c=Count('id'))
        .values('c')[:1]
    )

    # Última visita finalizada por doctor
    ultima_visita_sq = (
        Visita.objects
        .filter(usuario=user, doctor_id=OuterRef('pk'), fecha_final__isnull=False)
        .order_by('-fecha_inicio')
        .values('fecha_inicio')[:1]
    )

    # ¿Tiene ruta futura?
    ruta_futura_exists = Exists(
        Ruta.objects.filter(usuario=user, doctor_id=OuterRef('pk'), fecha_visita__gte=hoy)
    )

    # Id de próxima ruta (para el botón "Iniciar")
    ruta_proxima_id_sq = (
        Ruta.objects
        .filter(usuario=user, doctor_id=OuterRef('pk'), fecha_visita__gte=hoy)
        .order_by('fecha_visita')
        .values('id')[:1]
    )

    doctores_qs = (
        doctores_base
        .annotate(
            visitas_mes=Coalesce(Subquery(visitas_count_sq, output_field=IntegerField()), Value(0)),
            ultima_visita=Subquery(ultima_visita_sq, output_field=DateTimeField()),
            tiene_ruta=ruta_futura_exists,
            ruta_proxima_id=Subquery(ruta_proxima_id_sq, output_field=IntegerField()),
        )
        .annotate(
            # Semáforo & label del estado
            semaforo=Case(
                When(visitas_mes__gt=0, then=Value('verde')),
                When(tiene_ruta=True, then=Value('amarillo')),
                default=Value('rojo'),
                output_field=CharField()
            ),
            estado_label=Case(
                When(visitas_mes__gt=0, then=Value('Cubierto')),
                When(tiene_ruta=True, then=Value('Planificado')),
                default=Value('Pendiente'),
                output_field=CharField()
            )
        )
        .order_by('apellido', 'nombre')
    )

    # Añade atributo .ruta_disponible con .id si existe
    doctores = []
    for d in doctores_qs:
        setattr(d, 'ruta_disponible', SimpleNamespace(id=d.ruta_proxima_id) if d.ruta_proxima_id else None)
        doctores.append(d)

    return render(request, 'visitas/gestionar_visitas_medicas.html', {
        'rutas': rutas,
        'doctores': doctores,
    })


@login_required
def finalizar_visita(request):
    from .draft import get_draft, clear_draft

    draft = get_draft(request)
    if not draft:
        messages.error(request, "No hay una visita en curso para finalizar.")
        return redirect('visitas:gestionar_visitas_medicas')

    # 1) Tomamos la fecha de inicio del draft (string ISO) y la convertimos a datetime
    fecha_inicio_str = draft.get("fecha_inicio_iso")
    fecha_inicio = parse_datetime(fecha_inicio_str) if fecha_inicio_str else timezone.now()

    # 2) Definimos fecha_final = ahora
    fecha_final = timezone.now()

    # 3) Calculamos la duración directo (fin - inicio)
    delta = fecha_final - fecha_inicio
    if delta.total_seconds() < 0:
        delta = timedelta(0)  # por si algún tema de TZ/microsegundos la deja negativa

    try:
        with transaction.atomic():
            # --- 4) Crear la visita real con TODO ya calculado ---
            visita = Visita.objects.create(
                usuario=request.user,
                doctor_id=draft["doctor_id"],
                ruta_id=draft.get("ruta_id"),
                fecha_inicio=fecha_inicio,
                fecha_final=fecha_final,
                duracion=delta,
                ubicacion_inicio=draft.get("ubicacion_inicio") or "",
                comentarios=draft.get("comentarios") or "",
            )

            # --- 5) Crear detalles desde el borrador ---
            for prod_id in draft.get("productos_presentados", []):
                DetalleVisita.objects.create(
                    visita=visita,
                    producto_id=prod_id,
                    cantidad=1,
                    tipo_entrega="comercial",
                )

            for entrega in draft.get("entregas", []):
                DetalleVisita.objects.create(
                    visita=visita,
                    producto_id=entrega["producto_id"],
                    cantidad=entrega.get("cantidad", 1),
                    tipo_entrega=entrega.get("tipo_entrega", "comercial"),
                )

        clear_draft(request)
        messages.success(request, "Visita finalizada correctamente.")
        return redirect('visitas:gestionar_visitas_medicas')

    except Exception as e:
        messages.error(request, f"Ocurrió un error al finalizar la visita: {e}")
        return redirect('visitas:agregar_productos')


@login_required
def cancelar_visita(request):
    from .draft import clear_draft
    clear_draft(request)
    messages.info(request, "Visita cancelada. No se guardó nada en la base de datos.")
    return redirect('visitas:gestionar_visitas_medicas')

@login_required
def ver_historial(request):
    """
    Muestra el historial completo de visitas, entregas y productos presentados.
    Compatible con el nuevo flujo: solo cuenta visitas finalizadas (fecha_final no nula).
    """
    from django.db.models import (
        Count, Avg, DurationField, ExpressionWrapper, F, Value, Case, When,
        IntegerField, Exists, OuterRef, Subquery, BooleanField, Sum
    )
    from django.db.models.functions import ExtractIsoWeekDay, Coalesce
    from datetime import date, datetime, timedelta
    from django.contrib.auth import get_user_model
    import json

    User = get_user_model()
    user = request.user
    is_supervisor = user.is_superuser or getattr(user, "rol", "") == "supervisor"

    # ==== Determinar usuario objetivo ====
    rep_id = request.GET.get("rep_id")
    usuario_target = user
    visitadores_qs = User.objects.none()

    if is_supervisor:
        permitidos = [2,3,4,5,6,8,10,11,12,13,17,37,39,40]  # <-- pon aquí los IDs de los visitadores que debe ver ese supervisor

        visitadores_qs = User.objects.filter(
            rol="visitador",
            id__in=permitidos
        ).order_by("first_name", "last_name")

        if rep_id:
            usuario_target = get_object_or_404(User, id=rep_id, rol="visitador")

    # ==== Parámetros de semana ====
    hoy = timezone.localdate()
    y, w, _ = hoy.isocalendar()
    semana = int(request.GET.get("semana", w))
    año = int(request.GET.get("año", y))

    weekpick = request.GET.get("weekpick")
    if weekpick:
        try:
            a, ws = weekpick.split("-W")
            año = int(a)
            semana = int(ws)
        except Exception:
            pass

    week_start = datetime.fromisocalendar(año, semana, 1).date()
    week_end = week_start + timedelta(days=6)

    # ==== Visitas finalizadas (usuario_target) ====
    visitas_qs = (
        Visita.objects.filter(
            usuario=usuario_target,
            fecha_inicio__date__gte=week_start,
            fecha_inicio__date__lte=week_end,
            fecha_final__isnull=False
        )
        .annotate(duracion_min=ExpressionWrapper(F('fecha_final') - F('fecha_inicio'),
                                                output_field=DurationField()))
        .order_by('-fecha_inicio')
    )

    detalles_qs = DetalleVisita.objects.filter(visita__in=visitas_qs)
    presentados_qs = ProductoPresentado.objects.filter(visita__in=visitas_qs)

    total_visitas_semana = visitas_qs.count()
    total_entregas = detalles_qs.count()
    total_productos_presentados = presentados_qs.count()

    tiempo_promedio = visitas_qs.aggregate(
        prom=Avg(ExpressionWrapper(F('fecha_final') - F('fecha_inicio'),
                                  output_field=DurationField()))
    )['prom'] or timedelta(minutes=0)

    # ==== Visitas por día ====
    visitas_por_dia = (
        visitas_qs
        .annotate(dow=ExtractIsoWeekDay('fecha_inicio'))
        .values('dow')
        .annotate(c=Count('id'))
        .order_by('dow')
    )

    nombres_dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    mapa = {row['dow']: row['c'] for row in visitas_por_dia}
    visitas_semana_labels = nombres_dias
    visitas_semana_data = [mapa.get(i, 0) for i in range(1, 8)]

    # ==== Top doctores ====
    def _first_token(s: str) -> str:
        s = (s or "").strip()
        return s.split()[0] if s else ""

    top_raw = (
        visitas_qs.values('doctor__apellido', 'doctor__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:5]
    )

    top_doctores_labels = [
        (f"{_first_token(d['doctor__apellido'])} {_first_token(d['doctor__nombre'])}".strip() or "Sin nombre")
        for d in top_raw
    ]
    top_doctores_data = [d['total'] for d in top_raw]

    # ==== Navegación semanal ====
    prev_monday = week_start - timedelta(days=7)
    next_monday = week_start + timedelta(days=7)
    prev_year, prev_week, _ = prev_monday.isocalendar()
    next_year, next_week, _ = next_monday.isocalendar()
    weekpick_value = f"{año}-W{semana:02d}"

    # ==== Cobertura mensual (usuario_target) ====
    month_param = request.GET.get("month")
    if month_param:
        try:
            y_, m_ = month_param.split("-")
            year_q = int(y_)
            month_q = int(m_)
        except Exception:
            year_q, month_q = hoy.year, hoy.month
    else:
        year_q, month_q = hoy.year, hoy.month

    month_value = f"{year_q}-{month_q:02d}"
    first_month_day = date(year_q, month_q, 1)
    next_month = (first_month_day.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    doctores_base = Doctor.objects.all()
    if not is_supervisor:
        doctores_base = doctores_base.filter(visitador_id=usuario_target.id)

    visitado_mes_qs = Visita.objects.filter(
        usuario=usuario_target,
        doctor_id=OuterRef('pk'),
        fecha_inicio__gte=first_month_day,
        fecha_inicio__lt=next_month,
        fecha_final__isnull=False
    )

    visitas_count_sq = (
        Visita.objects.filter(
            usuario=usuario_target,
            doctor_id=OuterRef('pk'),
            fecha_inicio__gte=first_month_day,
            fecha_inicio__lt=next_month,
            fecha_final__isnull=False
        )
        .values('doctor_id')
        .annotate(c=Count('id'))
        .values('c')[:1]
    )

    doctores = (
        doctores_base
        .annotate(
            visitas_mes=Coalesce(Subquery(visitas_count_sq, output_field=IntegerField()), Value(0)),
            visitado_mes=Exists(visitado_mes_qs)
        )
        .order_by('apellido', 'nombre')
    )

    asignados_total = doctores.count()
    visitados_count = sum(1 for d in doctores if d.visitado_mes)
    cobertura_pct = round((visitados_count / asignados_total) * 100, 1) if asignados_total else 0.0
    pendientes = max(asignados_total - visitados_count, 0)

    # ==== RESUMEN GENERAL POR VISITADOR (vista gerente) ====
    resumen_visitadores = []
    if is_supervisor and not rep_id:
        for v in visitadores_qs:
            # Visitas finalizadas en la semana y mes
            visitas_semana_v = Visita.objects.filter(
                usuario=v,
                fecha_inicio__date__gte=week_start,
                fecha_inicio__date__lte=week_end,
                fecha_final__isnull=False,
            ).count()

            visitas_mes_v = Visita.objects.filter(
                usuario=v,
                fecha_inicio__gte=first_month_day,
                fecha_inicio__lt=next_month,
                fecha_final__isnull=False,
            ).count()

            # Total de unidades entregadas en la semana
            productos_semana_v = DetalleVisita.objects.filter(
                visita__usuario=v,
                visita__fecha_inicio__date__gte=week_start,
                visita__fecha_inicio__date__lte=week_end,
                visita__fecha_final__isnull=False,
            ).aggregate(total=Sum('cantidad'))['total'] or 0

            # Doctores asignados a ese visitador
            asignados_v = Doctor.objects.filter(visitador_id=v.id).count()

            # Doctores visitados en el mes
            visitados_doctores_v = (
                Visita.objects.filter(
                    usuario=v,
                    fecha_inicio__gte=first_month_day,
                    fecha_inicio__lt=next_month,
                    fecha_final__isnull=False,
                )
                .values('doctor_id')
                .distinct()
                .count()
            )

            cobertura_v = round((visitados_doctores_v / asignados_v) * 100, 1) if asignados_v else 0.0

            resumen_visitadores.append({
                "visitador": v,
                "visitas_semana": visitas_semana_v,
                "visitas_mes": visitas_mes_v,
                "productos_semana": productos_semana_v,
                "asignados_semana": asignados_v,
                "cobertura": cobertura_v,
            })

    # ==== Título ====
    if not is_supervisor:
        titulo_nombre = "Mi historial"
    elif rep_id:
        titulo_nombre = usuario_target.get_full_name() or usuario_target.username
    else:
        titulo_nombre = "Resumen general"

    # ==== Render ====
    return render(request, 'visitas/historial.html', {
        'titulo_nombre': titulo_nombre,
        'is_supervisor': is_supervisor,
        'visitadores': visitadores_qs,
        'rep_id': str(rep_id or ""),
        'semana_actual': semana,
        'año_actual': año,
        'semana_anterior': prev_week,
        'año_anterior': prev_year,
        'semana_siguiente': next_week,
        'año_siguiente': next_year,
        'weekpick_value': weekpick_value,
        'month_value': month_value,

        # detalle actual (solo se usa cuando hay rep_id o es visitador)
        'visitas': visitas_qs,
        'detalles': detalles_qs,
        'presentados': presentados_qs,
        'total_visitas_semana': total_visitas_semana,
        'total_entregas': total_entregas,
        'total_productos_presentados': total_productos_presentados,
        'cobertura_pct': cobertura_pct,
        'visitados_count': visitados_count,
        'pendientes': pendientes,
        'asignados_total': asignados_total,
        'visitas_semana_labels': json.dumps(visitas_semana_labels),
        'visitas_semana_data': json.dumps(visitas_semana_data),
        'cobertura_labels': json.dumps(["Visitados", "Pendientes"]),
        'cobertura_data': json.dumps([visitados_count, pendientes]),
        'top_doctores_labels': json.dumps(top_doctores_labels),
        'top_doctores_data': json.dumps(top_doctores_data),
        'resumen_visitadores': resumen_visitadores,
    })