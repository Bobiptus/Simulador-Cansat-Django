from django.shortcuts import render, redirect
from .cansat_logic import simulate_cansat, consult_db, limpiar_bd
from django.conf import settings
from django.contrib import messages as django_messages
from django.conf.urls.static import static
import logging
logger = logging.getLogger(__name__)


def cansat_form_view(request):
    context = {}
    simulation_result_data = None 

    if request.method == 'POST':
        try:
            user_inclination = float(request.POST.get('user_inclination'))
            user_heading = float(request.POST.get('user_heading'))
            user_rail_length = float(request.POST.get('user_rail_length'))
            user_cansat_mass = float(request.POST.get('user_cansat_mass'))
            user_drag_coeff = float(request.POST.get('user_drag_coeff'))
            user_burn_time = float(request.POST.get('user_burn_time'))
            user_avg_thrust = float(request.POST.get('user_avg_thrust'))
            user_elevation = float(request.POST.get('user_elevation'))

            simulation_result_data = simulate_cansat(
                user_inclination, user_heading, user_rail_length, user_cansat_mass,
                user_drag_coeff, user_burn_time, user_avg_thrust, user_elevation
            )

            if simulation_result_data["success"]:
                context['apogee'] = simulation_result_data["apogee"]
                context['graph_image_url'] = settings.STATIC_URL + simulation_result_data["graphImage"]
                context['simulation_message'] = "¡Simulación completada con éxito!"
            else:
                context['error_message'] = simulation_result_data["message"]

        except (ValueError, TypeError) as e:
            context['error_message'] = f"Error en el formato de los datos: {e}. Asegúrate de introducir números válidos."
        except Exception as e:
            context['error_message'] = f"Error inesperado al procesar la simulación: {e}"
            logger.error(f"Error inesperado en cansat_form_view: {e}", exc_info=True)


        context['user_inclination'] = user_inclination if 'user_inclination' in locals() else request.POST.get('user_inclination')
        context['user_heading'] = user_heading if 'user_heading' in locals() else request.POST.get('user_heading')
        context['user_rail_length'] = user_rail_length if 'user_rail_length' in locals() else request.POST.get('user_rail_length')
        context['user_cansat_mass'] = user_cansat_mass if 'user_cansat_mass' in locals() else request.POST.get('user_cansat_mass')
        context['user_drag_coeff'] = user_drag_coeff if 'user_drag_coeff' in locals() else request.POST.get('user_drag_coeff')
        context['user_burn_time'] = user_burn_time if 'user_burn_time' in locals() else request.POST.get('user_burn_time')
        context['user_avg_thrust'] = user_avg_thrust if 'user_avg_thrust' in locals() else request.POST.get('user_avg_thrust')
        context['user_elevation'] = user_elevation if 'user_elevation' in locals() else request.POST.get('user_elevation')

    else: 
        # Valores por defecto para la primera carga
        context['user_inclination'] = 90
        context['user_heading'] = 60
        context['user_rail_length'] = 2.0
        context['user_cansat_mass'] = 0.5
        context['user_drag_coeff'] = 0.8
        context['user_burn_time'] = 3.5
        context['user_avg_thrust'] = 20.0
        context['user_elevation'] = 1 

    return render(request, 'Simulacion/cansat_form.html', context)

def consult_results_view(request):
    results = []
    error_message = None

    try:
        results = consult_db()
        if not results:
            error_message = "No hay resultados de simulación en la base de datos."
    except Exception as e:
        error_message = f"Error al consultar la base de datos: {e}"
        logger.error(f"Error en consult_results_view: {e}", exc_info=True)

    context = {
        'results': results,
        'error_message': error_message,
    }

    return render(request, 'Simulacion/results.html', context)


def limpiar_db_view(request):
    print(f"DEBUG: Tipo de 'django_messages' dentro de limpiar_db_view: {type(django_messages)}") # <-- Nuevo print
    result = limpiar_bd()

    if result.get("success"):
        django_messages.success(request, result.get("message", "Base de datos limpiada exitosamente.")) # <--- Usa el alias
    else:
        django_messages.error(request, result.get("message", "Error al limpiar la base de datos.")) # <--- Usa el alias

    return redirect('cansat_form')