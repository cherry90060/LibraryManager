import requests
import os

# 下载默认封面图片
def download_default_cover():
    # 默认封面图片URL - 使用一个可靠的默认封面图片URL
    url = "https://via.placeholder.com/400x600?text=No+Cover"
    
    # 保存路径
    save_path = "D:\\LibraryManger-main\\static\\book_covers\\default_cover.jpg"
    
    try:
        # 发送请求
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # 保存图片
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        print(f"默认封面图片下载成功，保存到: {save_path}")
        print(f"文件大小: {os.path.getsize(save_path)} 字节")
    except Exception as e:
        print(f"下载默认封面图片时出错: {e}")

if __name__ == "__main__":
    download_default_cover()