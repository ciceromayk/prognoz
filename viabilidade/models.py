# viabilidade/models.py


from django.db import models
from .services import DEFAULT_CUSTOS_INDIRETOS, DEFAULT_CUSTOS_INDIRETOS_OBRA, ETAPAS_OBRA

# Funções para defaults dos JSONField
def default_custos_config():
    return {}

def default_etapas_percentuais():
    return {etapa: {"percentual": vals[1], "fonte": "Manual"} for etapa, vals in ETAPAS_OBRA.items()}

def default_custos_indiretos_percentuais():
    return {item: {"percentual": vals[1], "fonte": "Manual"} for item, vals in DEFAULT_CUSTOS_INDIRETOS.items()}

def default_custos_indiretos_fixos():
    return {}

def default_custos_indiretos_obra():
    return {k: v for k, v in DEFAULT_CUSTOS_INDIRETOS_OBRA.items()}

class Projeto(models.Model):
    nome = models.CharField(max_length=200)
    area_terreno = models.FloatField(default=0.0)
    area_privativa = models.FloatField(default=0.0)
    num_unidades = models.IntegerField(default=1)
    ETAPA_CHOICES = [
        ('1', 'Viabilizar'),
        ('2', 'Pré-execução'),
        ('3', 'Obra'),
        ('4', 'Gestão de Custos'),
    ]
    etapa = models.CharField(max_length=2, choices=ETAPA_CHOICES, default='1')
    
    # JSONField para armazenar a configuração do projeto de forma flexível
    custos_config = models.JSONField(default=default_custos_config)
    etapas_percentuais = models.JSONField(default=default_etapas_percentuais)
    custos_indiretos_percentuais = models.JSONField(default=default_custos_indiretos_percentuais)
    custos_indiretos_fixos = models.JSONField(default=default_custos_indiretos_fixos)
    custos_indiretos_obra = models.JSONField(default=default_custos_indiretos_obra)
    duracao_obra = models.IntegerField(default=12)
    
    # Novo campo para armazenar a análise da IA
    analise_ia = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"

    def __str__(self):
        return self.nome

# Vamos usar uma classe separada para os pavimentos,
# que terão uma relação com a classe Projeto
class Pavimento(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='pavimentos')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=100)
    rep = models.IntegerField(default=1)
    coef = models.FloatField(default=1.0)
    area = models.FloatField(default=0.0)
    constr = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nome} ({self.projeto.nome})"
