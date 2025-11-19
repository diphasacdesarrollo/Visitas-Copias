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
from django.db.models import Count, Avg, DurationField, ExpressionWrapper, F, OuterRef, Subquery, Exists, Value, CharField, IntegerField, Count, DateTimeField, Case, When
from django.core.paginator import Paginator
from django.db.models.functions import ExtractIsoWeekDay, TruncWeek, Coalesce
from django.db.models import Exists, OuterRef, Value, CharField, Case, When, IntegerField, BooleanField, Subquery, Count
from datetime import date, datetime, timedelta
from django.contrib.auth import get_user_model
import json
from django.db import transaction
from types import SimpleNamespace

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
    from .draft import get_draft, save_draft
    draft = get_draft(request)
    if not draft:
        messages.error(request, "No se ha iniciado una visita")
        return redirect('visitas:gestionar_visitas_medicas')

    productos_presentados_ids = draft.get("productos_presentados", [])
    entregas_draft = draft.get("entregas", [])
    comentarios = draft.get("comentarios", "")

    productos_promocionales = Producto.objects.filter(tipo_producto='promocional')
    productos_muestra = Producto.objects.filter(tipo_producto='muestra')
    productos_merch = Producto.objects.filter(tipo_producto='merch')

    productos_presentados_qs = Producto.objects.filter(id__in=productos_presentados_ids)

    imagen_productos = {
        # conserva tu mapeo existente producto → nombre de imagen
    }

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # Checkboxes de presentados
        nuevos_presentados = request.POST.getlist('productos_presentados')
        draft["productos_presentados"] = [int(pid) for pid in nuevos_presentados]

        # Entrega
        if accion == 'agregar_entrega':
            producto_id = request.POST.get('producto_entrega')
            cantidad = request.POST.get('cantidad_entrega')
            tipo_entrega = request.POST.get('tipo_entrega')
            try:
                if producto_id and cantidad and tipo_entrega:
                    pid = int(producto_id); cant = int(cantidad)
                    if cant > 0:
                        entregas = draft.get("entregas", [])
                        entregas.append({
                            "producto_id": pid,
                            "cantidad": cant,
                            "tipo_entrega": tipo_entrega
                        })
                        draft["entregas"] = entregas
                        messages.success(request, "Entrega añadida.")
                    else:
                        messages.warning(request, "La cantidad debe ser mayor a 0.")
            except ValueError:
                messages.warning(request, "Datos de entrega inválidos.")

        # Comentarios
        draft["comentarios"] = request.POST.get('comentarios', '')[:5000]
        save_draft(request, draft)

        # Acciones de flujo
        if accion == 'finalizar':
            return redirect('visitas:finalizar_visita')
        if accion == 'cancelar':
            return redirect('visitas:cancelar_visita')

        return redirect('visitas:agregar_productos')
    # IDs de productos usados en las entregas del borrador
    entrega_ids = [e.get("producto_id") for e in entregas_draft if e.get("producto_id")]
    productos_map = {
    p.id: {"nombre": p.nombre, "presentacion": getattr(p, "presentacion", "")}
    for p in Producto.objects.filter(id__in=entrega_ids)
    }


    return render(request, 'visitas/agregar_productos.html', {
        "draft": draft,
        "productos_promocionales": productos_promocionales,
        "productos_muestra": productos_muestra,
        "productos_merch": productos_merch,
        "productos_presentados": productos_presentados_qs,
        "productos_presentados_ids": productos_presentados_ids,
        "entregas": entregas_draft,
        "comentarios": comentarios,
        "imagen_productos": imagen_productos,
        "producto_nombres": productos_map,
    })

