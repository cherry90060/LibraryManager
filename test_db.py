from app_simple import app, get_db

with app.app_context():
    db = get_db()
    print('数据库连接成功')
    
    # 检查books表结构
    cursor = db.execute('PRAGMA table_info(books);')
    print('\nbooks表结构:')
    columns = cursor.fetchall()
    for row in columns:
        print(f'字段: {row[1]}, 类型: {row[2]}')
    
    # 检查books表数据
    print('\nbooks表数据:')
    books = db.execute('SELECT id, title, author FROM books LIMIT 5;').fetchall()
    for book in books:
        print(f'ID: {book[0]}, 书名: {book[1]}, 作者: {book[2]}')
