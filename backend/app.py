#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A500活动评分工具后端 - Vercel Serverless Version
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import io
import json
from score_calculator import process_file

app = Flask(__name__)
CORS(app, supports_credentials=True)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传并处理文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'})

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'})

        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            return jsonify({'success': False, 'message': '仅支持Excel和CSV文件'})

        # 读取文件内容到内存
        file_content = file.read()

        # 处理文件
        if file.filename.endswith('.xlsx'):
            result_df = process_file(io.BytesIO(file_content))
        else:
            result_df = process_file(io.BytesIO(file_content))

        if result_df is None or result_df.empty:
            return jsonify({'success': False, 'message': '文件处理失败，没有有效数据'})

        # 生成预览数据（前10条）
        preview_data = result_df.head(10).to_dict('records')

        # 将完整结果存储在内存中（实际生产环境应使用外部存储）
        result_csv = result_df.to_csv(index=False, encoding='utf-8-sig')

        return jsonify({
            'success': True,
            'result_id': 'memory',
            'preview': preview_data,
            'total_count': len(result_df),
            'result_csv': result_csv,
            'message': '评分计算完成'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'计算失败: {str(e)}'})


@app.route('/api/calculate', methods=['POST'])
def calculate_score():
    """计算评分（复用上传接口）"""
    return jsonify({'success': False, 'message': '请先上传文件'})


@app.route('/api/download/<result_id>', methods=['GET'])
def download_result(result_id):
    """下载结果文件"""
    return jsonify({'success': False, 'message': '结果已在上传响应中返回'})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'success': True, 'message': '服务正常'})


@app.route('/api/', methods=['GET'])
def api_index():
    """API根路径"""
    return jsonify({
        'success': True,
        'message': 'A500活动评分工具API',
        'endpoints': [
            'POST /api/upload - 上传文件并计算评分',
            'GET /api/health - 健康检查'
        ]
    })


def handler(event, context):
    """Vercel serverless handler"""
    return app(event, context)