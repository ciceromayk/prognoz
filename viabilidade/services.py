# viabilidade/services.py

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

# --- 1. FUNÇÕES AUXILIARES ---
def fmt_br(valor):
    """
    Formata um valor numérico para a moeda brasileira (R$) de forma independente do locale.
    """
    if pd.isna(valor) or valor is None:
        return "0,00"
    s = f"{valor:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# --- 2. CONSTANTES E DADOS PADRÃO ---

TIPOS_PAVIMENTO = {
    "Área Privativa (Autônoma)": (1.00, 1.00), "Áreas de lazer ambientadas": (2.00, 4.00), "Varandas": (0.75, 1.00),
    "Terraços / Áreas Descobertas": (0.30, 0.60), "Garagem (Subsolo)": (0.50, 0.75), "Estacionamento (terreno)": (0.05, 0.10),
    "Salas com Acabamento": (1.00, 1.00), "Salas sem Acabamento": (0.75, 0.90), "Loja sem Acabamento": (0.40, 0.60),
    "Serviço (unifam. baixa, aberta)": (0.50, 0.50), "Barrilete / Cx D'água / Casa Máquinas": (0.50, 0.75),
    "Piscinas": (0.50, 0.75), "Quintais / Calçadas / Jardins": (0.10, 0.30), "Projeção Terreno sem Benfeitoria": (0.00, 0.00),
}
DEFAULT_PAVIMENTO = {"nome": "Pavimento Tipo", "tipo": "Área Privativa (Autônoma)", "rep": 1, "coef": 1.00, "area": 100.0, "constr": True}

ETAPAS_OBRA = {
    "Serviços Preliminares e Fundações":        (7.0, 8.0, 9.0),
    "Estrutura (Supraestrutura)":               (14.0, 16.0, 22.0),
    "Vedações (Alvenaria)":                     (8.0, 10.0, 15.0),
    "Cobertura e Impermeabilização":            (4.0, 5.0, 8.0),
    "Revestimentos de Fachada":                 (5.0, 6.0, 10.0),
    "Instalações (Elétrica e Hidráulica)":      (12.0, 15.0, 18.0),
    "Esquadrias (Portas e Janelas)":            (6.0, 8.0, 12.0),
    "Revestimentos de Piso":                    (8.0, 10.0, 15.0),
    "Revestimentos de Parede":                  (6.0, 8.0, 12.0),
    "Revestimentos de Forro":                   (3.0, 4.0, 6.0),
    "Pintura":                                  (4.0, 5.0, 8.0),
    "Serviços Complementares e Externos":       (3.0, 5.0, 10.0)
}

DEFAULT_CUSTOS_INDIRETOS = {
    "IRPJ/ CS/ PIS/ COFINS":        (3.0, 4.0, 6.0),
    "Corretagem":                   (3.0, 3.61, 5.0),
    "Publicidade":                  (0.5, 0.9, 2.0),
    "Manutenção":                   (0.3, 0.5, 1.0),
    "Custo Fixo da Incorporadora": (3.0, 4.0, 6.0),
    "Assessoria Técnica":           (0.5, 0.7, 1.5),
    "Projetos":                     (0.4, 0.52, 1.5),
    "Licenças e Incorporação":      (0.1, 0.2, 0.5),
    "Outorga Onerosa":              (0.0, 0.0, 10.0),
    "Condomínio":                   (0.0, 0.0, 0.5),
    "IPTU":                         (0.05, 0.07, 0.2),
    "Preparação do Terreno":        (0.2, 0.33, 1.0),
    "Financiamento Bancário":       (1.0, 1.9, 3.0),
}

DEFAULT_CUSTOS_INDIRETOS_FIXOS = {}
DEFAULT_CUSTOS_INDIRETOS_OBRA = {
    "Administração de Obra (Engenheiro/Arquiteto)": 15000.0,
    "Mestre de Obras e Encarregados": 8000.0,
    "Aluguel de Equipamentos (andaimes, betoneira, etc.)": 5000.0,
    "Consumo de Energia": 1000.0,
    "Consumo de Água": 500.0,
    "Telefone e Internet": 300.0,
    "Seguros e Licenças de Canteiro": 1200.0,
    "Transporte de Materiais e Pessoas": 2500.0,
    "Despesas de Escritório e Apoio": 800.0,
}


# --- FUNÇÃO DE CÁLCULO DE ÁREAS DE PAVIMENTOS ---
def calcular_areas_pavimentos(pavimentos, tipos_pavimento=TIPOS_PAVIMENTO):
    """
    Calcula área equivalente e área construída a partir de uma lista de pavimentos.
    Cada pavimento deve ser um dicionário com: 'tipo', 'area', 'coef', 'constr', etc.
    tipos_pavimento: dicionário com os coeficientes por tipo.
    Retorna: lista de pavimentos com área equivalente e área construída, totais.
    """
    total_area = 0
    total_area_eq = 0
    total_area_constr = 0
    pavimentos_result = []
    for pav in pavimentos:
        coef = pav.get('coef')
        if coef is None:
            coef = tipos_pavimento.get(pav['tipo'], (1.0, 1.0))[0]
        area = pav.get('area', 0)
        rep = pav.get('rep', 1)
        area_total = area * rep
        area_eq = area_total * coef
        pav['area_eq'] = area_eq
        pav['area_constr'] = area_total if pav.get('constr', True) else 0
        pavimentos_result.append(pav)
        total_area += area_total
        total_area_eq += area_eq
        if pav.get('constr', True):
            total_area_constr += area_total
    totais = {
        'total_area': total_area,
        'total_area_eq': total_area_eq,
        'total_area_constr': total_area_constr
    }
    return pavimentos_result, totais


