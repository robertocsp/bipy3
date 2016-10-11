from django import forms


class UploadCardapioForm(forms.Form):
    cardapio = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
