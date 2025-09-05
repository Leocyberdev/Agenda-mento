from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('comerciantes/', views.comerciantes_list, name='comerciantes_list'),
    path('comerciantes/create/', views.comerciante_create, name='comerciante_create'),
    path('comerciantes/<int:pk>/edit/', views.comerciante_edit, name='comerciante_edit'),
    path('comerciantes/<int:pk>/delete/', views.comerciante_delete, name='comerciante_delete'),
]

