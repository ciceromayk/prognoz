# View para salvar etapas da obra
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def salvar_etapas(request, projeto_id):
    if request.method == 'POST':
        projeto = get_object_or_404(Projeto, pk=projeto_id)
        etapas = projeto.etapas_percentuais.copy()
        for etapa in etapas:
            percentual = request.POST.get(f'percentual_{etapa}')
            if percentual is not None:
                try:
                    etapas[etapa]['percentual'] = float(percentual)
                except ValueError:
                    pass
        projeto.etapas_percentuais = etapas
        projeto.save()
        return redirect('custos_diretos', projeto_id=projeto_id)
    return HttpResponse('Método não permitido', status=405)
# viabilidade/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
import pandas as pd
from datetime import datetime
from weasyprint import HTML, CSS
import logging
from .models import Projeto, Pavimento
from .services import (
    DEFAULT_PAVIMENTO, ETAPAS_OBRA, DEFAULT_CUSTOS_INDIRETOS, DEFAULT_CUSTOS_INDIRETOS_FIXOS,
    DEFAULT_CUSTOS_INDIRETOS_OBRA,
    calcular_custos_diretos,
    calcular_custos_indiretos_porcentuais,
    calcular_custos_indiretos_obra,
    calcular_resultados_financeiros,
    fmt_br
)
# Novas importações para a API da IA
import json
import requests
from django.conf import settings

def pagina_inicial(request):
    """
    View para a página inicial, que lista e permite criar projetos.
    """
    # Calcular contadores por etapa (heurística leve baseada em campos existentes)
    projetos_all = Projeto.objects.all().order_by('id')
    stage_counts = {'1': 0, '2': 0, '3': 0, '4': 0}
    for p in projetos_all:
        etapa = str(getattr(p, 'etapa', '1'))
        if etapa in stage_counts:
            stage_counts[etapa] += 1

    selected_stage = request.GET.get('stage')

    if request.method == 'POST':
        nome = request.POST.get('nome')
        area_terreno = request.POST.get('area_terreno')
        area_privativa = request.POST.get('area_privativa')
        num_unidades = request.POST.get('num_unidades')
        # Não criar projeto se nome estiver vazio
        if not nome or nome.strip() == '':
            projetos = Projeto.objects.all().order_by('id')
            contexto = {'projetos': projetos, 'erro_nome': 'O nome do projeto é obrigatório.'}
            return render(request, 'viabilidade/index.html', contexto)

        novo_projeto = Projeto.objects.create(
            nome=nome,
            area_terreno=float(area_terreno) if area_terreno else 0,
            area_privativa=float(area_privativa) if area_privativa else 0,
            num_unidades=int(num_unidades) if num_unidades else 1,
            custos_config={'custo_terreno_m2': 2500.0, 'custo_area_privativa': 4500.0, 'preco_medio_venda_m2': 10000.0},
            etapas_percentuais={etapa: {"percentual": vals[1], "fonte": "Manual"} for etapa, vals in ETAPAS_OBRA.items()},
            custos_indiretos_percentuais={item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()},
            custos_indiretos_fixos=DEFAULT_CUSTOS_INDIRETOS_FIXOS.copy(),
            custos_indiretos_obra={k: v for k, v in DEFAULT_CUSTOS_INDIRETOS_OBRA.items()},
            duracao_obra=12
        )

        Pavimento.objects.create(
            projeto=novo_projeto,
            nome=DEFAULT_PAVIMENTO['nome'],
            tipo=DEFAULT_PAVIMENTO['tipo'],
            rep=DEFAULT_PAVIMENTO['rep'],
            coef=DEFAULT_PAVIMENTO['coef'],
            area=DEFAULT_PAVIMENTO['area'],
            constr=DEFAULT_PAVIMENTO['constr']
        )

        return redirect('pagina_inicial')

        projetos = Projeto.objects.all().order_by('id')
    else:
        projetos = projetos_all

    # Aplicar filtro por etapa se parâmetro for passado
    if selected_stage in ('1','2','3','4'):
        projetos = [p for p in projetos if str(getattr(p, 'etapa', '1')) == selected_stage]

    # Primeiro projeto por etapa (para link direto quando existir)
    first_project_by_stage = {}
    for k in ('1','2','3','4'):
        proj = Projeto.objects.filter(etapa=k).order_by('id').first()
        first_project_by_stage[k] = proj.id if proj else None

    contexto = {'projetos': projetos, 'stage_counts': stage_counts, 'selected_stage': selected_stage, 'first_project_by_stage': first_project_by_stage}
    return render(request, 'viabilidade/index.html', contexto)

