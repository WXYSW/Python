#!/usr/bin/env python3
import asyncio
import pyperclip
import pyautogui
import nodriver as uc
from datetime import datetime, date
from pathlib import Path

# ============ 配置 ============
CHAT_URL = "https://chat.deepseek.com/a/chat/s/d63d119a-ca8b-4580-8b0c-382a0351e3a9"
USER_DATA_DIR = r"C:\Vivhua_Edge_Profile"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
INPUT_X, INPUT_Y = 960, 980
COPY_X, COPY_Y = 498, 833
FIXED_MESSAGE = "这是小f自动发送的测试消息。"
SAVE_DIR = Path(r"C:\Users\24130\Desktop\Project")          # 回复保存目录
STATE_FILE = SAVE_DIR / "start_date.txt"                   # 记录起始日期
# =============================

def get_or_create_start_date() -> date:
    """读取起始日期，若无则设为今天并保存"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    if STATE_FILE.exists():
        try:
            start_str = STATE_FILE.read_text().strip()
            return datetime.strptime(start_str, "%Y-%m-%d").date()
        except Exception:
            pass
    # 无文件或格式错误，保存今天作为起始
    STATE_FILE.write_text(today.isoformat())
    return today

async def wait_for_copy(max_wait=90):
    pyperclip.copy('')
    for i in range(max_wait):
        pyautogui.click(COPY_X, COPY_Y)
        await asyncio.sleep(1)
        text = pyperclip.paste().strip()
        if text:
            return text
    return None

async def main():
    old_clip = pyperclip.paste()
    browser = None
    try:
        browser = await uc.start(
            browser_executable_path=EDGE_PATH,
            user_data_dir=USER_DATA_DIR,
            headless=False,
            no_sandbox=True
        )
        tab = browser.main_tab or await browser.get(CHAT_URL)
        await tab.get(CHAT_URL)
        await tab.find("给 DeepSeek 发送消息", timeout=20)
        pyautogui.press('f11')
        await asyncio.sleep(1)

        pyperclip.copy(FIXED_MESSAGE)
        pyautogui.click(INPUT_X, INPUT_Y)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        print("消息已发送，等待 AI 回复...")

        reply = await wait_for_copy()
        if reply:
            start_date = get_or_create_start_date()
            today = date.today()

            # 格式化中文日期
            def fmt_cn(d: date) -> str:
                return d.strftime("%Y年%m月%d日")

            start_cn = fmt_cn(start_date)
            today_cn = fmt_cn(today)

            # 文件名和内容头
            if start_date == today:
                date_range = today_cn
                file_name = f"{today_cn}.md"
            else:
                date_range = f"{start_cn} - {today_cn}"
                file_name = f"{date_range}.md"

            content = f"{date_range}\n{reply}"
            file_path = SAVE_DIR / file_name
            file_path.write_text(content, encoding="utf-8")
            print(f"回复已保存至: {file_path}")
        else:
            print("未获取到回复或超时")

    except Exception as e:
        print(f"出错: {e}")
    finally:
        pyautogui.press('f11')
        if browser:
            try:
                await browser.stop()
            except Exception:
                pass
        pyperclip.copy(old_clip)

if __name__ == "__main__":
    asyncio.run(main())