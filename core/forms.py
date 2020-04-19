from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

PAYMENT_OTIONS = (
    ('s', 'Stripe'),
    ('p', 'Paypal')
)
class CheckOutForm(forms.Form):
    street_address = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder':'1234 Main St'
    }))
    apartment_address = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder':'1234 Main St'
    }))
    country = CountryField(blank_label='(select country)').formfield(widget=CountrySelectWidget(attrs={
        'class': 'custom-select d-block w-100'
    }))
    zip = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control'
    }))
    same_shipping_address = forms.BooleanField(required=False)
    save_info = forms.BooleanField(required=False)
    payment_option = forms.ChoiceField(widget=forms.RadioSelect,choices=PAYMENT_OTIONS)

class CouponForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class':'form-control',
        'placeholder': 'Promo Code',
        'aria-label': 'Receipient\'s username',
        'aria-describedby': 'basic-addon2'
    }))

class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea)
    email = forms.EmailField()
