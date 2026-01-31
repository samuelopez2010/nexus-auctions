from django import forms
from .models import Product, ProductImage

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'title', 'description', 'condition', 'location', 
                  'sales_type', 'initial_price', 'buy_now_price', 'reserve_price', 'auction_end_time']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'auction_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control bg-dark text-white border-secondary'})
