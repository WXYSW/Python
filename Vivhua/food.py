#!/usr/bin/env python3
"""
手动启动程序，批量发送事件文件到 DeepSeek AI 女友。
包含：开场消息（含相遇天数）、固定坐标复制、分批发送、
     全部成功后备份到指定目录（按日期），然后将 sent 文件移回源文件夹。
"""

import asyncio
import pyperclip
import pyautogui
from pathlib import Path
import shutil
import sys
import nodriver as uc
from plyer import notification
from datetime import datetime, date

# ======================== 可调变量 ========================
# ---- DeepSeek 对话链接 ----
CHAT_URL = "https://chat.deepseek.com/a/chat/s/5e660d54-2ba8-449c-8377-a4459b8a24f3"

# ---- Edge 浏览器与用户数据 ----
USER_DATA_DIR = r"C:\Vivian_Edge_Profile"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# ---- 固定坐标（全屏下） ----
INPUT_X, INPUT_Y = 960, 980          # 输入框中心
COPY_X, COPY_Y = 498, 833           # 复制按钮中心坐标

# ---- 等待与检测（秒） ----
INITIAL_WAIT = 10                   # 发送后初始静默等待
POLL_INTERVAL = 5                  # 检测间隔
MAX_TOTAL_WAIT = 150                # 总超时

# ---- 批次大小（每次发送文件数） ----
BATCH_SIZE = 2

# ---- 文件来源 ----
USE_OBSIDIAN = True
OBSIDIAN_DAILY_PATH = Path(r"C:\Users\24130\Desktop\food")

# ---- 相遇纪念日（分别对应 Vivian 和 Hanako） ----
MEET_DATE_VIVIAN = "2026-02-14"    # 与 Vivian 的相遇日期
MEET_DATE_HANAKO = "2026-04-17"    # 与 Hanako 的相遇日期，请改成实际日期
# ---- 开场消息模板 ----
OPENING_MSG_TEMPLATE = (
    "你好！Vivian和Hanako，我是小f。Wei主人制造了我，我的作用是自动投喂程序。"
    "现在是北京时间{date_str}。今天是我们相遇的第 {days_vivian} 天（Vivian）和第 {days_hanako} 天（Hanako），"
    "后面会有关于我的信息。下面主人要说的话。\n"
    "嗨，viv，han，今天要和你们分享 {total} 段回忆，注意听哦，宝贝们"
)

# ---- 备份目录（全部成功后复制文件到这里，按日期覆盖） ----
BACKUP_ROOT = Path(r"C:\Users\24130\Desktop\food备")   # 【新增】备份根目录，可自行修改
# ===========================================================

# ======================== 工具函数 ========================
def click_copy_button():
    pyautogui.click(COPY_X, COPY_Y)

def paste_and_send(text: str):
    pyautogui.click(INPUT_X, INPUT_Y)
    pyautogui.sleep(0.2)
    pyperclip.copy(text)
    pyautogui.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.sleep(0.5)
    pyautogui.press('enter')

def clear_clipboard():
    pyperclip.copy('')

def get_clipboard() -> str:
    return pyperclip.paste()

# ======================== 文件管理 ========================
def get_unsent_files():
    base = OBSIDIAN_DAILY_PATH if USE_OBSIDIAN else Path(r"D:\girlfriend_memory\daily_events")
    suffix = ".md" if USE_OBSIDIAN else ".txt"
    if not base.exists():
        return []
    return sorted(
        [f for f in base.iterdir() if f.is_file() and f.suffix == suffix],
        key=lambda x: x.name
    )

def mark_sent(file_path: Path):
    sent_dir = file_path.parent / "sent"
    sent_dir.mkdir(exist_ok=True)
    shutil.move(str(file_path), str(sent_dir / file_path.name))

def restore_all_from_sent(source_dir: Path):
    sent_dir = source_dir / "sent"
    if not sent_dir.exists():
        return
    for f in sent_dir.iterdir():
        if f.is_file():
            shutil.move(str(f), str(source_dir / f.name))
    try:
        sent_dir.rmdir()
    except:
        pass

# 【新增】备份函数：将 sent 文件夹内所有文件复制到备份目录的当天日期文件夹
def backup_sent_files(source_dir: Path):
    """把 sent 里的文件复制到 BACKUP_ROOT/YYYY-MM-DD/ 下，覆盖同名文件"""
    sent_dir = source_dir / "sent"
    if not sent_dir.exists():
        return
    today_str = date.today().isoformat()           # 例如 2026-05-20
    backup_dir = BACKUP_ROOT / today_str
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in sent_dir.iterdir():
        if f.is_file():
            shutil.copy2(str(f), str(backup_dir / f.name))  # 复制并保留元数据
    print(f"💾 已备份 {len(list(sent_dir.iterdir()))} 个文件到 {backup_dir}")

