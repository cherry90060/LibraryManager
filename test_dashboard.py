from app_simple import app, get_db
import json

# 测试数据统计API接口
print('测试数据统计API接口...')

with app.test_client() as client:
    # 登录管理员账户
    login_response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123'
    })
    print(f'登录状态码: {login_response.status_code}')
    
    # 测试统计数据API
    print('\n测试统计数据API:')
    stats_response = client.get('/api/dashboard/stats', headers={
        'Accept': 'application/json'
    })
    print(f'状态码: {stats_response.status_code}')
    print(f'响应内容: {stats_response.json}')
    
    # 测试分类占比API
    print('\n测试分类占比API:')
    category_response = client.get('/api/dashboard/category_distribution', headers={
        'Accept': 'application/json'
    })
    print(f'状态码: {category_response.status_code}')
    print(f'响应内容: {category_response.json}')
    
    # 测试月度借阅量API
    print('\n测试月度借阅量API:')
    monthly_response = client.get('/api/dashboard/monthly_loans', headers={
        'Accept': 'application/json'
    })
    print(f'状态码: {monthly_response.status_code}')
    print(f'响应内容: {monthly_response.json}')
    
    # 测试读者类型分布API
    print('\n测试读者类型分布API:')
    user_response = client.get('/api/dashboard/user_distribution', headers={
        'Accept': 'application/json'
    })
    print(f'状态码: {user_response.status_code}')
    print(f'响应内容: {user_response.json}')
    
    # 测试库存预警API
    print('\n测试库存预警API:')
    low_stock_response = client.get('/api/books?stock_status=不足', headers={
        'Accept': 'application/json'
    })
    print(f'状态码: {low_stock_response.status_code}')
    print(f'响应内容: {low_stock_response.json}')
    
    # 测试新增图书自动获取封面
    print('\n测试新增图书自动获取封面:')
    new_book_data = {
        'title': 'Python编程：从入门到实践',
        'author': 'Eric Matthes',
        'isbn': '9787115428028',
        'publisher': '电子工业出版社',
        'publish_date': '',
        'category': '计算机',
        'total_copies': 1,
        'status': '可借阅',
        'description': ''
    }
    # 先删除可能已存在的同ISBN图书
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM books WHERE isbn = ?', (new_book_data['isbn'],))
        db.commit()
    create_resp = client.post('/book/create', data=new_book_data, headers={'Accept': 'application/json'})
    print(f'状态码: {create_resp.status_code}, 内容: {create_resp.json}')
    assert create_resp.status_code == 200
    assert create_resp.json.get('success')
    # 验证数据库中是否已保存封面路径
    with app.app_context():
        db = get_db()
        row = db.execute('SELECT cover_image FROM books WHERE isbn = ?', (new_book_data['isbn'],)).fetchone()
        print('数据库封面路径:', row['cover_image'] if row else None)
        assert row and row['cover_image']

    # 测试报表导出API
    print('\n测试报表导出API:')
    export_data = {
        'report_type': 'inventory',
        'format': 'csv',
        'filters': {}
    }
    export_response = client.post('/api/dashboard/export_report', 
        data=json.dumps(export_data),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    )
    print(f'状态码: {export_response.status_code}')
    if export_response.status_code == 200:
        print(f'报表导出成功，文件大小: {len(export_response.data)} bytes')
    else:
        print(f'响应内容: {export_response.json}')
