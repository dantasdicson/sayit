"""
URL configuration for sayit project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from core.auth_views import EntrarView, SairView, area, cadastro
from core import progresso_views
from core.views import (
    conclusao_modulo_1, descoberta_modulo_1, explicacao_modulo_1, pratica_modulo_1,
    resumo_modulo, explicacao_modulo_2, conclusao_modulo_2,
)

urlpatterns = [
    path('', area, name='home'),
    path('cadastro/', cadastro, name='cadastro'),
    path('login/', EntrarView.as_view(), name='login'),
    path('logout/', SairView.as_view(), name='logout'),
    path('trilha/', area, {'pagina': 'trilha'}, name='trilha'),
    path('modulos/', area, {'pagina': 'modulos'}, name='modulos'),
    path('progresso/', area, {'pagina': 'progresso'}, name='progresso'),
    path('perfil/', area, {'pagina': 'perfil'}, name='perfil'),
    path('modulos/<int:numero>/progresso/acertos/', progresso_views.registrar_acerto, name='registrar_acerto'),
    path('modulos/<int:numero>/progresso/erros/', progresso_views.registrar_erro, name='registrar_erro'),
    path('modulos/<int:numero>/progresso/concluir/', progresso_views.concluir_modulo, name='concluir_modulo'),
    path('modulos/1/pratica/', pratica_modulo_1, name='pratica_modulo_1'),
    path('modulos/1/explicacao/', explicacao_modulo_1, name='explicacao_modulo_1'),
    path('modulos/1/descoberta/<int:numero>/', descoberta_modulo_1, name='descoberta_modulo_1'),
    path('modulos/1/conclusao/', conclusao_modulo_1, name='conclusao_modulo_1'),
    path('modulos/1/resumo/', resumo_modulo, {'numero': 1}, name='resumo_modulo_1'),
    path('modulos/2/explicacao/', explicacao_modulo_2, name='explicacao_modulo_2'),
    path('modulos/<int:modulo_numero>/descobertas/<int:numero>/', descoberta_modulo_1, name='descoberta_modulo'),
    path('modulos/2/resumo/', resumo_modulo, {'numero': 2}, name='resumo_modulo_2'),
    path('modulos/2/conclusao/', conclusao_modulo_2, name='conclusao_modulo_2'),
    path('modulos/3/explicacao/', explicacao_modulo_2, {'numero': 3}, name='explicacao_modulo_3'),
    path('modulos/3/resumo/', resumo_modulo, {'numero': 3}, name='resumo_modulo_3'),
    path('modulos/3/conclusao/', conclusao_modulo_2, {'numero': 3}, name='conclusao_modulo_3'),
    path('modulos/4/explicacao/', explicacao_modulo_2, {'numero': 4}, name='explicacao_modulo_4'),
    path('modulos/4/resumo/', resumo_modulo, {'numero': 4}, name='resumo_modulo_4'),
    path('modulos/4/conclusao/', conclusao_modulo_2, {'numero': 4}, name='conclusao_modulo_4'),
    path('admin/', admin.site.urls),
    path('modulos/5/explicacao/', explicacao_modulo_2, {'numero': 5}, name='explicacao_modulo_5'),
    path('modulos/5/resumo/', resumo_modulo, {'numero': 5}, name='resumo_modulo_5'),
    path('modulos/5/conclusao/', conclusao_modulo_2, {'numero': 5}, name='conclusao_modulo_5'),
    path('modulos/6/explicacao/', explicacao_modulo_2, {'numero': 6}, name='explicacao_modulo_6'),
    path('modulos/6/resumo/', resumo_modulo, {'numero': 6}, name='resumo_modulo_6'),
    path('modulos/6/conclusao/', conclusao_modulo_2, {'numero': 6}, name='conclusao_modulo_6'),
    path('modulos/7/explicacao/', explicacao_modulo_2, {'numero': 7}, name='explicacao_modulo_7'),
    path('modulos/7/resumo/', resumo_modulo, {'numero': 7}, name='resumo_modulo_7'),
    path('modulos/7/conclusao/', conclusao_modulo_2, {'numero': 7}, name='conclusao_modulo_7'),
    path('modulos/8/explicacao/', explicacao_modulo_2, {'numero': 8}, name='explicacao_modulo_8'),
    path('modulos/8/resumo/', resumo_modulo, {'numero': 8}, name='resumo_modulo_8'),
    path('modulos/8/conclusao/', conclusao_modulo_2, {'numero': 8}, name='conclusao_modulo_8'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
