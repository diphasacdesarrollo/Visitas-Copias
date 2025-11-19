# apps/asistencia/views.py
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Asistencia
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import localtime
from datetime import date

@login_required
def registrar_asistencia(request):
    usuario = request.user

    asistencia_incompleta = Asistencia.objects.filter(
        usuario=usuario, fecha_salida__isnull=True
    ).order_by('-id').first()

    ya_ingreso = asistencia_incompleta is not None
    ya_salida = False

    # ➕ Obtener última asistencia (completa o incompleta)
    ultima_asistencia = Asistencia.objects.filter(usuario=usuario).order_by('-id').first()
    ultima_accion = None
    if ultima_asistencia:
        if ultima_asistencia.fecha_salida:
            ultima_accion = ('Salida', ultima_asistencia.fecha_salida)
        elif ultima_asistencia.fecha_ingreso:
            ultima_accion = ('Ingreso', ultima_asistencia.fecha_ingreso)

    # 👉 POST para registrar ingreso/salida
    if request.method == 'POST':
        accion = request.POST.get('accion')
        ubicacion = request.POST.get('ubicacion')

        if accion == 'ingreso' and not ya_ingreso:
            Asistencia.objects.create(
                usuario=usuario,
                fecha_ingreso=timezone.now(),
                ubicacion_ingreso=ubicacion
            )
            messages.success(request, "Ingreso registrado correctamente.")
            return redirect('inicio')

        elif accion == 'salida' and ya_ingreso:
            asistencia_incompleta.fecha_salida = timezone.now()
            asistencia_incompleta.ubicacion_salida = ubicacion
            asistencia_incompleta.save()
            messages.success(request, "Salida registrada correctamente.")
            return redirect('inicio')

    # 🔄 Obtener semana a mostrar
    hoy = localtime().date()
    año_param = request.GET.get('año')
    semana_param = request.GET.get('semana')

    if año_param and semana_param:
        try:
            año_iso = int(año_param)
            semana_iso = int(semana_param)
        except ValueError:
            año_iso, semana_iso, _ = hoy.isocalendar()
    else:
        año_iso, semana_iso, _ = hoy.isocalendar()

    # 📅 Filtro de asistencias por semana
    asistencias_semana = Asistencia.objects.filter(
        usuario=usuario,
        fecha_ingreso__week=semana_iso,
        fecha_ingreso__year=año_iso
    ).order_by('fecha_ingreso')

    context = {
        'ya_ingreso': ya_ingreso,
        'ya_salida': ya_salida,
        'ultima_accion': ultima_accion,
        'asistencias_semana': asistencias_semana,
        'semana_actual': semana_iso,
        'año_actual': año_iso,
    }

    return render(request, 'asistencia/registrar.html', context)