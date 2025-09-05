from django.urls import path
from . import views

app_name = 'comerciante_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('funcionarios/', views.funcionarios_list, name='funcionarios_list'),
    path('funcionarios/create/', views.funcionario_create, name='funcionario_create'),
    path('funcionarios/<int:pk>/edit/', views.funcionario_edit, name='funcionario_edit'),
    path('servicos/', views.servicos_list, name='servicos_list'),
    path('servicos/create/', views.servico_create, name='servico_create'),
    path('servicos/<int:pk>/edit/', views.servico_edit, name='servico_edit'),
    path('agendamentos/', views.agendamentos_list, name='agendamentos_list'),
    path('agendamentos/<int:pk>/edit/', views.agendamento_edit, name='agendamento_edit'),
    path('funcionario-dashboard/', views.funcionario_dashboard, name='funcionario_dashboard'),
    path('link-agendamento/', views.link_agendamento, name='link_agendamento'),
]

