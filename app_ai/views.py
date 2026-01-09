# coding:utf-8
from django.shortcuts import render
from django.core.cache import cache
from django.http.response import JsonResponse,StreamingHttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required # 登录需求装饰器
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination,LimitOffsetPagination # 分页
from rest_framework.authentication import SessionAuthentication # 认证
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from app_admin.decorators import superuser_only,open_register
from app_admin.models import SysSetting
from app_admin.utils import encrypt_data,decrypt_data
from app_api.auth_app import AppMustAuth
from app_api.permissions_app import SuperUserPermission
from app_doc.models import Doc, Project
from app_ai.utils import get_sys_value
from app_ai.models import DifyConversation, DifyMessage
from loguru import logger
import json
import sys
import os
import datetime
import time
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 返回用户标识符
def get_user_identifier(request):
    """
    返回用户标识符：
    - 已登录用户：user_<id>
    - 匿名用户：anon_<session_key>
    """
    if request.user.is_authenticated:
        return f"user_{request.user.id}"
    else:
        # 确保 session 存在
        if not request.session.session_key:
            request.session.create()
        return f"anon_{request.session.session_key}"



# 文本生成动态速率限制装饰器
def dynamic_rate_limit(view_func):
    """
    动态速率限制装饰器，基于 request.user 进行限制
    """

    def wrapped_view(request, *args, **kwargs):
        # 从数据库中获取速率限制值
        rate_limit_value = getattr(
            SysSetting.objects.filter(types='ai', name='ai_write_rate_limit').first(),
            'value', '-1'  # 默认值为 '5/m'
        )

        if rate_limit_value == '-1':
            return view_func(request, *args, **kwargs)

        # 获取用户标识符（使用 request.user）
        user_identifier = get_user_identifier(request)  # 使用用户ID作为标识符

        # 解析速率限制
        try:
            num_requests = int(rate_limit_value)
        except:
            num_requests = 5
        duration = 60

        # 生成缓存键
        cache_key = f'ai_text_rate_limit_{user_identifier}_{request.path}'

        # 获取当前请求时间
        current_time = time.time()

        # 获取缓存中的请求记录
        request_times = cache.get(cache_key, [])

        # 删除超过时间窗口的请求记录
        request_times = [t for t in request_times if current_time - t < duration]

        # 检查请求次数是否超过限制
        if len(request_times) >= num_requests:
            return JsonResponse({'status':False,'data':'已超过请求频率限制，请稍后再使用！'})

        # 添加当前请求时间到记录中
        request_times.append(current_time)

        # 更新缓存
        cache.set(cache_key, request_times, duration)

        # 调用原始视图函数
        return view_func(request, *args, **kwargs)

    return wrapped_view



# Create your views here.
# 后台管理 - 站点管理 - AI接入设置
@superuser_only
def ai_config(request):
    if request.method == 'GET':
        ai_frames = [
            {'name':'Dify','value':'1', 'status':True},
            # {'name': 'FastGPT', 'value': '2', 'status':False},
        ]

        return render(request,'app_ai/config.html',locals())
    elif request.method == 'POST':
        try:
            data = request.POST.get("data")
            data_json = json.loads(data)
            # print(data_json)
            for d in data_json:
                # print(d)
                if d['type'] == 'ai':
                    if d['name'] in ['ai_dify_chat_api_key','ai_dify_dataset_api_key','ai_dify_textgenerate_api_key']:
                        d['value'] = encrypt_data(d['value'])
                    SysSetting.objects.update_or_create(
                        name=d['name'],
                        defaults={'value': d['value'], 'types': 'ai'}
                    )
                else:
                    pass
            return JsonResponse({'code': 0, })
        except Exception as e:
            logger.exception("保存AI配置异常")
            return JsonResponse({'code',4})


from openai import OpenAI
from dify_client import Client as DifyClient, models

try:
    from http import HTTPMethod
except ImportError:
    class HTTPMethod:
        GET = "GET"
        POST = "POST"

# 从环境变量获取 AI 配置
AI_KEY = os.getenv("AI_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")

client = OpenAI(
    base_url=AI_BASE_URL,
    api_key=AI_KEY
)

