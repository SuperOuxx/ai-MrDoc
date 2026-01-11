#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Dify API 的脚本
用于排查 ai_text_genarate 方法的问题
"""

import requests
import json
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MrDoc.settings')
django.setup()

from app_admin.models import SysSetting
from app_admin.utils import decrypt_data

def test_dify_parameters():
    """测试获取 Dify 应用参数"""
    print("=" * 50)
    print("1. 获取 Dify 应用参数配置")
    print("=" * 50)

    dify_api_address = getattr(
        SysSetting.objects.filter(types='ai', name='ai_dify_api_address').first(),
        'value', ''
    )
    dify_textgenerate_key = getattr(
        SysSetting.objects.filter(types='ai', name='ai_dify_textgenerate_api_key').first(),
        'value', ''
    )

    if not dify_api_address or not dify_textgenerate_key:
        print("❌ 错误: Dify API 配置不完整")
        print(f"API 地址: {dify_api_address}")
        print(f"API Key: {'已配置' if dify_textgenerate_key else '未配置'}")
        return None

    print(f"✓ API 地址: {dify_api_address}")

    headers = {
        'Authorization': f'Bearer {decrypt_data(dify_textgenerate_key)}',
    }

    try:
        response = requests.get(f'{dify_api_address}/parameters', headers=headers)
        print(f"✓ 响应状态码: {response.status_code}")

        if response.status_code == 200:
            params = response.json()
            print("\n应用参数配置:")
            print(json.dumps(params, indent=2, ensure_ascii=False))
            return params
        else:
            print(f"❌ 错误响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def test_dify_completion(test_query="Hello, world!"):
    """测试 Dify 文本生成 API"""
    print("\n" + "=" * 50)
    print("2. 测试 Dify 文本生成 API")
    print("=" * 50)

    dify_api_address = getattr(
        SysSetting.objects.filter(types='ai', name='ai_dify_api_address').first(),
        'value', ''
    )
    dify_textgenerate_key = getattr(
        SysSetting.objects.filter(types='ai', name='ai_dify_textgenerate_api_key').first(),
        'value', ''
    )

    headers = {
        'Authorization': f'Bearer {decrypt_data(dify_textgenerate_key)}',
        'Content-Type': 'application/json',
    }

    print(f"=====headers========\r\n{headers}")

    # 测试不同的请求格式
    test_cases = [
        {
            "name": "根据应用配置：inputs.inputs + inputs.A",
            "data": {
                "inputs": {
                    "inputs": test_query,  # 变量名是 'inputs'
                    "A": "MySQL"           # 数据库类型
                },
                "response_mode": "blocking",
                "user": "test_user"
            }
        },
        {
            "name": "根据应用配置：只有 inputs.inputs（不提供 A）",
            "data": {
                "inputs": {
                    "inputs": test_query   # 变量名是 'inputs'
                },
                "response_mode": "blocking",
                "user": "test_user"
            }
        },
        {
            "name": "标准格式（query 在 inputs 中）",
            "data": {
                "inputs": {"query": test_query},
                "response_mode": "blocking",
                "user": "test_user"
            }
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case['name']}")
        print(f"请求数据: {json.dumps(test_case['data'], ensure_ascii=False)}")

        try:
            response = requests.post(
                f'{dify_api_address}/completion-messages',
                headers=headers,
                json=test_case['data']
            )

            print(f"✓ 响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 成功! 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("\n🎉 找到正确的格式!")
                return test_case['data']
            else:
                print(f"❌ 错误响应: {response.text}")
        except Exception as e:
            print(f"❌ 请求失败: {e}")

    return None


if __name__ == '__main__':
    print("Dify API 测试脚本")
    print("=" * 50)

    # 步骤1: 获取应用参数
    params = test_dify_parameters()

    # 步骤2: 测试不同的请求格式
    if params:
        print("\n从应用参数中分析...")
        if 'user_input_form' in params:
            print("检测到的输入表单配置:")
            for form in params['user_input_form']:
                print(f"  - {form}")

    working_format = test_dify_completion()

    if working_format:
        print("\n" + "=" * 50)
        print("✓ 测试完成，找到正确的请求格式")
        print("=" * 50)
        print(f"请使用以下格式: {json.dumps(working_format, indent=2, ensure_ascii=False)}")
    else:
        print("\n" + "=" * 50)
        print("❌ 所有测试用例均失败")
        print("=" * 50)
        print("请检查:")
        print("1. Dify API 地址是否正确")
        print("2. API Key 是否有效")
        print("3. Dify 应用类型是否为 Completion App")
        print("4. Dify 应用的输入表单配置")
