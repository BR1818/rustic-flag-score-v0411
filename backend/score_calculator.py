#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A500活动评分计算模块
"""

import pandas as pd
from datetime import datetime

# 活动关键时间节点
ACTIVITY_START = datetime(2026, 3, 13, 10, 0, 0)
ACTIVITY_END = datetime(2026, 4, 17, 14, 0, 0)
TOTAL_HOURS = (ACTIVITY_END - ACTIVITY_START).total_seconds() / 3600

def calculate_like_score(like_count):
    """计算点赞数量得分（10分）"""
    if pd.isna(like_count):
        like_count = 0
    base_score = 5
    increment_score = min(like_count, 15)
    raw_score = min(base_score + increment_score, 20)
    like_score = raw_score * 0.5  # 映射到10分满分
    return round(like_score, 2)

def calculate_reply_score(reply_count):
    """计算回帖数量得分（10分）"""
    if pd.isna(reply_count):
        reply_count = 0
    base_score = 5
    increment_score = min(reply_count * 0.5, 15)
    raw_score = min(base_score + increment_score, 20)
    reply_score = raw_score * 0.5  # 映射到10分满分
    return round(reply_score, 2)

def calculate_content_score(content, has_topic, content_length):
    """计算内容质量得分（30分）"""
    word_score = 0
    topic_score = 0
    depth_score = 0
    compliance_score = 5
    originality_score = 5

    if pd.isna(content_length) or content_length == 0:
        word_score = 0
    elif content_length >= 15:
        word_score = 5
    else:
        word_score = max(0, (content_length // 5) * 1)

    if pd.notna(has_topic) and has_topic:
        topic_score = 5
    elif pd.notna(has_topic) and str(has_topic).strip():
        topic_score = 2
    else:
        topic_score = 0

    if pd.notna(content) and content:
        content_str = str(content)
        if len(content_str) >= 50 and any(keyword in content_str for keyword in ['A500', '指数增强', '量化', '投资', '策略', '鹏扬']):
            depth_score = 10
        elif len(content_str) >= 30:
            depth_score = 8
        elif len(content_str) >= 15:
            depth_score = 6
        else:
            depth_score = 3
    else:
        depth_score = 0

    content_quality_score = word_score + topic_score + depth_score + compliance_score + originality_score
    return round(content_quality_score, 2)

def check_topic_in_content(content):
    """检查内容中是否包含话题标签"""
    if pd.isna(content):
        return False
    content_str = str(content)
    topic_keywords = ['#把握轮动机遇', '优选指数增强']
    return any(keyword in content_str for keyword in topic_keywords)

def calculate_sharing_score(post_tool):
    """计算晒操作/晒收益得分（30分）"""
    if pd.isna(post_tool):
        return 0

    post_tool_str = str(post_tool)
    screenshot_score = 15 if '晒收益' in post_tool_str else 0
    operation_score = 10 if '晒操作' in post_tool_str else 0
    prediction_score = 5 if '猜走势' in post_tool_str else 0

    total_raw = screenshot_score + operation_score + prediction_score
    sharing_score = min(total_raw, 30)
    return round(sharing_score, 2)

def calculate_time_score(submit_time_str):
    """计算留言时间得分（20分）"""
    try:
        if pd.isna(submit_time_str):
            return 0
        submit_time = pd.to_datetime(submit_time_str)
        hours_from_end = (ACTIVITY_END - submit_time).total_seconds() / 3600
        if hours_from_end < 0:
            hours_from_end = 0
        time_score = (hours_from_end / TOTAL_HOURS) * 20  # 直接计算20分满分
        return round(time_score, 2)
    except:
        return 0

def process_user_posts(user_data):
    """处理同一用户的多个帖子"""
    if len(user_data) == 0:
        return {}

    # 1. 点赞数量：所有帖子加和
    total_likes = user_data['点赞数'].sum()
    like_score = calculate_like_score(total_likes)

    # 2. 回帖数量：所有帖子加和
    total_replies = user_data['评论数'].sum()
    reply_score = calculate_reply_score(total_replies)

    # 3. 留言时间：取最早的发帖时间
    earliest_time = user_data['发帖时间'].min()
    time_score = calculate_time_score(earliest_time)

    # 4. 内容质量：取最高的一条
    max_content_score = 0
    best_content = None
    for _, post in user_data.iterrows():
        content = post.get('帖子摘要', '')
        content_length = len(str(content)) if pd.notna(content) else 0
        has_topic = check_topic_in_content(content)
        content_score = calculate_content_score(content, has_topic, content_length)
        if content_score > max_content_score:
            max_content_score = content_score
            best_content = content

    # 5. 晒操作/晒收益：所有帖子加和（上限30分）
    total_sharing = 0
    for _, post in user_data.iterrows():
        post_tool = post.get('发帖工具', '')
        sharing_score = calculate_sharing_score(post_tool)
        total_sharing += sharing_score
    total_sharing = min(total_sharing, 30)

    return {
        '总点赞数': total_likes,
        '总评论数': total_replies,
        '最早发帖时间': earliest_time,
        '最佳内容': best_content,
        '点赞数量得分': like_score,
        '回帖数量得分': reply_score,
        '留言时间得分': time_score,
        '内容质量得分': max_content_score,
        '晒操作/晒收益得分': total_sharing,
        '总分': round(like_score + reply_score + time_score + max_content_score + total_sharing, 2)
    }

def process_file(file_path):
    """处理上传的文件并计算评分"""
    try:
        # 读取文件
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            raise ValueError("不支持的文件格式")

        # 确保必要的列存在
        required_columns = ['发帖人', '发帖时间', '评论数', '点赞数', '发帖工具', '帖子摘要']
        for col in required_columns:
            if col not in df.columns:
                # 尝试映射常见的列名变体
                if col == '发帖人':
                    for alt in ['用户名称', '用户名', '昵称']:
                        if alt in df.columns:
                            df = df.rename(columns={alt: '发帖人'})
                            break
                elif col == '评论数':
                    for alt in ['回帖数', '回复数']:
                        if alt in df.columns:
                            df = df.rename(columns={alt: '评论数'})
                            break
                elif col == '点赞数':
                    for alt in ['点赞数量']:
                        if alt in df.columns:
                            df = df.rename(columns={alt: '点赞数'})
                            break
                elif col == '发帖时间':
                    for alt in ['时间', '提交时间', '发言时间']:
                        if alt in df.columns:
                            df = df.rename(columns={alt: '发帖时间'})
                            break
                elif col == '帖子摘要':
                    for alt in ['内容', '发言内容', '帖子内容']:
                        if alt in df.columns:
                            df = df.rename(columns={alt: '帖子摘要'})
                            break

        # 按用户分组
        user_groups = df.groupby('发帖人')

        results = []

        for user_name, user_data in user_groups:
            user_result = process_user_posts(user_data)
            if user_result:
                user_result['用户名称'] = user_name
                user_result['发帖数'] = len(user_data)
                results.append(user_result)

        result_df = pd.DataFrame(results)

        if not result_df.empty:
            result_df = result_df.sort_values(by='总分', ascending=False)
            result_df['排名'] = range(1, len(result_df) + 1)

            cols_order = ['排名', '用户名称', '发帖数', '总分', '点赞数量得分', '回帖数量得分', '留言时间得分',
                          '内容质量得分', '晒操作/晒收益得分', '总点赞数', '总评论数', '最早发帖时间', '最佳内容']
            result_df = result_df[cols_order]

        return result_df

    except Exception as e:
        raise Exception(f"文件处理失败: {str(e)}")