def custos_diretos(request, projeto_id):
    """
    View para a página de custos diretos e pavimentos.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    pavimentos = projeto.pavimentos.all()
    resultados_calculo = calcular_custos_diretos(
        list(pavimentos),
        projeto.custos_config.get('custo_area_privativa', 4500.0)
    )

    # Corrigir etapas_percentuais se vier como lista

    # Corrigir etapas_percentuais se vier como lista ou se algum valor não for dict
    etapas_percentuais = projeto.etapas_percentuais
    from .services import ETAPAS_OBRA
    precisa_corrigir = False
    if isinstance(etapas_percentuais, list):
        precisa_corrigir = True
    else:
        for v in etapas_percentuais.values():
            if not isinstance(v, dict) or 'percentual' not in v:
                precisa_corrigir = True
                break
    if precisa_corrigir:
        etapas_percentuais = {etapa: {"percentual": vals[1], "fonte": "Manual"} for etapa, vals in ETAPAS_OBRA.items()}
        projeto.etapas_percentuais = etapas_percentuais
        projeto.save()

    from .services import TIPOS_PAVIMENTO
    import json
    tipos_pavimento = TIPOS_PAVIMENTO
    tipos_pavimento_min = {k: v[0] for k, v in tipos_pavimento.items()}
    tipos_pavimento_max = {k: v[1] for k, v in tipos_pavimento.items()}
    tipos_pavimento_json = json.dumps({k: [v[0], v[1]] for k, v in tipos_pavimento.items()})
    contexto = {
        'projeto': projeto,
        'pavimentos': pavimentos,
        'resultados': resultados_calculo,
        'tipos_pavimento': tipos_pavimento,
        'tipos_pavimento_min': tipos_pavimento_min,
        'tipos_pavimento_max': tipos_pavimento_max,
        'tipos_pavimento_json': tipos_pavimento_json,
    }
    # calcular custo por etapa da obra com base nos percentuais configurados
    etapas = projeto.etapas_percentuais or {}
    tabela_etapas = []
    custo_total = resultados_calculo.get('custo_direto_total', 0)
    for etapa, dados in etapas.items():
        percentual = 0
        if isinstance(dados, dict):
            percentual = float(dados.get('percentual', 0))
        else:
            try:
                percentual = float(dados)
            except Exception:
                percentual = 0
        custo = custo_total * (percentual / 100)
        tabela_etapas.append({'etapa': etapa, 'percentual': percentual, 'custo': custo})
    contexto['tabela_etapas'] = tabela_etapas
    return render(request, 'viabilidade/custos_diretos.html', contexto)

def salvar_custos_diretos(request, projeto_id):
    """
    View que processa o formulário de salvamento dos custos diretos.
    """
    if request.method == 'POST':
        # Debug logging: registrar os valores recebidos para diagnóstico
        import logging
        logger = logging.getLogger(__name__)
        try:
            campos = ['pavimentos', 'custo_total', 'custo_unitario', 'area_total']
            payload = {k: request.POST.get(k) for k in campos}
            logger.info('salvar_custos_diretos payload: %s', payload)
            print('salvar_custos_diretos payload:', payload)
        except Exception as _e:
            logger.exception('Erro ao logar payload de salvar_custos_diretos: %s', _e)
        projeto = get_object_or_404(Projeto, pk=projeto_id)
        for pav in projeto.pavimentos.all():
            # read raw values from POST
            nome = request.POST.get(f'nome_{pav.id}')
            tipo = request.POST.get(f'tipo_{pav.id}')
            rep_raw = request.POST.get(f'rep_{pav.id}')
            area_raw = request.POST.get(f'area_{pav.id}')
            coef_raw = request.POST.get(f'coef_{pav.id}')
            excl = request.POST.get(f'excluir_{pav.id}')

            # If excluir is checked, mark as non-constructive (doesn't count for area construída)
            if excl:
                pav.constr = False
            else:
                pav.constr = True

            # Update simple fields if provided
            if nome is not None:
                pav.nome = nome
            if tipo is not None:
                pav.tipo = tipo

            # Validate and convert numeric fields before saving
            try:
                if rep_raw is not None:
                    rep_val = int(float(rep_raw))
                    pav.rep = rep_val if rep_val >= 1 else 1
            except (ValueError, TypeError):
                # keep existing pav.rep
                pass

            try:
                if area_raw is not None:
                    area_val = float(area_raw)
                    pav.area = area_val if area_val >= 0 else pav.area
            except (ValueError, TypeError):
                pass

            try:
                if coef_raw is not None:
                    coef_val = float(coef_raw)
                    pav.coef = coef_val if coef_val > 0 else pav.coef
            except (ValueError, TypeError):
                pass

            pav.save()
    return redirect('custos_diretos', projeto_id=projeto_id)

def adicionar_pavimento(request, projeto_id):
    """
    View para adicionar um novo pavimento a um projeto.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    Pavimento.objects.create(
        projeto=projeto,
        nome=DEFAULT_PAVIMENTO['nome'],
        tipo=DEFAULT_PAVIMENTO['tipo'],
        rep=DEFAULT_PAVIMENTO['rep'],
        coef=DEFAULT_PAVIMENTO['coef'],
        area=DEFAULT_PAVIMENTO['area'],
        constr=DEFAULT_PAVIMENTO['constr']
    )
    return redirect('custos_diretos', projeto_id=projeto_id)

