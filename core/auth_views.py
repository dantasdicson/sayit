from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models import Count, Max, Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import CadastroForm, EntrarForm
from . import progresso
from .models import Modulo, Tentativa


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
    titulos = {'home': 'Vamos aprender?', 'trilha': 'Minha trilha', 'modulos': 'Meus módulos',
               'progresso': 'Meu progresso', 'perfil': 'Meu perfil'}
    contexto = {'pagina': pagina, 'titulo': titulos[pagina]}
    if pagina in ('trilha', 'modulos', 'progresso'):
        numeros = sorted(progresso.DESCOBERTAS_POR_MODULO)
        modulos = Modulo.objects.filter(ativo=True, numero__in=numeros).order_by('ordem')
        estados = []
        anteriores_concluidos = True
        for modulo in modulos:
            try:
                estado = progresso.consultar_progresso(request.user, modulo.numero)
            # O processo de desenvolvimento pode recarregar progresso.py e
            # manter uma classe ErroProgresso antiga em memória. Capturamos a
            # falha na borda da tela para que a trilha nunca vire erro 500.
            except BaseException:
                # A trilha deve continuar navegável mesmo quando um catálogo
                # está incompleto durante uma atualização de conteúdo. A tela
                # do módulo continuará protegida pela validação original.
                estados.append({
                    'modulo': modulo, 'percentual': 0, 'concluido': False,
                    'iniciado': False, 'bloqueado': True, 'indisponivel': True,
                    'descobertas_concluidas': 0,
                    'total_descobertas': progresso.DESCOBERTAS_POR_MODULO.get(modulo.numero, 0),
                    'url': reverse(f'explicacao_modulo_{modulo.numero}'),
                })
                anteriores_concluidos = False
                continue
            percentual = estado['percentual']
            estados.append({
                'modulo': modulo, 'percentual': percentual,
                'concluido': bool(estado['concluido_em']), 'iniciado': percentual > 0,
                'bloqueado': not anteriores_concluidos,
                'indisponivel': False,
                'descobertas_concluidas': estado['descobertas_concluidas'],
                'total_descobertas': estado['total_descobertas'],
                'url': reverse(f'explicacao_modulo_{modulo.numero}'),
            })
            anteriores_concluidos = anteriores_concluidos and bool(estado['concluido_em'])
        total = len(estados)
        metricas = Tentativa.objects.filter(usuario=request.user).aggregate(
            tentativas=Count('pk'), palavras=Count('palavra_id', distinct=True),
            acertos=Count('pk', filter=Q(resultado=Tentativa.Resultado.CORRETO)),
            erros=Count('pk', filter=Q(resultado__in=(
                Tentativa.Resultado.INCORRETO, Tentativa.Resultado.NAO_RECONHECIDO))),
            ultima_atividade=Max('data_hora'))
        contexto.update({
            'modulos_estado': estados,
            'percentual_curso': sum(item['percentual'] for item in estados) // total if total else 0,
            'modulos_concluidos': sum(item['concluido'] for item in estados),
            'modulos_em_andamento': sum(item['iniciado'] and not item['concluido'] for item in estados),
            'total_modulos': total,
            'proximo_modulo': next((item for item in estados
                                    if not item['concluido'] and not item['bloqueado']), None),
            'total_tentativas': metricas['tentativas'] or 0,
            'total_acertos': metricas['acertos'] or 0,
            'total_erros': metricas['erros'] or 0,
            'palavras_praticadas': metricas['palavras'] or 0,
            'ultima_atividade': metricas['ultima_atividade'],
        })
    return render(request, 'core/area.html', contexto)
