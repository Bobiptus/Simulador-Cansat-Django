from django.urls import path
from . import views # Importa el módulo views de la app

urlpatterns = [
    path('', views.cansat_form_view, name='cansat_form'),
    path('results/', views.consult_results_view, name='consult_results'), # <--- ¡Añade esta línea!
    path('limpiar/', views.limpiar_db_view, name='limpiar_db'),
]