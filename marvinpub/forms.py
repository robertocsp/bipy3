from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=20)
    senha = forms.CharField(max_length=20,widget=forms.PasswordInput)
