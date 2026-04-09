import sqlite3
conn = sqlite3.connect('library.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM loan_requests WHERE status IN ("pending", "approved")')
print('借阅请求数量:', c.fetchone()[0])
conn.close()