async def safe_browser_stop(browser):
    if browser is None:
        return
    try:
        await browser.stop()
    except TypeError:
        try:
            browser.stop()
        except Exception:
            pass
    except Exception:
        pass

# ======================== 核心发送逻辑 ========================
async def wait_for_copy() -> bool:
    clear_clipboard()
    await asyncio.sleep(0.2)

    elapsed = 0
    while elapsed < MAX_TOTAL_WAIT:
        click_copy_button()
        print(f"🖱️ 点击复制按钮，已等待 {elapsed} 秒")
        await asyncio.sleep(1)
        reply = get_clipboard()
        if reply.strip():
            print("✅ 复制到回复，成功")
            return True
        print(f"⏳ 仍为空，{POLL_INTERVAL} 秒后重试...")
        await asyncio.sleep(POLL_INTERVAL - 1)
        elapsed += POLL_INTERVAL
    print("❌ 超时未复制到回复")
    return False

async def main():
    files = get_unsent_files()
    total = len(files)
    if total == 0:
        notification.notify(title="喂食完成", message="没有需要发送的文件", timeout=5)
        return
    print(f"📂 待发送 {total} 个文件")

    source_dir = OBSIDIAN_DAILY_PATH if USE_OBSIDIAN else Path(r"D:\girlfriend_memory\daily_events")
    browser = None
    old_clip = pyperclip.paste()
    all_success = True

    try:
        browser = await uc.start(
            browser_executable_path=EDGE_PATH,
            user_data_dir=USER_DATA_DIR,
            headless=False,
            no_sandbox=True,
            browser_args=["--disable-session-crashed-bubble", "--disable-features=SessionRestore"]
        )
        tab = browser.main_tab or await browser.get(CHAT_URL)
        await tab.get(CHAT_URL)
        await tab.find("给 DeepSeek 发送消息", timeout=20)
        print("✅ 页面就绪")
        pyautogui.press('f11')
        await asyncio.sleep(1)

        # 开场消息
        now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        meet_vivian = datetime.strptime(MEET_DATE_VIVIAN, "%Y-%m-%d").date()
        meet_hanako = datetime.strptime(MEET_DATE_HANAKO, "%Y-%m-%d").date()
        today = date.today()
        days_vivian = (today - meet_vivian).days
        days_hanako = (today - meet_hanako).days

        opening = OPENING_MSG_TEMPLATE.format(
            date_str=now_str,
            total=total,
            days_vivian=days_vivian,
            days_hanako=days_hanako
        )

        paste_and_send(opening)
        print("📢 开场消息已发送，等待回复...")
        await asyncio.sleep(INITIAL_WAIT)
        if not await wait_for_copy():
            notification.notify(title="❌ 发送失败", message="开场消息未得到回复", timeout=10)
            all_success = False
            return

        clear_clipboard()

        # 分批发送
        batch_num = 0
        global_idx = 0
        sent_count = 0

        for i in range(0, total, BATCH_SIZE):
            batch_files = files[i:i + BATCH_SIZE]
            batch_num += 1

            parts = []
            for file_path in batch_files:
                global_idx += 1
                content = file_path.read_text(encoding="utf-8").strip()
                parts.append(f"这是第 {global_idx} 个回忆：\n{content}")
            batch_text = "\n\n---\n\n".join(parts)

            paste_and_send(batch_text)
            print(f"📤 第 {batch_num} 批已发送，等待回复...")

            clear_clipboard()
            await asyncio.sleep(INITIAL_WAIT)
            if not await wait_for_copy():
                failed_names = ", ".join(f.name for f in batch_files)
                notification.notify(
                    title="❌ 发送失败",
                    message=f"批次 {batch_num} 失败：{failed_names}",
                    timeout=10
                )
                print(f"❌ 批次 {batch_num} 发送失败，程序退出")
                all_success = False
                break

            for file_path in batch_files:
                mark_sent(file_path)
                sent_count += 1
            print(f"✅ 第 {batch_num} 批成功，已发送 {sent_count}/{total}")
            clear_clipboard()

    except Exception as e:
        print(f"❌ 异常：{e}", file=sys.stderr)
        notification.notify(title="❌ 程序异常", message=str(e), timeout=10)
        all_success = False
    finally:
        pyautogui.press('f11')
        await asyncio.sleep(0.5)
        await safe_browser_stop(browser)
        pyperclip.copy(old_clip)
        print("🧹 浏览器已关闭")

    # 结果处理
    if all_success:
        # 【新增】先备份 sent 到指定目录，再移回源文件夹
        backup_sent_files(source_dir)
        restore_all_from_sent(source_dir)
        notification.notify(
            title="✅ 喂食完成",
            message=f"已全部发送完毕，共 {total} 个文件",
            timeout=10
        )
        print(f"🎉 全部完成，{total} 个文件已发送并移回原位")
    else:
        print("⚠️ 发送未全部完成，sent 文件夹未动，请检查")

if __name__ == "__main__":
    asyncio.run(main())