from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Modelo de usuário customizado que estende o AbstractUser do Django
    """
    TIPO_USUARIO_CHOICES = [
        ('admin', 'Administrador'),
        ('comerciante', 'Comerciante'),
        ('funcionario', 'Funcionário'),
    ]
    
    tipo_usuario = models.CharField(
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default='comerciante',
        verbose_name='Tipo de Usuário'
    )
    
    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Telefone'
    )
    
    data_nascimento = models.DateField(
        blank=True,
        null=True,
        verbose_name='Data de Nascimento'
    )
    
    foto_perfil = models.ImageField(
        upload_to='perfil/',
        blank=True,
        null=True,
        verbose_name='Foto do Perfil'
    )
    
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de Criação'
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name='Data de Atualização'
    )
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.username} - {self.get_tipo_usuario_display()}"
    
    def is_admin(self):
        return self.tipo_usuario == 'admin'
    
    def is_comerciante(self):
        return self.tipo_usuario == 'comerciante'
    
    def is_funcionario(self):
        return self.tipo_usuario == 'funcionario'
