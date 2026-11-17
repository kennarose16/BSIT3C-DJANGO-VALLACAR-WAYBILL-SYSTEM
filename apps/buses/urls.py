from django.urls import path

from . import views

app_name = 'buses'

urlpatterns = [
    path('', views.bus_list, name='bus_list'),
    path('ajax/list/', views.bus_list_ajax, name='bus_list_ajax'),
    path('ajax/get/<int:pk>/', views.bus_get_ajax, name='bus_get_ajax'),
    path('ajax/save/', views.bus_save_ajax, name='bus_save_ajax'),
    path('ajax/delete/<int:pk>/', views.bus_delete_ajax, name='bus_delete_ajax'),
    path('add/', views.bus_form, name='bus_add'),
    path('<int:pk>/edit/', views.bus_form, name='bus_edit'),
    path('<int:pk>/delete/', views.bus_delete, name='bus_delete'),
    path('<int:bus_pk>/routes/', views.route_list, name='route_list'),
    path('<int:bus_pk>/routes/ajax/list/', views.route_list_ajax, name='route_list_ajax'),
    path('<int:bus_pk>/routes/ajax/get/<int:pk>/', views.route_get_ajax, name='route_get_ajax'),
    path('<int:bus_pk>/routes/ajax/save/', views.route_save_ajax, name='route_save_ajax'),
    path('<int:bus_pk>/routes/ajax/delete/<int:pk>/', views.route_delete_ajax, name='route_delete_ajax'),
    path('<int:bus_pk>/routes/add/', views.route_form, name='route_add'),
    path('<int:bus_pk>/routes/<int:pk>/edit/', views.route_form, name='route_edit'),
    path('<int:bus_pk>/routes/<int:pk>/delete/', views.route_delete, name='route_delete'),
]