from django import forms
from django.utils import timezone

from apps.buses.models import Bus, BusRoute
from .pricing import calculate_amount, default_base_rate
from .models import Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['bus', 'destination', 'sender_name', 'receiver_name', 'amount', 'payment_status', 'status', 'proof_image']
        labels = {
            'bus': 'Fleet number and plate',
            'destination': 'Destination',
            'sender_name': 'Sender name',
            'receiver_name': 'Receiver name',
            'amount': 'Amount (PHP)',
            'payment_status': 'Payment status',
            'status': 'Initial status',
            'proof_image': 'Picture received',
        }
        widgets = {
            'bus': forms.Select(attrs={'class': 'form-select'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'placeholder': 'Enter destination'}),
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'receiver_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control fw-bold', 'min': '0', 'step': '0.01'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'proof_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'capture': 'environment',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bus'].queryset = Bus.objects.order_by('fleet_number')
        self.fields['payment_status'].choices = [
            (Transaction.PaymentStatus.PAID, 'Paid'),
            (Transaction.PaymentStatus.UNPAID, 'Unpaid'),
        ]

    def clean(self):
        cleaned_data = super().clean()
        bus = cleaned_data.get('bus')
        destination = cleaned_data.get('destination', '').strip()
        if destination:
            cleaned_data['destination'] = destination
        if bus:
            cleaned_data['_calculated_amount'] = calculate_amount(bus, default_base_rate())
        return cleaned_data

    def clean_proof_image(self):
        image = self.cleaned_data.get('proof_image')
        if image and image.size > 10 * 1024 * 1024:
            raise forms.ValidationError('The proof image must be 10 MB or smaller.')
        return image

    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.route = BusRoute.objects.filter(
            bus=transaction.bus,
            destination__iexact=transaction.destination,
        ).first()
        transaction.amount = self.cleaned_data.get('amount')
        if transaction.amount is None:
            transaction.amount = self.cleaned_data['_calculated_amount']
        if transaction.proof_image:
            transaction.status = Transaction.Status.COMPLETED
            transaction.received_at = timezone.now()
        if commit:
            transaction.save()
        return transaction


class ProofUploadForm(forms.Form):
    proof_image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
        }),
    )

    def clean_proof_image(self):
        image = self.cleaned_data['proof_image']
        if image.size > 10 * 1024 * 1024:
            raise forms.ValidationError('The proof image must be 10 MB or smaller.')
        return image
