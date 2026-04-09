#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试借阅请求修复脚本
"""

import sqlite3
from datetime import datetime

def test_loan_requests():
    """测试借阅请求功能"""
    db_path = 'library.db'

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("检查 loan_requests 表是否存在...")

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='loan_requests'")
        table_exists = cursor.fetchone()
        if not table_exists:
            print("❌ loan_requests 表不存在")
            return
        else:
            print("✅ loan_requests 表存在")

        print("\n检查 loan_requests 表中的记录...")

        # 查询所有借阅请求
        cursor.execute('''
            SELECT COUNT(*) FROM loan_requests
        ''')

        total_count = cursor.fetchone()[0]
        print(f"loan_requests 表总记录数: {total_count}")

        if total_count == 0:
            print("表中没有记录，创建一些测试数据...")

            # 检查是否有用户和图书
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM books")
            book_count = cursor.fetchone()[0]

            print(f"用户数量: {user_count}, 图书数量: {book_count}")

            if user_count > 0 and book_count > 0:
                # 获取第一个用户和图书
                cursor.execute("SELECT id FROM users LIMIT 1")
                user_id = cursor.fetchone()[0]
                cursor.execute("SELECT id FROM books WHERE available_copies > 0 LIMIT 1")
                book_id = cursor.fetchone()[0]

                # 创建一个测试借阅请求
                cursor.execute('''
                    INSERT INTO loan_requests (user_id, book_id, status, pickup_code)
                    VALUES (?, ?, 'approved', 'TEST123')
                ''', (user_id, book_id))

                conn.commit()
                print("✅ 创建了测试借阅请求")

        # 重新查询
        cursor.execute('''
            SELECT lr.id, lr.user_id, lr.book_id, lr.status, lr.pickup_code, lr.pickup_confirmed,
                   b.title, u.username
            FROM loan_requests lr
            LEFT JOIN books b ON lr.book_id = b.id
            LEFT JOIN users u ON lr.user_id = u.id
            ORDER BY lr.request_date DESC
            LIMIT 10
        ''')

        requests = cursor.fetchall()

        print(f"\n找到 {len(requests)} 条借阅请求记录：")
        for req in requests:
            print(f"ID: {req[0]}, 用户: {req[7] or 'N/A'}, 图书: {req[6] or 'N/A'}, 状态: {req[3]}, 取货码: {req[4] or '无'}, 已取货: {req[5]}")

        conn.close()

    except Exception as e:
        print(f"数据库查询错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_loan_requests()