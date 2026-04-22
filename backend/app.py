#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A500活动评分工具后端
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
import uuid
from score_calculator import process_file

app = Flask(__name__)
# 配置CORS，允许所有跨域请求
CORS(app, supports_credentials=True)

# 使用临时目录存储文件
UPLOAD_DIR = tempfile.gettempdir()
OUTPUT_DIR = tempfile.gettempdir()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'})

        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择文件'})

        # 检查文件格式
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            return jsonify({'success': False, 'message': '仅支持Excel和CSV文件'})

        # 保存文件
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, f'a500_{file_id}{file_ext}')
        file.save(file_path)

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file.filename,
            'message': '文件上传成功'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@app.route('/api/calculate', methods=['POST'])
def calculate_score():
    """计算评分"""
    try:
        data = request.json
        file_id = data.get('file_id')
        if not file_id:
            return jsonify({'success': False, 'message': '缺少文件ID'})

        # 找到文件
        file_path = None
        for ext in ['.xlsx', '.csv']:
            temp_path = os.path.join(UPLOAD_DIR, f'a500_{file_id}{ext}')
            if os.path.exists(temp_path):
                file_path = temp_path
                break

        if not file_path:
            return jsonify({'success': False, 'message': '文件不存在'})

        # 处理文件
        result_df = process_file(file_path)

        if result_df is None or result_df.empty:
            return jsonify({'success': False, 'message': '文件处理失败，没有有效数据'})

        # 生成结果文件
        result_file_id = str(uuid.uuid4())
        result_file_path = os.path.join(OUTPUT_DIR, f'a500_result_{result_file_id}.csv')
        result_df.to_csv(result_file_path, index=False, encoding='utf-8-sig')

        # 生成预览数据（前10条）
        preview_data = result_df.head(10).to_dict('records')

        return jsonify({
            'success': True,
            'result_id': result_file_id,
            'preview': preview_data,
            'total_count': len(result_df),
            'message': '评分计算完成'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'计算失败: {str(e)}'})

@app.route('/api/download/<result_id>', methods=['GET'])
def download_result(result_id):
    """下载结果文件"""
    try:
        result_file_path = os.path.join(OUTPUT_DIR, f'a500_result_{result_id}.csv')
        if not os.path.exists(result_file_path):
            return jsonify({'success': False, 'message': '结果文件不存在'})

        return send_file(
            result_file_path,
            as_attachment=True,
            download_name='打分明细.csv',
            mimetype='text/csv'
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'})

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'success': True, 'message': '服务正常'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)