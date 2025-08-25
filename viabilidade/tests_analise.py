from django.test import TestCase, Client
from .models import Projeto
from .services import gerar_analise_local

class AnaliseLocalTests(TestCase):
    def test_gerar_analise_local_basic(self):
        data = {
            "nome_projeto": "Teste A",
            "vgv_total": 1000000,
            "custo_total": 850000,
            "lucro_bruto": 150000,
            "margem_lucro_percentual": 15.0,
            "custo_direto": 500000,
            "custo_indireto_venda": 100000,
            "custo_indireto_obra": 150000,
            "custo_terreno": 100000,
            "area_privativa": 200.0,
            "area_construida": 250.0,
        }
        texto = gerar_analise_local(data)
        self.assertIsInstance(texto, str)
        self.assertIn('1. Avaliação', texto)
        self.assertIn('5. Conclusão', texto)

class DownloadAnaliseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.projeto = Projeto.objects.create(nome='PJT', area_terreno=1000, area_privativa=200)
        self.projeto.analise_ia = 'Relatório de teste.'
        self.projeto.save()

    def test_download_analise_ia(self):
        url = f'/projeto/{self.projeto.id}/analise-ia/download/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/plain; charset=utf-8')
        self.assertIn('attachment;', resp['Content-Disposition'])
        self.assertIn('Relatório de teste.', resp.content.decode('utf-8'))
