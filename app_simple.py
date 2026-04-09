#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LibraryManager - 智慧图书馆管理系统
使用Python内置sqlite3数据库，避免版本兼容性问题
"""

import sqlite3
import hashlib  # 仅用于兼容旧密码
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import base64
from io import BytesIO

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'library_management_system_secret_key_2024'
# 启用模板自动重新加载
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 数据库配置
DATABASE = 'library.db'

# 限流配置
RATE_LIMIT_PER_MINUTE = 60  # 每分钟最多60次请求

# 标准化返回格式
def standard_response(success=True, book_name='', cover_url='', cover_local_path='', book_info=None, error='', cache_hit=False):
    """
    标准化返回格式
    
    Args:
        success: 是否成功
        book_name: 书名
        cover_url: 封面URL
        cover_local_path: 本地存储路径
        book_info: 图书信息
        error: 错误信息
        cache_hit: 是否命中缓存
        
    Returns:
        标准化的响应字典
    """
    return {
        'success': success,
        'book_name': book_name,
        'cover_url': cover_url,
        'cover_local_path': cover_local_path,
        'book_info': book_info or {},
        'error': error,
        'cache_hit': cache_hit
    }

# 限流中间件
@app.before_request
def rate_limit():
    """
    限流中间件
    """
    # 跳过静态文件请求
    if request.path.startswith('/static/'):
        return
    
    # 跳过封面图片访问请求
    if request.path.startswith('/api/book/cover/image/'):
        return
    
    # 获取客户端IP
    client_ip = request.remote_addr or 'unknown'
    current_time = datetime.now()
    one_minute_ago = current_time - timedelta(minutes=1)
    
    # 记录请求
    db = get_db()
    try:
        db.execute('''
            INSERT INTO request_logs (client_ip, request_path)
            VALUES (?, ?)
        ''', (client_ip, request.path))
        db.commit()
    except Exception as e:
        print(f"记录请求日志时出错: {e}")
    
    # 统计1分钟内的请求次数
    try:
        count = db.execute('''
            SELECT COUNT(*) FROM request_logs 
            WHERE client_ip = ? AND request_time >= ?
        ''', (client_ip, one_minute_ago.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()[0]
        
        if count > RATE_LIMIT_PER_MINUTE:
            return jsonify(standard_response(
                success=False,
                error=f'请求过于频繁，请稍后再试。每分钟最多允许 {RATE_LIMIT_PER_MINUTE} 次请求。'
            )), 429
    except Exception as e:
        print(f"限流检查时出错: {e}")

def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_cache():
    """初始化缓存相关目录"""
    # 创建静态封面图片存储目录
    cover_dir = os.path.join(app.root_path, 'static', 'book_covers')
    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir)
        print(f"创建封面存储目录: {cover_dir}")


def clean_expired_cache():
    """清理过期的缓存数据"""
    db = get_db()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        deleted_count = db.execute('''
            DELETE FROM book_cover_cache 
            WHERE expire_at IS NOT NULL AND expire_at < ?
        ''', (current_time,)).rowcount
        db.commit()
        print(f"清理过期缓存: 删除了 {deleted_count} 条记录")
        return deleted_count
    except Exception as e:
        print(f"清理过期缓存时出错: {e}")
        return 0


def get_cache_by_book_name(book_name):
    """
    根据书名从缓存中获取封面信息
    
    Args:
        book_name: 书名
        
    Returns:
        缓存记录，如果不存在或已过期返回None
    """
    db = get_db()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cache = db.execute('''
            SELECT * FROM book_cover_cache 
            WHERE book_name = ? AND (expire_at IS NULL OR expire_at >= ?)
        ''', (book_name, current_time)).fetchone()
        
        if cache:
            return dict(cache)
        return None
    except Exception as e:
        print(f"从缓存中查询封面时出错: {e}")
        return None


def set_cache_by_book_name(book_name, cover_url, cover_local_path, book_info, expire_days=7):
    """
    根据书名设置封面缓存信息
    
    Args:
        book_name: 书名
        cover_url: 封面URL
        cover_local_path: 本地存储路径
        book_info: 图书信息
        expire_days: 过期天数，默认7天
        
    Returns:
        是否设置成功
    """
    db = get_db()
    expire_at = (datetime.now() + timedelta(days=expire_days)).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # 使用INSERT OR REPLACE来更新缓存
        db.execute('''
            INSERT OR REPLACE INTO book_cover_cache 
            (book_name, cover_url, cover_local_path, book_info, expire_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (book_name, cover_url, cover_local_path, book_info, expire_at))
        db.commit()
        print(f"缓存封面信息: {book_name}")
        return True
    except Exception as e:
        print(f"设置封面缓存时出错: {e}")
        return False


def delete_cache_by_book_name(book_name):
    """
    根据书名删除缓存
    
    Args:
        book_name: 书名
        
    Returns:
        是否删除成功
    """
    db = get_db()
    
    try:
        deleted_count = db.execute('''
            DELETE FROM book_cover_cache WHERE book_name = ?
        ''', (book_name,)).rowcount
        db.commit()
        print(f"删除缓存: {book_name}, 删除了 {deleted_count} 条记录")
        return deleted_count > 0
    except Exception as e:
        print(f"删除封面缓存时出错: {e}")
        return False


def create_session_with_retry():
    """
    创建带重试机制的requests会话
    
    Returns:
        带重试机制的requests会话对象
    """
    session = requests.Session()
    
    # 配置重试策略
    retry = Retry(
        total=3,  # 总重试次数
        status_forcelist=[429, 500, 502, 503, 504],  # 触发重试的状态码
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],  # 允许重试的方法
        backoff_factor=0.5,  # 退避因子
        respect_retry_after_header=True  # 尊重Retry-After头
    )
    
    # 配置适配器
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session



def fetch_book_info_from_google_books(book_name_or_query):
    """假定传入可以是书名也可以已格式化的查询（例如 "isbn:xxx"）。"""
    """
    从Google Books API获取图书信息
    
    Args:
        book_name: 书名
        
    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    session = create_session_with_retry()
    
    try:
        # 构建Google Books API请求URL
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": book_name_or_query,
            "maxResults": 5,
            "fields": "items(id,volumeInfo(title,authors,publisher,description,industryIdentifiers,imageLinks,printType))"
        }
        
        # 发送请求
        response = session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        
        if data.get("items"):
            for item in data["items"]:
                book = item["volumeInfo"]
                cover_url = book.get("imageLinks", {}).get("thumbnail", "")
                if cover_url:
                    isbn = ""
                    if book.get("industryIdentifiers"):
                        for identifier in book["industryIdentifiers"]:
                            if identifier["type"] == "ISBN_13":
                                isbn = identifier["identifier"]
                                break
                        if not isbn and book["industryIdentifiers"]:
                            isbn = book["industryIdentifiers"][0]["identifier"]
                    
                    book_info = {
                        "cover_url": cover_url.replace("zoom=1", "zoom=2"),
                        "title": book.get("title", ""),
                        "author": ", ".join(book.get("authors", [])),
                        "publisher": book.get("publisher", ""),
                        "summary": book.get("description", ""),
                        "isbn": isbn,
                        "price": "",
                        "pubdate": ""
                    }
                    return book_info
            
            book = data["items"][0]["volumeInfo"]
            isbn = ""
            if book.get("industryIdentifiers"):
                for identifier in book["industryIdentifiers"]:
                    if identifier["type"] == "ISBN_13":
                        isbn = identifier["identifier"]
                        break
                if not isbn and book["industryIdentifiers"]:
                    isbn = book["industryIdentifiers"][0]["identifier"]
            
            book_info = {
                "cover_url": book.get("imageLinks", {}).get("thumbnail", "").replace("zoom=1", "zoom=2"),
                "title": book.get("title", ""),
                "author": ", ".join(book.get("authors", [])),
                "publisher": book.get("publisher", ""),
                "summary": book.get("description", ""),
                "isbn": isbn,
                "price": "",
                "pubdate": ""
            }
            return book_info
        
        return None
    except Exception as e:
        print(f"从Google Books API获取图书信息时出错: {e}")
        return None


def fetch_book_info_from_open_library(book_name):
    """
    从Open Library API获取图书信息
    
    Args:
        book_name: 书名
        
    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    session = create_session_with_retry()
    
    try:
        # 构建Open Library API请求URL
        url = "https://openlibrary.org/search.json"
        params = {
            "q": book_name,
            "limit": 5
        }
        
        # 发送请求
        response = session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        
        if data.get("docs"):
            for doc in data["docs"]:
                isbn = ""
                if doc.get("isbn"):
                    isbn = doc["isbn"][0]
                
                cover_url = ""
                if isbn:
                    cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
                elif doc.get("cover_i"):
                    cover_url = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
                
                if cover_url:
                    book_info = {
                        "cover_url": cover_url,
                        "title": doc.get("title", ""),
                        "author": ", ".join(doc.get("author_name", [])),
                        "publisher": ", ".join(doc.get("publisher", [])),
                        "summary": doc.get("first_sentence", [""])[0] if doc.get("first_sentence") else "",
                        "isbn": isbn,
                        "price": "",
                        "pubdate": doc.get("publish_date", [""])[0] if doc.get("publish_date") else ""
                    }
                    return book_info
            
        return None
    except Exception as e:
        print(f"从Open Library API获取图书信息时出错: {e}")
        return None


def fetch_book_info_from_bookshop(book_name):
    """
    从Bookshop API获取图书信息
    
    Args:
        book_name: 书名
        
    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    session = create_session_with_retry()
    
    try:
        # 构建Bookshop API请求URL
        url = "https://api.bookshop.org/v1/books"
        params = {
            "q": book_name,
            "limit": 5
        }
        
        # 发送请求
        response = session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        
        if data.get("data"):
            for book in data["data"]:
                attributes = book.get("attributes", {})
                cover_url = attributes.get("cover_image", "")
                if cover_url:
                    book_info = {
                        "cover_url": cover_url,
                        "title": attributes.get("title", ""),
                        "author": attributes.get("author", ""),
                        "publisher": attributes.get("publisher", ""),
                        "summary": attributes.get("description", ""),
                        "isbn": attributes.get("isbn", ""),
                        "price": attributes.get("price", ""),
                        "pubdate": attributes.get("publication_date", "")
                    }
                    return book_info
            
        return None
    except Exception as e:
        print(f"从Bookshop API获取图书信息时出错: {e}")
        return None


def fetch_book_info_from_goodreads(book_name):
    """
    从Goodreads API获取图书信息
    
    Args:
        book_name: 书名
        
    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    session = create_session_with_retry()
    
    try:
        # 构建Goodreads API请求URL
        url = "https://www.goodreads.com/search.xml"
        params = {
            "q": book_name,
            "key": "wQ91Y85JZ1hXs8kDnG6A"
        }
        
        # 发送请求
        response = session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 解析XML响应
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # 查找书籍元素
        search_results = root.find(".//search_results")
        if search_results:
            for work in search_results.findall(".//work"):
                best_book = work.find(".//best_book")
                if best_book:
                    title = best_book.find(".//title").text if best_book.find(".//title") else ""
                    author = best_book.find(".//author/name").text if best_book.find(".//author/name") else ""
                    cover_url = best_book.find(".//image_url").text if best_book.find(".//image_url") else ""
                    
                    if cover_url:
                        book_info = {
                            "cover_url": cover_url,
                            "title": title,
                            "author": author,
                            "publisher": "",
                            "summary": "",
                            "isbn": "",
                            "price": "",
                            "pubdate": ""
                        }
                        return book_info
        
        return None
    except Exception as e:
        print(f"从Goodreads API获取图书信息时出错: {e}")
        return None


def fetch_book_info_from_douban(book_name_or_query):
    """豆瓣搜索同样接受ISBN作为关键词，直接传递即可。"""
    """
    从豆瓣API获取图书信息（国内接口）
    
    Args:
        book_name: 书名
        
    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    session = create_session_with_retry()
    
    try:
        # 构建豆瓣API请求URL
        url = "https://api.douban.com/v2/book/search"
        params = {
            "q": book_name_or_query,
            "count": 5
        }
        
        # 发送请求
        response = session.get(url, params=params, timeout=5)
        response.raise_for_status()
        
        # 解析响应
        data = response.json()
        
        if data.get("books"):
            for book in data["books"]:
                cover_url = book.get("image", "")
                if cover_url:
                    book_info = {
                        "cover_url": cover_url,
                        "title": book.get("title", ""),
                        "author": ", ".join(book.get("author", [])),
                        "publisher": book.get("publisher", ""),
                        "summary": book.get("summary", ""),
                        "isbn": book.get("isbn13", "") or book.get("isbn10", ""),
                        "price": book.get("price", ""),
                        "pubdate": book.get("pubdate", "")
                    }
                    return book_info
        
        return None
    except Exception as e:
        print(f"从豆瓣API获取图书信息时出错: {e}")
        return None