def custos_indiretos(request, projeto_id):
    """
    View para a página de custos indiretos.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    vgv_total = projeto.area_privativa * projeto.custos_config.get('preco_medio_venda_m2', 10000.0)
    

    custos_indiretos_percentuais = projeto.custos_indiretos_percentuais
    # Se vier como lista, converte para dict usando os próprios dados
    if isinstance(custos_indiretos_percentuais, list):
        # Tenta converter lista de pares para dict
        try:
            custos_indiretos_percentuais = {
                item if isinstance(item, str) else str(idx):
                    dados if isinstance(dados, dict) else {"percentual": dados, "fonte": "Manual"}
                for idx, (item, dados) in enumerate(custos_indiretos_percentuais)
            }
        except Exception:
            # fallback para padrão
            custos_indiretos_percentuais = {item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()}
        projeto.custos_indiretos_percentuais = custos_indiretos_percentuais
        projeto.save()
    elif not isinstance(custos_indiretos_percentuais, dict):
        # fallback para padrão
        custos_indiretos_percentuais = {item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()}
        projeto.custos_indiretos_percentuais = custos_indiretos_percentuais
        projeto.save()

    lista_custos_indiretos = []
    for item, dados in custos_indiretos_percentuais.items():
        # Garante que dados seja dict com chave 'percentual'
        if isinstance(dados, list):
            # Se for lista, tenta converter para dict
            if len(dados) == 2:
                dados = {"percentual": dados[1], "fonte": "Manual"}
            else:
                dados = {"percentual": 0, "fonte": "Manual"}
        elif not isinstance(dados, dict):
            dados = {"percentual": dados, "fonte": "Manual"}
        percentual = dados.get('percentual', 0)
        custo_calculado_item = vgv_total * (float(percentual) / 100)
        lista_custos_indiretos.append({
            'item': item,
            'percentual': percentual,
            'custo': custo_calculado_item
        })
    custo_indireto_calculado = sum(item['custo'] for item in lista_custos_indiretos)
    if vgv_total > 0:
        percentual_custo_indireto = (custo_indireto_calculado / vgv_total) * 100
    else:
        percentual_custo_indireto = 0
    contexto = {
        'projeto': projeto,
        'vgv_total': vgv_total,
        'custo_indireto_calculado': custo_indireto_calculado,
        'lista_custos_indiretos': lista_custos_indiretos,
        'percentual_custo_indireto': percentual_custo_indireto,
    }
    return render(request, 'viabilidade/custos_indiretos.html', contexto)


def empreendimento_dados(request, projeto_id):
    """Nova view para exibir/editar dados do empreendimento (projeto)."""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if request.method == 'POST':
        # redirect to salvar view for handling
        return redirect('salvar_empreendimento_dados', projeto_id=projeto_id)
    # calcular totals similares aos apresentados na página de custos diretos
    pavimentos = projeto.pavimentos.all()
    try:
        custo_area_privativa = projeto.custos_config.get('custo_area_privativa', 4500.0)
    except Exception:
        custo_area_privativa = 4500.0
    resultados = calcular_custos_diretos(list(pavimentos), custo_area_privativa)
    # custo por m2 protegido contra divisão por zero
    area_construida = resultados.get('area_construida_total', 0) or 0
    custo_direto_total = resultados.get('custo_direto_total', 0) or 0
    if area_construida > 0:
        custo_m2 = custo_direto_total / area_construida
    else:
        custo_m2 = 0

    contexto = {
        'projeto': projeto,
        'resultados': resultados,
        'custo_m2': custo_m2,
    }
    # adicionar contexto necessário para a tabela de pavimentos
    from .services import TIPOS_PAVIMENTO
    tipos_pavimento = TIPOS_PAVIMENTO
    tipos_pavimento_min = {k: v[0] for k, v in tipos_pavimento.items()}
    tipos_pavimento_max = {k: v[1] for k, v in tipos_pavimento.items()}
    import json
    tipos_pavimento_json = json.dumps({k: [v[0], v[1]] for k, v in tipos_pavimento.items()})
    contexto.update({
        'pavimentos': pavimentos,
        'tipos_pavimento': tipos_pavimento,
        'tipos_pavimento_min': tipos_pavimento_min,
        'tipos_pavimento_max': tipos_pavimento_max,
        'tipos_pavimento_json': tipos_pavimento_json,
    })
    return render(request, 'viabilidade/empreendimento_dados.html', contexto)
    


def salvar_empreendimento_dados(request, projeto_id):
    if request.method == 'POST':
        # Debug logging: registrar os valores recebidos para diagnóstico
        logger = logging.getLogger(__name__)
        try:
            payload = {k: request.POST.get(k) for k in ['nome', 'area_terreno', 'area_privativa', 'num_unidades', 'custo_terreno_m2', 'custo_area_privativa', 'preco_medio_venda_m2']}
            logger.info('salvar_empreendimento_dados payload: %s', payload)
            # Também imprimir para garantir visibilidade no console do devserver
            print('salvar_empreendimento_dados payload:', payload)
        except Exception as _e:
            logger.exception('Erro ao logar payload de salvar_empreendimento_dados: %s', _e)
        projeto = get_object_or_404(Projeto, pk=projeto_id)
        nome = request.POST.get('nome')
        area_terreno = request.POST.get('area_terreno')
        area_privativa = request.POST.get('area_privativa')
        num_unidades = request.POST.get('num_unidades')
        # custos_config fields
        custo_terreno_m2 = request.POST.get('custo_terreno_m2')
        custo_area_privativa = request.POST.get('custo_area_privativa')
        preco_medio_venda_m2 = request.POST.get('preco_medio_venda_m2')
        # helpers para parsear números com separador brasileiro
        def clean_number_str(s):
            if s is None:
                return None
            if isinstance(s, (int, float)):
                return str(s)
            s = s.strip()
            if s == '':
                return None
            # remover espaços e símbolos conflitantes
            # remove pontos de milhar e troca vírgula decimal por ponto
            s = s.replace(' ', '')
            s = s.replace('.', '')
            s = s.replace(',', '.')
            return s

        def parse_float_br(s):
            cs = clean_number_str(s)
            if cs is None:
                return None
            try:
                return float(cs)
            except (ValueError, TypeError):
                return None

        def parse_int_br(s):
            cs = clean_number_str(s)
            if cs is None:
                return None
            try:
                return int(float(cs))
            except (ValueError, TypeError):
                return None

        # apenas sobrescreve campos quando existirem valores válidos no POST
        if nome is not None and nome.strip() != '':
            projeto.nome = nome.strip()

        v = parse_float_br(area_terreno)
        if v is not None:
            projeto.area_terreno = v

        v = parse_float_br(area_privativa)
        if v is not None:
            projeto.area_privativa = v

        v = parse_int_br(num_unidades)
        if v is not None and v > 0:
            projeto.num_unidades = v

        custos = projeto.custos_config or {}
        v = parse_float_br(custo_terreno_m2)
        if v is not None:
            custos['custo_terreno_m2'] = v

        v = parse_float_br(custo_area_privativa)
        if v is not None:
            custos['custo_area_privativa'] = v

        v = parse_float_br(preco_medio_venda_m2)
        if v is not None:
            custos['preco_medio_venda_m2'] = v

        projeto.custos_config = custos
        projeto.save()
    return redirect('empreendimento_dados', projeto_id=projeto_id)

def salvar_custos_indiretos(request, projeto_id):
    """
    View que processa o formulário de salvamento dos custos indiretos.
    """
    if request.method == 'POST':
        projeto = get_object_or_404(Projeto, pk=projeto_id)
        novos_custos = {}
        for item, percentual in request.POST.items():
            if item.startswith('percentual_'):
                item_nome = item.split('percentual_')[1]
                try:
                    percentual_val = float(percentual)
                    novos_custos[item_nome] = {
                        'percentual': percentual_val,
                        'fonte': 'Manual'
                    }
                except (ValueError, TypeError):
                    pass
        projeto.custos_indiretos_percentuais = novos_custos
        projeto.save()
    return redirect('custos_indiretos', projeto_id=projeto_id)

def administracao_obra(request, projeto_id):
    """
    View para a página de administração da obra (custos mensais e duração).
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.custos_indiretos_obra:
        projeto.custos_indiretos_obra = {k: v for k, v in DEFAULT_CUSTOS_INDIRETOS_OBRA.items()}
        projeto.save()
    custos_mensais = projeto.custos_indiretos_obra
    duracao_obra = projeto.duracao_obra
    resultados_custos_obra_dict = calcular_custos_indiretos_obra(custos_mensais, duracao_obra)
    contexto = {
        'projeto': projeto,
        'custos_mensais': custos_mensais,
        'duracao_obra': duracao_obra,
        'resultados': resultados_custos_obra_dict,
    }
    return render(request, 'viabilidade/administracao.html', contexto)

