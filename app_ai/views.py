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
    """动态速率限制装饰器，基于 request.user 进行限制"""

    def wrapped_view(request, *args, **kwargs):
        # 从数据库中获取速率限制值
        rate_limit_value = get_sys_setting_value('ai_write_rate_limit', '-1')

        if rate_limit_value == '-1':
            return view_func(request, *args, **kwargs)

        # 获取用户标识符
        user_identifier = get_user_identifier(request)

        # 解析速率限制
        try:
            num_requests = int(rate_limit_value)
        except (ValueError, TypeError):
            num_requests = 5
        duration = 60

        # 生成缓存键
        cache_key = f'ai_text_rate_limit_{user_identifier}_{request.path}'

        # 获取当前时间和请求记录
        current_time = time.time()
        request_times = cache.get(cache_key, [])

        # 删除超过时间窗口的请求记录
        request_times = [t for t in request_times if current_time - t < duration]

        # 检查请求次数是否超过限制
        if len(request_times) >= num_requests:
            return JsonResponse({'status': False, 'data': '已超过请求频率限制，请稍后再使用！'})

        # 添加当前请求时间到记录中
        request_times.append(current_time)
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
    """AI 文本生成（使用 Dify）"""
    def event_stream():
        ai_frame = get_sys_setting_value('ai_frame')

        # 解析请求数据
        try:
            request_json = json.loads(request.body)
            logger.info(f"收到的请求: {request_json}")

            inputs_data = request_json.get('inputs', {})
            user_query = inputs_data.get('query', '')

            if not user_query:
                yield f"event: error\ndata: {json.dumps({'message': '请求参数 query 不能为空'})}\n\n"
                return

        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"解析请求数据失败: {e}")
            yield f"event: error\ndata: {json.dumps({'message': f'请求数据格式错误: {str(e)}'})}\n\n"
            return

        # 处理 Dify 文本生成
        try:
            if ai_frame == '1':  # Dify
                # 获取配置并创建客户端
                api_key = decrypt_data(get_sys_setting_value('ai_dify_textgenerate_api_key'))
                dify_client = get_dify_client(api_key=api_key)

                logger.info(f"Dify API 地址: {get_dify_api_address()}")
                logger.info(f"请求输入: {user_query}")

                # 调用 Dify Completion API（流式模式）
                completion_request = models.CompletionRequest(
                    inputs=models.CompletionInputs(query=user_query, inputs=user_query),
                    response_mode=models.ResponseMode.STREAMING,
                    user=request.user.username
                )

                # 获取并转发流式响应
                for chunk in dify_client.completion_messages(completion_request):
                    yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        except Exception as e:
            logger.exception("AI文本生成失败")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'X-Accel-Buffering': 'no'}
    )


# AI文本写作（OpenAI 兼容）
@csrf_exempt
@login_required
@dynamic_rate_limit
def openai_text_generate(request):
    """AI 文本生成（使用 OpenAI 兼容 API）"""
    def event_stream():
        # 获取用户消息
        try:
            user_input = json.loads(request.body)['inputs']['query']
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"解析请求数据失败: {e}")
            yield f"event: error\ndata: {json.dumps({'message': f'请求数据格式错误: {str(e)}'})}\n\n"
            return

        try:
            # 发起流式请求
            response = client.chat.completions.create(
                model="ds-r1",
                messages=[
                    {'role': 'system', 'content': "你是一个软件测试专家"},
                    {'role': 'user', 'content': user_input}
                ],
                stream=True
            )

            # 流式输出内容
            for chunk in response:
                if chunk and chunk.choices[0].delta.content:
                    event_data = {
                        "event": "message",
                        "answer": chunk.choices[0].delta.content
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"

            # 流式结束标志
            yield f"data: {json.dumps({'event': 'message_end'})}\n\n"

        except Exception as e:
            logger.exception("OpenAI 文本生成失败")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'X-Accel-Buffering': 'no'}
    )

# ================== Dify 会话管理 ==================

def get_sys_setting_value(name, default=''):
    """从系统设置获取配置值的通用函数"""
    setting = SysSetting.objects.filter(types='ai', name=name).first()
    return getattr(setting, 'value', default)


