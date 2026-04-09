#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的封面图片路径
"""

import sqlite3
import os


def check_cover_images():
    """
    检查数据库中的封面图片路径
    """
    # 连接数据库
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # 查询前5本书的封面图片路径
    cursor.execute('SELECT id, title, cover_image FROM books LIMIT 5')
    books = cursor.fetchall()
    
    print("前5本书的封面图片路径:")
    print("-" * 100)
    
    for book in books:
        book_id, title, cover_image = book
        print(f"ID: {book_id} | 书名: {title} | 封面路径: {cover_image}")
        
        # 检查封面图片文件是否存在
        if cover_image:
            cover_path = os.path.join('static', cover_image)
            if os.path.exists(cover_path):
                print(f"  ✅ 封面文件存在: {cover_path}")
            else:
                print(f"  ❌ 封面文件不存在: {cover_path}")
        else:
            print(f"  ❌ 未设置封面路径")
        
        print()
    
    # 关闭数据库连接
    conn.close()


if __name__ == '__main__':
    check_cover_images()