# ……………………………………………………………………………………………………………………………
# (Resto de tus vistas originales SIN CAMBIOS)
# ……………………………………………………………………………………………………………………………

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
    # importa helpers del draft (¡ya actualizado!)
    from .draft import get_draft, clear_draft, get_ruta_id

    draft = get_draft(request)
    if not draft:
        messages.error(request, "No hay borrador para finalizar.")
        return redirect('visitas:gestionar_visitas_medicas')

    if not draft.get("doctor_id"):
        messages.error(request, "Borrador inválido: falta doctor.")
        return redirect('visitas:agregar_productos')

    try:
        with transaction.atomic():
            # --- 1) Crear la visita real ---
            visita = Visita.objects.create(
                usuario=request.user,
                doctor_id=draft["doctor_id"],
                ruta_id=draft.get("ruta_id"),  # puede venir o no; no es obligatorio
                fecha_inicio=draft.get("fecha_inicio_iso", timezone.now()),
                ubicacion_inicio=draft.get("ubicacion_inicio") or "",
                comentarios=draft.get("comentarios") or "",
                fecha_final=timezone.now(),
            )

            # --- 2) Duración (si tu modelo la soporta) ---
            try:
                if hasattr(visita, "calcular_duracion"):
                    visita.duracion = visita.calcular_duracion()
                    visita.save(update_fields=["duracion"])
            except Exception:
                pass

            # --- 3) Productos presentados ---
            presentados = [
                ProductoPresentado(visita=visita, producto_id=pid)
                for pid in draft.get("productos_presentados", [])
                if pid
            ]
            if presentados:
                ProductoPresentado.objects.bulk_create(
                    presentados, ignore_conflicts=True
                )

            # --- 4) Entregas (muestras / merch) ---
            entregas_objs = []
            for e in draft.get("entregas", []):
                try:
                    entregas_objs.append(
                        DetalleVisita(
                            visita=visita,
                            producto_id=int(e["producto_id"]),
                            cantidad=int(e["cantidad"]),
                            tipo_entrega=e.get("tipo_entrega"),  # "muestra" o "merch"
                        )
                    )
                except Exception:
                    continue
            if entregas_objs:
                DetalleVisita.objects.bulk_create(entregas_objs)

            # --- 5) Actualizar la ruta asociada (si corresponde) ---
            try:
                # Prioriza ruta_id del draft; si no hay, usará ruta_sugerida_id
                ruta_id = get_ruta_id(request)

                ruta = None
                if ruta_id:
                    ruta = (
                        Ruta.objects.select_for_update()
                        .filter(id=ruta_id)
                        .first()
                    )

                # Si por algún motivo no se encontró, no bloqueamos el flujo
                if ruta:
                    for _campo in ("estado", "estatus", "status"):
                        if hasattr(ruta, _campo):
                            setattr(ruta, _campo, "completado")
                            break

                    # Sella fecha real de cobertura si existe el campo
                    if hasattr(ruta, "fecha_visita_real") and not ruta.fecha_visita_real:
                        ruta.fecha_visita_real = timezone.localdate(visita.fecha_final)

                    ruta.save()

                    # Si tu modelo tiene lógica adicional
                    if hasattr(ruta, "actualizar_estatus"):
                        try:
                            ruta.actualizar_estatus()
                        except Exception:
                            pass

            except Exception:
                # Nunca romper el cierre de visita por un problema con rutas
                pass

    except Exception as ex:
        messages.error(request, f"No se pudo finalizar la visita: {ex}")
        return redirect('visitas:agregar_productos')

    # --- 6) Limpiar draft DESPUÉS del commit y redirigir a gestión ---
    def _post_commit():
        clear_draft(request)
        messages.success(request, "Visita finalizada y ruta marcada como completada.")
    transaction.on_commit(_post_commit)

    return redirect('visitas:gestionar_visitas_medicas')


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
    from django.db.models import Count, Avg, DurationField, ExpressionWrapper, F, Value, Case, When, IntegerField, Exists, OuterRef, Subquery, BooleanField
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
        visitadores_qs = User.objects.filter(rol="visitador").order_by("first_name", "last_name")
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

    # ==== Visitas finalizadas ====
    visitas_qs = (
        Visita.objects.filter(
            usuario=usuario_target,
            fecha_inicio__date__gte=week_start,
            fecha_inicio__date__lte=week_end,
            fecha_final__isnull=False
        )
        .annotate(duracion_min=ExpressionWrapper(F('fecha_final') - F('fecha_inicio'), output_field=DurationField()))
        .order_by('-fecha_inicio')
    )

    detalles_qs = DetalleVisita.objects.filter(visita__in=visitas_qs)
    presentados_qs = ProductoPresentado.objects.filter(visita__in=visitas_qs)

    total_visitas_semana = visitas_qs.count()
    total_entregas = detalles_qs.count()
    total_productos_presentados = presentados_qs.count()

    tiempo_promedio = visitas_qs.aggregate(
        prom=Avg(ExpressionWrapper(F('fecha_final') - F('fecha_inicio'), output_field=DurationField()))
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

    # ==== Cobertura mensual ====
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

    # ==== Render ====
    titulo_nombre = (
        "Mi historial" if not is_supervisor
        else f"Historial — {usuario_target.get_full_name() or usuario_target.username}"
    )

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
    })