def salvar_administracao_obra(request, projeto_id):
    """
    View que processa o formulário de salvamento da administração da obra.
    """
    if request.method == 'POST':
        projeto = get_object_or_404(Projeto, pk=projeto_id)
        duracao_obra = request.POST.get('duracao_obra')
        if duracao_obra:
            projeto.duracao_obra = int(duracao_obra)
        novos_custos = {}
        for item in DEFAULT_CUSTOS_INDIRETOS_OBRA.keys():
            valor = request.POST.get(f'custo_mensal_{item}')
            try:
                novos_custos[item] = float(valor)
            except (ValueError, TypeError):
                novos_custos[item] = projeto.custos_indiretos_obra.get(item, 0.0)
        projeto.custos_indiretos_obra = novos_custos
        projeto.save()
    return redirect('administracao_obra', projeto_id=projeto_id)

def resultados(request, projeto_id):
    """
    View para a página de resultados e indicadores.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    pavimentos = projeto.pavimentos.all()
    custos_config = projeto.custos_config
    resultados_diretos = calcular_custos_diretos(
        list(pavimentos),
        custos_config.get('custo_area_privativa', 4500.0)
    )
    vgv = projeto.area_privativa * custos_config.get('preco_medio_venda_m2', 10000.0)
    
    custos_indiretos_percentuais = projeto.custos_indiretos_percentuais
    if isinstance(custos_indiretos_percentuais, list):
        custos_indiretos_percentuais = {item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()}

    custo_indireto_venda = calcular_custos_indiretos_porcentuais(vgv, custos_indiretos_percentuais)
    resultados_custos_obra_dict = calcular_custos_indiretos_obra(projeto.custos_indiretos_obra, projeto.duracao_obra)
    custo_indireto_obra = resultados_custos_obra_dict
    
    resultados_financeiros = calcular_resultados_financeiros(
        projeto,
        resultados_diretos['custo_direto_total']
    )
    
    # Calcular as porcentagens para a composição do custo total
    custo_total_despesas = resultados_financeiros['custo_total_despesas']
    if custo_total_despesas > 0:
        p_direto = (resultados_diretos['custo_direto_total'] / custo_total_despesas) * 100
        p_indireto_venda = (custo_indireto_venda / custo_total_despesas) * 100
        p_indireto_obra = (custo_indireto_obra / custo_total_despesas) * 100
        p_terreno = (resultados_financeiros['custo_terreno'] / custo_total_despesas) * 100
    else:
        p_direto, p_indireto_venda, p_indireto_obra, p_terreno = 0, 0, 0, 0

    contexto = {
        'projeto': projeto,
        'vgv_total': vgv,
        'custo_total_despesas': custo_total_despesas,
        'lucratividade_valor': resultados_financeiros['lucro_bruto'],
        'lucratividade_percentual': resultados_financeiros['margem_lucro'],
        'custo_direto_total': resultados_diretos['custo_direto_total'],
        'custo_terreno_total': resultados_financeiros['custo_terreno'],
        'custo_indireto_venda': custo_indireto_venda,
        'custo_indireto_obra': custo_indireto_obra,
        'area_construida_total': resultados_diretos['area_construida_total'],
        'p_direto': p_direto,
        'p_indireto_venda': p_indireto_venda,
        'p_indireto_obra': p_indireto_obra,
        'p_terreno': p_terreno,
        'analise_ia': projeto.analise_ia, # Adicionamos o campo da IA aqui
    }
    return render(request, 'viabilidade/resultados.html', contexto)

def gerar_analise_ia(request, projeto_id):
    """
    View que faz a chamada para a API da IA, gera a análise e salva no projeto.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Realiza os mesmos cálculos da view 'resultados' para ter os dados
    pavimentos = projeto.pavimentos.all()
    custos_config = projeto.custos_config
    resultados_diretos = calcular_custos_diretos(
        list(pavimentos),
        custos_config.get('custo_area_privativa', 4500.0)
    )
    vgv = projeto.area_privativa * custos_config.get('preco_medio_venda_m2', 10000.0)
    custo_indireto_venda = calcular_custos_indiretos_porcentuais(vgv, projeto.custos_indiretos_percentuais)
    resultados_custos_obra_dict = calcular_custos_indiretos_obra(projeto.custos_indiretos_obra, projeto.duracao_obra)
    custo_indireto_obra = resultados_custos_obra_dict
    resultados_financeiros = calcular_resultados_financeiros(
        projeto,
        resultados_diretos['custo_direto_total']
    )
    
    # Prepara o prompt com os dados
    prompt_data = {
        "nome_projeto": projeto.nome,
        "vgv_total": vgv,
        "custo_total": resultados_financeiros['custo_total_despesas'],
        "lucro_bruto": resultados_financeiros['lucro_bruto'],
        "margem_lucro_percentual": resultados_financeiros['margem_lucro'],
        "custo_direto": resultados_diretos['custo_direto_total'],
        "custo_indireto_venda": custo_indireto_venda,
        "custo_indireto_obra": custo_indireto_obra,
        "custo_terreno": resultados_financeiros['custo_terreno'],
        "area_privativa": projeto.area_privativa,
        "area_terreno": projeto.area_terreno,
        "area_construida": resultados_diretos['area_construida_total'],
        "composicao_custos": {} # Adicione a composição de custos aqui se necessário
    }
    
    prompt = f"""
    Atue como um analista sênior de viabilidade de empreendimentos imobiliários. Sua tarefa é analisar os dados de um projeto e gerar um relatório detalhado e analítico em português.

    O relatório deve ter as seguintes seções, formatadas com títulos numerados e simples seguidos pelo conteúdo:
    
    1. Avaliação da Viabilidade Financeira
    Comece com um parágrafo que resume a saúde financeira do projeto. Compare a Margem de Lucro Bruta com o benchmark de mercado (uma margem acima de 15% é considerada promissora). Explique as implicações do Lucro Bruto do projeto e sua atratividade geral.
    
    2. Análise Detalhada dos Custos
    Analise a composição do Custo Total. Apresente os valores absolutos e as porcentagens de cada tipo de custo (Custo Direto, Custo Indireto de Venda, Custo Indireto de Obra e Custo do Terreno).

    3. Análise de Desempenho por Área
    Forneça e interprete os indicadores de custo por metro quadrado (m²) para Custo Direto, Custo Indireto e Custo Total.
    
    4. Recomendações Estratégicas
    Forneça uma lista de 3 a 5 recomendações estratégicas acionáveis para melhorar a viabilidade do projeto. As recomendações devem ser específicas. Por exemplo, cite exemplos de onde a redução de custos pode ocorrer ou como a receita pode ser aumentada.

    5. Conclusão e Próximos Passos
    Um parágrafo final que resume a análise e oferece uma perspectiva sobre os próximos passos, como a realização de estudos de mercado mais aprofundados.

    Abaixo estão os dados do projeto. Use-os para a análise. Os valores estão em Reais (R$).
    
    Dados do Projeto:
    - Nome: {prompt_data['nome_projeto']}
    - VGV Total: R$ {fmt_br(prompt_data['vgv_total'])}
    - Custo Total: R$ {fmt_br(prompt_data['custo_total'])}
    - Lucro Bruto: R$ {fmt_br(prompt_data['lucro_bruto'])}
    - Margem de Lucro: {prompt_data['margem_lucro_percentual']:.2f}%
    - Custo Direto: R$ {fmt_br(prompt_data['custo_direto'])}
    - Custo Indireto de Venda: R$ {fmt_br(prompt_data['custo_indireto_venda'])}
    - Custo Indireto de Obra: R$ {fmt_br(prompt_data['custo_indireto_obra'])}
    - Custo do Terreno: R$ {fmt_br(prompt_data['custo_terreno'])}
    - Área Privativa: {prompt_data['area_privativa']:.2f} m²
    - Área Construída: {prompt_data['area_construida']:.2f} m²
    """
    
    # Lógica de chamada da API
    # Se a chave da API não estiver configurada, usar gerador local (offline) para evitar custos
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    use_local = not api_key or api_key.strip() == '' or 'SUA_CHAVE' in str(api_key)

    from .services import gerar_analise_local

    if use_local:
        prompt_data = {
            "nome_projeto": projeto.nome,
            "vgv_total": vgv,
            "custo_total": resultados_financeiros['custo_total_despesas'],
            "lucro_bruto": resultados_financeiros['lucro_bruto'],
            "margem_lucro_percentual": resultados_financeiros['margem_lucro'],
            "custo_direto": resultados_diretos['custo_direto_total'],
            "custo_indireto_venda": custo_indireto_venda,
            "custo_indireto_obra": custo_indireto_obra,
            "custo_terreno": resultados_financeiros['custo_terreno'],
            "area_privativa": projeto.area_privativa,
            "area_construida": resultados_diretos['area_construida_total']
        }
        analysis = gerar_analise_local(prompt_data)
        projeto.analise_ia = analysis
        projeto.save()
        # Se for requisição AJAX, retornar JSON com a análise
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'analise': analysis})
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
                "responseMimeType": "text/plain"
            }
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            if result and 'candidates' in result and len(result['candidates']) > 0:
                analysis = result['candidates'][0]['content']['parts'][0]['text']
                projeto.analise_ia = analysis
                projeto.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                from django.http import JsonResponse
                return JsonResponse({'analise': analysis})
        except requests.exceptions.RequestException as e:
            print(f"Erro ao chamar a API da IA: {e}")
    
    return redirect('resultados', projeto_id=projeto.id)