# --- 3. FUNÇÕES DE CÁLCULO E ANÁLISE ---

def calcular_custos_diretos(pavimentos, custo_area_privativa):
    """
    Calcula os custos diretos e as áreas totais a partir dos pavimentos.
    Recebe uma lista de objetos 'Pavimento' e o custo por m².
    """
    
    # Criar um DataFrame a partir da lista de objetos Pavimento
    pavimentos_data = []
    for pav in pavimentos:
        pavimentos_data.append({
            "nome": pav.nome,
            "tipo": pav.tipo,
            "rep": pav.rep,
            "coef": pav.coef,
            "area": pav.area,
            "constr": pav.constr,
        })
    
    if not pavimentos_data:
        return {
            "custo_direto_total": 0,
            "area_construida_total": 0,
            "pavimentos_df": pd.DataFrame()
        }
    
    df = pd.DataFrame(pavimentos_data)
    
    df["area_total"] = df["area"] * df["rep"]
    df["area_eq"] = df["area_total"] * df["coef"]
    df["area_constr"] = df.apply(lambda r: r["area_total"] if r["constr"] else 0.0, axis=1)
    df["custo_direto"] = df["area_eq"] * custo_area_privativa

    custo_direto_total = df["custo_direto"].sum()
    # Corrigir: área construída total deve ser a soma de area*rep de todos os pavimentos construtivos
    area_construida_total = df.apply(lambda r: r["area"] * r["rep"] if r["constr"] else 0.0, axis=1).sum()

    # Corrigir: área equivalente total deve ser a soma de area*rep*coeficiente de todos os pavimentos
    area_equivalente_total = df.apply(lambda r: r["area"] * r["rep"] * r["coef"], axis=1).sum()

    # Corrigir: área privativa total deve ser a soma de area*rep dos pavimentos privativos
    area_privativa_total = df.apply(lambda r: r["area"] * r["rep"] if r["tipo"] == "Área Privativa (Autônoma)" else 0.0, axis=1).sum()

    return {
        "custo_direto_total": custo_direto_total,
        "area_construida_total": area_construida_total,
        "area_privativa_total": area_privativa_total,
        "area_equivalente_total": area_equivalente_total,
        "pavimentos_df": df
    }

def calcular_custos_indiretos_porcentuais(vgv, custos_indiretos_percentuais):
    """
    Calcula os custos indiretos com base no VGV.
    """
    custo_indireto_calculado = 0
    # Corrige se vier como lista vazia ou lista
    if isinstance(custos_indiretos_percentuais, list):
        custos_indiretos_percentuais = {}
    if custos_indiretos_percentuais:
        for item, values in custos_indiretos_percentuais.items():
            if isinstance(values, dict):
                percentual = values.get('percentual', 0)
                custo_indireto_calculado += vgv * (float(percentual) / 100)
            else:
                # Se values não for dict, ignora ou trata como zero
                continue
    return custo_indireto_calculado

def calcular_custos_indiretos_obra(custos_indiretos_obra, duracao_obra):
    """
    Calcula o custo indireto total da obra.
    """
    total_mensal = sum(custos_indiretos_obra.values())
    return total_mensal * duracao_obra

def calcular_resultados_financeiros(projeto, custos_diretos):
    """
    Calcula todos os indicadores financeiros do projeto.
    """
    vgv_total = projeto.area_privativa * projeto.custos_config.get('preco_medio_venda_m2', 0)
    custo_terreno_total = projeto.area_terreno * projeto.custos_config.get('custo_terreno_m2', 0)
    
    custo_indireto_calculado = calcular_custos_indiretos_porcentuais(vgv_total, projeto.custos_indiretos_percentuais)
    custo_indireto_obra_total = calcular_custos_indiretos_obra(projeto.custos_indiretos_obra, projeto.duracao_obra)
    
    valor_total_despesas = custos_diretos + custo_indireto_calculado + custo_terreno_total + custo_indireto_obra_total
    lucratividade_valor = vgv_total - valor_total_despesas
    lucratividade_percentual = (lucratividade_valor / vgv_total) * 100 if vgv_total > 0 else 0
    
    return {
        "vgv_total": vgv_total,
        "custo_total_despesas": valor_total_despesas,
        "lucro_bruto": lucratividade_valor,
        "margem_lucro": lucratividade_percentual,
        "custo_terreno": custo_terreno_total,
        "custo_indireto_venda": custo_indireto_calculado,
        "custo_indireto_obra": custo_indireto_obra_total
    }


