from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, OperationalError, connection, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import CadastroForm, EntrarForm
from .models import Modulo


class EntrarView(LoginView):
    template_name = 'core/auth/form.html'
    authentication_form = EntrarForm
    redirect_authenticated_user = True
    extra_context = {'titulo': 'Bem-vindo!', 'acao': 'Entrar'}

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class SairView(LogoutView):
    next_page = reverse_lazy('login')

    def get_success_url(self):
        return str(self.next_page)


@sensitive_post_parameters('password1', 'password2')
@never_cache
@require_http_methods(['GET', 'POST'])
def cadastro(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = CadastroForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        user = None
        try:
            # Keep the uniqueness reads and insert in one transaction. SQLite
            # rejects a concurrent read-to-write upgrade rather than inserting
            # a second account based on a stale email check.
            with transaction.atomic():
                if form.is_valid():
                    user = form.save()
        except IntegrityError:
            form.add_error(None, 'Não foi possível criar a conta. Confira o nome de usuário e o e-mail e tente novamente.')
        except OperationalError as error:
            if connection.vendor != 'sqlite' or 'locked' not in str(error).lower():
                raise
            form.add_error(None, 'Há outro cadastro em andamento. Tente novamente em alguns instantes.')
        else:
            if user is not None:
                login(request, user, backend='core.auth_backends.UsuarioOuEmailBackend')
                return redirect('home')
    return render(request, 'core/auth/form.html', {
        'form': form, 'titulo': 'Criar minha conta', 'acao': 'Criar conta', 'cadastro': True,
    })


@login_required
def area(request, pagina='home'):
    titulos = {'home': 'Vamos aprender?', 'trilha': 'Minha trilha', 'modulos': 'Módulos',
               'progresso': 'Meu progresso', 'perfil': 'Meu perfil'}
    return render(request, 'core/area.html', {
        'pagina': pagina, 'titulo': titulos[pagina],
        'modulos': Modulo.objects.filter(ativo=True) if pagina in ('trilha', 'modulos') else [],
    })
