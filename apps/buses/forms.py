from django import forms
from django.core.exceptions import ValidationError

from apps.drivers.models import Driver
from .models import Bus, BusRoute


class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['fleet_number', 'plate_number', 'capacity', 'driver', 'status']
        widgets = {
            'fleet_number': forms.TextInput(attrs={'class': 'form-control'}),
            'plate_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'driver': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['driver'].required = False
        self.fields['driver'].empty_label = 'Unassigned'
        self.fields['driver'].queryset = Driver.objects.filter(is_active=True).order_by('last_name', 'first_name')
        if self.instance.pk and self.instance.driver_id:
            self.fields['driver'].queryset |= Driver.objects.filter(pk=self.instance.driver_id)


class BusRouteForm(forms.ModelForm):
    class Meta:
        model = BusRoute
        fields = ['name', 'origin', 'destination', 'departure_time', 'arrival_time', 'fare', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'departure_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'arrival_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        routes = BusRoute.objects.filter(bus=self.instance.bus, name__iexact=name)
        if self.instance.pk:
            routes = routes.exclude(pk=self.instance.pk)
        if routes.exists():
            raise ValidationError('This route name is already used for this bus.')
        return name