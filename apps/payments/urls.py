from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('process/', views.process_payments, name='process_payments'),
]
