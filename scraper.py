import requests
import os
import time
import re
from bs4 import BeautifulSoup
from PIL import Image

# --- 辅助函数 ---

def sanitize_filename(filename):
    """清理文件名，移除在Windows/Mac/Linux上不允许的特殊字符。"""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def create_pdf_from_images(image_folder, pdf_path):
    """将指定文件夹中的所有图片按名称顺序合并成一个PDF文件。"""
    try:
        image_files = sorted([f for f in os.listdir(image_folder) if f.endswith('.png')])
        if not image_files:
            print("PDF生成失败：文件夹中没有找到PNG图片。")
            return

        print(f"正在将 {len(image_files)} 张图片整合为PDF...")
        
        images = []
        first_image_path = os.path.join(image_folder, image_files[0])
        img1 = Image.open(first_image_path).convert('RGB')
        
        for i in range(1, len(image_files)):
            image_path = os.path.join(image_folder, image_files[i])
            img = Image.open(image_path).convert('RGB')
            images.append(img)
            
        img1.save(pdf_path, save_all=True, append_images=images)
        print(f"PDF文件已成功生成: {os.path.basename(pdf_path)}")
    
    except Exception as e:
        print(f"PDF生成过程中发生错误: {e}")

def extract_id_from_input(user_input):
    """智能地从用户输入中提取试卷ID。"""
    user_input = user_input.strip()
    if "gaokaozhitongche.com" in user_input:
        try:
            exam_id = user_input.split('/')[-1]
            if '?' in exam_id:
                exam_id = exam_id.split('?')[0]
            return exam_id
        except IndexError:
            return None
    elif user_input:
        return user_input
    else:
        return None

# --- 核心下载函数 ---

def download_exam_images(exam_id, base_output_dir):
    """
    根据试卷ID下载所有图片，并将所有产物归档到指定的基础输出目录中。
    """
    print("-" * 50)
    print(f"正在处理试卷ID: {exam_id}")
    
    page_url = f"https://app.gaokaozhitongche.com/newsexam/h/{exam_id}"
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    }
    
    # 步骤 1: 访问页面并提取数据
    try:
        print("步骤 1/3: 正在访问页面并提取数据...")
        page_response = requests.get(page_url, headers=headers, timeout=20)
        page_response.raise_for_status()
        
        soup = BeautifulSoup(page_response.text, 'html.parser')

        # 获取标题并创建本次下载的目标文件夹
        title_tag = soup.find('title')
        page_title = title_tag.get_text(strip=True).replace("-高考直通车", "").strip()
        sub_folder_name = sanitize_filename(page_title) or f"试卷_{exam_id}"

        # --- 核心改动：在基础输出目录下创建子文件夹 ---
        target_folder = os.path.join(base_output_dir, sub_folder_name)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        
        print(f"试卷标题: {page_title}")

        # 提取图片链接
        paper_container = soup.find('div', id='paper-img')
        if not paper_container:
            print(f"\n错误：未能找到图片容器！请检查ID或URL是否正确。")
            return

        image_urls = [img['data-imgsrc'] for img in paper_container.find_all('img') if img.has_attr('data-imgsrc')]
        
        total_images = len(image_urls)
        if total_images == 0:
            print("错误：未找到任何可下载的图片。")
            return

        print(f"成功提取到 {total_images} 张图片链接！")
        
    except requests.exceptions.RequestException as e:
        print(f"步骤1失败：网络错误: {e}")
        return
    except Exception as e:
        print(f"步骤1失败：解析页面数据时出错: {e}")
        return
        
    # 步骤 2: 下载所有图片到目标文件夹
    print(f"\n步骤 2/3: 开始下载图片到文件夹 '{target_folder}'")
    for index, image_url in enumerate(image_urls):
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
            
        page_number = index + 1
        file_name = f"page_{page_number:02d}.png"
        file_path = os.path.join(target_folder, file_name)
        
        print(f"({page_number}/{total_images}) 正在下载...")
        
        try:
            image_response = requests.get(image_url, headers=headers, timeout=30)
            image_response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(image_response.content)
            time.sleep(0.3) 
        except requests.exceptions.RequestException as e:
            print(f"下载第 {page_number} 页时发生错误: {e}")

    print("\n所有图片下载完成！")

    # 步骤 3: 自动将图片整合为PDF
    print(f"\n步骤 3/3: 准备生成PDF文件...")
    pdf_filename = f"{sub_folder_name}.pdf"
    # --- 核心改动：PDF也保存在目标文件夹内 ---
    pdf_path = os.path.join(target_folder, pdf_filename)
    create_pdf_from_images(target_folder, pdf_path)
    
    print(f"\n处理完成！所有文件已保存在 '{target_folder}' 文件夹中。")
    print("-" * 50)

# --- 主程序 ---
if __name__ == "__main__":
    # 定义总的输出目录名
    BASE_OUTPUT_DIRECTORY = "下载的试卷"
    
    # 如果总目录不存在，则创建它
    if not os.path.exists(BASE_OUTPUT_DIRECTORY):
        os.makedirs(BASE_OUTPUT_DIRECTORY)

    print("--- 终极版试卷下载器 (自动归档、命名并生成PDF) ---")
    print(f"所有下载内容将保存在 '{BASE_OUTPUT_DIRECTORY}' 文件夹中。")
    
    while True:
        user_input = input("\n请输入试卷的URL或ID (输入 'q' 或 'quit' 退出): ")
        
        if user_input.lower() in ['q', 'quit']:
            print("程序已退出。")
            break
            
        exam_id = extract_id_from_input(user_input)
        
        if exam_id:
            # 将总输出目录名传递给下载函数
            download_exam_images(exam_id, BASE_OUTPUT_DIRECTORY)
        else:
            print("输入无效，请输入一个有效的URL或ID。")