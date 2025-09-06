from django.urls import path
from . import views

app_name = 'agendamento'

urlpatterns = [
    # Páginas públicas de agendamento
    path('<int:comerciante_id>/', views.agendar_servico, name='agendar_servico'),
    path('confirmacao/', views.confirmar_agendamento, name='confirmar_agendamento'),
    path('sucesso/', views.agendamento_sucesso, name='agendamento_sucesso'),

    # APIs para agendamento
    path('api/<int:comerciante_id>/funcionarios/<int:servico_id>/',
         views.get_funcionarios_servico, name='funcionarios_servico'),
    path('api/<int:comerciante_id>/horarios/<int:funcionario_id>/',
         views.get_horarios_disponiveis, name='horarios_disponiveis'),
    path('api/<int:comerciante_id>/criar/',
         views.criar_agendamento, name='criar_agendamento'),
    path('api/verificar-disponibilidade/',
         views.verificar_disponibilidade, name='verificar_disponibilidade'),
]