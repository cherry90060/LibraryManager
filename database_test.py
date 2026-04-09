#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图书馆管理系统数据库连接测试脚本
用于验证SQLite数据库连接和基本查询功能
"""

import sqlite3
import os
from datetime import datetime

def test_database_connection():
    """测试数据库连接"""
    db_path = 'library.db'
    
    print("=" * 60)
    print("🏛️ 图书馆管理系统数据库连接测试")
    print("=" * 60)
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"❌ 错误：数据库文件不存在 - {db_path}")
        return False
    
    print(f"✅ 数据库文件存在：{db_path}")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("✅ 数据库连接成功！")
        
        # 获取数据库信息
        cursor.execute("SELECT sqlite_version()")
        db_version = cursor.fetchone()[0]
        print(f"📊 SQLite版本：{db_version}")
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 数据表数量：{len(tables)}")
        
        table_names = [table[0] for table in tables]
        print(f"📋 数据表列表：{', '.join(table_names)}")
        
        # 测试基本查询
        print("\n" + "=" * 40)
        print("📊 数据统计")
        print("=" * 40)
        
        # 用户统计
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👤 用户总数：{user_count}")
        
        # 管理员统计
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        print(f"👑 管理员数量：{admin_count}")
        
        # 图书统计
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        print(f"📚 图书总数：{book_count}")
        
        # 借阅统计
        cursor.execute("SELECT COUNT(*) FROM loans")
        loan_count = cursor.fetchone()[0]
        print(f"🔄 借阅记录总数：{loan_count}")
        
        # 当前借阅
        cursor.execute("SELECT COUNT(*) FROM loans WHERE is_returned = 0")
        active_loans = cursor.fetchone()[0]
        print(f"📖 当前借阅：{active_loans}")
        
        # 显示用户列表（密码已哈希）
        print("\n" + "=" * 40)
        print("👥 用户列表")
        print("=" * 40)
        cursor.execute("SELECT username, email, is_admin, created_at FROM users")
        users = cursor.fetchall()
        
        for user in users:
            role = "管理员" if user[2] else "普通用户"
            print(f"• {user[0]} ({user[1]}) - {role} - {user[3]}")
        
        # 显示图书列表
        print("\n" + "=" * 40)
        print("📚 图书列表")
        print("=" * 40)
        cursor.execute("SELECT title, author, category, total_copies, available_copies FROM books ORDER BY title")
        books = cursor.fetchall()
        
        for book in books:
            status = "可借" if book[4] > 0 else "无库存"
            print(f"• {book[0]} - {book[1]} ({book[2]}) - 总量:{book[3]} 可借:{book[4]} [{status}]")
        
        # 显示最近借阅记录
        print("\n" + "=" * 40)
        print("📖 借阅记录")
        print("=" * 40)
        cursor.execute("""
            SELECT u.username, b.title, l.loan_date, l.due_date, l.is_returned
            FROM loans l
            JOIN users u ON l.user_id = u.id
            JOIN books b ON l.book_id = b.id
            ORDER BY l.loan_date DESC
            LIMIT 10
        """)
        loans = cursor.fetchall()
        
        for loan in loans:
            status = "已归还" if loan[4] else "借阅中"
            print(f"• {loan[0]} 借阅《{loan[1]}》 - {loan[2]} (应还:{loan[3]}) [{status}]")
        
        # 数据库完整性检查
        print("\n" + "=" * 40)
        print("🔍 数据完整性检查")
        print("=" * 40)
        
        # 检查孤儿借阅记录
        cursor.execute("""
            SELECT COUNT(*) FROM loans l 
            LEFT JOIN users u ON l.user_id = u.id 
            WHERE u.id IS NULL
        """)
        orphan_loans = cursor.fetchone()[0]
        print(f"🔗 孤儿借阅记录：{orphan_loans} (应该为0)")
        
        # 检查库存一致性
        cursor.execute("""
            SELECT COUNT(*) FROM books 
            WHERE available_copies > total_copies OR available_copies < 0
        """)
        inventory_issues = cursor.fetchone()[0]
        print(f"📦 库存异常记录：{inventory_issues} (应该为0)")
        
        # 关闭连接
        conn.close()
        print("\n✅ 数据库连接测试完成！")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误：{e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误：{e}")
        return False

def show_table_schemas():
    """显示所有表的结构"""
    db_path = 'library.db'
    
    print("\n" + "=" * 60)
    print("🏗️ 数据库表结构")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"\n📋 表名：{table_name}")
            print("-" * 40)
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                print(f"  • {col[1]} {col[2]} {'(PK)' if col[5] else ''}")
            
            # 获取表数据示例
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            
            if rows:
                print(f"  📊 示例数据 ({len(rows)} 条记录)：")
                for row in rows:
                    print(f"    {row}")
            else:
                print(f"  📭 表为空")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ 数据库错误：{e}")

if __name__ == "__main__":
    # 运行连接测试
    success = test_database_connection()
    
    if success:
        # 显示表结构
        show_table_schemas()
        
        print("\n" + "=" * 60)
        print("🎉 测试完成！数据库连接正常，可以进行SQLTools配置")
        print("=" * 60)
        print("📝 建议配置步骤：")
        print("1. 打开VS Code")
        print("2. 安装SQLTools插件")
        print("3. 添加SQLite连接，文件路径：c:\\Users\\27970\\Documents\\trae_projects\\demo\\LibraryManager\\library.db")
        print("4. 连接名称：图书馆管理系统")
    else:
        print("\n❌ 测试失败，请检查数据库文件")