# helper to query by isbn

def fetch_book_info_by_isbn(isbn):
    """使用 ISBN 在各个服务中精确查找封面信息。
    返回与 fetch_* 函数兼容的 book_info。"""
    # google books isbn search
    session = create_session_with_retry()
    try:
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {"q": f"isbn:{isbn}"}
        resp = session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("items"):
            book = data["items"][0]["volumeInfo"]
            cover_url = book.get("imageLinks", {}).get("thumbnail", "")
            if cover_url:
                # extract isbn again
                isbn_found = ""
                if book.get("industryIdentifiers"):
                    for identifier in book["industryIdentifiers"]:
                        if identifier.get("type") in ("ISBN_13", "ISBN_10"):
                            isbn_found = identifier.get("identifier")
                            break
                return {
                    "cover_url": cover_url.replace("zoom=1", "zoom=2"),
                    "title": book.get("title", ""),
                    "author": ", ".join(book.get("authors", [])),
                    "publisher": book.get("publisher", ""),
                    "summary": book.get("description", ""),
                    "isbn": isbn_found or isbn,
                    "price": "",
                    "pubdate": ""
                }
    except Exception:
        pass

    # try Open Library isbn lookup
    try:
        url = "https://openlibrary.org/api/books"
        params = {"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"}
        resp = session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        key = f"ISBN:{isbn}"
        if key in data:
            info = data[key]
            cover = info.get("cover", {}).get("large") or info.get("cover", {}).get("medium") or info.get("cover", {}).get("small")
            return {
                "cover_url": cover or "",
                "title": info.get("title", ""),
                "author": ", ".join(a.get("name", "") for a in info.get("authors", [])),
                "publisher": ", ".join(p.get("name", "") for p in info.get("publishers", [])),
                "summary": info.get("notes", ""),
                "isbn": isbn,
                "price": "",
                "pubdate": info.get("publish_date", "")
            }
    except Exception:
        pass

    # no isbn result
    return None


def fetch_book_cover(book_name, isbn=None):
    """
    获取图书封面信息，支持多API源。
    优先使用 ISBN 精确查询，其次使用书名模糊查询。

    Args:
        book_name: 书名
        isbn: 可选的 ISBN 编号，优先用于查询

    Returns:
        图书信息字典，包含封面URL、书名、作者、出版社、简介等
    """
    # 如果传入了 isbn，则先尝试用 ISBN 查找
    if isbn:
        book_info = fetch_book_info_by_isbn(isbn)
        if book_info:
            return book_info
        else:
            print(f"ISBN 查询未命中，退回到名称搜索: {isbn}")

    # 否则或者 ISBN 查询失败，按照原有顺序使用书名模糊匹配
    book_info = fetch_book_info_from_douban(book_name)
    if not book_info:
        print(f"豆瓣API失败，尝试从Google Books API获取: {book_name}")
        book_info = fetch_book_info_from_google_books(book_name)
    if not book_info:
        print(f"Google Books API失败，尝试从Open Library API获取: {book_name}")
        book_info = fetch_book_info_from_open_library(book_name)
    if not book_info:
        print(f"Open Library API失败，尝试从Bookshop API获取: {book_name}")
        book_info = fetch_book_info_from_bookshop(book_name)
    if not book_info:
        print(f"Bookshop API失败，尝试从Goodreads API获取: {book_name}")
        book_info = fetch_book_info_from_goodreads(book_name)
    return book_info


def generate_unique_filename(book_name, cover_url):
    """
    生成唯一的文件名
    
    Args:
        book_name: 书名
        cover_url: 封面URL
        
    Returns:
        唯一的文件名
    """
    # 基于书名和URL生成MD5哈希
    combined = f"{book_name}_{cover_url}"
    hash_obj = hashlib.md5(combined.encode('utf-8'))
    hash_str = hash_obj.hexdigest()
    
    # 获取文件扩展名
    ext = os.path.splitext(cover_url)[1]
    if not ext:
        ext = ".jpg"  # 默认使用jpg扩展名
    
    # 生成文件名
    filename = f"{hash_str}{ext}"
    return filename


def download_and_save_cover(book_name, cover_url):
    """
    下载并保存封面图片
    
    Args:
        book_name: 书名
        cover_url: 封面URL
        
    Returns:
        本地存储路径，如果下载失败返回None
    """
    if not cover_url:
        return None
    
    # 创建封面存储目录
    cover_dir = os.path.join(app.root_path, 'static', 'book_covers')
    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir)
    
    # 生成唯一文件名
    filename = generate_unique_filename(book_name, cover_url)
    local_path = os.path.join(cover_dir, filename)
    
    # 检查文件是否已存在
    if os.path.exists(local_path):
        print(f"封面图片已存在: {local_path}")
        return f"book_covers/{filename}"
    
    # 下载图片
    session = create_session_with_retry()
    
    try:
        response = session.get(cover_url, timeout=10)
        response.raise_for_status()
        
        # 保存图片
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"封面图片已保存: {local_path}")
        return f"book_covers/{filename}"
    except Exception as e:
        print(f"下载封面图片时出错: {e}")
        return None


def create_default_cover():
    """
    创建默认封面图片
    
    Returns:
        默认封面图片的本地存储路径
    """
    # 创建封面存储目录
    cover_dir = os.path.join(app.root_path, 'static', 'book_covers')
    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir)
    
    # 默认封面文件名
    default_filename = "default_cover.jpg"
    default_path = os.path.join(cover_dir, default_filename)
    
    # 检查默认封面是否已存在
    if os.path.exists(default_path):
        return f"book_covers/{default_filename}"
    
    # 创建一个简单的默认封面（使用Base64编码的图片）
    # 这里使用一个简单的默认封面图片（300x450）
    default_cover_base64 = "iVBORw0KGgoAAAANSUhEUgAAASwAAACWCAYAAABkW7XSAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAABISURBVHgB7c8xDQAgDENwqC0A8T6eR5554D8GQQ1Q+8Jf1gAAAABJRU5ErkJggg=="
    
    try:
        # 解码Base64字符串
        image_data = base64.b64decode(default_cover_base64)
        
        # 保存图片
        with open(default_path, 'wb') as f:
            f.write(image_data)
        
        print(f"默认封面图片已创建: {default_path}")
        return f"book_covers/{default_filename}"
    except Exception as e:
        print(f"创建默认封面图片时出错: {e}")
        return None


def get_cover_path(book_name, cover_url):
    """
    获取封面图片路径
    
    Args:
        book_name: 书名
        cover_url: 封面URL
        
    Returns:
        封面图片的本地存储路径
    """
    if cover_url:
        local_path = download_and_save_cover(book_name, cover_url)
        if local_path:
            return local_path
    
    # 如果下载失败，返回默认封面
    return create_default_cover()


def save_uploaded_cover(uploaded_file, book_name):
    """
    保存上传的封面图片
    
    Args:
        uploaded_file: 上传的文件对象
        book_name: 书名
        
    Returns:
        封面图片的本地存储路径，如果保存失败返回None
    """
    if not uploaded_file:
        return None
    
    # 创建封面存储目录
    cover_dir = os.path.join(app.root_path, 'static', 'book_covers')
    if not os.path.exists(cover_dir):
        os.makedirs(cover_dir)
    
    # 生成唯一文件名
    filename = generate_unique_filename(book_name, uploaded_file.filename)
    local_path = os.path.join(cover_dir, filename)
    
    # 保存文件
    try:
        uploaded_file.save(local_path)
        print(f"封面图片已保存: {local_path}")
        return f"book_covers/{filename}"
    except Exception as e:
        print(f"保存封面图片时出错: {e}")
        return None


