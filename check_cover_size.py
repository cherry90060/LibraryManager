#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查封面图片文件的大小
"""

import os


def check_cover_size(cover_path):
    """
    检查封面图片文件的大小
    
    Args:
        cover_path: 封面图片文件路径
    """
    if os.path.exists(cover_path):
        size = os.path.getsize(cover_path)
        print(f'文件大小: {size} 字节')
        if size < 1000:
            print('⚠️  文件大小可能过小，可能不是有效的图片文件')
        else:
            print('✅ 文件大小正常')
    else:
        print('❌ 文件不存在')


if __name__ == '__main__':
    cover_path = 'static/book_covers/308f0f7b850d31ba60eddc744b14daba.jpg'
    check_cover_size(cover_path)
