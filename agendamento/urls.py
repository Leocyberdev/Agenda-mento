from django.urls import path
from . import views

app_name = 'agendamento'

urlpatterns = [
    # Páginas públicas de agendamento
    path('<int:comerciante_id>/', views.agendar_servico, name='agendar_servico'),
    path('confirmar/', views.confirmar_agendamento, name='confirmar_agendamento'),
    path('confirmar/<str:token>/', views.confirmar_agendamento_token, name='confirmar_agendamento_token'),
    path('cancelar/<str:token>/', views.cancelar_agendamento_token, name='cancelar_agendamento_token'),
    path('confirmado/<int:agendamento_id>/', views.agendamento_confirmado, name='agendamento_confirmado'),
    path('cancelado/<int:agendamento_id>/', views.agendamento_cancelado, name='agendamento_cancelado'),
    path('sucesso/', views.agendamento_sucesso, name='agendamento_sucesso'),

    # APIs para agendamento
    path('api/<int:comerciante_id>/funcionarios/<int:servico_id>/',
         views.get_funcionarios_servico, name='funcionarios_servico'),
    path('api/<int:comerciante_id>/horarios/<int:funcionario_id>/',
         views.get_horarios_disponiveis, name='horarios_disponiveis'),
    path('api/<int:comerciante_id>/criar/',
         views.criar_agendamento, name='criar_agendamento'),
    path('api/verificar_disponibilidade/',
         views.verificar_disponibilidade, name='verificar_disponibilidade'),
]