# coding:utf-8

from django.urls import path,include,re_path
from django.conf import settings
from app_ai import views

urlpatterns = [
    path('config/',views.ai_config,name="ai_config"), # AI配置页面
    path('text_generate/',views.ai_text_genarate,name="ai_text_genarate"), # AI文本生成
    path('openai_text_generate/',views.openai_text_generate,name="openai_text_generate"), # AI文本生成

    # Dify 会话管理
    path('dify/conversations/', views.dify_get_conversations, name="dify_get_conversations"), # 获取会话列表
    path('dify/conversations/create/', views.dify_create_or_get_conversation, name="dify_create_conversation"), # 创建或获取会话
    path('dify/conversations/rename/', views.dify_rename_conversation, name="dify_rename_conversation"), # 重命名会话

    # Dify 消息管理
    path('dify/messages/', views.dify_get_messages, name="dify_get_messages"), # 获取消息列表
    path('dify/messages/send/', views.dify_send_message, name="dify_send_message"), # 发送消息

    # Dify 应用信息
    path('dify/app/info/', views.dify_get_app_info, name="dify_get_app_info"), # 获取应用信息
]