# AI文本写作
@csrf_exempt
@login_required
@dynamic_rate_limit
def ai_text_genarate(request):
    def event_stream():
        ai_frame = getattr(SysSetting.objects.filter(types='ai', name='ai_frame').first(), 'value', '')

        # 调试：查看原始请求体
        raw_body = request.body.decode('utf-8')
        logger.info(f"收到的原始请求体: {raw_body}")

        # 获取用户消息
        try:
            request_json = json.loads(request.body)
            logger.info(f"解析后的 JSON: {request_json}")
            # 获取完整的 inputs 对象
            inputs_data = request_json.get('inputs', {})
            # 提取 query 字段作为主要输入
            user_query = inputs_data.get('query', '')
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"解析请求数据失败: {e}, 请求数据: {request.body}")
            yield f"event: error\ndata: {json.dumps({'message': f'请求数据格式错误: {str(e)}'})}\n\n"
            return

        try:
            if ai_frame == '1':  # Dify
                # 获取 Dify 配置
                dify_api_address = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_api_address').first(),
                    'value', ''
                )
                dify_textgenerate_key = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_textgenerate_api_key').first(),
                    'value', ''
                )

                # 解密 API Key
                api_key = decrypt_data(dify_textgenerate_key)

                # 创建 Dify Client 实例
                dify_client = DifyClient(api_key=api_key, api_base=dify_api_address)

                # 调试日志
                logger.info(f"Dify API 地址: {dify_api_address}")
                logger.info(f"请求输入: {user_query}")

                # 调用 Dify Completion API（流式模式）
                # 注意：CompletionInputs 需要 query 字段，同时也需要传递 Dify 应用配置的输入变量
                # 这里的 Dify 应用配置了一个名为 'inputs' 的变量
                completion_request = models.CompletionRequest(
                    inputs=models.CompletionInputs(query=user_query, inputs=user_query),
                    response_mode=models.ResponseMode.STREAMING,
                    user=request.user.username
                )

                # 获取流式响应
                for chunk in dify_client.completion_messages(completion_request):
                    # chunk 是 CompletionStreamResponse 对象
                    # 转换为 SSE 格式
                    event_type = chunk.event
                    data = chunk.model_dump()
                    yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            logger.exception("AI文本生成失败")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'X-Accel-Buffering': 'no'}  # 禁用Nginx缓冲
    )


# AI文本写作
@csrf_exempt
@login_required
@dynamic_rate_limit
def openai_text_generate(request):
    def event_stream():
        ai_frame = getattr(SysSetting.objects.filter(types='ai', name='ai_frame').first(), 'value', '')
        # 获取用户消息
        user_input = json.loads(request.body)['inputs']['query']

        try:
            
            # 发起流式请求
            response = client.chat.completions.create(
                model="ds-r1",
                messages=[
                    { 'role': 'system', 'content': "你是一个软件测试专家" },
                    { 'role': 'user', 'content': user_input }
                ],
                stream=True
            )
            for chunk in response:
                if chunk:
                    content = chunk.choices[0].delta.content
                    
                    if content:  # Only send non-empty content
                        event_data = {
                            "event": "message",
                            "answer": content
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"

            # When stream completes:
            yield f"data: {json.dumps({'event': 'message_end'})}\n\n"

    
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'X-Accel-Buffering': 'no'}  # 禁用Nginx缓冲
    )

# ================== Dify 会话管理 ==================

def get_dify_client(conversation):
    """获取 Dify 客户端"""
    api_key = decrypt_data(conversation.app_api_key)
    return DifyClient(api_key=api_key, api_base=conversation.dify_api_address)