def gerar_analise_local(prompt_data: dict) -> str:
    """
    Gera uma análise textual local (offline) baseada nos dados do projeto.
    Estrutura o relatório nas seções pedidas pelo sistema: 1..5.
    Usa `fmt_br` para formatar valores. Retorna uma string pronta para salvar.
    """
    # Extrai valores com fallback
    nome = prompt_data.get('nome_projeto', 'Projeto')
    vgv = prompt_data.get('vgv_total', 0) or 0
    custo_total = prompt_data.get('custo_total', 0) or 0
    lucro = prompt_data.get('lucro_bruto', 0) or 0
    margem = prompt_data.get('margem_lucro_percentual', 0) or 0
    custo_direto = prompt_data.get('custo_direto', 0) or 0
    custo_ind_venda = prompt_data.get('custo_indireto_venda', 0) or 0
    custo_ind_obra = prompt_data.get('custo_indireto_obra', 0) or 0
    custo_terreno = prompt_data.get('custo_terreno', 0) or 0
    area_priv = prompt_data.get('area_privativa', 0) or 0
    area_constr = prompt_data.get('area_construida', 0) or 0

    # Composição de custos
    soma = custo_direto + custo_ind_venda + custo_ind_obra + custo_terreno
    if soma <= 0:
        soma = custo_total or 1

    p_direto = (custo_direto / soma) * 100
    p_ind_venda = (custo_ind_venda / soma) * 100
    p_ind_obra = (custo_ind_obra / soma) * 100
    p_terreno = (custo_terreno / soma) * 100

    # Seções do relatório
    lines = []
    # 1. Avaliação
    lines.append("1. Avaliação da Viabilidade Financeira")
    health = "promissora" if margem >= 15 else ("marginal" if margem >= 5 else "preocupante")
    lines.append(f"Resumo: O projeto '{nome}' apresenta margem bruta de {margem:.2f}% ({fmt_br(lucro)}), considerada {health}.")
    if margem < 15:
        lines.append("Interpretação: a margem está abaixo do benchmark de mercado (15%), será necessário ajuste para tornar o projeto atrativo a investidores.")
    else:
        lines.append("Interpretação: margem acima de 15% — boa atratividade; ainda assim é recomendável validar riscos e sensibilidade a preços.")

    # 2. Análise de custos
    lines.append("")
    lines.append("2. Análise Detalhada dos Custos")
    lines.append(f"Custo Direto: R$ {fmt_br(custo_direto)} ({p_direto:.1f}%)")
    lines.append(f"Custo Indireto de Venda: R$ {fmt_br(custo_ind_venda)} ({p_ind_venda:.1f}%)")
    lines.append(f"Custo Indireto de Obra: R$ {fmt_br(custo_ind_obra)} ({p_ind_obra:.1f}%)")
    lines.append(f"Custo do Terreno: R$ {fmt_br(custo_terreno)} ({p_terreno:.1f}%)")

    # 3. Performance por área
    lines.append("")
    lines.append("3. Análise de Desempenho por Área")
    if area_priv > 0:
        custo_total_m2 = custo_total / area_priv
        custo_direto_m2 = custo_direto / area_priv
        custo_ind_m2 = (custo_ind_venda + custo_ind_obra + custo_terreno) / area_priv
        lines.append(f"Custo Direto por m²: R$ {fmt_br(custo_direto_m2)}")
        lines.append(f"Custo Indireto por m²: R$ {fmt_br(custo_ind_m2)}")
        lines.append(f"Custo Total por m²: R$ {fmt_br(custo_total_m2)}")
    else:
        lines.append("Não foi possível calcular indicadores por m² (área privativa zero).")

    # 4. Recomendações estratégicas (3-5 itens)
    lines.append("")
    lines.append("4. Recomendações Estratégicas")
    recs = []
    # Prioridade: aumentar margem ou reduzir custos
    if margem < 15:
        recs.append("Rever o preço médio de venda e segmentação de produto para capturar melhor valor por m².")
    recs.append("Negociar preço de insumos e custo por m² com fornecedores; avaliar alternativas de acabamento para reduzir custo direto.")
    if p_terreno > 25:
        recs.append("Avaliar renegociação do terreno ou ajustar a tipologia/unidades para diluir o custo do terreno por unidade.")
    if p_ind_obra > 10:
        recs.append("Reduzir duração da obra (replanejamento/cronograma) para diminuir custos indiretos de obra.")
    recs.append("Revisar corretagem/publicidade e plano comercial para reduzir comissões ou aumentar taxa de absorção.")
    # Limit 5
    for r in recs[:5]:
        lines.append(f"- {r}")

    # 5. Conclusão e próximos passos
    lines.append("")
    lines.append("5. Conclusão e Próximos Passos")
    lines.append("Conclusão: o projeto precisa de ajustes (preço, custos ou escopo) se a margem estiver abaixo do benchmark; caso contrário, seguir para due diligence de mercado.")
    lines.append("Próximos passos: 1) análise de sensibilidade de preço e custo; 2) negociação de insumos e terreno; 3) validação comercial (pesquisa de mercado).")

    return "\n".join(lines)