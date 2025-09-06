from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Comerciante(models.Model):
    """
    Modelo para representar um comerciante (dono do estabelecimento)
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )

    nome_salao = models.CharField(
        max_length=200,
        verbose_name="Nome do Estabelecimento",
        help_text="Nome fantasia do estabelecimento"
    )

    cnpj = models.CharField(
        max_length=18,
        unique=True,
        blank=True,
        null=True,
        verbose_name='CNPJ'
    )

    endereco = models.TextField(
        verbose_name='Endereço'
    )

    telefone_comercial = models.CharField(
        max_length=20,
        verbose_name='Telefone Comercial'
    )

    horario_funcionamento = models.TextField(
        verbose_name='Horário de Funcionamento',
        help_text='Ex: Segunda a Sexta: 8h às 18h, Sábado: 8h às 16h'
    )

    logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True,
        verbose_name='Logo do Estabelecimento'
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )

    class Meta:
        verbose_name = "Proprietário"
        verbose_name_plural = "Proprietários"
        ordering = ['nome_salao']

    def __str__(self):
        return f"{self.nome_salao} - {self.user.username}"

class Funcionario(models.Model):
    """
    Modelo para representar um funcionário do estabelecimento
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Usuário'
    )

    comerciante = models.ForeignKey(
        Comerciante,
        on_delete=models.CASCADE,
        related_name='funcionarios',
        verbose_name='Proprietário'
    )

    especialidades = models.TextField(
        verbose_name='Especialidades',
        help_text='Ex: Corte masculino, Coloração, Escova progressiva'
    )

    horario_trabalho = models.TextField(
        verbose_name='Horário de Trabalho',
        help_text='Ex: Segunda a Sexta: 9h às 17h'
    )

    comissao_percentual = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        default=Decimal('30'),
        verbose_name='Comissão (%)'
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    data_contratacao = models.DateField(
        auto_now_add=True,
        verbose_name='Data de Contratação'
    )

    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.comerciante.nome_salao}"

class Servico(models.Model):
    """
    Modelo para representar um serviço oferecido pelo estabelecimento
    """
    comerciante = models.ForeignKey(
        Comerciante,
        on_delete=models.CASCADE,
        related_name='servicos',
        verbose_name='Proprietário'
    )

    nome = models.CharField(
        max_length=200,
        verbose_name='Nome do Serviço'
    )

    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )

    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Preço'
    )

    duracao_minutos = models.PositiveIntegerField(
        verbose_name='Duração (minutos)'
    )

    funcionarios = models.ManyToManyField(
        Funcionario,
        related_name='servicos',
        verbose_name='Funcionários que realizam este serviço'
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"

class Cliente(models.Model):
    """
    Modelo para representar um cliente
    """
    nome = models.CharField(
        max_length=200,
        verbose_name='Nome Completo'
    )

    email = models.EmailField(
        verbose_name='E-mail'
    )

    telefone = models.CharField(
        max_length=20,
        verbose_name='Telefone'
    )

    data_nascimento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Data de Nascimento'
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações',
        help_text='Alergias, preferências, etc.'
    )

    comerciante = models.ForeignKey(
        Comerciante,
        on_delete=models.CASCADE,
        related_name='clientes',
        verbose_name='Proprietário'
    )

    data_cadastro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Cadastro'
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']
        unique_together = ['email', 'comerciante']

    def __str__(self):
        return f"{self.nome} - {self.email}"

class Agendamento(models.Model):
    """
    Modelo para representar um agendamento
    """
    STATUS_CHOICES = [
        ('agendado', 'Agendado'),
        ('confirmado', 'Confirmado'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
        ('nao_compareceu', 'Não Compareceu'),
    ]

    comerciante = models.ForeignKey(
        Comerciante,
        on_delete=models.CASCADE,
        related_name='agendamentos',
        verbose_name='Proprietário'
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='agendamentos',
        verbose_name='Cliente'
    )

    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='agendamentos',
        verbose_name='Funcionário'
    )

    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='agendamentos',
        verbose_name='Serviço'
    )

    data_agendamento = models.DateTimeField(
        verbose_name='Data e Hora do Agendamento'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='agendado',
        verbose_name='Status'
    )

    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações'
    )

    valor_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name='Valor Pago'
    )

    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )

    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name='Data de Atualização'
    )

    token_confirmacao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Token de Confirmação'
    )

    lembrete_enviado = models.BooleanField(
        default=False,
        verbose_name='Lembrete Enviado'
    )

    confirmado_pelo_cliente = models.BooleanField(
        default=False,
        verbose_name='Confirmado pelo Cliente'
    )

    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['-data_agendamento']

    def __str__(self):
        return f"{self.cliente.nome} - {self.servico.nome} - {self.data_agendamento.strftime('%d/%m/%Y %H:%M')}"

    def get_data_fim(self):
        """Calcula a data/hora de fim do agendamento baseado na duração do serviço"""
        from datetime import timedelta
        return self.data_agendamento + timedelta(minutes=self.servico.duracao_minutos)