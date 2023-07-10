# arxivSpider_mnbvc

## 描述

arxivSpider_mnbvc是一个Python项目，用于从Arxiv下载论文。它包含多个脚本，可以并行下载论文，处理网络错误和连接中断，使用随机用户代理来防止被Arxiv封锁，使用进度条显示下载进度，并且可以选择从不同的URL下载论文。这个项目是[MNBVC计划](https://github.com/esbatmop/MNBVC)的一部分。

## 脚本

### arxivSpider.py

这是主程序，用于从Arxiv下载论文。它使用多线程并行下载论文，可以处理网络错误和连接中断。

### single-arxivSpider.py

这个脚本是一个单线程版本的`arxivSpider.py`，用于从Arxiv下载论文。

### update_records.py

这个脚本用于更新已经存在的用于记录已下载论文的jsonline文件。

### run.sh

这是一个bash脚本，用于启动`arxivSpider.py`。

## 使用

运行以下命令来启动主程序：

```bash
python arxivSpider.py
```

你可以使用命令行参数来配置脚本的行为。以下是可用的命令行参数：

- --meta_file: 存储arxiv论文元信息的文件地址，默认为./arxiv-metadata-oai-snapshot.json
- --retry_times: 对同一个url最多重试次数，默认为3
- --log_interval: 间隔多少篇文章打印一次信息，默认为10
- --max_workers: 线程数量，默认为5
- --max_files: 调试用，最大论文爬取数量，设置为0时，则全部爬取，默认为100
- --out_folder: 下载的文件夹位置，默认为./download

例如，如果你想使用10个线程来下载论文，你可以运行以下命令：

```bash
python arxivSpider.py --max_workers 10
```

你也可以在bash脚本中进行设置，并且直接启动bash脚本：

```bash
bash run.sh
```

要更新已下载论文的记录，你需要修改`update_records.py`中的参数，然后运行以下命令：

```bash
python update_records.py
```

它接受以下三个参数：

- `jsonl_file`：这是一个已经存在的jsonline文件，该文件记录了已经下载的论文。
- `updated_jsonl_file`：这是一个新的jsonline文件，该文件将包含更新后的记录。
- `main_folder`：这是你的主文件夹路径，其中包含了下载的论文。

这个脚本会遍历`jsonl_file`中的每一条记录，检查对应的PDF文件和源文件是否存在于`main_folder`中。如果存在，并且记录中的状态为None，那么它会更新记录的状态为'downloaded'，并记录下载时间。

## 注意

该项目仅供学习和研究使用，不得用于任何商业用途。请遵守Arxiv的使用条款，并尊重作者的版权。

## 许可

MIT license
