#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A500活动评分工具后端 - Vercel Serverless Version
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app, supports_credentials=True)

ACTIVITY_START = datetime(2026, 3, 13, 10, 0, 0)
ACTIVITY_END = datetime(2026, 4, 17, 14, 0, 0)
TOTAL_HOURS = (ACTIVITY_END - ACTIVITY_START).total_seconds() / 3600


def calculate_like_score(like_count):
    if like_count is None:
        like_count = 0
    base_score = 5
    increment_score = min(like_count, 15)
    raw_score = min(base_score + increment_score, 20)
    return round(raw_score * 0.5, 2)


def calculate_reply_score(reply_count):
    if reply_count is None:
        reply_count = 0
    base_score = 5
    increment_score = min(reply_count * 0.5, 15)
    raw_score = min(base_score + increment_score, 20)
    return round(raw_score * 0.5, 2)


def calculate_content_score(content, has_topic, content_length):
    word_score = topic_score = depth_score = 0
    compliance_score = originality_score = 5

    if content_length is not None and content_length >= 15:
        word_score = 5
    elif content_length is not None:
        word_score = max(0, (content_length // 5) * 1)

    if has_topic:
        topic_score = 5

    if content and len(str(content)) >= 15:
        depth_score = 6
        if len(str(content)) >= 50:
            depth_score = 10

    return round(word_score + topic_score + depth_score + compliance_score + originality_score, 2)


def check_topic(content):
    if not content:
        return False
    return '#把握轮动机遇' in str(content) or '优选指数增强' in str(content)


def calculate_sharing_score(post_tool):
    if not post_tool:
        return 0
    score = 0
    if '晒收益' in str(post_tool):
        score += 15
    if '晒操作' in str(post_tool):
        score += 10
    if '猜走势' in str(post_tool):
        score += 5
    return min(score, 30)


def calculate_time_score(submit_time):
    try:
        if submit_time is None:
            return 0
        submit_dt = pd.to_datetime(submit_time)
        hours_from_end = (ACTIVITY_END - submit_dt).total_seconds() / 3600
        if hours_from_end < 0:
            hours_from_end = 0
        return round((hours_from_end / TOTAL_HOURS) * 20, 2)
    except:
        return 0


def process_file(file_content):
    try:
        if file_content.startswith(b'PK'):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            df = pd.read_csv(io.BytesIO(file_content))

        col_mapping = {'用户名称': '发帖人', '用户名': '发帖人', '回帖数': '评论数',
                       '回复数': '评论数', '时间': '发帖时间', '提交时间': '发帖时间'}
        df = df.rename(columns=col_mapping)

        user_groups = df.groupby('发帖人')
        results = []

        for user_name, user_data in user_groups:
            total_likes = user_data['点赞数'].sum()
            total_replies = user_data['评论数'].sum()
            earliest_time = user_data['发帖时间'].min()

            best_content_score = 0
            for _, post in user_data.iterrows():
                content = post.get('帖子摘要', '')
                content_length = len(str(content)) if content else 0
                has_topic = check_topic(content)
                score = calculate_content_score(content, has_topic, content_length)
                if score > best_content_score:
                    best_content_score = score

            total_sharing = 0
            for _, post in user_data.iterrows():
                post_tool = post.get('发帖工具', '')
                total_sharing += calculate_sharing_score(post_tool)
            total_sharing = min(total_sharing, 30)

            like_score = calculate_like_score(total_likes)
            reply_score = calculate_reply_score(total_replies)
            time_score = calculate_time_score(earliest_time)
            total = round(like_score + reply_score + time_score + best_content_score + total_sharing, 2)

            results.append({
                '用户名称': user_name,
                '发帖数': len(user_data),
                '总分': total,
                '点赞数量得分': like_score,
                '回帖数量得分': reply_score,
                '留言时间得分': time_score,
                '内容质量得分': best_content_score,
                '晒操作/晒收益得分': total_sharing
            })

        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values(by='总分', ascending=False)
        result_df['排名'] = range(1, len(result_df) + 1)

        cols_order = ['排名', '用户名称', '发帖数', '总分', '点赞数量得分', '回帖数量得分',
                      '留言时间得分', '内容质量得分', '晒操作/晒收益得分']
        result_df = result_df[cols_order]

        return result_df

    except Exception as e:
        raise Exception(f"文件处理失败: {str(e)}")


@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择文件'})

        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'message': '请选择文件'})

        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.csv')):
            return jsonify({'success': False, 'message': '仅支持Excel和CSV文件'})

        file_content = file.read()
        result_df = process_file(file_content)

        if result_df is None or result_df.empty:
            return jsonify({'success': False, 'message': '文件处理失败'})

        preview_data = result_df.head(10).to_dict('records')
        result_csv = result_df.to_csv(index=False, encoding='utf-8-sig')

        return jsonify({
            'success': True,
            'preview': preview_data,
            'total_count': len(result_df),
            'result_csv': result_csv,
            'message': '评分计算完成'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'计算失败: {str(e)}'})


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'message': '服务正常'})


handler = app