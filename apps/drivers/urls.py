from django.urls import path

from . import views

app_name = 'drivers'

urlpatterns = [
    path('', views.driver_list, name='driver_list'),
    path('ajax/list/', views.driver_list_ajax, name='driver_list_ajax'),
    path('ajax/get/<int:pk>/', views.driver_get_ajax, name='driver_get_ajax'),
    path('ajax/save/', views.driver_save_ajax, name='driver_save_ajax'),
    path('ajax/delete/<int:pk>/', views.driver_delete_ajax, name='driver_delete_ajax'),
    path('add/', views.driver_form, name='driver_add'),
    path('<int:pk>/edit/', views.driver_form, name='driver_edit'),
    path('<int:pk>/delete/', views.driver_delete, name='driver_delete'),
]