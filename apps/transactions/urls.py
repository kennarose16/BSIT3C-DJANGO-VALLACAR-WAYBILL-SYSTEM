from django.urls import path

from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('create/', views.transaction_create_ajax, name='transaction_create_ajax'),
    path('buses/<int:bus_pk>/options/', views.transaction_bus_data, name='transaction_bus_data'),
    path('<int:pk>/mark-paid/', views.transaction_mark_paid, name='transaction_mark_paid'),
    path('<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('<int:pk>/', views.transaction_detail, name='transaction_detail'),
]