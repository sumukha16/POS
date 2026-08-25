from django import forms

from .models import Category, MenuItem


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = [
            "name",
            "category_type",
            "display_order",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Category name",
                }
            ),

            "category_type": forms.Select(),

            "display_order": forms.NumberInput(
                attrs={
                    "min": 0,
                }
            ),

            "is_active": forms.CheckboxInput(),
        }


class MenuItemForm(forms.ModelForm):

    class Meta:
        model = MenuItem
        fields = [
            "category",
            "name",
            "price",
            "code",
            "is_active",
        ]

        widgets = {
            "category": forms.Select(),

            "name": forms.TextInput(
                attrs={
                    "placeholder": "Item name",
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "min": 0,
                    "step": 1,
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "placeholder": "Item code",
                }
            ),

            "is_active": forms.CheckboxInput(),
        }