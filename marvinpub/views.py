from marvinpub.forms import *
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect

#a ideia e fazer um login unico verificando se e marca ou operacao
def login_geral(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST['username']
            senha = request.POST['senha']
            user = authenticate(username=username, password=senha)
            if user != None:
                login(request, user)
                # if user.groups.filter(name='marca').count() != 0:
                #     marca = Marca.objects.get(user=request.user)
                #     request.session['marca_id'] = marca.id
                return HttpResponseRedirect('/dashboard/')
                # else:
                #     return HttpResponseRedirect('/operacional/dashboard/')
            else:
                return render(request, 'login.html', {'form': form, 'error': True})
        else:
            raise forms.ValidationError("Algum nome ou id incoerrente com o formulario")
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form, 'error': False})
