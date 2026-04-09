#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建消息表脚本
"""

import sqlite3

def create_message_table():
    """创建消息表"""
    # 连接数据库
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    try:
        # 创建消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_is_read ON messages (is_read)')
        
        conn.commit()
        print("消息表创建成功")
        
    except Exception as e:
        print(f"创建消息表时出错: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    create_message_table()
