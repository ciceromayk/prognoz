from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viabilidade', '0002_projeto_analise_ia_alter_projeto_custos_config_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='projeto',
            name='etapa',
            field=models.CharField(choices=[('1', 'Viabilizar'), ('2', 'Pré-execução'), ('3', 'Obra'), ('4', 'Gestão de Custos')], default='1', max_length=2),
            preserve_default=False,
        ),
    ]
