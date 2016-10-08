from django import forms


class UploadCardapioForm(forms.Form):
    cardapios = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))
