#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新获取指定图书的封面
"""

import sqlite3
import os
import sys

# 添加当前目录到Python路径
sys.path.append('.')

from app_simple import fetch_book_cover, get_cover_path


def refresh_book_cover(book_title):
    """
    重新获取指定图书的封面
    
    Args:
        book_title: 图书标题
    """
    print(f"开始重新获取图书封面: {book_title}")
    
    # 如果数据库中有ISBN，可用于精确查询
    isbn = None
    try:
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        cursor.execute('SELECT isbn FROM books WHERE title LIKE ? LIMIT 1', (f'%{book_title}%',))
        row = cursor.fetchone()
        if row and row[0]:
            isbn = row[0]
        conn.close()
    except Exception as e:
        print(f"查询ISBN时出错: {e}")

    # 获取封面信息（优先使用ISBN）
    book_info = fetch_book_cover(book_title, isbn=isbn)
    if not book_info:
        print(f"❌ 获取封面信息失败: {book_title}")
        return
    
    print(f"✅ 获取封面信息成功: {book_title}")
    print(f"封面URL: {book_info.get('cover_url', '无')}")
    
    # 下载并保存封面
    cover_url = book_info.get('cover_url', '')
    cover_local_path = get_cover_path(book_title, cover_url)
    
    if cover_local_path:
        print(f"✅ 封面保存成功: {cover_local_path}")
        
        # 更新数据库中的封面路径
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE books SET cover_image = ? WHERE title LIKE ?',
            (cover_local_path, f'%{book_title}%')
        )
        
        conn.commit()
        print(f"✅ 数据库更新成功，影响行数: {cursor.rowcount}")
        
        conn.close()
    else:
        print(f"❌ 封面保存失败: {book_title}")


if __name__ == '__main__':
    book_title = "Python编程：从入门到实践"
    refresh_book_cover(book_title)