def get_dify_api_address():
    """从系统设置获取 Dify API 地址"""
    return get_sys_setting_value('ai_dify_api_address')


def get_dify_chat_api_key():
    """从系统设置获取并解密 Dify Chat API Key"""
    encrypted_key = get_sys_setting_value('ai_dify_chat_api_key')
    return decrypt_data(encrypted_key) if encrypted_key else ''


def get_dify_client(conversation=None, api_key=None):
    """
    获取 Dify 客户端

    Args:
        conversation: DifyConversation 对象（可选）
        api_key: 明文 API Key（可选，如果提供则直接使用）

    Returns:
        DifyClient 实例
    """
    dify_api_address = get_dify_api_address()

    if api_key is None:
        if conversation:
            api_key = decrypt_data(conversation.app_api_key)
        else:
            api_key = get_dify_chat_api_key()

    return DifyClient(api_key=api_key, api_base=dify_api_address)


def get_conversation_or_404(conversation_id, user, use_db_id=False):
    """
    获取会话对象，不存在则返回 404 响应

    Args:
        conversation_id: 会话 ID（Dify 会话 ID 或数据库 ID）
        user: 用户对象
        use_db_id: 是否使用数据库 ID 查询（默认使用 Dify 会话 ID）

    Returns:
        tuple: (conversation, error_response)
        如果成功返回 (conversation, None)，失败返回 (None, JsonResponse)
    """
    filter_kwargs = {'user': user}
    if use_db_id:
        filter_kwargs['id'] = conversation_id
    else:
        filter_kwargs['conversation_id'] = conversation_id

    conversation = DifyConversation.objects.filter(**filter_kwargs).first()

    if not conversation:
        return None, JsonResponse({
            'status': False,
            'message': '会话不存在'
        }, status=404)

    return conversation, None


def success_response(data):
    """返回成功的 JSON 响应"""
    return JsonResponse({'status': True, 'data': data})


def error_response(message, status_code=500):
    """返回错误的 JSON 响应"""
    return JsonResponse({'status': False, 'message': message}, status=status_code)


@csrf_exempt
@login_required
def dify_get_conversations(request):
    """获取用户的所有会话列表"""
    if request.method != 'GET':
        return error_response('仅支持 GET 请求', 405)

    try:
        conversations = DifyConversation.objects.filter(user=request.user)

        result = [{
            'id': conv.id,
            'conversation_id': conv.conversation_id,
            'app_name': conv.app_name,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
        } for conv in conversations]

        return success_response(result)

    except Exception as e:
        logger.exception("获取会话列表失败")
        return error_response(str(e))


@csrf_exempt
@login_required
def dify_create_or_get_conversation(request):
    """创建或获取会话"""
    if request.method != 'POST':
        return error_response('仅支持 POST 请求', 405)

    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        app_name = data.get('app_name', '默认应用')
        app_api_key = data.get('app_api_key')

        # 如果提供了 conversation_id，尝试获取现有会话
        if conversation_id:
            conversation = DifyConversation.objects.filter(
                conversation_id=conversation_id,
                user=request.user
            ).first()

            if conversation:
                return success_response({
                    'id': conversation.id,
                    'conversation_id': conversation.conversation_id,
                    'app_name': conversation.app_name,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat(),
                })

        # 创建新会话：获取配置
        dify_api_address = get_dify_api_address()
        if not app_api_key:
            app_api_key = get_sys_setting_value('ai_dify_chat_api_key')

        # 加密 API 密钥
        encrypted_key = app_api_key if app_api_key.startswith('gAAAAA') else encrypt_data(app_api_key)

        # 创建会话
        conversation = DifyConversation.objects.create(
            conversation_id=conversation_id,
            user=request.user,
            app_name=app_name,
            app_api_key=encrypted_key,
            dify_api_address=dify_api_address
        )

        return success_response({
            'id': conversation.id,
            'conversation_id': conversation.conversation_id,
            'app_name': conversation.app_name,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
        })

    except Exception as e:
        logger.exception("创建会话失败")
        return error_response(str(e))


