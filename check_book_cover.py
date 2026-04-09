#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查指定图书的封面图片路径
"""

import sqlite3
import os


def check_book_cover(book_title):
    """
    检查指定图书的封面图片路径
    
    Args:
        book_title: 图书标题
    """
    # 连接数据库
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # 查询指定图书的封面图片路径
    cursor.execute('SELECT id, title, cover_image FROM books WHERE title LIKE ?', (f'%{book_title}%',))
    books = cursor.fetchall()
    
    print(f"查找图书: {book_title}")
    print("-" * 100)
    
    if books:
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
    else:
        print(f"❌ 未找到图书: {book_title}")
    
    # 关闭数据库连接
    conn.close()


if __name__ == '__main__':
    book_title = "Python编程：从入门到实践"
    check_book_cover(book_title)
