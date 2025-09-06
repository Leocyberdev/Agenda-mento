
# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamento', '0002_alter_comerciante_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamento',
            name='token_confirmacao',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Token de Confirmação'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='lembrete_enviado',
            field=models.BooleanField(default=False, verbose_name='Lembrete Enviado'),
        ),
        migrations.AddField(
            model_name='agendamento',
            name='confirmado_pelo_cliente',
            field=models.BooleanField(default=False, verbose_name='Confirmado pelo Cliente'),
        ),
    ]
