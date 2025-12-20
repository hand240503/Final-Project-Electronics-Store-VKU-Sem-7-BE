from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Document


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price",
            "discount_price", "brand", "category"
        ]
        
class DocumentForm(forms.ModelForm):
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif'],
        'video': ['video/mp4', 'video/mpeg', 'video/quicktime'],
        'file': ['application/pdf', 'application/msword']
    }
    
    class Meta:
        model = Document
        fields = ['title', 'file', 'type']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        doc_type = self.cleaned_data.get('type')
        
        if file:
            # Check kích thước file
            if file.size > self.MAX_FILE_SIZE:
                raise ValidationError(f"File không được vượt quá {self.MAX_FILE_SIZE / 1024 / 1024}MB")
            
            # Check loại file
            if doc_type in self.ALLOWED_TYPES:
                if file.content_type not in self.ALLOWED_TYPES[doc_type]:
                    raise ValidationError(f"Loại file không được hỗ trợ cho {doc_type}")
        
        return file
        
        
