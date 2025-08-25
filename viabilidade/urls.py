# viabilidade/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URLs da página inicial
    path('', views.pagina_inicial, name='pagina_inicial'),
    
    # URLs da página de Custos Diretos
    path('projeto/<int:projeto_id>/custos-diretos/', views.custos_diretos, name='custos_diretos'),
    path('projeto/<int:projeto_id>/custos-diretos/salvar/', views.salvar_custos_diretos, name='salvar_custos_diretos'),
    path('projeto/<int:projeto_id>/custos-diretos/adicionar/', views.adicionar_pavimento, name='adicionar_pavimento'),
    path('projeto/<int:projeto_id>/custos-diretos/salvar-etapas/', views.salvar_etapas, name='salvar_etapas'),
    
    # URLs da página de Custos Indiretos
    path('projeto/<int:projeto_id>/custos-indiretos/', views.custos_indiretos, name='custos_indiretos'),
    path('projeto/<int:projeto_id>/custos-indiretos/salvar/', views.salvar_custos_indiretos, name='salvar_custos_indiretos'),
    
    # URLs da página de Administração da Obra
    path('projeto/<int:projeto_id>/administracao/', views.administracao_obra, name='administracao_obra'),
    path('projeto/<int:projeto_id>/administracao/salvar/', views.salvar_administracao_obra, name='salvar_administracao_obra'),
    
    # URL da página de Resultados
    path('projeto/<int:projeto_id>/resultados/', views.resultados, name='resultados'),

    # URL da geração do PDF
    path('projeto/<int:projeto_id>/pdf/', views.generate_pdf_view, name='generate_pdf'),

    # URL da Análise de IA
    path('projeto/<int:projeto_id>/analise-ia/', views.gerar_analise_ia, name='gerar_analise_ia'),
    path('projeto/<int:projeto_id>/analise-ia/download/', views.download_analise_ia, name='download_analise_ia'),

    # Dados do Empreendimento (nova página)
    path('projeto/<int:projeto_id>/empreendimento/', views.empreendimento_dados, name='empreendimento_dados'),
    path('projeto/<int:projeto_id>/empreendimento/salvar/', views.salvar_empreendimento_dados, name='salvar_empreendimento_dados'),
]
