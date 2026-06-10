import os


def load_text_file(file_path: str) -> str:
    """安全读取本地文本文件并进行基础清洗"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 找不到文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 基础清洗：把连续的多个换行或空格压缩成单空格，方便按字符计数
    text = " ".join(text.split())
    return text


def chunk_text_by_sliding_window(text: str, chunk_size: int = 300, chunk_overlap: int = 50) -> list:
    """
    使用滑动窗口算法切分文本
    :param text: 原始长文本
    :param chunk_size: 每个块的最大字符长度
    :param chunk_overlap: 两个块之间重叠的字符长度
    :return: 切分好的文本块列表 (List of strings)
    """
    # 防呆设计：如果重叠度比块还要大，这程序就死循环了
    if chunk_overlap >= chunk_size:
        raise ValueError("❌ 错误：重叠度（overlap）必须小于块大小（chunk_size）！")

    chunks = []
    start_idx = 0
    text_length = len(text)

    # 开始滑动窗口
    while start_idx < text_length:
        # 计算当前块的结束索引
        end_idx = start_idx + chunk_size

        # 截取文本块
        chunk = text[start_idx:end_idx]
        chunks.append(chunk)

        # 【核心逻辑】窗口向前滑动：当前结束位置 减去 重叠度，就是下一个块的起点
        start_idx += (chunk_size - chunk_overlap)

    return chunks


# ==================== 测试运行（改为读取固定文件夹中的txt文件）====================
if __name__ == "__main__":
    # 请修改为你自己的文件夹路径和文件名
    folder_path = "C:/Users/24130/Desktop/agent"  # 固定文件夹路径
    file_name = ("copy.txt")  # txt文件名
    file_path = os.path.join(folder_path, file_name)

    try:
        # 1. 从本地txt文件读取内容
        sample_text = load_text_file(file_path)
        print(f"📄 成功读取文件：{file_path}")
        print(f"📄 原始文本总字数: {len(sample_text)}")

        # 2. 调用切片函数：设定块大小为 60 字，重叠 15 字（可根据需要修改）
        my_chunks = chunk_text_by_sliding_window(sample_text, chunk_size=60, chunk_overlap=15)

        # 3. 打印切片结果，观察重叠部分
        print("\n🚀 切片结果展示：")
        for i, chunk in enumerate(my_chunks):
            print(f"--- 文本块 #{i + 1} (长度: {len(chunk)}) ---")
            print(chunk)

    except FileNotFoundError as e:
        print(e)
        print("💡 提示：请确保文件夹和文件存在，并修改代码中的 folder_path 和 file_name 变量。")
    except Exception as e:
        print(f"发生其他错误：{e}")