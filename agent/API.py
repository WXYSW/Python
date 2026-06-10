import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 核心步骤：启动时立刻加载 .env 文件
# 这行代码会把 .env 里的内容注入到系统的 os.environ 中
load_dotenv()

# 2. 从环境变量中读取配置
# 这样做的好处是：如果未来部署到云服务器（如 Docker），不需要改动任何代码，只需修改服务器的环境变量即可
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")  # 后面的是防呆兜底值

# 安全检查：防止忘记配置 .env 导致程序报错
if not api_key:
    raise ValueError("❌ 错误：未在环境变量中找到 OPENAI_API_KEY，请检查 .env 文件！")

# 3. 初始化客户端
# 技巧：OpenAI 的 SDK 其实默认就会去系统环境变量里找 "OPENAI_API_KEY" 和 "OPENAI_BASE_URL"
# 即使你不传参数，写 client = OpenAI() 它也能自动识别。这里为了清晰，我们手动传入。
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 4. 初始化对话历史
history = [
    {"role": "system", "content": "你是一个乐于助人的AI助手。"}
]

print(f"🤖 安全版大模型聊天机器人已启动！当前模型: {model_name}")
print("（输入 'exit' 退出，输入 'clear' 清空记忆）")

# 5. 启动无线循环 MVP
while True:
    user_input = input("\n你: ").strip()

    if user_input.lower() == 'exit':
        print("🤖 再见！")
        break

    if user_input.lower() == 'clear':
        history = [{"role": "system", "content": "你是一个乐于助人的AI助手。"}]
        print("🧹 记忆已清空，开启全新的对话！")
        continue

    if not user_input:
        continue

    # 追加用户输入
    history.append({"role": "user", "content": user_input})

    try:
        # 调用大模型
        response = client.chat.completions.create(
            model=model_name,  # 动态读取环境变量里的模型名称
            messages=history,
            temperature=0.7
        )

        # 获取并打印回复
        completion = response.choices[0].message.content
        print(f"AI: {completion}")

        # 追加 AI 回复到记忆中
        history.append({"role": "assistant", "content": completion})

    except Exception as e:
        print(f"❌ 呼叫大模型时发生错误: {e}")
        history.pop()