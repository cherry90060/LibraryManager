#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看当前数据库中的书籍
"""

import sqlite3

DATABASE = 'library.db'

def view_current_books():
    """查看当前书籍"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    books = cursor.execute('SELECT id, title, author, category, total_copies, available_copies FROM books ORDER BY title').fetchall()
    
    print("📚 当前数据库中的书籍：")
    print("-" * 80)
    
    for book in books:
        book_id, title, author, category, total_copies, available_copies = book
        print(f"ID: {book_id:2d} | {title[:40]:<40} | {author[:20]:<20} | {category:<15} | {total_copies}/{available_copies}")
    
    print(f"\n总计：{len(books)} 本书")
    
    # 查看分类统计
    categories = cursor.execute('SELECT category, COUNT(*) FROM books GROUP BY category').fetchall()
    print("\n📊 分类统计：")
    for category, count in categories:
        print(f"  {category}: {count} 本")
    
    conn.close()

if __name__ == "__main__":
    view_current_books()