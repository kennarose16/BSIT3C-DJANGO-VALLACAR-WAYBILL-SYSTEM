from django import forms

from apps.buses.models import Bus, BusRoute
from .pricing import DESTINATION_PRESETS, calculate_amount
from .models import Transaction


class TransactionForm(forms.ModelForm):
    destination_choice = forms.ChoiceField(
        choices=(),
        label='Destination',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Transaction
        fields = ['bus', 'sender_name', 'receiver_name', 'amount', 'payment_status', 'status']
        labels = {
            'bus': 'Fleet number and plate',
            'sender_name': 'Sender name',
            'receiver_name': 'Receiver name',
            'amount': 'Amount (PHP)',
            'payment_status': 'Payment status',
            'status': 'Initial status',
        }
        widgets = {
            'bus': forms.Select(attrs={'class': 'form-select'}),
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'receiver_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control fw-bold', 'min': '0', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bus'].queryset = Bus.objects.order_by('fleet_number')
        self.fields['payment_status'].choices = [
            (Transaction.PaymentStatus.PAID, 'Paid'),
            (Transaction.PaymentStatus.UNPAID, 'Unpaid'),
        ]
        bus_id = self.data.get('bus') or self.initial.get('bus')
        destinations = [('', 'Select destination')]
        if bus_id:
            routes = BusRoute.objects.filter(bus_id=bus_id).order_by('destination', 'name')
            destinations.extend((f'route:{route.pk}', f'{route.destination} - {route.name} (PHP {route.fare:.2f})') for route in routes)
        destinations.extend((f'preset:{key}', f"{item['name']} (PHP {item['base_fare']:.2f})") for key, item in DESTINATION_PRESETS.items())
        self.fields['destination_choice'].choices = destinations

    def clean(self):
        cleaned_data = super().clean()
        bus = cleaned_data.get('bus')
        destination_choice = cleaned_data.get('destination_choice', '')
        route = None
        base_fare = None
        if destination_choice.startswith('route:'):
            route_id = destination_choice.removeprefix('route:')
            route = BusRoute.objects.filter(pk=route_id, bus=bus).first() if bus else None
            if not route:
                self.add_error('destination_choice', 'Choose a destination assigned to the selected bus.')
            else:
                base_fare = route.fare
        elif destination_choice.startswith('preset:'):
            preset = DESTINATION_PRESETS.get(destination_choice.removeprefix('preset:'))
            if not preset:
                self.add_error('destination_choice', 'Choose a valid destination.')
            else:
                base_fare = preset['base_fare']
        if bus and base_fare is not None:
            cleaned_data['_selected_route'] = route
            cleaned_data['_destination_name'] = route.destination if route else preset['name']
            cleaned_data['_calculated_amount'] = calculate_amount(bus, base_fare)
        return cleaned_data

    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.route = self.cleaned_data['_selected_route']
        transaction.destination = self.cleaned_data['_destination_name']
        transaction.amount = self.cleaned_data.get('amount')
        if transaction.amount is None:
            transaction.amount = self.cleaned_data['_calculated_amount']
        if commit:
            transaction.save()
        return transaction
