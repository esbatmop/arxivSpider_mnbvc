import os
import time
from loguru import logger
import traceback
import requests
import random
import jsonlines
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import argparse
import itertools
from concurrent.futures import as_completed
from bs4 import BeautifulSoup
import copy

# 创建一个Session对象
session = requests.Session()

# 创建一个URL列表
url_list = ['http://cn.arxiv.org/', 'http://export.arxiv.org/', 'http://de.arxiv.org/', 'https://arxiv.org/', 'http://xxx.itp.ac.cn/']

def get_pdf_link(url):
    headers = {'User-Agent': 'Lynx/2.8.8dev.3 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/3.6.16'}
    has_source = True
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 在arXiv网站中，PDF链接通常在"Download"部分下的"PDF"链接
        pdf_links = soup.find_all('a', string=['PDF only', 'PDF'])

        # 获取输入URL的前缀，然后将其添加到PDF链接前面
        url_prefix = url.split('/abs')[0]

        for link in pdf_links:
            if link.text == 'PDF only':
                has_source = False
                return url_prefix + link['href'], has_source
            elif link.text == 'PDF':
                return url_prefix + link['href'], has_source

        return None, has_source
    except Exception as e:
        logger.error(f"Error in get_pdf_link: {e}, URL: {url}")
        return None, has_source
    
def crawl(pid, file_type, headers=None):
    headers = {'User-Agent': 'Lynx/2.8.8dev.3 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/3.6.16'}
    has_source = True  # 初始化has_source为True
    
    # 根据file_type构造URL的后缀
    url_suffix = 'e-print/' if file_type == 'source' else 'abs/'
    
    url_list_copy = copy.copy(url_list)
    # 打乱URL列表顺序
    random.shuffle(url_list_copy)
    
    while url_list_copy:
        base_url = url_list_copy.pop()  # 从列表中获取并移除一个URL
        try:
            # 构造URL
            url = base_url + url_suffix + pid
            # 如果我们正在下载PDF文件，我们需要使用get_pdf_link函数获取URL
            if file_type == 'pdf':
                pdf_url, has_source = get_pdf_link(url)
                if pdf_url is None:
                    continue
                resp = session.get(pdf_url, timeout=30)
                # time.sleep(1)  # 如果爬太快被反爬，就把这一行的注释去掉
            else:
                resp = session.get(url, timeout=30)
                # time.sleep(1)  # 如果爬太快被反爬，就把这一行的注释去掉
            for i in range(retry_times):
                if resp.status_code == 200:
                    break
                resp = session.get(url, headers=headers, timeout=30)
                time.sleep(2)  # 如果爬太快被反爬，就把这一行的注释去掉
            return resp, has_source
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}, URL: {url}")
            # 如果我们已经尝试了所有的URL，那么我们返回None
            if not url_list:
                return None, False
            # 否则，我们继续下一个URL
            continue
    
    return None, False


