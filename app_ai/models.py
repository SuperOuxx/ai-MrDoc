from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DifyConversation(models.Model):
    """Dify对话会话模型"""
    conversation_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Dify会话ID'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dify_conversations',
        verbose_name='用户'
    )
    app_name = models.CharField(
        max_length=255,
        default='默认应用',
        verbose_name='应用名称'
    )
    app_api_key = models.TextField(
        verbose_name='应用API密钥（加密）'
    )
    dify_api_address = models.URLField(
        max_length=500,
        verbose_name='Dify API地址'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )

    class Meta:
        db_table = 'dify_conversation'
        verbose_name = 'Dify对话会话'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.app_name} - {self.conversation_id or 'New'}"


class DifyMessage(models.Model):
    """Dify对话消息模型"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', '助手'),
    ]

    conversation = models.ForeignKey(
        DifyConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='所属会话'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='角色'
    )
    content = models.TextField(
        verbose_name='消息内容'
    )
    message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Dify消息ID'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )

    class Meta:
        db_table = 'dify_message'
        verbose_name = 'Dify对话消息'
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
