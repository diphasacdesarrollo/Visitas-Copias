# apps/doctores/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Doctor, Prescripcion
from apps.ubicaciones.models import Departamento, Provincia, Distrito
from django.db.models import Max, Subquery, OuterRef, DateField

@login_required
def crear_doctor(request):
    departamento_id = request.GET.get('departamento')
    provincia_id = request.GET.get('provincia')
    distrito_id = request.GET.get('distrito')

    if request.method == 'POST':
        cmp = request.POST.get('cmp', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        categoria = request.POST.get('categoria', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        distrito_final_id = request.POST.get('distrito')

        if not (cmp and nombre and apellido and especialidad and direccion and categoria and distrito_final_id):
            messages.error(request, 'Todos los campos excepto fecha de nacimiento son obligatorios.')
            return redirect('doctores:crear_doctor')

        Doctor.objects.create(
            cmp=cmp,
            nombre=nombre.upper(),
            apellido=apellido.upper(),
            especialidad=especialidad.upper(),
            direccion=direccion,
            categoria=categoria,
            fecha_nacimiento=fecha_nacimiento,
            ubigeo_id=distrito_final_id
        )
        messages.success(request, 'Doctor agregado exitosamente.')
        return redirect('crear_ruta')

    departamentos = Departamento.objects.all().order_by('nombre')
    provincias = Provincia.objects.filter(departamento_id=departamento_id) if departamento_id else []
    distritos = Distrito.objects.filter(provincia_id=provincia_id) if provincia_id else []

    return render(request, 'doctores/crear_doctor.html', {
        'departamentos': departamentos,
        'provincias': provincias,
        'distritos': distritos,
        'departamento_actual': int(departamento_id) if departamento_id else None,
        'provincia_actual': int(provincia_id) if provincia_id else None,
        'distrito_actual': int(distrito_id) if distrito_id else None,
    })

@login_required
def gestionar_medicos(request):
    doctores = Doctor.objects.all()
    return render(request, 'doctores/gestionar_medicos.html', {'doctores': doctores})

@login_required
def ver_prescripciones_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    prescripciones = (
        Prescripcion.objects
        .filter(doctor_id=doctor.id)
        .select_related('producto')
        .order_by('-fecha_registro')
    )

    # 🔹 Devuelve SOLO la tabla (fragmento) para usar en un modal
    return render(request, 'doctores/_prescripciones_table.html', {
        'doctor': doctor,
        'prescripciones': prescripciones
    })