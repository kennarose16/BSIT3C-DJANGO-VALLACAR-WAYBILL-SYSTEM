from django.contrib import admin

from .models import AutoPayment


@admin.register(AutoPayment)
class AutoPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'target_name', 'amount', 'due_date', 'status', 'auto_pay')
    list_filter = ('status', 'auto_pay', 'frequency')
    search_fields = ('reference_number', 'notes')
