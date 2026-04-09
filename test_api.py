import requests
import json

# 直接测试Google Books API
print("直接测试Google Books API...")
book_name = "Python编程：从入门到实践"
url = "https://www.googleapis.com/books/v1/volumes"
params = {
    "q": book_name,
    "maxResults": 5,
    "fields": "items(id,volumeInfo(title,authors,publisher,description,industryIdentifiers,imageLinks,printType))",
    "key": "AIzaSyCNFpKkxKT3D0iXC3Smm-44CZ11kI_wuos"
}
response = requests.get(url, params=params)
print(f"状态码: {response.status_code}")
print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
print()

# 测试获取图书封面API
print("测试获取图书封面API...")
book_name = "Python编程：从入门到实践"
url = f"http://127.0.0.1:5000/api/book/cover?book_name={book_name}&refresh=true"
response = requests.get(url)
print(f"状态码: {response.status_code}")
print(f"响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
print()