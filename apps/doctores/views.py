from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Doctor, Prescripcion


@login_required
def crear_doctor(request):
    if request.method == 'POST':
        cmp = request.POST.get('cmp', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        if not (cmp and nombre and especialidad and direccion):
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('doctores:crear_doctor')

        doctor, creado = Doctor.objects.update_or_create(
            cmp=cmp,
            defaults={
                'nombre': nombre.upper(),
                'apellido': '|',
                'especialidad': especialidad.upper(),
                'direccion': direccion.upper(),
                'categoria': 1,
                'ubigeo': None,
                'visitador': request.user,
            }
        )

        if creado:
            messages.success(request, 'Doctor agregado exitosamente.')
        else:
            messages.success(request, 'Doctor actualizado exitosamente.')

        return redirect('visitas:gestionar_visitas_medicas')

    return render(request, 'doctores/crear_doctor.html')


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

    return render(request, 'doctores/_prescripciones_table.html', {
        'doctor': doctor,
        'prescripciones': prescripciones
    })