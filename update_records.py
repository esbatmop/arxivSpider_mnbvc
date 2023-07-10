import os
import jsonlines
import time
from loguru import logger
from tqdm import tqdm

# 设置日志文件的路径
logger.add("./log/update_records_{time}.log")

def update_records(jsonl_file, updated_jsonl_file, main_folder):
    data = []
    with jsonlines.open(jsonl_file, mode='r') as reader:
        for i, line in enumerate(reader.iter(type=dict, skip_invalid=True), 1):
            data.append(line)
            if not line:
                logger.error(f"Invalid JSON at line {i}")

    for obj in tqdm(data, ncols=100):
        pid = obj.get('id')
        if pid:
            pdf_out_folder = os.path.join(main_folder, pid.replace('/','_'), 'pdf')
            source_out_folder = os.path.join(main_folder, pid.replace('/','_'), 'source')
            pdf_out_path = os.path.join(pdf_out_folder, pid.replace('/','_')+'.pdf')
            source_out_path = os.path.join(source_out_folder, pid.replace('/','_'))

            if os.path.exists(pdf_out_path) and obj.get('pdf_status') is None:
                obj['pdf_path'] = pdf_out_path
                obj['pdf_status'] = 'downloaded'
                obj['download_time'] = time.strftime('%Y-%m-%d')
                logger.info(f"Updated record for PDF file at path: {pdf_out_path}")

            if os.path.exists(source_out_path) and obj.get('source_status') is None:
                obj['source_path'] = source_out_path
                obj['source_status'] = 'downloaded'
                if obj.get('download_time') is None:
                    obj['download_time'] = time.strftime('%Y-%m-%d')
                logger.info(f"Updated record for source file at path: {source_out_path}")

    with jsonlines.open(updated_jsonl_file, mode='w') as writer:
        writer.write_all(data)

# 设置你的参数
jsonl_file = './log/spider_log.jsonl'  # 将这里替换为你的jsonl文件名
updated_jsonl_file = './log/spider_log_new.jsonl'  # 将这里替换为你希望的新文件名

main_folder = './download'  # 将这里替换为你的主文件夹路径

# 调用函数
update_records(jsonl_file, updated_jsonl_file, main_folder)
