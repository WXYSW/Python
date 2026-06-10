import numpy as np
from openai import OpenAI

# 1. 初始化客户端
# 如果你使用的是国内免费/主流平台，只需替换 base_url 和 api_key 即可
client = OpenAI(
    api_key="sk-",  # 替换为你的真实 API Key
    base_url="https://api.deepseek.com"  # 或者是国内平台的 endpoint，例如 https://api.siliconflow.cn/v1
)


def get_embedding(text: str, model="deepseek-embedding-v1"):
    """调用 API 获取文本的向量表示"""
    # 清洗一下文本中的换行符，这是提升 Embedding 质量的小细节
    text = text.replace("\n", " ")

    response = client.embeddings.create(
        input=[text],
        model=model
    )
    # API 会返回一个 1536 维（或 1024 维）的浮点数列表
    return response.data[0].embedding


def cosine_similarity(vec1, vec2):
    """使用 NumPy 计算两个向量的余弦相似度"""
    a = np.array(vec1)
    b = np.array(vec2)

    # 余弦相似度公式：(A · B) / (||A|| * ||B||)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    return dot_product / (norm_a * norm_b)


# --- 实战测试 ---
if __name__ == "__main__":
    print("正在把文本送进空间进行坐标定位...")

    # 测试三句话：前两句语义相近，第三句风马牛不相及
    text_a = "今天人工智能领域的进展让人感到兴奋。"
    text_b = "大语言模型和深度学习在最近取得了突破性的突破。"
    text_c = "红烧肉的做法是先将五花肉切块，然后焯水。"

    # 获取三句话的向量坐标
    vec_a = get_embedding(text_a)
    vec_b = get_embedding(text_b)
    vec_c = get_embedding(text_c)

    # 打印其中一个向量看看它的真面目（只看前 5 个数字）
    print(f"\n文本 A 的向量片段 (总长度 {len(vec_a)} 维): {vec_a[:5]} ...")

    # 计算距离
    sim_ab = cosine_similarity(vec_a, vec_b)
    sim_ac = cosine_similarity(vec_a, vec_c)

    print("\n--- 语义距离判决结果 ---")
    print(f"【A】与【B】的相似度: {sim_ab:.4f}  (科技 vs 科技)")
    print(f"【A】与【C】的相似度: {sim_ac:.4f}  (科技 vs 美食)")