def cancel_expired_pickups():
    """取消过期的未取货借阅记录"""
    db = get_db()
    
    # 获取当前日期
    current_date = datetime.now().date()
    
    # 查找过期的未取货借阅记录
    expired_loans = db.execute('''
        SELECT l.* FROM loans l
        WHERE l.pickup_confirmed = 0 AND l.is_returned = 0
    ''').fetchall()
    
    for loan in expired_loans:
        # 解析借阅日期
        try:
            loan_date = datetime.strptime(loan['loan_date'], '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            loan_date = datetime.strptime(loan['loan_date'], '%Y-%m-%d %H:%M:%S')
        
        # 检查是否过期（超过当天）
        if loan_date.date() < current_date:
            # 更新借阅记录为已归还
            db.execute('''
                UPDATE loans 
                SET is_returned = 1, return_date = ?
                WHERE id = ?
            ''', (datetime.now(), loan['id']))
            
            # 更新图书可借数量
            db.execute('''
                UPDATE books 
                SET available_copies = available_copies + 1
                WHERE id = ?
            ''', (loan['book_id'],))
    
    db.commit()

def mark_expired_loan_requests():
    """标记超过当天还没取货的借阅请求为失效"""
    db = get_db()
    
    # 获取当前日期
    current_date = datetime.now().date()
    
    # 查找已批准但超过当天还没有取货的借阅请求
    expired_requests = db.execute('''
        SELECT lr.* FROM loan_requests lr
        WHERE lr.status = 'approved' 
        AND lr.pickup_code IS NOT NULL 
        AND lr.pickup_confirmed = 0
    ''').fetchall()
    
    for lr in expired_requests:
        # 解析批准时间
        try:
            approval_date = datetime.strptime(lr['approval_date'], '%Y-%m-%d %H:%M:%S.%f')
        except (ValueError, TypeError):
            try:
                approval_date = datetime.strptime(lr['approval_date'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                continue
        
        # 检查是否过期（当前日期 > 批准日期）
        if current_date > approval_date.date():
            # 更新请求状态为过期
            db.execute('''
                UPDATE loan_requests 
                SET status = 'expired'
                WHERE id = ?
            ''', (lr['id'],))
    
    db.commit()

def init_db():
    """初始化数据库"""
    db = get_db()
    
    # 创建用户表
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建图书表
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT,
            description TEXT,
            total_copies INTEGER DEFAULT 1,
            available_copies INTEGER DEFAULT 1,
            publisher TEXT,
            publish_date TEXT,
            status TEXT DEFAULT '可借阅',
            cover_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建借阅记录表
    db.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date TIMESTAMP NOT NULL,
            return_date TIMESTAMP,
            is_returned BOOLEAN DEFAULT 0,
            fine_amount REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    ''')
    
    # 检查并添加loans表的新字段
    try:
        # 检查pickup_code字段是否存在
        db.execute('SELECT pickup_code FROM loans LIMIT 1')
    except Exception:
        # 添加pickup_code字段
        db.execute('ALTER TABLE loans ADD COLUMN pickup_code TEXT')
    
    try:
        # 检查pickup_confirmed字段是否存在
        db.execute('SELECT pickup_confirmed FROM loans LIMIT 1')
    except Exception:
        # 添加pickup_confirmed字段
        db.execute('ALTER TABLE loans ADD COLUMN pickup_confirmed BOOLEAN DEFAULT 0')
    
    # 检查并添加loan_requests表的新字段
    try:
        # 检查pickup_code字段是否存在
        db.execute('SELECT pickup_code FROM loan_requests LIMIT 1')
    except Exception:
        # 添加pickup_code字段
        db.execute('ALTER TABLE loan_requests ADD COLUMN pickup_code TEXT')
    
    try:
        # 检查pickup_confirmed字段是否存在
        db.execute('SELECT pickup_confirmed FROM loan_requests LIMIT 1')
    except Exception:
        # 添加pickup_confirmed字段
        db.execute('ALTER TABLE loan_requests ADD COLUMN pickup_confirmed BOOLEAN DEFAULT 0')
    
    # 创建借阅申请表
    db.execute('''
        CREATE TABLE IF NOT EXISTS loan_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected, expired
            admin_id INTEGER,
            approval_date TIMESTAMP,
            rejection_reason TEXT,
            pickup_code TEXT,
            pickup_confirmed BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (admin_id) REFERENCES users (id)
        )
    ''')
    
    # 创建公告模板表
    db.execute('''
        CREATE TABLE IF NOT EXISTS announcement_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'all',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建公告推送记录表
    db.execute('''
        CREATE TABLE IF NOT EXISTS announcement_push_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER,
            template_name TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'all',
            push_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (template_id) REFERENCES announcement_templates (id)
        )
    ''')
    
    # 创建统计记录表
    db.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date DATE NOT NULL,
            stat_type TEXT NOT NULL,
            stat_value REAL NOT NULL,
            stat_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stat_date, stat_type)
        )
    ''')
    
    # 创建报表记录表
    db.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT NOT NULL,
            report_name TEXT NOT NULL,
            start_date DATE,
            end_date DATE,
            filters TEXT,
            file_path TEXT,
            file_format TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    db.execute('''
        CREATE TABLE IF NOT EXISTS ai_api_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_name TEXT NOT NULL UNIQUE,
            api_endpoint TEXT NOT NULL,
            api_key TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建图书封面缓存表
    db.execute('''
        CREATE TABLE IF NOT EXISTS book_cover_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_name TEXT NOT NULL,
            cover_url TEXT,
            cover_local_path TEXT,
            book_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expire_at TIMESTAMP
        )
    ''')
    
    # 创建请求日志表
    db.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_ip TEXT NOT NULL,
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            request_path TEXT
        )
    ''')
    
    # 为book_cover_cache表的book_name字段创建唯一索引
    try:
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_book_cover_cache_book_name ON book_cover_cache (book_name)')
    except Exception as e:
        print(f"创建book_cover_cache索引失败: {e}")
    
    # 为request_logs表的client_ip+request_time创建联合索引
    try:
        db.execute('CREATE INDEX IF NOT EXISTS idx_request_logs_ip_time ON request_logs (client_ip, request_time)')
    except Exception as e:
        print(f"创建request_logs索引失败: {e}")
    
    db.commit()
    
    # 创建默认管理员账户
    admin_password = generate_password_hash('admin123', method='pbkdf2:sha256', salt_length=16)
    try:
        db.execute('''
            INSERT OR IGNORE INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@library.com', admin_password, 1))
        db.commit()
    except Exception as e:
        print(f"创建管理员账户失败: {e}")
    
    # 取消过期的未取货借阅记录
    try:
        cancel_expired_pickups()
        print("已检查并取消过期的未取货借阅记录")
    except Exception as e:
        print(f"检查过期未取货记录失败: {e}")
    
    print("默认管理员账户已创建: admin / admin123")
    
    # 检查是否已有示例图书数据，如果没有才添加
    existing_books_count = db.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    
    if existing_books_count == 0:
        # 添加示例图书数据
        sample_books = [
            ('978-7-111-12345-6', 'Python编程：从入门到实践', 'Eric Matthes', '计算机', '适合初学者的Python编程指南', 5, 5),
            ('978-7-111-23456-3', 'Flask Web开发', 'Miguel Grinberg', '计算机', 'Flask框架实战教程', 3, 3),
            ('978-7-111-34567-0', '深入理解计算机系统', 'Randal E. Bryant', '计算机', '计算机系统经典教材', 2, 2),
            ('978-7-111-45678-7', '算法导论', 'Thomas H. Cormen', '计算机', '算法设计分析的权威教材', 1, 1),
            ('978-7-111-56789-4', '设计模式：可复用面向对象软件的基础', 'Erich Gamma', '计算机', '经典设计模式书籍', 2, 2),
        ]
        
        for book_data in sample_books:
            try:
                db.execute('''
                    INSERT INTO books (isbn, title, author, category, description, total_copies, available_copies)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', book_data)
                db.commit()
            except Exception as e:
                print(f"添加图书时出错: {e}")
        
        print("示例图书数据已初始化")
    else:
        print(f"数据库中已有 {existing_books_count} 本图书，跳过示例数据初始化")

def _verify_legacy_password(stored_hash, password):
    """
    验证旧格式密码（SHA-256）
    仅用于向后兼容，不推荐新密码使用此方式
    """
    return stored_hash == hashlib.sha256(password.encode()).hexdigest()

def hash_password(password):
    """
    使用werkzeug生成密码哈希
    采用PBKDF2+SHA256算法
    """
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # 检查是否为API请求（URL包含/api/或请求头Accept为application/json）
            if '/api/' in request.path or request.headers.get('Accept') == 'application/json':
                return jsonify({'success': False, 'message': '请先登录'})
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        
        if not user or not user['is_admin']:
            # 检查是否为API请求
            if '/api/' in request.path or request.headers.get('Accept') == 'application/json':
                return jsonify({'success': False, 'message': '您没有权限执行此操作'})
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

def current_user():
    """获取当前用户"""
    if 'user_id' in session:
        db = get_db()
        return db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return None

@app.before_request
def before_request():
    """请求前设置当前用户"""
    g.user = current_user()

# 路由定义
@app.route('/')
def index():
    """首页"""
    db = get_db()
    
    # 统计信息
    total_books = db.execute('SELECT COUNT(*) as count FROM books').fetchone()['count']
    total_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    active_loans = db.execute('SELECT COUNT(*) as count FROM loans WHERE is_returned = 0').fetchone()['count']
    
    # 热门图书
    popular_books = db.execute('''
        SELECT b.*, COUNT(l.id) as loan_count 
        FROM books b 
        LEFT JOIN loans l ON b.id = l.book_id 
        GROUP BY b.id 
        ORDER BY loan_count DESC, b.created_at DESC 
        LIMIT 6
    ''').fetchall()
    
    return render_template('index_simple.html', 
                         total_books=total_books,
                         total_users=total_users,
                         active_loans=active_loans,
                         popular_books=popular_books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('密码不匹配', 'danger')
            return render_template('register_simple.html')
        
        if len(password) < 6:
            flash('密码长度至少6位', 'danger')
            return render_template('register_simple.html')
        
        db = get_db()
        
        # 检查用户名是否已存在
        existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash('用户名已存在', 'danger')
            return render_template('register_simple.html')
        
        # 创建新用户
        password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        db.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        db.commit()
        
        flash('注册成功，请登录', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_simple.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('''
            SELECT * FROM users 
            WHERE username = ? AND is_active = 1
        ''', (username,)).fetchone()
        
        if user:
            stored_hash = user['password_hash']
            is_password_valid = False
            needs_upgrade = False
            
            # 检测是否为新格式（werkzeug生成的格式以pbkdf2:sha256:开头）
            if stored_hash.startswith('pbkdf2:sha256:'):
                # 新格式密码，直接验证
                is_password_valid = check_password_hash(stored_hash, password)
            else:
                # 旧格式密码（SHA-256），使用兼容验证
                is_password_valid = _verify_legacy_password(stored_hash, password)
                if is_password_valid:
                    # 密码验证成功，标记需要升级
                    needs_upgrade = True
            
            if is_password_valid:
                # 如果检测到旧格式密码，自动升级为新格式
                if needs_upgrade:
                    new_password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
                    db.execute('''
                        UPDATE users SET password_hash = ? WHERE id = ?
                    ''', (new_password_hash, user['id']))
                    db.commit()
                    print(f"已自动将用户 {username} 的密码升级为新格式")
                
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                
                flash('登录成功', 'success')
                next_page = request.args.get('next') or url_for('index')
                return redirect(next_page)
            else:
                flash('用户名或密码错误', 'danger')
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('login_simple.html')

@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已成功登出', 'info')
    return redirect(url_for('index'))

@app.route('/books')
def books():
    """馆藏图书"""
    db = get_db()
    
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    # 构建查询
    query = 'SELECT * FROM books WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY created_at DESC'
    
    books_list = db.execute(query, params).fetchall()
    
    # 打印封面图片路径
    for book in books_list:
        print(f"Book: {book['title']}, Cover Image: {book['cover_image']}")
        if book['cover_image']:
            print(f"Static path: /static/{book['cover_image']}")
    
    # 定义所有支持的分类
    all_categories = [
        '文学', '历史', '科普', '计算机', '艺术', '教育', 
        '经济管理', '法律', '哲学宗教', '生活休闲', '少儿读物', '其他'
    ]
    
    # 将分类转换为与原有代码兼容的格式
    categories = [{'category': cat} for cat in all_categories]
    
    return render_template('books_simple.html', 
                         books=books_list, 
                         categories=categories,
                         search=search,
                         selected_category=category)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    """图书详情"""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if not book:
        flash('图书不存在', 'danger')
        return redirect(url_for('books'))
    
    # 获取借阅历史
    loan_history = db.execute('''
        SELECT l.*, u.username 
        FROM loans l 
        JOIN users u ON l.user_id = u.id 
        WHERE l.book_id = ? 
        ORDER BY l.loan_date DESC 
        LIMIT 10
    ''', (book_id,)).fetchall()
    
    return render_template('book_detail_simple.html', book=book, loan_history=loan_history)

def generate_pickup_code():
    """生成取货码"""
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    """申请借阅图书"""
    db = get_db()
    
    # 检查图书是否存在
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if not book:
        flash('图书不存在', 'danger')
        return redirect(url_for('books'))
    
    if book['available_copies'] <= 0:
        flash('该图书暂无库存', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # 检查用户是否已借阅该图书且未归还
    existing_loan = db.execute('''
        SELECT * FROM loans 
        WHERE user_id = ? AND book_id = ? AND is_returned = 0
    ''', (session['user_id'], book_id)).fetchone()
    
    if existing_loan:
        flash('您已经借阅了这本书', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # 检查用户当前借阅数量
    current_loans = db.execute('''
        SELECT COUNT(*) as count FROM loans 
        WHERE user_id = ? AND is_returned = 0
    ''', (session['user_id'],)).fetchone()['count']
    
    if current_loans >= 5:
        flash('最多只能同时借阅5本书', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # 检查是否已有未处理的借阅请求
    existing_request = db.execute('''
        SELECT * FROM loan_requests 
        WHERE user_id = ? AND book_id = ? AND status = 'pending'
    ''', (session['user_id'], book_id)).fetchone()
    
    if existing_request:
        flash('您已经提交了该图书的借阅申请，请等待管理员审批', 'warning')
        return redirect(url_for('book_detail', book_id=book_id))
    
    # 创建借阅请求
    db.execute('''
        INSERT INTO loan_requests (user_id, book_id)
        VALUES (?, ?)
    ''', (session['user_id'], book_id))
    
    db.commit()
    flash(f'借阅申请已提交，请等待管理员审批', 'success')
    return redirect(url_for('book_detail', book_id=book_id))

@app.route('/my_loans')
@login_required
def my_loans():
    """个人中心"""
    db = get_db()
    
    loans = db.execute('''
        SELECT l.*, b.title, b.author, b.isbn
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        WHERE l.user_id = ?
        ORDER BY l.loan_date DESC
    ''', (session['user_id'],)).fetchall()
    
    # 计算逾期状态
    current_date = datetime.now()
    loans_with_status = []
    
    for loan in loans:
        loan_dict = dict(loan)
        if loan_dict['due_date']:
            try:
                due_date = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                due_date = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S')
            loan_dict['is_overdue'] = not loan_dict['is_returned'] and current_date > due_date
        else:
            loan_dict['is_overdue'] = False
        loans_with_status.append(loan_dict)
    
    # 获取借阅请求状态
    requests = db.execute('''
        SELECT lr.*, b.title
        FROM loan_requests lr
        JOIN books b ON lr.book_id = b.id
        WHERE lr.user_id = ? AND lr.status = 'pending'
        ORDER BY lr.request_date DESC
    ''', (session['user_id'],)).fetchall()
    
    return render_template('my_loans_simple.html', loans=loans_with_status, current_date=current_date, requests=requests)

@app.route('/cancel_loan_request/<int:request_id>', methods=['POST'])
@login_required
def cancel_loan_request(request_id):
    """撤销借阅请求"""
    db = get_db()
    
    # 检查请求是否存在且属于当前用户
    request = db.execute('''
        SELECT * FROM loan_requests 
        WHERE id = ? AND user_id = ? AND status = 'pending'
    ''', (request_id, session['user_id'])).fetchone()
    
    if not request:
        flash('借阅请求不存在或已处理', 'danger')
        return redirect(url_for('my_loans'))
    
    # 移除3分钟时间限制，用户可以随时撤销借阅请求
    
    # 更新请求状态
    db.execute('''
        UPDATE loan_requests 
        SET status = 'cancelled'
        WHERE id = ?
    ''', (request_id,))
    
    db.commit()
    flash('借阅请求已撤销', 'success')
    return redirect(url_for('my_loans'))

@app.route('/return/<int:loan_id>', methods=['POST'])
@login_required
def return_book(loan_id):
    """归还图书"""
    db = get_db()
    
    # 检查借阅记录是否存在且属于当前用户
    loan = db.execute('''
        SELECT l.*, b.id as book_id
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        WHERE l.id = ? AND l.user_id = ?
    ''', (loan_id, session['user_id'])).fetchone()
    
    if not loan:
        flash('借阅记录不存在', 'danger')
        return redirect(url_for('my_loans'))
    
    if loan['is_returned']:
        flash('该图书已归还', 'warning')
        return redirect(url_for('my_loans'))
    
    # 计算逾期费用
    current_date = datetime.now()
    try:
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S')
    fine_amount = 0
    
    if current_date > due_date:
        days_overdue = (current_date - due_date).days
        fine_amount = days_overdue * 0.5
    
    # 更新借阅记录
    db.execute('''
        UPDATE loans 
        SET is_returned = 1, return_date = ?, fine_amount = ?
        WHERE id = ?
    ''', (current_date, fine_amount, loan_id))
    
    # 更新图书库存
    db.execute('''
        UPDATE books 
        SET available_copies = available_copies + 1 
        WHERE id = ?
    ''', (loan['book_id'],))
    
    db.commit()
    
    if fine_amount > 0:
        flash(f'图书已归还，逾期费用：{fine_amount:.2f}元', 'info')
    else:
        flash('图书已归还', 'success')
    
    return redirect(url_for('my_loans'))

@app.route('/admin')
@admin_required
def admin():
    """管理员面板"""
    db = get_db()
    
    # 统计数据
    total_books = db.execute('SELECT COUNT(*) as count FROM books').fetchone()['count']
    total_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    active_loans = db.execute('SELECT COUNT(*) as count FROM loans WHERE is_returned = 0').fetchone()['count']
    overdue_loans = db.execute('''
        SELECT COUNT(*) as count FROM loans 
        WHERE is_returned = 0 AND due_date < ?
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),)).fetchone()['count']
    pending_requests = db.execute('SELECT COUNT(*) as count FROM loan_requests WHERE status = "pending"').fetchone()['count']
    
    # 所有数据
    books = db.execute('SELECT * FROM books ORDER BY created_at DESC').fetchall()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    loans_raw = db.execute('''
        SELECT l.*, u.username, b.title 
        FROM loans l 
        JOIN users u ON l.user_id = u.id 
        JOIN books b ON l.book_id = b.id 
        ORDER BY l.loan_date DESC
    ''').fetchall()
    
    # 预处理借阅数据，转换日期格式
    loans = []
    current_date = datetime.now()
    for loan in loans_raw:
        loan_dict = dict(loan)
        # 转换due_date为datetime对象进行比较
        if loan_dict['due_date']:
            try:
                loan_dict['due_date_dt'] = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                loan_dict['due_date_dt'] = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S')
        loans.append(loan_dict)
    
    return render_template('admin_simple.html',
                         total_books=total_books,
                         total_users=total_users,
                         active_loans=active_loans,
                         overdue_loans=overdue_loans,
                         pending_requests=pending_requests,
                         books=books,
                         users=users,
                         loans=loans,
                         current_date=current_date)

