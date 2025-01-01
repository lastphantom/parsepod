from flask import Flask, request, jsonify, render_template, redirect
import requests
import re
import logging
from bs4 import BeautifulSoup

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# 添加CORS支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 添加安全相关的响应头
@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

def extract_title(soup):
    # 尝试从多个可能的位置提取标题
    title = None
    # 尝试从 meta 标签提取
    meta_title = soup.find('meta', property='og:title')
    if meta_title:
        title = meta_title.get('content')
    
    # 如果 meta 标签没有找到，尝试从 h1 标签提取
    if not title:
        h1_title = soup.find('h1')
        if h1_title:
            title = h1_title.text.strip()
    
    # 如果还是没找到，尝试从 title 标签提取
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
    
    return title

def extract_audio_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.xiaoyuzhoufm.com/'
    }
    
    try:
        logging.info(f"正在请求页面: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title = extract_title(soup)
        
        # 从script标签中提取音频链接
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                content = script.string
                audio_patterns = [
                    r'https://media\.xyzcdn\.net/[^"\']+\.m4a',
                    r'https://cdn\.xiaoyuzhoufm\.com/[^"\']+\.m4a',
                    r'https://[^"\']+/audio/[^"\']+\.m4a',
                    r'"url":"(https://[^"]+\.m4a)"',
                    r'"audioUrl":"(https://[^"]+\.m4a)"'
                ]
                
                for pattern in audio_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        audio_url = matches[0] if '(' in pattern else matches[0]
                        logging.info(f"找到音频链接: {audio_url}")
                        return audio_url, title
        
        raise Exception('未找到音频下载地址')
            
    except requests.RequestException as e:
        logging.error(f"请求失败: {e}")
        raise Exception(f'获取播客数据失败: {str(e)}')
    except Exception as e:
        logging.error(f"处理失败: {e}")
        raise

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse_podcast():
    try:
        url = request.json.get('url')
        logging.info(f"收到解析请求，URL: {url}")
        
        if not url:
            return jsonify({'error': '请提供播客链接'}), 400

        audio_url, title = extract_audio_url(url)
        logging.info("成功获取音频链接和标题")
        
        return jsonify({
            'audio_url': audio_url,
            'title': title
        })
    except Exception as e:
        logging.error(f"处理请求失败: {str(e)}")
        logging.exception("详细错误信息：")
        return jsonify({'error': f"处理请求失败: {str(e)}"}), 500

@app.before_request
def redirect_to_https():
    if not request.is_secure and request.environ.get('HTTP_X_FORWARDED_PROTO', 'http') != 'https':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

@app.before_request
def redirect_to_www():
    if not request.host.startswith('www.'):
        url = request.url.replace('://', '://www.', 1)
        return redirect(url, code=301)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
