from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(max_length=200)
    senha = forms.CharField(max_length=30, widget=forms.PasswordInput)