@app.route('/admin/loan_requests')
@admin_required
def admin_loan_requests():
    """管理员查看借阅请求"""
    db = get_db()
    
    # 标记过期的借阅请求
    mark_expired_loan_requests()
    
    # 获取所有借阅请求，包括对应的借阅记录信息
    requests = db.execute('''
        SELECT lr.*, u.username, b.title, l.pickup_code, l.pickup_confirmed
        FROM loan_requests lr
        JOIN users u ON lr.user_id = u.id
        JOIN books b ON lr.book_id = b.id
        LEFT JOIN loans l ON lr.user_id = l.user_id AND lr.book_id = l.book_id AND lr.status = 'approved' AND l.is_returned = 0
        ORDER BY lr.request_date DESC
    ''').fetchall()
    
    return render_template('admin_loan_requests_simple.html', requests=requests)

@app.route('/admin/loan_requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_loan_request(request_id):
    """审批借阅请求"""
    db = get_db()
    
    # 检查请求是否存在
    request = db.execute('''
        SELECT lr.*, b.available_copies
        FROM loan_requests lr
        JOIN books b ON lr.book_id = b.id
        WHERE lr.id = ? AND lr.status = 'pending'
    ''', (request_id,)).fetchone()
    
    if not request:
        flash('借阅请求不存在或已处理', 'danger')
        return redirect(url_for('loan_management'))
    
    if request['available_copies'] <= 0:
        flash('图书暂无库存', 'warning')
        return redirect(url_for('loan_management'))
    
    # 开始事务
    try:
        # 更新请求状态
        db.execute('''
            UPDATE loan_requests 
            SET status = 'approved', admin_id = ?, approval_date = ?
            WHERE id = ?
        ''', (session['user_id'], datetime.now(), request_id))
        
        # 生成取货码
        pickup_code = generate_pickup_code()
        
        # 保存取货码到借阅请求记录
        db.execute('''
            UPDATE loan_requests 
            SET pickup_code = ?
            WHERE id = ?
        ''', (pickup_code, request_id))
        
        db.commit()
        flash('借阅请求已审批通过，取货码已生成', 'success')
    except Exception as e:
        db.rollback()
        print(f"审批失败错误: {e}")
        flash(f'审批失败，请重试: {str(e)}', 'danger')
    
    return redirect(url_for('loan_management'))

@app.route('/admin/loan_requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_loan_request(request_id):
    """拒绝借阅请求"""
    db = get_db()
    
    # 检查请求是否存在
    request = db.execute('''
        SELECT * FROM loan_requests 
        WHERE id = ? AND status = 'pending'
    ''', (request_id,)).fetchone()
    
    if not request:
        flash('借阅请求不存在或已处理', 'danger')
        return redirect(url_for('loan_management'))
    
    # 获取拒绝原因
    rejection_reason = request.form.get('rejection_reason', '未提供原因')
    
    # 更新请求状态
    db.execute('''
        UPDATE loan_requests 
        SET status = 'rejected', admin_id = ?, approval_date = ?, rejection_reason = ?
        WHERE id = ?
    ''', (session['user_id'], datetime.now(), rejection_reason, request_id))
    
    db.commit()
    flash('借阅请求已拒绝', 'success')
    return redirect(url_for('loan_management'))

@app.route('/admin/loan_requests/<int:request_id>/confirm_pickup', methods=['POST'])
@admin_required
def confirm_pickup(request_id):
    """确认用户取货"""
    db = get_db()
    
    # 通过借阅请求ID查找对应的请求记录
    loan_request = db.execute('''
        SELECT * FROM loan_requests 
        WHERE id = ? AND status = 'approved' AND pickup_code IS NOT NULL
    ''', (request_id,)).fetchone()
    
    if not loan_request:
        flash('借阅请求不存在或已处理', 'danger')
        return redirect(url_for('loan_management'))
    
    # 检查取货码是否当天有效（使用请求的审批时间）
    approval_date = loan_request['approval_date']
    if isinstance(approval_date, str):
        try:
            approval_date = datetime.strptime(approval_date, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            approval_date = datetime.strptime(approval_date, '%Y-%m-%d %H:%M:%S')
    
    current_date = datetime.now()
    if approval_date.date() != current_date.date():
        flash('取货码已过期', 'danger')
        return redirect(url_for('loan_management'))
    
    # 开始事务
    try:
        # 创建借阅记录
        due_date = datetime.now() + timedelta(days=14)
        db.execute('''
            INSERT INTO loans (user_id, book_id, due_date, pickup_code, pickup_confirmed)
            VALUES (?, ?, ?, ?, 1)
        ''', (loan_request['user_id'], loan_request['book_id'], due_date, loan_request['pickup_code']))
        
        # 更新图书库存
        db.execute('''
            UPDATE books 
            SET available_copies = available_copies - 1 
            WHERE id = ?
        ''', (loan_request['book_id'],))
        
        # 更新借阅请求状态为已取货
        db.execute('''
            UPDATE loan_requests 
            SET pickup_confirmed = 1
            WHERE id = ?
        ''', (request_id,))
        
        db.commit()
        flash('取货已确认', 'success')
    except Exception as e:
        db.rollback()
        print(f"确认取货失败错误: {e}")
        flash(f'确认取货失败，请重试: {str(e)}', 'danger')
    
    return redirect(url_for('loan_management'))

@app.route('/readers')
@admin_required
def readers():
    """读者管理列表"""
    db = get_db()
    
    # 获取查询参数
    search = request.args.get('search', '')
    reader_type = request.args.get('reader_type', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # 构建查询
    query = 'SELECT * FROM users WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (username LIKE ? OR name LIKE ? OR phone LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])
    
    if reader_type:
        if reader_type == 'admin':
            query += ' AND is_admin = 1'
        else:
            query += ' AND is_admin = 0'
    
    # 计算总数
    count_query = f'SELECT COUNT(*) as count FROM ({query})'
    total = db.execute(count_query, params).fetchone()['count']
    
    # 分页
    offset = (page - 1) * per_page
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    readers = db.execute(query, params).fetchall()
    
    # 获取每个读者的借阅统计
    readers_with_stats = []
    for reader in readers:
        reader_dict = dict(reader)
        
        # 获取借阅数量
        loan_count = db.execute('''
            SELECT COUNT(*) as count FROM loans 
            WHERE user_id = ? AND is_returned = 0
        ''', (reader['id'],)).fetchone()['count']
        
        # 获取逾期数量
        overdue_count = db.execute('''
            SELECT COUNT(*) as count FROM loans 
            WHERE user_id = ? AND is_returned = 0 AND due_date < ?
        ''', (reader['id'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))).fetchone()['count']
        
        reader_dict['loan_count'] = loan_count
        reader_dict['overdue_count'] = overdue_count
        readers_with_stats.append(reader_dict)
    
    # 计算总页数
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('readers_simple.html',
                         readers=readers_with_stats,
                         search=search,
                         reader_type=reader_type,
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         total=total)

@app.route('/readers/add', methods=['GET', 'POST'])
@admin_required
def add_reader():
    """新增读者"""
    if request.method == 'POST':
        db = get_db()
        
        # 获取表单数据
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        gender = request.form['gender']
        phone = request.form['phone']
        id_card = request.form['id_card']
        is_admin = 1 if request.form.get('is_admin') else 0
        
        # 检查用户名是否已存在
        existing_user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash('用户名已存在', 'danger')
            return redirect(url_for('add_reader'))
        
        # 密码哈希
        password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        # 插入新读者
        db.execute('''
            INSERT INTO users (username, email, password_hash, name, gender, phone, id_card, is_admin, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, name, gender, phone, id_card, is_admin, 1))
        
        db.commit()
        flash('读者添加成功', 'success')
        return redirect(url_for('readers'))
    
    return render_template('add_reader_simple.html')

@app.route('/readers/<int:reader_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_reader(reader_id):
    """编辑读者"""
    db = get_db()
    reader = db.execute('SELECT * FROM users WHERE id = ?', (reader_id,)).fetchone()
    
    if not reader:
        flash('读者不存在', 'danger')
        return redirect(url_for('readers'))
    
    if request.method == 'POST':
        # 获取表单数据
        name = request.form['name']
        email = request.form['email']
        gender = request.form['gender']
        phone = request.form['phone']
        id_card = request.form['id_card']
        is_admin = 1 if request.form.get('is_admin') else 0
        is_active = 1 if request.form.get('is_active') else 0
        
        # 如果提供了新密码，则更新密码
        password = request.form.get('password')
        if password:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            db.execute('''
                UPDATE users 
                SET name = ?, email = ?, gender = ?, phone = ?, id_card = ?, is_admin = ?, is_active = ?, password_hash = ?
                WHERE id = ?
            ''', (name, email, gender, phone, id_card, is_admin, is_active, password_hash, reader_id))
        else:
            db.execute('''
                UPDATE users 
                SET name = ?, email = ?, gender = ?, phone = ?, id_card = ?, is_admin = ?, is_active = ?
                WHERE id = ?
            ''', (name, email, gender, phone, id_card, is_admin, is_active, reader_id))
        
        db.commit()
        flash('读者信息更新成功', 'success')
        return redirect(url_for('readers'))
    
    return render_template('edit_reader_simple.html', reader=reader)

@app.route('/readers/<int:reader_id>/delete', methods=['POST'])
@admin_required
def delete_reader(reader_id):
    """删除读者"""
    db = get_db()
    
    # 检查读者是否存在
    reader = db.execute('SELECT * FROM users WHERE id = ?', (reader_id,)).fetchone()
    if not reader:
        flash('读者不存在', 'danger')
        return redirect(url_for('readers'))
    
    # 检查读者是否有未归还的图书
    active_loans = db.execute('''
        SELECT COUNT(*) as count FROM loans 
        WHERE user_id = ? AND is_returned = 0
    ''', (reader_id,)).fetchone()['count']
    
    if active_loans > 0:
        flash('该读者还有未归还的图书，无法删除', 'danger')
        return redirect(url_for('readers'))
    
    # 删除读者
    db.execute('DELETE FROM users WHERE id = ?', (reader_id,))
    db.commit()
    
    flash('读者删除成功', 'success')
    return redirect(url_for('readers'))

@app.route('/readers/<int:reader_id>/toggle_status', methods=['POST'])
@admin_required
def toggle_reader_status(reader_id):
    """切换读者状态（启用/禁用）"""
    db = get_db()
    
    # 获取当前状态
    reader = db.execute('SELECT is_active FROM users WHERE id = ?', (reader_id,)).fetchone()
    if not reader:
        flash('读者不存在', 'danger')
        return redirect(url_for('readers'))
    
    # 切换状态
    new_status = 0 if reader['is_active'] else 1
    db.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, reader_id))
    db.commit()
    
    status_text = '启用' if new_status else '禁用'
    flash(f'读者已{status_text}成功', 'success')
    return redirect(url_for('readers'))

@app.route('/loan_management')
@admin_required
def loan_management():
    """借阅管理页面"""
    db = get_db()
    
    # 标记过期的借阅请求
    mark_expired_loan_requests()
    
    # 获取查询参数
    search = request.args.get('search', '')
    return_status = request.args.get('return_status', '')
    overdue_status = request.args.get('overdue_status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # 构建查询
    query = '''
        SELECT l.id, u.username, u.name, b.title, l.loan_date, l.due_date, l.return_date, l.is_returned
        FROM loans l
        JOIN users u ON l.user_id = u.id
        JOIN books b ON l.book_id = b.id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (u.username LIKE ? OR u.name LIKE ? OR b.title LIKE ? OR l.id LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])
    
    if return_status:
        if return_status == 'returned':
            query += ' AND l.is_returned = 1'
        else:
            query += ' AND l.is_returned = 0'
    
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if overdue_status:
        if overdue_status == 'overdue':
            query += ' AND l.is_returned = 0 AND l.due_date < ?'
            params.append(current_date)
        elif overdue_status == 'normal':
            query += ' AND (l.is_returned = 1 OR l.due_date >= ?)'
            params.append(current_date)
    
    if start_date:
        query += ' AND l.loan_date >= ?'
        params.append(f'{start_date} 00:00:00')
    
    if end_date:
        query += ' AND l.loan_date <= ?'
        params.append(f'{end_date} 23:59:59')
    
    # 计算总数
    count_query = f'SELECT COUNT(*) as count FROM ({query})'
    total = db.execute(count_query, params).fetchone()['count']
    
    # 分页
    offset = (page - 1) * per_page
    query += ' ORDER BY l.loan_date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    loans = db.execute(query, params).fetchall()
    
    # 计算逾期天数
    loans_with_status = []
    for loan in loans:
        loan_dict = dict(loan)
        try:
            loan_dict['due_date_dt'] = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            loan_dict['due_date_dt'] = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S')
        
        if loan['is_returned']:
            loan_dict['return_status'] = '已归还'
            loan_dict['is_overdue'] = False
            loan_dict['overdue_days'] = 0
        else:
            loan_dict['return_status'] = '未归还'
            now = datetime.now()
            if now > loan_dict['due_date_dt']:
                loan_dict['is_overdue'] = True
                loan_dict['overdue_days'] = (now - loan_dict['due_date_dt']).days
            else:
                loan_dict['is_overdue'] = False
                loan_dict['overdue_days'] = 0
        
        loans_with_status.append(loan_dict)
    
    # 获取借阅请求数据
    requests_query = '''
        SELECT lr.*, u.username, b.title, l.pickup_code, l.pickup_confirmed
        FROM loan_requests lr
        JOIN users u ON lr.user_id = u.id
        JOIN books b ON lr.book_id = b.id
        LEFT JOIN loans l ON lr.user_id = l.user_id AND lr.book_id = l.book_id AND l.is_returned = 0
        WHERE lr.status != 'cancelled'
        ORDER BY lr.request_date DESC
    '''
    requests = db.execute(requests_query).fetchall()
    requests_with_data = []
    for r in requests:
        request_dict = dict(r)
        requests_with_data.append(request_dict)
    
    # 计算总页数
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('loan_management_simple.html',
                         loans=loans_with_status,
                         requests=requests_with_data,
                         search=search,
                         return_status=return_status,
                         overdue_status=overdue_status,
                         start_date=start_date,
                         end_date=end_date,
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         total=total)

@app.route('/api/search_users', methods=['GET'])
@admin_required
def search_users():
    """搜索读者API"""
    db = get_db()
    keyword = request.args.get('keyword', '')
    
    if not keyword:
        return jsonify([])
    
    users = db.execute('''
        SELECT id, username, name, is_active
        FROM users 
        WHERE username LIKE ? OR name LIKE ? OR phone LIKE ?
        LIMIT 10
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')).fetchall()
    
    return jsonify([dict(user) for user in users])

@app.route('/api/search_books', methods=['GET'])
@admin_required
def search_books():
    """搜索图书API"""
    db = get_db()
    keyword = request.args.get('keyword', '')
    
    if not keyword:
        return jsonify([])
    
    books = db.execute('''
        SELECT id, title, author, isbn, available_copies, total_copies
        FROM books 
        WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?
        LIMIT 10
    ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')).fetchall()
    
    return jsonify([dict(book) for book in books])

@app.route('/api/search_loans', methods=['GET'])
@admin_required
def search_loans():
    """搜索借阅记录API"""
    db = get_db()
    keyword = request.args.get('keyword', '')
    
    query = '''
        SELECT l.id, u.username, u.name, b.title, l.loan_date
        FROM loans l
        JOIN users u ON l.user_id = u.id
        JOIN books b ON l.book_id = b.id
        WHERE l.is_returned = 0
    '''
    params = []
    
    if keyword:
        query += ' AND (l.id LIKE ? OR u.username LIKE ? OR u.name LIKE ? OR b.title LIKE ?)'
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
    
    query += ' ORDER BY l.loan_date DESC LIMIT 10'
    loans = db.execute(query, params).fetchall()
    
    return jsonify([dict(loan) for loan in loans])

@app.route('/loan/create', methods=['POST'])
@admin_required
def create_loan():
    """办理借阅API"""
    db = get_db()
    
    user_id = request.form.get('user_id')
    book_id = request.form.get('book_id')
    due_date_str = request.form.get('due_date')
    
    if not user_id or not book_id:
        return jsonify({'success': False, 'message': '请选择读者和图书'})
    
    # 检查读者是否存在且可用
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'success': False, 'message': '读者不存在'})
    
    if not user['is_active']:
        return jsonify({'success': False, 'message': '该读者无法借阅'})
    
    # 检查图书是否存在且有库存
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if not book:
        return jsonify({'success': False, 'message': '图书不存在'})
    
    if book['available_copies'] <= 0:
        return jsonify({'success': False, 'message': '该图书无库存'})
    
    # 检查读者是否已借阅该图书且未归还
    existing_loan = db.execute('''
        SELECT * FROM loans 
        WHERE user_id = ? AND book_id = ? AND is_returned = 0
    ''', (user_id, book_id)).fetchone()
    
    if existing_loan:
        return jsonify({'success': False, 'message': '该读者已借阅了这本书'})
    
    # 设置应还日期
    if due_date_str:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    else:
        due_date = datetime.now() + timedelta(days=30)
    
    # 创建借阅记录
    db.execute('''
        INSERT INTO loans (user_id, book_id, due_date)
        VALUES (?, ?, ?)
    ''', (user_id, book_id, due_date))
    
    # 更新图书库存
    db.execute('''
        UPDATE books 
        SET available_copies = available_copies - 1 
        WHERE id = ?
    ''', (book_id,))
    
    db.commit()
    return jsonify({'success': True, 'message': '借阅成功'})

@app.route('/loan/return', methods=['POST'])
@admin_required
def return_loan():
    """办理归还API"""
    db = get_db()
    
    loan_id = request.form.get('loan_id')
    
    if not loan_id:
        return jsonify({'success': False, 'message': '请选择借阅记录'})
    
    # 检查借阅记录是否存在且未归还
    loan = db.execute('''
        SELECT l.*, b.id as book_id
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        WHERE l.id = ? AND l.is_returned = 0
    ''', (loan_id,)).fetchone()
    
    if not loan:
        return jsonify({'success': False, 'message': '借阅记录不存在或已归还'})
    
    # 计算逾期费用
    current_date = datetime.now()
    try:
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d %H:%M:%S')
    fine_amount = 0
    overdue_days = 0
    
    if current_date > due_date:
        overdue_days = (current_date - due_date).days
        fine_amount = overdue_days * 0.5
    
    # 更新借阅记录
    db.execute('''
        UPDATE loans 
        SET is_returned = 1, return_date = ?, fine_amount = ?
        WHERE id = ?
    ''', (current_date, fine_amount, loan_id))
    
    # 更新图书库存
    db.execute('''
        UPDATE books 
        SET available_copies = available_copies + 1 
        WHERE id = ?
    ''', (loan['book_id'],))
    
    db.commit()
    
    message = '归还成功'
    if overdue_days > 0:
        message += f'，逾期{overdue_days}天，逾期费用：{fine_amount:.2f}元'
    
    return jsonify({'success': True, 'message': message})

# =======================================
# 图书管理模块
# =======================================

@app.route('/book_management')
@admin_required
def book_management():
    """图书管理页面"""
    db = get_db()
    
    # 获取查询参数
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    stock_status = request.args.get('stock_status', '')
    sort_by = request.args.get('sort_by', 'title')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    # 构建查询
    query = 'SELECT * FROM books WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR publisher LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    # 库存筛选
    if stock_status:
        if stock_status == '充足':
            query += ' AND total_copies > 1'
        elif stock_status == '不足':
            query += ' AND total_copies <= 1 AND (status = "可借阅" OR status IS NULL)'
        elif stock_status == '无库存':
            query += ' AND total_copies = 0'
    
    # 排序
    if sort_by in ['title', 'publish_date', 'total_copies']:
        query += f' ORDER BY {sort_by} {sort_order}'
    
    # 计算总数
    count_query = f'SELECT COUNT(*) as count FROM ({query})'
    total = db.execute(count_query, params).fetchone()['count']
    
    # 分页
    offset = (page - 1) * per_page
    query += ' LIMIT ? OFFSET ?'
    params.extend([per_page, offset])
    
    books = db.execute(query, params).fetchall()
    
    # 定义所有支持的分类
    all_categories = [
        '文学', '历史', '科普', '计算机', '艺术', '教育', 
        '经济管理', '法律', '哲学宗教', '生活休闲', '少儿读物', '其他'
    ]
    
    # 将分类转换为与原有代码兼容的格式
    categories = [{'category': cat} for cat in all_categories]
    
    # 计算总页数
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('book_management_simple.html',
                         books=books,
                         categories=categories,
                         search=search,
                         category=category,
                         status=status,
                         stock_status=stock_status,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         total=total)

@app.route('/book/create', methods=['POST'])
@admin_required
def create_book():
    """新增图书API"""
    db = get_db()
    
    # 获取表单数据
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    publisher = request.form.get('publisher')
    publish_date = request.form.get('publish_date')
    category = request.form.get('category')
    total_copies = int(request.form.get('total_copies', 1))
    status = request.form.get('status', '可借阅')
    cover_image = request.form.get('cover_image', '')
    description = request.form.get('description', '')
    
    # 处理封面上传
    cover_image_file = request.files.get('cover_image_file')
    if cover_image_file and cover_image_file.filename:
        cover_image = save_uploaded_cover(cover_image_file, title)
        if cover_image:
            print(f"封面上传成功: {cover_image}")
        else:
            print("封面上传失败")
    
    if not title or not author:
        return jsonify({'success': False, 'message': '书名和作者不能为空'})
    
    # 检查ISBN是否已存在（如果提供了ISBN）
    if isbn:
        existing_book = db.execute('SELECT * FROM books WHERE isbn = ?', (isbn,)).fetchone()
        if existing_book:
            return jsonify({'success': False, 'message': '该ISBN已存在'})
    
    # 创建图书
    db.execute('''
        INSERT INTO books (title, author, isbn, publisher, publish_date, category, total_copies, available_copies, status, cover_image, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, author, isbn, publisher, publish_date, category, total_copies, total_copies, status, cover_image, description))
    db.commit()

    # 如果没有提供封面，尝试自动获取并保存到数据库
    if not cover_image:
        book_info = fetch_book_cover(title, isbn=isbn)
        if book_info:
            url = book_info.get('cover_url', '')
            if url:
                local_path = get_cover_path(title, url)
                if local_path:
                    db.execute('UPDATE books SET cover_image = ? WHERE title = ?', (local_path, title))
                    db.commit()
    
    return jsonify({'success': True, 'message': f'图书《{title}》新增成功'})

@app.route('/book/<int:book_id>/edit', methods=['POST'])
@admin_required
def edit_book(book_id):
    """编辑图书API"""
    db = get_db()
    
    # 检查图书是否存在
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if not book:
        return jsonify({'success': False, 'message': '图书不存在'})
    
    # 获取表单数据
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    publisher = request.form.get('publisher')
    publish_date = request.form.get('publish_date')
    category = request.form.get('category')
    total_copies = int(request.form.get('total_copies', 1))
    status = request.form.get('status', '可借阅')
    cover_image = request.form.get('cover_image', '')
    description = request.form.get('description', '')
    
    # 处理封面上传
    cover_image_file = request.files.get('cover_image_file')
    if cover_image_file and cover_image_file.filename:
        cover_image = save_uploaded_cover(cover_image_file, title)
        if cover_image:
            print(f"封面上传成功: {cover_image}")
        else:
            print("封面上传失败")
    
    if not title or not author:
        return jsonify({'success': False, 'message': '书名和作者不能为空'})
    
    # 检查ISBN是否已存在（排除当前图书）
    if isbn:
        existing_book = db.execute('SELECT * FROM books WHERE isbn = ? AND id != ?', (isbn, book_id)).fetchone()
        if existing_book:
            return jsonify({'success': False, 'message': '该ISBN已存在'})
    
    # 计算可借数量的变化
    current_available = book['available_copies']
    current_total = book['total_copies']
    new_available = current_available + (total_copies - current_total)
    
    # 更新图书
    db.execute('''
        UPDATE books 
        SET title = ?, author = ?, isbn = ?, publisher = ?, publish_date = ?, category = ?, 
            total_copies = ?, available_copies = ?, status = ?, cover_image = ?, description = ?
        WHERE id = ?
    ''', (title, author, isbn, publisher, publish_date, category, total_copies, new_available, status, cover_image, description, book_id))
    db.commit()

    # 如果当前没有封面且用户未上传，则尝试根据isbn/title自动获取
    if not cover_image:
        book_info = fetch_book_cover(title, isbn=isbn)
        if book_info:
            url = book_info.get('cover_url', '')
            if url:
                local_path = get_cover_path(title, url)
                if local_path:
                    db.execute('UPDATE books SET cover_image = ? WHERE id = ?', (local_path, book_id))
                    db.commit()
    return jsonify({'success': True, 'message': f'图书《{title}》编辑成功'})

@app.route('/api/book/<int:book_id>')
@admin_required
def get_book_api(book_id):
    """获取图书详情API（用于编辑）"""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if not book:
        return jsonify({'success': False, 'message': '图书不存在'})
    
    # 将图书对象转换为字典
    book_dict = dict(book)
    
    # 确保日期格式正确（如果日期为None或空字符串，转换为''）
    if not book_dict['publish_date']:
        book_dict['publish_date'] = ''
    
    return jsonify({'success': True, 'book': book_dict})

@app.route('/book/<int:book_id>/delete', methods=['POST'])
@admin_required
def delete_book(book_id):
    """删除图书API"""
    db = get_db()
    
    # 检查图书是否存在
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if not book:
        return jsonify({'success': False, 'message': '图书不存在'})
    
    # 检查是否有未归还记录
    active_loans = db.execute('''
        SELECT COUNT(*) as count FROM loans 
        WHERE book_id = ? AND is_returned = 0
    ''', (book_id,)).fetchone()['count']
    
    if active_loans > 0:
        return jsonify({'success': False, 'message': f'该图书存在未归还记录，无法删除'})
    
    # 删除图书
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'success': True, 'message': f'图书《{book["title"]}》删除成功'})

@app.route('/categories')
@admin_required
def categories():
    """分类管理页面"""
    db = get_db()
    
    # 获取所有分类及图书数量
    categories = db.execute('''
        SELECT category, COUNT(*) as book_count 
        FROM books 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY category
    ''').fetchall()
    
    return render_template('categories_simple.html', categories=categories)

@app.route('/category/create', methods=['POST'])
@admin_required
def create_category():
    """新增分类API"""
    db = get_db()
    
    category_name = request.form.get('category_name')
    
    if not category_name:
        return jsonify({'success': False, 'message': '分类名称不能为空'})
    
    # 检查分类是否已存在
    existing_category = db.execute('''
        SELECT * FROM books WHERE category = ?
    ''', (category_name,)).fetchone()
    
    if existing_category:
        return jsonify({'success': False, 'message': '该分类已存在'})
    
    # 新增分类（通过在books表中添加一个带有该分类的记录，但不实际创建分类表）
    # 这里我们使用一种简单的方式，通过在books表中插入一个带有该分类的占位记录
    # 实际应用中应该创建一个独立的categories表
    db.execute('''
        INSERT INTO books (title, author, category, total_copies, available_copies, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('占位图书', '系统', category_name, 0, 0, '已下架'))
    
    db.commit()
    return jsonify({'success': True, 'message': f'分类《{category_name}》新增成功'})

@app.route('/category/<string:category_name>/edit', methods=['POST'])
@admin_required
def edit_category(category_name):
    """编辑分类API"""
    db = get_db()
    
    new_name = request.form.get('category_name')
    
    if not new_name:
        return jsonify({'success': False, 'message': '分类名称不能为空'})
    
    # 检查新分类名称是否已存在
    existing_category = db.execute('''
        SELECT * FROM books WHERE category = ? AND category != ?
    ''', (new_name, category_name)).fetchone()
    
    if existing_category:
        return jsonify({'success': False, 'message': '该分类已存在'})
    
    # 更新分类
    db.execute('''
        UPDATE books 
        SET category = ? 
        WHERE category = ?
    ''', (new_name, category_name))
    
    db.commit()
    return jsonify({'success': True, 'message': f'分类《{category_name}》已更新为《{new_name}》'})

@app.route('/category/<string:category_name>/delete', methods=['POST'])
@admin_required
def delete_category(category_name):
    """删除分类API"""
    db = get_db()
    
    # 检查分类下是否有图书
    book_count = db.execute('''
        SELECT COUNT(*) as count FROM books 
        WHERE category = ? AND title != '占位图书'
    ''', (category_name,)).fetchone()['count']
    
    if book_count > 0:
        return jsonify({'success': False, 'message': f'该分类下有{book_count}本图书，无法删除'})
    
    # 删除分类（包括占位图书）
    db.execute('''
        DELETE FROM books 
        WHERE category = ?
    ''', (category_name,))
    
    db.commit()
    return jsonify({'success': True, 'message': f'分类《{category_name}》删除成功'})

@app.route('/api/categories', methods=['GET'])
@admin_required
def get_categories():
    """获取所有分类API"""
    db = get_db()
    
    categories = db.execute('''
        SELECT DISTINCT category FROM books 
        WHERE category IS NOT NULL 
        ORDER BY category
    ''').fetchall()
    
    return jsonify([category['category'] for category in categories])

@app.route('/book/<int:book_id>/loan_records')
@admin_required
def book_loan_records(book_id):
    """查看图书借阅记录"""
    # 这里可以直接跳转到借阅管理页面，并筛选该图书的借阅记录
    return redirect(url_for('loan_management', search=str(book_id)))

# =======================================
# 公告管理模块
# =======================================

@app.route('/announcement_management')
@admin_required
def announcement_management():
    """公告管理页面"""
    db = get_db()
    
    # 获取查询参数
    module = request.args.get('module', 'templates')
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # 获取所有模板
    query = 'SELECT * FROM announcement_templates WHERE 1=1'
    params = []
    
    if search:
        query += ' AND name LIKE ?'
        params.append(f'%{search}%')
    
    query += ' ORDER BY created_at DESC'
    templates = db.execute(query, params).fetchall()
    
    # 获取所有推送记录
    query = 'SELECT * FROM announcement_push_records WHERE 1=1'
    params = []
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if start_date:
        query += ' AND DATE(push_time) >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND DATE(push_time) <= ?'
        params.append(end_date)
    
    query += ' ORDER BY push_time DESC'
    records = db.execute(query, params).fetchall()
    
    # 获取所有模板用于快捷推送
    all_templates = db.execute('SELECT * FROM announcement_templates ORDER BY created_at DESC').fetchall()
    
    # 定义所有支持的分类
    all_categories = [
        '文学', '历史', '科普', '计算机', '艺术', '教育', 
        '经济管理', '法律', '哲学宗教', '生活休闲', '少儿读物', '其他'
    ]
    categories = [{'category': cat} for cat in all_categories]
    
    return render_template('announcement_management_simple.html',
                         module=module,
                         templates=templates,
                         records=records,
                         all_templates=all_templates,
                         search=search,
                         status=status,
                         start_date=start_date,
                         end_date=end_date,
                         categories=categories)

@app.route('/template/create', methods=['POST'])
@admin_required
def create_template():
    """创建推文模板"""
    db = get_db()
    
    name = request.form.get('name')
    title = request.form.get('title')
    content = request.form.get('content')
    target_type = request.form.get('target_type', 'all')
    
    if not name or not title or not content:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    db.execute('''
        INSERT INTO announcement_templates (name, title, content, target_type)
        VALUES (?, ?, ?, ?)
    ''', (name, title, content, target_type))
    
    db.commit()
    return jsonify({'success': True, 'message': '模板新增成功'})

@app.route('/template/<int:template_id>/edit', methods=['POST'])
@admin_required
def edit_template(template_id):
    """编辑推文模板"""
    db = get_db()
    
    name = request.form.get('name')
    title = request.form.get('title')
    content = request.form.get('content')
    target_type = request.form.get('target_type', 'all')
    
    if not name or not title or not content:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    db.execute('''
        UPDATE announcement_templates
        SET name = ?, title = ?, content = ?, target_type = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (name, title, content, target_type, template_id))
    
    db.commit()
    return jsonify({'success': True, 'message': '模板编辑成功'})

@app.route('/template/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_template(template_id):
    """删除公告模板"""
    db = get_db()
    
    db.execute('DELETE FROM announcement_templates WHERE id = ?', (template_id,))
    db.commit()
    return jsonify({'success': True, 'message': '模板删除成功'})

@app.route('/quick_push', methods=['POST'])
@admin_required
def quick_push():
    """快捷推送"""
    db = get_db()
    
    template_id = request.form.get('template_id')
    title = request.form.get('title')
    content = request.form.get('content')
    target_type = request.form.get('target_type', 'all')
    
    if not title or not content:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    # 获取模板名称
    template_name = ''
    if template_id:
        template = db.execute('SELECT name FROM announcement_templates WHERE id = ?', (template_id,)).fetchone()
        if template:
            template_name = template['name']
    
    # 模拟推送（实际应用中需要调用微信API）
    import random
    success = random.random() > 0.1  # 90%成功率
    status = 'success' if success else 'failed'
    error_message = None if success else '推送超时，请重试'
    
    db.execute('''
        INSERT INTO announcement_push_records (template_id, template_name, title, content, target_type, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (template_id, template_name, title, content, target_type, status, error_message))
    
    # 向符合条件的用户发送消息
    if success:
        # 获取目标用户
        if target_type == 'all':
            users = db.execute('SELECT id FROM users WHERE is_active = 1').fetchall()
        elif target_type == 'user':
            users = db.execute('SELECT id FROM users WHERE is_active = 1 AND is_admin = 0').fetchall()
        elif target_type == 'admin':
            users = db.execute('SELECT id FROM users WHERE is_active = 1 AND is_admin = 1').fetchall()
        else:
            users = []
        
        # 向用户发送消息
        for user in users:
            db.execute('''
                INSERT INTO messages (user_id, title, content)
                VALUES (?, ?, ?)
            ''', (user['id'], title, content))
    
    db.commit()
    
    if success:
        return jsonify({'success': True, 'message': '推送已发出'})
    else:
        return jsonify({'success': False, 'message': '推送失败，请查看推送记录'})

@app.route('/api/template/<int:template_id>')
@admin_required
def get_template(template_id):
    """获取模板详情API"""
    db = get_db()
    template = db.execute('SELECT * FROM announcement_templates WHERE id = ?', (template_id,)).fetchone()
    
    if template:
        return jsonify({'success': True, 'template': dict(template)})
    else:
        return jsonify({'success': False, 'message': '模板不存在'})

@app.route('/api/messages')
@login_required
def get_messages():
    """获取用户消息"""
    db = get_db()
    user_id = g.user['id']
    
    # 获取未读消息
    messages = db.execute('''
        SELECT id, title, content, created_at
        FROM messages
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    # 将消息标记为已读
    if messages:
        message_ids = [msg['id'] for msg in messages]
        placeholders = ','.join('?' for _ in message_ids)
        db.execute(f'''
            UPDATE messages
            SET is_read = 1
            WHERE id IN ({placeholders})
        ''', message_ids)
        db.commit()
    
    return jsonify({
        'success': True,
        'messages': [dict(msg) for msg in messages]
    })

@app.route('/api/messages/all')
@login_required
def get_all_messages():
    """获取用户所有消息"""
    db = get_db()
    user_id = g.user['id']
    
    # 获取所有消息
    messages = db.execute('''
        SELECT id, title, content, is_read, created_at
        FROM messages
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    
    return jsonify({
        'success': True,
        'messages': [dict(msg) for msg in messages]
    })

@app.route('/api/messages/mark-all-read', methods=['POST'])
@login_required
def mark_all_messages_as_read():
    """标记所有消息为已读"""
    db = get_db()
    user_id = g.user['id']
    
    # 标记所有消息为已读
    db.execute('''
        UPDATE messages
        SET is_read = 1
        WHERE user_id = ?
    ''', (user_id,))
    db.commit()
    
    return jsonify({
        'success': True,
        'message': '所有消息已标记为已读'
    })

@app.route('/api/push_record/<int:record_id>')
@admin_required
def get_push_record(record_id):
    """获取推送记录详情API"""
    db = get_db()
    record = db.execute('SELECT * FROM announcement_push_records WHERE id = ?', (record_id,)).fetchone()
    
    if record:
        return jsonify({'success': True, 'record': dict(record)})
    else:
        return jsonify({'success': False, 'message': '推送记录不存在'})

# =======================================
# API配置管理模块
# =======================================

@app.route('/ai_api_config')
@admin_required
def ai_api_config():
    """API配置管理页面"""
    return render_template('ai_api_config.html')

@app.route('/api/ai_api_config', methods=['GET', 'POST'])
@admin_required
def api_ai_api_config():
    """API配置管理接口"""
    db = get_db()
    
    if request.method == 'POST':
        data = request.get_json()
        provider_name = data.get('provider_name')
        api_endpoint = data.get('api_endpoint')
        api_key = data.get('api_key')
        is_active = data.get('is_active', 0)
        
        if not all([provider_name, api_endpoint, api_key]):
            return jsonify({'success': False, 'message': '请填写所有必填字段'})
        
        try:
            if is_active:
                db.execute('UPDATE ai_api_config SET is_active = 0')
            
            db.execute('''
                INSERT INTO ai_api_config (provider_name, api_endpoint, api_key, is_active)
                VALUES (?, ?, ?, ?)
            ''', (provider_name, api_endpoint, api_key, is_active))
            db.commit()
            
            return jsonify({'success': True, 'message': '配置保存成功'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': '该服务提供商已存在'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    else:
        try:
            configs = db.execute('SELECT * FROM ai_api_config ORDER BY created_at DESC').fetchall()
            config_list = [dict(config) for config in configs]
            return jsonify({'success': True, 'configs': config_list})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai_api_config/<int:config_id>', methods=['DELETE'])
@admin_required
def delete_ai_api_config(config_id):
    """删除API配置"""
    db = get_db()
    try:
        db.execute('DELETE FROM ai_api_config WHERE id = ?', (config_id,))
        db.commit()
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai_api_config/<int:config_id>/set_active', methods=['POST'])
@admin_required
def set_active_ai_api_config(config_id):
    """设置API配置为默认"""
    db = get_db()
    try:
        db.execute('UPDATE ai_api_config SET is_active = 0')
        db.execute('UPDATE ai_api_config SET is_active = 1 WHERE id = ?', (config_id,))
        db.commit()
        return jsonify({'success': True, 'message': '设置成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai_api_config/active', methods=['GET'])
@login_required
def get_active_ai_api_config():
    """获取当前激活的API配置"""
    db = get_db()
    try:
        config = db.execute('SELECT * FROM ai_api_config WHERE is_active = 1').fetchone()
        if config:
            return jsonify({'success': True, 'config': dict(config)})
        else:
            return jsonify({'success': False, 'message': '未找到激活的API配置'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# =======================================
# 数据统计模块
# =======================================

@app.route('/ai_recommendation')
@login_required
def ai_recommendation():
    """AI图书推荐页面"""
    return render_template('ai_recommendation.html')

@app.route('/dashboard')
@admin_required
def dashboard():
    """数据统计页面"""
    return render_template('dashboard.html')


@app.route('/api/books')
@admin_required

def api_books():
    """根据筛选条件返回图书列表（主要供统计面板等使用）"""
    db = get_db()
    stock_status = request.args.get('stock_status', '')
    query = 'SELECT id, title, author, available_copies, total_copies FROM books WHERE 1=1'
    params = []

    if stock_status:
        if stock_status == '充足':
            query += ' AND total_copies > 1'
        elif stock_status == '不足':
            query += ' AND total_copies <= 1 AND (status = "可借阅" OR status IS NULL)'
        elif stock_status == '无库存':
            query += ' AND total_copies = 0'

    books = db.execute(query, params).fetchall()
    return jsonify({'success': True, 'books': [dict(b) for b in books]})


@app.route('/api/dashboard/stats')
@admin_required
def dashboard_stats():
    """获取统计数据"""
    db = get_db()
    
    # 图书总库存
    total_books = db.execute('SELECT SUM(total_copies) FROM books').fetchone()[0] or 0
    
    # 可借数量
    available_books = db.execute('SELECT SUM(available_copies) FROM books WHERE status = "可借阅"').fetchone()[0] or 0
    
    # 今日借阅数
    today = datetime.now().strftime('%Y-%m-%d')
    today_loans = db.execute('''
        SELECT COUNT(*) FROM loans 
        WHERE DATE(loan_date) = ?
    ''', (today,)).fetchone()[0] or 0
    
    # 逾期记录数
    overdue_loans = db.execute('''
        SELECT COUNT(*) FROM loans 
        WHERE is_returned = 0 AND due_date < ?
    ''', (datetime.now(),)).fetchone()[0] or 0
    
    # 库存预警数（总库存小于等于1的图书）
    low_stock_books = db.execute('''
        SELECT COUNT(*) FROM books 
        WHERE total_copies <= 1 AND (status = "可借阅" OR status IS NULL)
    ''').fetchone()[0] or 0
    
    return jsonify({
        'success': True,
        'stats': {
            'total_books': total_books,
            'available_books': available_books,
            'today_loans': today_loans,
            'overdue_loans': overdue_loans,
            'low_stock_books': low_stock_books
        }
    })

@app.route('/api/dashboard/category_distribution')
@admin_required
def category_distribution():
    """获取图书分类占比数据"""
    db = get_db()
    
    categories = db.execute('''
        SELECT category, COUNT(*) as count 
        FROM books 
        WHERE category IS NOT NULL 
        GROUP BY category 
        ORDER BY count DESC
    ''').fetchall()
    
    data = [{'category': row['category'], 'count': row['count']} for row in categories]
    
    return jsonify({
        'success': True,
        'data': data
    })

@app.route('/api/dashboard/monthly_loans')
@admin_required
def monthly_loans():
    """获取月度借阅量趋势数据"""
    db = get_db()
    
    # 获取最近6个月的数据
    monthly_data = db.execute('''
        SELECT 
            strftime('%Y-%m', loan_date) as month,
            COUNT(*) as count
        FROM loans
        WHERE loan_date >= date('now', '-6 months')
        GROUP BY month
        ORDER BY month
    ''').fetchall()
    
    data = [{'month': row['month'], 'count': row['count']} for row in monthly_data]
    
    return jsonify({
        'success': True,
        'data': data
    })

@app.route('/api/dashboard/user_distribution')
@admin_required
def user_distribution():
    """获取最近30天借出图书的类型分布数据"""
    db = get_db()
    
    # 计算最近30天的日期
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # 统计最近30天各类型图书的借阅数量
    category_stats = db.execute('''
        SELECT b.category, COUNT(*) as count
        FROM loans l
        JOIN books b ON l.book_id = b.id
        WHERE l.loan_date >= ?
        GROUP BY b.category
        ORDER BY count DESC
    ''', (thirty_days_ago,)).fetchall()
    
    data = [{'type': row[0], 'count': row[1]} for row in category_stats]
    
    return jsonify({
        'success': True,
        'data': data
    })

@app.route('/api/dashboard/export_report', methods=['POST'])
@admin_required
def export_report():
    """导出报表"""
    import csv
    from io import StringIO
    import json
    
    data = request.get_json()
    report_type = data.get('report_type')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    filters = data.get('filters', {})
    file_format = data.get('format', 'csv')
    
    db = get_db()
    
    if report_type == 'monthly_loans':
        # 月度借阅报表
        query = '''
            SELECT 
                u.username,
                b.title,
                b.author,
                l.loan_date,
                l.due_date,
                l.return_date,
                CASE WHEN l.is_returned = 1 THEN '已归还' ELSE '未归还' END as status
            FROM loans l
            JOIN users u ON l.user_id = u.id
            JOIN books b ON l.book_id = b.id
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += ' AND DATE(l.loan_date) >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND DATE(l.loan_date) <= ?'
            params.append(end_date)
        
        query += ' ORDER BY l.loan_date DESC'
        
        records = db.execute(query, params).fetchall()
        
        # 生成CSV文件
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['用户名', '书名', '作者', '借阅日期', '应还日期', '归还日期', '状态'])
        
        for record in records:
            writer.writerow([
                record['username'],
                record['title'],
                record['author'],
                record['loan_date'],
                record['due_date'],
                record['return_date'] or '',
                record['status']
            ])
        
        output.seek(0)
        
        # 记录报表导出信息
        report_name = f"月度借阅报表_{start_date}_{end_date}"
        db.execute('''
            INSERT INTO reports (report_type, report_name, start_date, end_date, filters, file_format, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (report_type, report_name, start_date, end_date, json.dumps(filters), file_format, session.get('user_id')))
        db.commit()
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={report_name}.csv'}
        )
    
    elif report_type == 'inventory':
        # 库存盘点报表
        query = '''
            SELECT 
                b.isbn,
                b.title,
                b.author,
                b.category,
                b.publisher,
                b.total_copies,
                b.available_copies,
                b.status
            FROM books b
            WHERE 1=1
        '''
        params = []
        
        if filters.get('category'):
            query += ' AND b.category = ?'
            params.append(filters['category'])
        
        if filters.get('status'):
            query += ' AND b.status = ?'
            params.append(filters['status'])
        
        query += ' ORDER BY b.title'
        
        records = db.execute(query, params).fetchall()
        
        # 生成CSV文件
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ISBN', '书名', '作者', '分类', '出版社', '总库存', '可借数量', '状态'])
        
        for record in records:
            writer.writerow([
                record['isbn'] or '',
                record['title'],
                record['author'],
                record['category'] or '',
                record['publisher'] or '',
                record['total_copies'],
                record['available_copies'],
                record['status']
            ])
        
        output.seek(0)
        
        # 记录报表导出信息
        report_name = f"库存盘点报表_{datetime.now().strftime('%Y%m%d')}"
        db.execute('''
            INSERT INTO reports (report_type, report_name, filters, file_format, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_type, report_name, json.dumps(filters), file_format, session.get('user_id')))
        db.commit()
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={report_name}.csv'}
        )
    
    elif report_type == 'user_credit':
        # 读者信用分报表
        query = '''
            SELECT 
                u.username,
                u.email,
                u.is_admin,
                COUNT(l.id) as total_loans,
                SUM(CASE WHEN l.is_returned = 0 AND l.due_date < datetime('now') THEN 1 ELSE 0 END) as overdue_count,
                SUM(l.fine_amount) as total_fines
            FROM users u
            LEFT JOIN loans l ON u.id = l.user_id
            GROUP BY u.id
            ORDER BY total_loans DESC
        '''
        
        records = db.execute(query).fetchall()
        
        # 生成CSV文件
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['用户名', '邮箱', '角色', '总借阅次数', '逾期次数', '总罚款金额'])
        
        for record in records:
            writer.writerow([
                record['username'],
                record['email'] or '',
                '管理员' if record['is_admin'] else '普通用户',
                record['total_loans'],
                record['overdue_count'],
                record['total_fines'] or 0
            ])
        
        output.seek(0)
        
        # 记录报表导出信息
        report_name = f"读者信用分报表_{datetime.now().strftime('%Y%m%d')}"
        db.execute('''
            INSERT INTO reports (report_type, report_name, file_format, created_by)
            VALUES (?, ?, ?, ?)
        ''', (report_type, report_name, file_format, session.get('user_id')))
        db.commit()
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={report_name}.csv'}
        )
    
    else:
        return jsonify({'success': False, 'message': '不支持的报表类型'})

# =======================================
# 图书封面服务模块
# =======================================

# 获取图书封面接口（支持传递 ISBN 提高精度）
@app.route('/api/book/cover', methods=['GET'])
def get_book_cover():
    """
    获取图书封面接口
    
    Query参数:
        book_name: 书名（必填）
        refresh: 是否刷新缓存，默认为false
    """
    try:
        book_name = request.args.get('book_name', '').strip()
        isbn = request.args.get('isbn', '').strip()
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 获取图书封面请求: 书名={book_name}, 刷新缓存={refresh}")
        
        if not book_name:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 书名不能为空")
            return jsonify(standard_response(
                success=False,
                error='书名不能为空'
            )), 400
        
        # 检查图书是否已经有手动上传的封面
        db = get_db()
        book = db.execute('SELECT cover_image FROM books WHERE title = ?', (book_name,)).fetchone()
        if book and book['cover_image']:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 图书已有手动上传的封面，跳过自动获取: {book_name}")
            return jsonify(standard_response(
                success=True,
                book_name=book_name,
                cover_url='',
                cover_local_path=book['cover_image'],
                book_info={},
                cache_hit=False
            ))
        
        # 如果需要刷新缓存，先删除旧缓存
        if refresh:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 刷新缓存: {book_name}")
            delete_cache_by_book_name(book_name)
        
        # 尝试从缓存中获取
        cache = get_cache_by_book_name(book_name)
        if cache and not refresh:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 缓存命中: {book_name}")
            return jsonify(standard_response(
                success=True,
                book_name=book_name,
                cover_url=cache['cover_url'],
                cover_local_path=cache['cover_local_path'],
                book_info=json.loads(cache['book_info']) if cache['book_info'] else {},
                cache_hit=True
            ))
        
        # 从API获取图书信息（优先使用 ISBN）
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 从API获取图书信息: title={book_name}, isbn={isbn}")
        book_info = fetch_book_cover(book_name, isbn=isbn)
        if not book_info:
            # 如果API获取失败，返回默认封面
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] API获取失败，使用默认封面: {book_name}")
            default_cover_path = create_default_cover()
            
            # 保存默认封面到缓存
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 保存默认封面到缓存: {book_name}")
            set_cache_by_book_name(
                book_name=book_name,
                cover_url='',
                cover_local_path=default_cover_path,
                book_info=json.dumps({})
            )
            
            return jsonify(standard_response(
                success=True,
                book_name=book_name,
                cover_url='',
                cover_local_path=default_cover_path,
                book_info={},
                cache_hit=False
            ))
        
        # 下载并保存封面
        cover_url = book_info.get('cover_url', '')
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 下载并保存封面: {cover_url}")
        cover_local_path = get_cover_path(book_name, cover_url)
        
        # 保存到缓存
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 保存到缓存: {book_name}")
        set_cache_by_book_name(
            book_name=book_name,
            cover_url=cover_url,
            cover_local_path=cover_local_path,
            book_info=json.dumps(book_info)
        )
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 获取图书封面成功: {book_name}")
        return jsonify(standard_response(
            success=True,
            book_name=book_name,
            cover_url=cover_url,
            cover_local_path=cover_local_path,
            book_info=book_info,
            cache_hit=False
        ))
    except Exception as e:
        error_msg = f"获取图书封面时发生异常: {str(e)}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}")
        return jsonify(standard_response(
            success=False,
            error=error_msg
        )), 500

# 静态封面图片访问接口
@app.route('/api/book/cover/image/<path:filename>')
def get_cover_image(filename):
    """
    静态封面图片访问接口
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 访问封面图片: {filename}")
        cover_dir = os.path.join(app.root_path, 'static', 'book_covers')
        return send_from_directory(cover_dir, filename)
    except Exception as e:
        error_msg = f"访问封面图片时发生异常: {str(e)}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}")
        return jsonify(standard_response(
            success=False,
            error=error_msg
        )), 500

# 清理过期缓存接口
@app.route('/api/book/cover/clean_cache', methods=['POST'])
def clean_cache():
    """
    清理过期缓存接口
    """
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 清理过期缓存")
        deleted_count = clean_expired_cache()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 清理完成，删除了 {deleted_count} 条过期缓存记录")
        return jsonify({
            'success': True,
            'message': f'清理完成，删除了 {deleted_count} 条过期缓存记录'
        })
    except Exception as e:
        error_msg = f"清理过期缓存时发生异常: {str(e)}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

# 删除指定图书缓存接口
@app.route('/api/book/cover/delete_cache', methods=['POST'])
def delete_cache():
    """
    删除指定图书缓存接口
    
    JSON参数:
        book_name: 书名（必填）
    """
    try:
        data = request.get_json() or {}
        book_name = data.get('book_name', '').strip()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 删除指定图书缓存请求: {book_name}")
        
        if not book_name:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 书名不能为空")
            return jsonify(standard_response(
                success=False,
                error='书名不能为空'
            )), 400
        
        deleted = delete_cache_by_book_name(book_name)
        if deleted:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 缓存删除成功: {book_name}")
            return jsonify({
                'success': True,
                'message': f'缓存删除成功: {book_name}'
            })
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] 缓存删除失败: {book_name}")
            return jsonify({
                'success': False,
                'message': f'缓存删除失败: {book_name}'
            })
    except Exception as e:
        error_msg = f"删除指定图书缓存时发生异常: {str(e)}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}")
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

# 更新图书封面到数据库
@app.route('/api/book/cover/update', methods=['POST'])
def update_book_cover():
    """
    更新图书封面到数据库
    
    JSON参数:
        book_title: 书名（必填）
        cover_local_path: 封面本地路径（必填）
    """
    try:
        data = request.get_json() or {}
        book_title = data.get('book_title', '').strip()
        cover_local_path = data.get('cover_local_path', '').strip()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 更新图书封面请求: 书名={book_title}, 封面路径={cover_local_path}")
        
        if not book_title or not cover_local_path:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 书名和封面路径不能为空")
            return jsonify(standard_response(
                success=False,
                error='书名和封面路径不能为空'
            )), 400
        
        db = get_db()
        # 更新图书封面
        updated_count = db.execute('''
            UPDATE books 
            SET cover_image = ? 
            WHERE title = ?
        ''', (cover_local_path, book_title)).rowcount
        
        db.commit()
        
        if updated_count > 0:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] 图书封面更新成功: {book_title}")
            return jsonify({
                'success': True,
                'message': f'图书封面更新成功: {book_title}'
            })
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] 未找到匹配的图书: {book_title}")
            return jsonify({
                'success': False,
                'message': f'未找到匹配的图书: {book_title}'
            })
    except Exception as e:
        error_msg = f"更新图书封面时发生异常: {str(e)}"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}")
        return jsonify(standard_response(
            success=False,
            error=error_msg
        )), 500

if __name__ == '__main__':
    # 初始化数据库
    with app.app_context():
        init_db()
        init_cache()
        clean_expired_cache()  # 启动时清理过期缓存
    
    print("=" * 50)
    print("🎉 图书馆管理系统启动成功！")
    print("🌐 访问地址: http://127.0.0.1:5000")
    print("👤 默认管理员: admin / admin123")
    print("🖼️  图书封面服务已就绪")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
