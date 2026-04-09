import sqlite3

# 连接到数据库
conn = sqlite3.connect('library.db')
cursor = conn.cursor()

# 查询图书封面信息
cursor.execute('SELECT id, title, cover_image FROM books LIMIT 10')

# 打印结果
print('ID | 书名 | 封面图片')
print('-' * 50)
for row in cursor.fetchall():
    print(f'{row[0]} | {row[1]} | {row[2]}')

# 关闭连接
conn.close()