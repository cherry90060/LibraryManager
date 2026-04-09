from app_simple import app, get_db
from datetime import datetime, timedelta

# 测试修复后的借阅功能
print('测试修复后的借阅功能...')

with app.app_context():
    db = get_db()
    
    # 查询借阅记录
    loans = db.execute('''
        SELECT l.*, b.title, b.author, b.isbn
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        ORDER BY l.loan_date DESC
        LIMIT 5
    ''').fetchall()
    
    print(f'找到 {len(loans)} 条借阅记录')
    
    # 测试日期解析
    current_date = datetime.now()
    for loan in loans:
        loan_dict = dict(loan)
        if loan_dict['due_date']:
            try:
                due_date = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S.%f')
                print(f'✓ 成功解析日期（带微秒）: {loan_dict["due_date"]}')
            except ValueError:
                try:
                    due_date = datetime.strptime(loan_dict['due_date'], '%Y-%m-%d %H:%M:%S')
                    print(f'✓ 成功解析日期（不带微秒）: {loan_dict["due_date"]}')
                except ValueError as e:
                    print(f'✗ 日期解析失败: {loan_dict["due_date"]}, 错误: {e}')
            
            loan_dict['is_overdue'] = not loan_dict['is_returned'] and current_date > due_date
            print(f'  书名: {loan_dict["title"]}, 逾期: {loan_dict["is_overdue"]}')
    
    print('\n日期解析测试完成！')
