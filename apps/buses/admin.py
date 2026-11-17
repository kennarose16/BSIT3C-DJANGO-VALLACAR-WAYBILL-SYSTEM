from django.contrib import admin

from .models import Bus, BusRoute


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('fleet_number', 'plate_number', 'capacity', 'driver', 'status')
    list_filter = ('status',)
    search_fields = ('fleet_number', 'plate_number', 'driver__first_name', 'driver__last_name')


@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'bus', 'origin', 'destination', 'fare', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'origin', 'destination', 'bus__fleet_number')