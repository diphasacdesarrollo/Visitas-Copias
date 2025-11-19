//static/js/ubicaciones.js
document.addEventListener('DOMContentLoaded', function () {
    const departamentoSelect = document.getElementById('departamento');
    const provinciaSelect = document.getElementById('provincia');
    const distritoSelect = document.getElementById('distrito');

    if (!departamentoSelect || !provinciaSelect || !distritoSelect) return;

    const resetSelect = (selectElement, placeholder) => {
        selectElement.innerHTML = `<option value="">${placeholder}</option>`;
        selectElement.disabled = true;
    };

    departamentoSelect.addEventListener('change', function () {
        const departamentoId = this.value;
        resetSelect(provinciaSelect, '-- Selecciona una provincia --');
        resetSelect(distritoSelect, '-- Selecciona un distrito --');

        if (departamentoId) {
            fetch(`/api/provincias/?departamento_id=${departamentoId}`)
                .then(response => response.json())
                .then(data => {
                    provinciaSelect.disabled = false;
                    data.forEach(provincia => {
                        const option = document.createElement('option');
                        option.value = provincia.id;
                        option.textContent = provincia.nombre;
                        provinciaSelect.appendChild(option);
                    });
                });
        }
    });

    provinciaSelect.addEventListener('change', function () {
        const provinciaId = this.value;
        resetSelect(distritoSelect, '-- Selecciona un distrito --');

        if (provinciaId) {
            fetch(`/api/distritos/?provincia_id=${provinciaId}`)
                .then(response => response.json())
                .then(data => {
                    distritoSelect.disabled = false;
                    data.forEach(distrito => {
                        const option = document.createElement('option');
                        option.value = distrito.id;
                        option.textContent = distrito.nombre;
                        distritoSelect.appendChild(option);
                    });
                });
        }
    });

    // Estado inicial al cargar la página
    if (!departamentoSelect.value) {
        provinciaSelect.disabled = true;
        distritoSelect.disabled = true;
    } else if (!provinciaSelect.value) {
        distritoSelect.disabled = true;
    }
});