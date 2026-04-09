#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

DATABASE = 'library.db'

def cleanup_duplicate_books():
    """清理重复的书籍记录"""
    
    print("🧹 开始清理重复书籍...")
    
    # 连接数据库
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # 1. 找出所有重复的书籍标题
    cursor.execute('''
        SELECT title, COUNT(*) as count, GROUP_CONCAT(id) as ids
        FROM books 
        GROUP BY title 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    ''')
    
    duplicate_groups = cursor.fetchall()
    
    if not duplicate_groups:
        print("✅ 没有发现重复书籍！")
        conn.close()
        return
    
    print(f"📚 发现 {len(duplicate_groups)} 组重复书籍：")
    total_removed = 0
    total_preserved = 0
    
    for title, count, ids_str in duplicate_groups:
        ids = [int(id_str) for id_str in ids_str.split(',')]
        print(f"\n📖 书籍: {title}")
        print(f"   重复数量: {count} 本 (ID: {ids})")
        
        # 获取所有重复记录的信息
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'''
            SELECT id, total_copies, available_copies, author, category, description, isbn
            FROM books WHERE id IN ({placeholders})
        ''', ids)
        
        records = cursor.fetchall()
        print(f"   详细信息:")
        for record in records:
            book_id, total, available, author, category, description, isbn = record
            print(f"     ID:{book_id} | 总数:{total} | 可借:{available} | 作者:{author}")
        
        # 合并所有副本数量到第一个记录
        first_record = records[0]
        first_id = first_record[0]
        total_copies_sum = sum(record[1] for record in records)  # total_copies
        available_copies_sum = sum(record[2] for record in records)  # available_copies
        
        print(f"   ✅ 保留 ID:{first_id}，合并副本: 总数{total_copies_sum}, 可借{available_copies_sum}")
        
        # 更新保留记录的副本数量
        cursor.execute('''
            UPDATE books 
            SET total_copies = ?, available_copies = ?
            WHERE id = ?
        ''', (total_copies_sum, available_copies_sum, first_id))
        
        total_preserved += 1
        
        # 删除其他重复记录（除了第一个）
        duplicate_ids = ids[1:]
        placeholders = ','.join('?' * len(duplicate_ids))
        cursor.execute(f'DELETE FROM books WHERE id IN ({placeholders})', duplicate_ids)
        
        removed_count = len(duplicate_ids)
        total_removed += removed_count
        print(f"   🗑️  删除 {removed_count} 个重复记录")
        
        # 提交这个组的处理
        conn.commit()
    
    print(f"\n🎉 清理完成！")
    print(f"   📊 统计结果:")
    print(f"   - 保留书籍: {total_preserved} 本")
    print(f"   - 删除重复: {total_removed} 本")
    print(f"   - 节省空间: {total_removed} 条记录")
    
    # 显示清理后的统计信息
    total_books = cursor.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    
    # 按分类统计
    cursor.execute('''
        SELECT category, COUNT(*) as count, SUM(total_copies) as total_copies
        FROM books 
        GROUP BY category 
        ORDER BY count DESC
    ''')
    
    categories = cursor.fetchall()
    
    print(f"\n📈 清理后的数据库统计:")
    print(f"   总书籍数量: {total_books} 本")
    print(f"\n📚 分类统计:")
    for category, count, total_copies in categories:
        print(f"   {category}: {count} 本 (总副本: {total_copies})")
    
    conn.close()
    print(f"\n✅ 数据库清理完成！")

if __name__ == '__main__':
    cleanup_duplicate_books()