@csrf_exempt
@login_required
def dify_rename_conversation(request):
    """重命名会话"""
    if request.method != 'POST':
        return error_response('仅支持 POST 请求', 405)

    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        new_name = data.get('name')

        if not conversation_id or not new_name:
            return error_response('conversation_id 和 name 参数必填', 400)

        # 获取会话
        conversation, error = get_conversation_or_404(conversation_id, request.user)
        if error:
            return error

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

        return success_response(response.json())

    except Exception as e:
        logger.exception("重命名会话失败")
        return error_response(str(e))


# ================== Dify 消息管理 ==================

@csrf_exempt
@login_required
def dify_get_messages(request):
    """获取会话的消息列表"""
    if request.method != 'GET':
        return error_response('仅支持 GET 请求', 405)

    try:
        conversation_id = request.GET.get('conversation_id')

        if not conversation_id:
            return error_response('conversation_id 参数必填', 400)

        # 获取会话
        conversation, error = get_conversation_or_404(conversation_id, request.user)
        if error:
            return error

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

        # 同步消息到本地数据库
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

        return success_response(messages_data)

    except Exception as e:
        logger.exception("获取消息列表失败")
        return error_response(str(e))


@csrf_exempt
@login_required
@dynamic_rate_limit
def dify_send_message(request):
    """发送消息到会话（支持流式和阻塞模式）"""
    if request.method != 'POST':
        return error_response('仅支持 POST 请求', 405)

    try:
        data = json.loads(request.body)
        conversation_db_id = data.get('conversation_id')  # 数据库 ID
        query = data.get('query')
        inputs = data.get('inputs', {})
        response_mode = data.get('response_mode', 'blocking')

        if not conversation_db_id or not query:
            return error_response('conversation_id 和 query 参数必填', 400)

        # 获取会话
        conversation, error = get_conversation_or_404(conversation_db_id, request.user, use_db_id=True)
        if error:
            return error

        # 获取 Dify 客户端和用户标识
        dify_client = get_dify_client(conversation)
        user_identifier = get_user_identifier(request)

        # 保存用户消息到数据库
        DifyMessage.objects.create(
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
                conversation_id=conversation.conversation_id or None
            )
            result = dify_client.chat_messages(chat_request)

            # 更新会话 ID（如果是第一次发送）
            if not conversation.conversation_id and result.conversation_id:
                conversation.conversation_id = result.conversation_id
                conversation.save()

            # 保存助手回复
            if result.answer:
                DifyMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=result.answer,
                    message_id=result.id
                )

            return success_response(result.model_dump())

        # 流式模式
        else:
            def event_stream():
                try:
                    chat_request = models.ChatRequest(
                        inputs=inputs,
                        query=query,
                        user=user_identifier,
                        response_mode=models.ResponseMode.STREAMING,
                        conversation_id=conversation.conversation_id or None
                    )

                    full_answer = ""
                    message_id = None
                    conv_id = None

                    for chunk in dify_client.chat_messages(chat_request):
                        # 记录 conversation_id 和 message_id
                        if hasattr(chunk, 'conversation_id') and chunk.conversation_id:
                            conv_id = chunk.conversation_id
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
        return error_response(str(e))


# ================== Dify 应用信息 ==================

@csrf_exempt
@login_required
def dify_get_app_info(request):
    """获取应用基本信息"""
    if request.method != 'GET':
        return error_response('仅支持 GET 请求', 405)

    try:
        conversation_db_id = request.GET.get('conversation_id')

        # 获取 Dify 客户端（使用会话配置或系统默认配置）
        if conversation_db_id:
            conversation, error = get_conversation_or_404(conversation_db_id, request.user, use_db_id=True)
            if error:
                return error
            dify_client = get_dify_client(conversation)
        else:
            # 使用系统默认配置
            dify_client = get_dify_client()

        user_identifier = get_user_identifier(request)

        # 获取应用参数
        response = dify_client.request(
            endpoint="/parameters",
            method=HTTPMethod.GET,
            params={"user": user_identifier}
        )

        return success_response(response.json())

    except Exception as e:
        logger.exception("获取应用信息失败")
        return error_response(str(e))