def generate_pdf_view(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    pavimentos = projeto.pavimentos.all()
    custos_config = projeto.custos_config
    resultados_diretos = calcular_custos_diretos(
        list(pavimentos),
        custos_config.get('custo_area_privativa', 4500.0)
    )
    vgv_total = projeto.area_privativa * custos_config.get('preco_medio_venda_m2', 10000.0)
    
    custos_indiretos_percentuais = projeto.custos_indiretos_percentuais
    if isinstance(custos_indiretos_percentuais, list):
        custos_indiretos_percentuais = {item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()}

    custo_indireto_venda = calcular_custos_indiretos_porcentuais(vgv_total, custos_indiretos_percentuais)
    resultados_custos_obra_dict = calcular_custos_indiretos_obra(projeto.custos_indiretos_obra, projeto.duracao_obra)
    custo_indireto_obra_total = resultados_custos_obra_dict
    custo_terreno_total = projeto.area_terreno * custos_config.get('custo_terreno_m2', 2500.0)
    valor_total_despesas = resultados_diretos['custo_direto_total'] + custo_indireto_venda + custo_terreno_total + custo_indireto_obra_total
    lucratividade_valor = vgv_total - valor_total_despesas
    lucratividade_percentual = (lucratividade_valor / vgv_total) * 100 if vgv_total > 0 else 0
    
    # Criar DataFrame para as tabelas do PDF
    pavimentos_df = pd.DataFrame(list(pavimentos.values()))
    
    contexto = {
        'projeto': projeto,
        'vgv_total': vgv_total,
        'valor_total_despesas': valor_total_despesas,
        'lucratividade_valor': lucratividade_valor,
        'lucratividade_percentual': lucratividade_percentual,
        'custo_direto_total': resultados_diretos['custo_direto_total'],
        'custo_indireto_calculado': custo_indireto_venda,
        'custo_terreno_total': custo_terreno_total,
        'area_construida_total': resultados_diretos['area_construida_total'],
        'custos_config': custos_config,
        'custos_indiretos_percentuais': custos_indiretos_percentuais,
        'pavimentos_df': pavimentos_df,
        'custo_indireto_obra_total': custo_indireto_obra_total,
        'data_geracao': datetime.now(),
        'ETAPAS_OBRA': ETAPAS_OBRA,
    }
    
    html_string = render_to_string('viabilidade/pdf_report.html', contexto)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{projeto.nome}.pdf"'
    HTML(string=html_string).write_pdf(response, stylesheets=[CSS(string='''
        @page { size: A4; margin: 1.5cm; }
        body { font-family: sans-serif; }
        h2 { color: #1a5276; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; font-size: 10px; }
        th { background-color: #f2f2f2; }
    ''')])
    
    return response


def download_analise_ia(request, projeto_id):
    """Retorna a análise de IA (salva em `projeto.analise_ia`) como um arquivo .txt para download."""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    conteudo = projeto.analise_ia or "Nenhuma análise disponível para este projeto."
    response = HttpResponse(conteudo, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="analise_ia_{projeto.id}.txt"'
    return response