@csrf_exempt
@login_required
def dify_get_conversations(request):
    """获取用户的所有会话列表"""
    if request.method == 'GET':
        try:
            # 从数据库获取用户的所有会话
            conversations = DifyConversation.objects.filter(user=request.user)

            result = []
            for conv in conversations:
                result.append({
                    'id': conv.id,
                    'conversation_id': conv.conversation_id,
                    'app_name': conv.app_name,
                    'created_at': conv.created_at.isoformat(),
                    'updated_at': conv.updated_at.isoformat(),
                })

            return JsonResponse({
                'status': True,
                'data': result
            })
        except Exception as e:
            logger.exception("获取会话列表失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)


@csrf_exempt
@login_required
def dify_create_or_get_conversation(request):
    """创建或获取会话"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            app_name = data.get('app_name', '默认应用')
            app_api_key = data.get('app_api_key')
            dify_api_address = data.get('dify_api_address')

            # 如果提供了 conversation_id，尝试获取现有会话
            if conversation_id:
                conversation = DifyConversation.objects.filter(
                    conversation_id=conversation_id,
                    user=request.user
                ).first()

                if conversation:
                    return JsonResponse({
                        'status': True,
                        'data': {
                            'id': conversation.id,
                            'conversation_id': conversation.conversation_id,
                            'app_name': conversation.app_name,
                            'created_at': conversation.created_at.isoformat(),
                            'updated_at': conversation.updated_at.isoformat(),
                        }
                    })

            # 创建新会话
            if not app_api_key or not dify_api_address:
                # 使用系统默认配置
                dify_api_address = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_api_address').first(),
                    'value', ''
                )
                app_api_key = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_chat_api_key').first(),
                    'value', ''
                )

            # 加密 API 密钥
            encrypted_key = encrypt_data(app_api_key) if not app_api_key.startswith('gAAAAA') else app_api_key

            conversation = DifyConversation.objects.create(
                conversation_id=conversation_id,  # 可以为空，首次发送消息时会自动设置
                user=request.user,
                app_name=app_name,
                app_api_key=encrypted_key,
                dify_api_address=dify_api_address
            )

            return JsonResponse({
                'status': True,
                'data': {
                    'id': conversation.id,
                    'conversation_id': conversation.conversation_id,
                    'app_name': conversation.app_name,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat(),
                }
            })

        except Exception as e:
            logger.exception("创建会话失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)


@csrf_exempt
@login_required
def dify_rename_conversation(request):
    """重命名会话"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            new_name = data.get('name')

            if not conversation_id or not new_name:
                return JsonResponse({
                    'status': False,
                    'message': 'conversation_id 和 name 参数必填'
                }, status=400)

            # 获取数据库中的会话
            conversation = DifyConversation.objects.filter(
                conversation_id=conversation_id,
                user=request.user
            ).first()

            if not conversation:
                return JsonResponse({
                    'status': False,
                    'message': '会话不存在'
                }, status=404)

            # 调用 Dify API 重命名
            dify_client = get_dify_client(conversation)
            user_identifier = get_user_identifier(request)

            response = dify_client.request(
                endpoint=f"/conversations/{conversation_id}/name",
                method=HTTPMethod.POST,
                json={
                    "name": new_name,
                    "auto_generate": False,
                    "user": user_identifier
                }
            )

            # 更新本地数据库
            conversation.app_name = new_name
            conversation.save()

            return JsonResponse({
                'status': True,
                'data': response.json()
            })

        except Exception as e:
            logger.exception("重命名会话失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)


# ================== Dify 消息管理 ==================

@csrf_exempt
@login_required
def dify_get_messages(request):
    """获取会话的消息列表"""
    if request.method == 'GET':
        try:
            conversation_id = request.GET.get('conversation_id')

            if not conversation_id:
                return JsonResponse({
                    'status': False,
                    'message': 'conversation_id 参数必填'
                }, status=400)

            # 获取数据库中的会话
            conversation = DifyConversation.objects.filter(
                conversation_id=conversation_id,
                user=request.user
            ).first()

            if not conversation:
                return JsonResponse({
                    'status': False,
                    'message': '会话不存在'
                }, status=404)

            # 从 Dify API 获取消息列表
            dify_client = get_dify_client(conversation)
            user_identifier = get_user_identifier(request)

            response = dify_client.request(
                endpoint="/messages",
                method=HTTPMethod.GET,
                params={
                    "conversation_id": conversation_id,
                    "user": user_identifier
                }
            )

            messages_data = response.json()

            # 可选：同步到本地数据库
            if messages_data.get('data'):
                for msg in messages_data['data']:
                    DifyMessage.objects.update_or_create(
                        message_id=msg.get('id'),
                        defaults={
                            'conversation': conversation,
                            'role': 'user' if msg.get('query') else 'assistant',
                            'content': msg.get('query') or msg.get('answer', ''),
                        }
                    )

            return JsonResponse({
                'status': True,
                'data': messages_data
            })

        except Exception as e:
            logger.exception("获取消息列表失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)


@csrf_exempt
@login_required
@dynamic_rate_limit
def dify_send_message(request):
    """发送消息到会话（支持流式和阻塞模式）"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            conversation_db_id = data.get('conversation_id')  # 数据库 ID
            query = data.get('query')
            inputs = data.get('inputs', {})
            response_mode = data.get('response_mode', 'blocking')  # blocking 或 streaming

            if not conversation_db_id or not query:
                return JsonResponse({
                    'status': False,
                    'message': 'conversation_id 和 query 参数必填'
                }, status=400)

            # 获取数据库中的会话
            conversation = DifyConversation.objects.filter(
                id=conversation_db_id,
                user=request.user
            ).first()

            if not conversation:
                return JsonResponse({
                    'status': False,
                    'message': '会话不存在'
                }, status=404)

            # 获取 Dify 客户端
            dify_client = get_dify_client(conversation)
            user_identifier = get_user_identifier(request)

            # 保存用户消息到数据库
            user_message = DifyMessage.objects.create(
                conversation=conversation,
                role='user',
                content=query
            )

            # 阻塞模式
            if response_mode == 'blocking':
                chat_request = models.ChatRequest(
                    inputs=inputs,
                    query=query,
                    user=user_identifier,
                    response_mode=models.ResponseMode.BLOCKING,
                    conversation_id=conversation.conversation_id if conversation.conversation_id else None
                )
                result = dify_client.chat_messages(chat_request)

                # 更新会话 ID（如果是第一次发送）
                if not conversation.conversation_id and result.conversation_id:
                    conversation.conversation_id = result.conversation_id
                    conversation.save()

                # 保存助手回复到数据库
                if result.answer:
                    DifyMessage.objects.create(
                        conversation=conversation,
                        role='assistant',
                        content=result.answer,
                        message_id=result.id
                    )

                return JsonResponse({
                    'status': True,
                    'data': result.model_dump()
                })

            # 流式模式
            else:
                def event_stream():
                    try:
                        chat_request = models.ChatRequest(
                            inputs=inputs,
                            query=query,
                            user=user_identifier,
                            response_mode=models.ResponseMode.STREAMING,
                            conversation_id=conversation.conversation_id if conversation.conversation_id else None
                        )

                        full_answer = ""
                        message_id = None
                        conv_id = None

                        for chunk in dify_client.chat_messages(chat_request):
                            # chunk 是 ChatStreamResponse 对象
                            # 记录 conversation_id
                            if hasattr(chunk, 'conversation_id') and chunk.conversation_id:
                                conv_id = chunk.conversation_id

                            # 记录 message_id
                            if hasattr(chunk, 'id') and chunk.id:
                                message_id = chunk.id

                            # 累积答案
                            if hasattr(chunk, 'answer') and chunk.answer:
                                full_answer += chunk.answer

                            # 转发数据
                            yield f"data: {json.dumps(chunk.model_dump())}\n\n"

                        # 更新会话 ID
                        if not conversation.conversation_id and conv_id:
                            conversation.conversation_id = conv_id
                            conversation.save()

                        # 保存完整的助手回复
                        if full_answer:
                            DifyMessage.objects.create(
                                conversation=conversation,
                                role='assistant',
                                content=full_answer,
                                message_id=message_id
                            )

                    except Exception as e:
                        logger.exception("流式发送消息失败")
                        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

                return StreamingHttpResponse(
                    event_stream(),
                    content_type='text/event-stream',
                    headers={'X-Accel-Buffering': 'no'}
                )

        except Exception as e:
            logger.exception("发送消息失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)


# ================== Dify 应用信息 ==================

@csrf_exempt
@login_required
def dify_get_app_info(request):
    """获取应用基本信息"""
    if request.method == 'GET':
        try:
            conversation_db_id = request.GET.get('conversation_id')

            if not conversation_db_id:
                # 使用系统默认配置
                dify_api_address = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_api_address').first(),
                    'value', ''
                )
                app_api_key = getattr(
                    SysSetting.objects.filter(types='ai', name='ai_dify_chat_api_key').first(),
                    'value', ''
                )
                api_key = decrypt_data(app_api_key)
                dify_client = DifyClient(api_key=api_key, api_base=dify_api_address)
            else:
                # 使用指定会话的配置
                conversation = DifyConversation.objects.filter(
                    id=conversation_db_id,
                    user=request.user
                ).first()

                if not conversation:
                    return JsonResponse({
                        'status': False,
                        'message': '会话不存在'
                    }, status=404)

                dify_client = get_dify_client(conversation)

            user_identifier = get_user_identifier(request)

            # 获取应用参数
            response = dify_client.request(
                endpoint="/parameters",
                method=HTTPMethod.GET,
                params={"user": user_identifier}
            )

            return JsonResponse({
                'status': True,
                'data': response.json()
            })

        except Exception as e:
            logger.exception("获取应用信息失败")
            return JsonResponse({
                'status': False,
                'message': str(e)
            }, status=500)
