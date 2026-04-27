#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A500活动评分工具后端 - Vercel Serverless Version
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import io

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Import after app creation to avoid circular import
from score_calculator import process_file


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

        file_content = file.read()

        if file.filename.endswith('.xlsx'):
            result_df = process_file(io.BytesIO(file_content))
        else:
            result_df = process_file(io.BytesIO(file_content))

        if result_df is None or result_df.empty:
            return jsonify({'success': False, 'message': '文件处理失败，没有有效数据'})

        preview_data = result_df.head(10).to_dict('records')
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
    return jsonify({'success': False, 'message': '请先上传文件'})


@app.route('/api/download/<result_id>', methods=['GET'])
def download_result(result_id):
    return jsonify({'success': False, 'message': '结果已在上传响应中返回'})


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'message': '服务正常'})


@app.route('/api/', methods=['GET'])
def api_index():
    return jsonify({
        'success': True,
        'message': 'A500活动评分工具API',
        'endpoints': [
            'POST /api/upload - 上传文件并计算评分',
            'GET /api/health - 健康检查'
        ]
    })


# Vercel handler export
handler = app