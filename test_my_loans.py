#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 my_loans 修复脚本
"""

import sqlite3

def test_my_loans_logic():
    """测试 my_loans 函数的逻辑"""
    db_path = 'library.db'

    print("开始测试 my_loans 逻辑...")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("连接数据库成功")

        # 检查用户表
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"用户总数: {user_count}")

        # 检查借阅请求表
        cursor.execute("SELECT COUNT(*) FROM loan_requests")
        request_count = cursor.fetchone()[0]
        print(f"借阅请求总数: {request_count}")

        # 模拟 session['user_id'] = 某个用户ID
        # 首先获取一个有借阅请求的用户ID
        cursor.execute('''
            SELECT DISTINCT user_id FROM loan_requests
            WHERE status IN ('pending', 'approved')
            LIMIT 1
        ''')
        user_result = cursor.fetchone()

        if not user_result:
            print("没有找到有借阅请求的用户")
            return

        user_id = user_result[0]
        print(f"测试用户ID: {user_id}")

        # 模拟 my_loans 函数的查询
        print("\n=== 测试借阅请求查询 ===")
        requests = cursor.execute('''
            SELECT lr.*, b.title
            FROM loan_requests lr
            JOIN books b ON lr.book_id = b.id
            WHERE lr.user_id = ? AND (lr.status = 'pending' OR lr.status = 'approved')
            ORDER BY lr.request_date DESC
        ''', (user_id,)).fetchall()

        print(f"找到 {len(requests)} 条借阅请求:")
        for req in requests:
            print(f"  ID: {req[0]}, 图书: {req[9]}, 状态: {req[4]}, 取货码: {req[8] or '无'}")

        print("\n=== 测试借阅记录查询 ===")
        loans = cursor.execute('''
            SELECT l.*, b.title, b.author, b.isbn
            FROM loans l
            JOIN books b ON l.book_id = b.id
            WHERE l.user_id = ?
            ORDER BY l.loan_date DESC
        ''', (user_id,)).fetchall()

        print(f"找到 {len(loans)} 条借阅记录:")
        for loan in loans:
            print(f"  ID: {loan[0]}, 图书: {loan[8]}, 取货码: {loan[6] or '无'}, 已取货: {loan[7]}")

        conn.close()
        print("\n测试完成")

    except Exception as e:
        print(f"测试错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_my_loans_logic()

if __name__ == "__main__":
    test_my_loans_logic()