def download_files(j, out_folder):
    pid = j['id']

    if out_folder is None:
        out_folder = "download"

    # 生成输出目录
    pdf_out_folder = os.path.join(out_folder, pid.replace('/', '_'),'pdf') 
    # 带有replace的部分是因为有的pid里存在 '/' 符号
    source_out_folder = os.path.join(out_folder, pid.replace('/','_'), 'source') 
    pdf_out_path = os.path.join(pdf_out_folder, pid.replace('/','_')+'.pdf')
    source_out_path = os.path.join(source_out_folder, pid.replace('/','_'))
    # Delivered as a gzipped tar (.tar.gz) file if there are multiple files, 
    # otherwise as a PDF file, or a gzipped TeX, DVI, PostScript or HTML (
    # .gz, .dvi.gz, .ps.gz or .html.gz) file depending on submission format.
    
    # 检查文件是否已经下载
    if os.path.exists(pdf_out_path) and os.path.exists(source_out_path):
        logger.info(f'Files {pid} already downloaded, skip.')
        return
    
    # 下载pdf文件
    pdf_resp, has_source = crawl(pid, 'pdf') 
    pdf_status = pdf_resp.status_code if pdf_resp else None
    # 下载source文件
    source_resp = None
    source_status = None
    if has_source:  # 如果存在源文件，我们才下载源文件
        source_resp, _ = crawl(pid, 'source') 
        source_status = source_resp.status_code if source_resp else None
    else:
        logger.info(f"No source file for paper {pid}")
    
    if pdf_status == 200:
        os.makedirs(pdf_out_folder, exist_ok=True)
        with open(pdf_out_path, 'wb')as wb: wb.write(pdf_resp.content)
        logger.info(f"Successfully downloaded PDF file {pid}")  
    else: 
        pdf_out_path = ""
        logger.error(f"Failed to download PDF file {pid}")
    if source_status == 200:
        os.makedirs(source_out_folder, exist_ok=True)
        with open(source_out_path, 'wb')as wb: wb.write(source_resp.content)
        logger.info(f"Successfully downloaded source file {pid}")
    elif source_status is not None:
        source_out_path = ""
        logger.error(f"Failed to download source file {pid}")

    if pdf_out_path == '' or source_out_path == '':
        logger.warning(f'{pid} {pdf_status} {source_status} | Can not found.')

def worker(obj, out_folder):
    try:
        download_files(obj, out_folder)
    except ConnectionResetError:
        logger.error(f"Connection reset error: {obj['id']}")
    except requests.exceptions.ProxyError:
        logger.error(f"Requests proxy error: {obj['id']}")
    except Exception as e:
        logger.error(f"Other exception: {obj['id']}\n\t{e}\n\t{traceback.format_exc()}")

def main():
    all_counter = 0
    if not os.path.exists(meta_file):
        logger.error('没有找到arxiv论文元信息文件')
        return
    read_iter = iter(jsonlines.open(meta_file))
    
    if max_files > 0:
        # 只读取前100个元数据，调试用
        read_iter = itertools.islice(read_iter, max_files)
    
    for obj in tqdm(read_iter, ncols=100, desc='完成进度'):
        try:
            worker(obj, out_folder)
        except ConnectionResetError:
            logger.error(f"Connection reset error: {obj['id']}")
        except requests.exceptions.ProxyError:
            logger.error(f"Requests proxy error: {obj['id']}")
        except Exception as e:
            logger.error(f"Other exception: {obj['id']}\n\t{e}\n\t{traceback.format_exc()}")
        all_counter += 1 
        if all_counter % log_interval == 0:
            logger.info(f'已获取{all_counter}篇论文。')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--meta_file', default='./arxiv-metadata-oai-snapshot.json', help='存储arxiv论文元信息的文件地址')
    parser.add_argument('--retry_times', type=int, default=3, help='对同一个url最多重试次数')
    parser.add_argument('--log_interval', type=int, default=10, help='间隔多少篇文章打印一次信息')
    parser.add_argument('--max_files', type=int, default=100, help='调试用，最大论文爬取数量，设置为0时，则全部爬取。')
    parser.add_argument('--out_folder', default='./download', help='下载的文件夹位置')
    args = parser.parse_args()
    
    log_dir = './log'  # log文件夹的路径
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    error_log_file = f'./{log_dir}/error_log_{timestamp}.log'  
    
    meta_file = args.meta_file  # 存储arxiv论文元信息的文件地址
    retry_times = args.retry_times  # 对同一个url最多重试次数
    log_interval = args.log_interval  # 间隔多少篇文章打印一次信息
    max_files = args.max_files  # 调试用，最大论文爬取数量，设置为0时，则全部爬取。
    out_folder = args.out_folder  # 下载的文件夹位置
    
    logger.add(error_log_file, rotation="500 MB")  # 使用loguru记录日志
    
    main()
