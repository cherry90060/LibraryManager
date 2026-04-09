#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新所有图书的封面图片
"""

import sqlite3
import os
import sys
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_simple import get_db, fetch_book_cover, get_cover_path


def update_all_book_covers():
    """
    更新所有图书的封面图片
    """
    db = get_db()
    
    # 获取所有图书及ISBN
    cursor = db.execute('SELECT id, title, isbn FROM books')
    books = cursor.fetchall()
    
    total_books = len(books)
    print(f"开始更新 {total_books} 本图书的封面图片...")
    
    success_count = 0
    failure_count = 0
    
    for i, book in enumerate(books, 1):
        book_id, book_title, book_isbn = book
        print(f"\n[{i}/{total_books}] 处理图书: {book_title}")
        
        try:
            # 获取图书封面信息
            # 优先使用ISBN查找
            book_info = fetch_book_cover(book_title, isbn=book_isbn if book_isbn else None)
            
            if book_info:
                cover_url = book_info.get('cover_url', '')
                if cover_url:
                    # 下载并保存封面图片
                    cover_local_path = get_cover_path(book_title, cover_url)
                    
                    if cover_local_path:
                        # 更新数据库中的封面路径
                        db.execute('''
                            UPDATE books 
                            SET cover_image = ? 
                            WHERE id = ?
                        ''', (cover_local_path, book_id))
                        db.commit()
                        
                        print(f"✅ 成功更新封面: {book_title}")
                        success_count += 1
                    else:
                        print(f"❌ 封面下载失败: {book_title}")
                        failure_count += 1
                else:
                    print(f"❌ 未找到封面图片: {book_title}")
                    failure_count += 1
            else:
                print(f"❌ 未找到图书信息: {book_title}")
                failure_count += 1
        except Exception as e:
            print(f"❌ 处理失败: {book_title}, 错误: {str(e)}")
            failure_count += 1
    
    print(f"\n更新完成！")
    print(f"成功: {success_count} 本")
    print(f"失败: {failure_count} 本")


if __name__ == '__main__':
    from app_simple import app
    
    with app.app_context():
        update_all_book_covers()
