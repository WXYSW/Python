import asyncio
import random
import math
import ctypes
import pyperclip
import pyautogui
from plyer import notification
from datetime import datetime
import nodriver as uc

# ======================== 可调参数区（你的设置不变）========================
CHAT_URL = "https://chat.deepseek.com/a/chat/s/41381d6e-b433-4620-ac96-475760a170c1"
USER_DATA_DIR = r"C:\Vivian_Edge_Profile"

INPUT_X, INPUT_Y = 960, 980          # 输入框坐标
COPY_CENTER = (498, 833)            # 复制按钮中心坐标
COPY_RADIUS = 5

WAIT_AFTER_SEND = 20                # 等待 AI 回复的秒数
NOTIFICATION_DURATION = 0           # 通知显示时长（0 可能永久显示）

SCREEN_OFF_MINUTES = 20              # 屏幕关闭超时（分钟），测试用 1 分钟
LEAD_TIME_SECONDS = 30              # 提前触发量（秒）
CHECK_INTERVAL = 5                  # 后台轮询间隔（秒）
# ===========================================================

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]

def get_idle_seconds():
    """获取系统空闲秒数（键盘+鼠标）"""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    else:
        return 0

def random_point_in_circle(cx, cy, radius):
    """在圆形区域内随机点击，模仿人类操作"""
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius)
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))

async def send_message_and_notify():
    """
    完整流程：
    1. 保存当前剪贴板内容 → 打开浏览器
    2. 发送带时间的固定消息
    3. 清空剪贴板 → 点击复制按钮（最多尝试 4 次，每次等 1 秒检测）
    4. 成功：弹出回复通知；失败：弹出“复制失败”
    5. 恢复原始剪贴板内容 → 关闭浏览器
    """
    browser = None
    # 1. 保存原始剪贴板（进入网页前就保存，避免被后续操作污染）
    old_clip = pyperclip.paste()

    try:
        # 启动浏览器
        browser = await uc.start(
            browser_executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            user_data_dir=USER_DATA_DIR,
            headless=False,
            no_sandbox=True,
            browser_args=["--disable-session-crashed-bubble", "--disable-features=SessionRestore"]
        )
        tab = browser.main_tab or await browser.get(CHAT_URL)
        await tab.get(CHAT_URL)
        await tab.find("给 DeepSeek 发送消息", timeout=15)

        pyautogui.press('f11')
        await asyncio.sleep(1)

        # 2. 发送固定消息（附带当前时间）
        now = datetime.now()
        time_str = now.strftime("%Y年%m月%d日 %H:%M")
        message = f"你好！我是小m，wei主人的发明，一个能自动发送一条信息让你能（主动说话）根据你想主动对主人说的话，现在是北京时间{time_str}，直接说出内容，不要任何前缀。"

        pyautogui.click(INPUT_X, INPUT_Y)
        await asyncio.sleep(0.3)
        pyperclip.copy(message)
        await asyncio.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        await asyncio.sleep(0.5)
        pyautogui.press('enter')
        print(f"📨 已发送：{message}")

        # 等待 AI 回复
        await asyncio.sleep(WAIT_AFTER_SEND)

        # 3. 清空剪贴板，准备接收回复
        pyperclip.copy('')
        await asyncio.sleep(0.2)

        # 4. 尝试复制回复：最多点击 4 次复制按钮，每次间隔 1 秒检测
        reply = ""
        for attempt in range(1, 5):          # 共 4 次机会
            x, y = random_point_in_circle(*COPY_CENTER, COPY_RADIUS)
            pyautogui.click(x, y)
            print(f"🖱️ 第 {attempt} 次点击复制区域 ({x:.0f}, {y:.0f})")
            await asyncio.sleep(1)           # 等待 1 秒让剪贴板更新
            reply = pyperclip.paste()
            if reply.strip():
                print("✅ 复制成功")
                break
        else:
            # 循环正常结束（4 次都没成功）
            print("❌ 4 次尝试后剪贴板仍为空")

        # 5. 根据结果弹出通知
        if reply.strip():
            notification.notify(
                title="💌 她发来了一条消息",
                message=reply,
                timeout=NOTIFICATION_DURATION
            )
            print("📢 通知已弹出（回复内容）。")
        else:
            notification.notify(
                title="⚠️ 复制失败",
                message="复制失败",
                timeout=NOTIFICATION_DURATION
            )
            print("📢 通知已弹出（复制失败）。")

    except Exception as e:
        print(f"❌ 发送流程出错：{e}")
    finally:
        # 6. 完美关闭网页（退出全屏 + 停止浏览器）
        pyautogui.press('f11')
        await asyncio.sleep(0.5)
        if browser is not None:
            try:
                await browser.stop()
                await asyncio.sleep(0.5)
            except Exception:
                pass
        # 7. 无论发生什么，都将原始剪贴板内容恢复
        pyperclip.copy(old_clip)
        print("🧹 浏览器已关闭，剪贴板已恢复")

async def idle_monitor_loop():
    """后台循环：检测空闲时间，达到阈值触发流程"""
    threshold = SCREEN_OFF_MINUTES * 60 - LEAD_TIME_SECONDS
    print(f"🕒 屏幕息屏监控已启动，触发阈值为 {SCREEN_OFF_MINUTES}分钟 前 {LEAD_TIME_SECONDS}秒")
    triggered = False

    while True:
        idle_sec = get_idle_seconds()

        if idle_sec >= threshold and not triggered:
            print(f"⏳ 空闲 {idle_sec/60:.1f} 分钟，即将息屏，开始发送消息...")
            await send_message_and_notify()
            triggered = True

        if idle_sec < 1.0 and triggered:
            print("👋 检测到用户活动，重置触发状态")
            triggered = False

        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    asyncio.run(idle_monitor_loop())