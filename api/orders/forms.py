from django import forms
from django.core.exceptions import ValidationError
from .models import Order

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "address_full_name", "order_code", "total_price", "status",
        ]