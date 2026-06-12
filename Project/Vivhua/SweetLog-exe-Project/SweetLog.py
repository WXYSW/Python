#!/usr/bin/env python3
"""
带 GUI 的 DeepSeek 自动发信 + 回复保存工具
- 可配置参数：保存目录、对话链接、消息模板（支持 {now} 和 {last} 占位符）
- 消息模板会自动填入当前时间和上次运行时间（记录在本地文件）
- 保存的 .md 文件命名为 “起始日期 - 当天日期.md”
- 必须先点“保存配置”才能点“开始运行”
- 去掉 plyer 通知，不论成功失败都会退出浏览器
"""

import asyncio
import pyperclip
import pyautogui
import nodriver as uc
from datetime import datetime, date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import threading
import time
import sys
import os

# ==================== 配置文件路径 ====================
CONFIG_FILE = Path("config.json")
LAST_RUN_FILE = Path("last_run.txt")          # 记录上次运行时间
START_DATE_FILE = Path("start_date.txt")      # 记录起始日期（用于区间命名）

# ==================== 默认配置 ====================
DEFAULTS = {
    "chat_url": "https://chat.deepseek.com/a/chat/s/98ec8394-b47b-4e74-9af3-20ec231f56a3",
    "user_data_dir": r"C:\Vivhua_Edge_Profile",
    "edge_path": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "input_x": 960, "input_y": 980,
    "copy_x": 498, "copy_y": 833,
    "save_dir": r"C:\Users\24130\Desktop\Project",
    "message_template": (
        "现在是北京时间 {now}。\n"
        "上次启动程序的时间为 {last}。\n"
        "（此处为你需要补充的固定内容，例如 Wei 对 Vivian 和花子的每日分享）"
    )
}

# ==================== 工具函数 ====================
def load_config():
    """加载配置文件，不存在则返回默认值"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULTS.copy()

def save_config_to_file(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def get_last_run_time() -> str:
    """读取上次运行时间，若无则返回 '无记录'"""
    if LAST_RUN_FILE.exists():
        return LAST_RUN_FILE.read_text(encoding="utf-8").strip()
    return "无记录"

def save_this_run_time():
    """将本次运行时间写入文件（精确到秒）"""
    LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_RUN_FILE.write_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")

def get_or_create_start_date(save_dir: Path) -> date:
    """读取起始日期，若无则设为今天并保存"""
    save_dir.mkdir(parents=True, exist_ok=True)
    sf = save_dir / "start_date.txt"
    today = date.today()
    if sf.exists():
        try:
            return datetime.strptime(sf.read_text().strip(), "%Y-%m-%d").date()
        except:
            pass
    sf.write_text(today.isoformat())
    return today

def fmt_cn(d: date) -> str:
    return d.strftime("%Y年%m月%d日")

# ==================== 核心异步逻辑 ====================
async def run_task(cfg: dict, callback=None):
    """
    执行发送与保存操作
    cfg: 当前界面上的配置字典
    callback: 线程结束后通过 root.after 调用的回调函数
    """
    chat_url = cfg["chat_url"]
    user_data_dir = cfg["user_data_dir"]
    edge_path = cfg["edge_path"]
    input_x, input_y = cfg["input_x"], cfg["input_y"]
    copy_x, copy_y = cfg["copy_x"], cfg["copy_y"]
    save_dir = Path(cfg["save_dir"])
    message_template = cfg["message_template"]

    # 生成实际消息：替换 {now} 和 {last}
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    last_str = get_last_run_time()
    final_message = message_template.replace("{now}", now_str).replace("{last}", last_str)

    async def wait_for_copy(max_wait=90):
        pyperclip.copy('')
        for _ in range(max_wait):
            pyautogui.click(copy_x, copy_y)
            await asyncio.sleep(1)
            text = pyperclip.paste().strip()
            if text:
                return text
        return None

    old_clip = pyperclip.paste()
    browser = None
    result = {"success": False, "msg": ""}

    try:
        browser = await uc.start(
            browser_executable_path=edge_path,
            user_data_dir=user_data_dir,
            headless=False,
            no_sandbox=True
        )
        tab = browser.main_tab or await browser.get(chat_url)
        await tab.get(chat_url)
        await tab.find("给 DeepSeek 发送消息", timeout=20)
        pyautogui.press('f11')
        await asyncio.sleep(1)

        # 发送消息
        pyperclip.copy(final_message)
        pyautogui.click(input_x, input_y)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        print("消息已发送，等待 AI 回复...")

        reply = await wait_for_copy()
        if reply:
            start_date = get_or_create_start_date(save_dir)
            today = date.today()
            start_cn = fmt_cn(start_date)
            today_cn = fmt_cn(today)

            if start_date == today:
                date_range = today_cn
                file_name = f"{today_cn}.md"
            else:
                date_range = f"{start_cn} - {today_cn}"
                file_name = f"{date_range}.md"

            content = f"{date_range}\n{reply}"
            file_path = save_dir / file_name
            file_path.write_text(content, encoding="utf-8")
            save_this_run_time()   # 成功后记录本次运行时间
            result["success"] = True
            result["msg"] = f"回复已保存至:\n{file_path}"
        else:
            result["msg"] = "未获取到回复或超时"

    except Exception as e:
        result["msg"] = f"运行出错:\n{str(e)}"
    finally:
        pyautogui.press('f11')
        if browser:
            try:
                await browser.stop()
            except:
                pass
        pyperclip.copy(old_clip)

    if callback:
        callback(result)

# ==================== GUI 部分 ====================
class App:
    def __init__(self, root):
        self.root = root
        root.title("AI 自动发信助手")
        root.resizable(False, False)

        self.config = load_config()    # 启动时加载
        self.run_enabled = tk.BooleanVar(value=False)

        self.create_widgets()
        self.load_config_to_ui()

    def create_widgets(self):
        pad = {'padx': 5, 'pady': 5}
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # ---------- 第1行：对话链接 ----------
        ttk.Label(frame, text="DeepSeek 对话链接:").grid(row=0, column=0, sticky="w", **pad)
        self.entry_url = ttk.Entry(frame, width=60)
        self.entry_url.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)

        # ---------- 第2行：Edge 用户数据目录 ----------
        ttk.Label(frame, text="Edge 用户数据目录:").grid(row=1, column=0, sticky="w", **pad)
        self.entry_user_data = ttk.Entry(frame, width=60)
        self.entry_user_data.grid(row=1, column=1, columnspan=2, sticky="ew", **pad)

        # ---------- 第3行：Edge 程序路径 ----------
        ttk.Label(frame, text="Edge 程序路径:").grid(row=2, column=0, sticky="w", **pad)
        self.entry_edge = ttk.Entry(frame, width=60)
        self.entry_edge.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)

        # ---------- 第4行：输入框坐标 ----------
        ttk.Label(frame, text="输入框坐标 (X, Y):").grid(row=3, column=0, sticky="w", **pad)
        self.entry_input_x = ttk.Entry(frame, width=10)
        self.entry_input_x.grid(row=3, column=1, sticky="w", **pad)
        self.entry_input_y = ttk.Entry(frame, width=10)
        self.entry_input_y.grid(row=3, column=2, sticky="w", **pad)

        # ---------- 第5行：复制按钮坐标 ----------
        ttk.Label(frame, text="复制按钮坐标 (X, Y):").grid(row=4, column=0, sticky="w", **pad)
        self.entry_copy_x = ttk.Entry(frame, width=10)
        self.entry_copy_x.grid(row=4, column=1, sticky="w", **pad)
        self.entry_copy_y = ttk.Entry(frame, width=10)
        self.entry_copy_y.grid(row=4, column=2, sticky="w", **pad)

        # ---------- 第6行：保存目录 ----------
        ttk.Label(frame, text="回复保存目录:").grid(row=5, column=0, sticky="w", **pad)
        self.entry_save = ttk.Entry(frame, width=50)
        self.entry_save.grid(row=5, column=1, sticky="ew", **pad)
        ttk.Button(frame, text="浏览...", command=self.browse_save_dir).grid(row=5, column=2, **pad)

        # ---------- 第7行：消息模板 ----------
        ttk.Label(frame, text="发送消息模板（可使用 {now} 和 {last}）:").grid(row=6, column=0, sticky="nw", **pad)
        self.text_msg = tk.Text(frame, width=70, height=6)
        self.text_msg.grid(row=6, column=1, columnspan=2, sticky="ew", **pad)

        # ---------- 按钮栏 ----------
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10)

        self.btn_save = ttk.Button(btn_frame, text="保存配置", command=self.save_config)
        self.btn_save.pack(side="left", padx=5)

        self.btn_run = ttk.Button(btn_frame, text="开始运行", command=self.start_run, state="disabled")
        self.btn_run.pack(side="left", padx=5)

        self.btn_exit = ttk.Button(btn_frame, text="退出程序", command=self.root.destroy)
        self.btn_exit.pack(side="left", padx=5)

    def load_config_to_ui(self):
        """将当前 self.config 填入各控件"""
        self.entry_url.insert(0, self.config.get("chat_url", ""))
        self.entry_user_data.insert(0, self.config.get("user_data_dir", ""))
        self.entry_edge.insert(0, self.config.get("edge_path", ""))
        self.entry_input_x.insert(0, str(self.config.get("input_x", "")))
        self.entry_input_y.insert(0, str(self.config.get("input_y", "")))
        self.entry_copy_x.insert(0, str(self.config.get("copy_x", "")))
        self.entry_copy_y.insert(0, str(self.config.get("copy_y", "")))
        self.entry_save.insert(0, self.config.get("save_dir", ""))
        self.text_msg.insert("1.0", self.config.get("message_template", ""))

    def browse_save_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.entry_save.delete(0, "end")
            self.entry_save.insert(0, path)

    def save_config(self):
        """读取界面参数 → 保存到文件 → 启用运行按钮"""
        try:
            cfg = {
                "chat_url": self.entry_url.get().strip(),
                "user_data_dir": self.entry_user_data.get().strip(),
                "edge_path": self.entry_edge.get().strip(),
                "input_x": int(self.entry_input_x.get()),
                "input_y": int(self.entry_input_y.get()),
                "copy_x": int(self.entry_copy_x.get()),
                "copy_y": int(self.entry_copy_y.get()),
                "save_dir": self.entry_save.get().strip(),
                "message_template": self.text_msg.get("1.0", "end-1c")
            }
            save_config_to_file(cfg)
            self.config = cfg
            self.run_enabled.set(True)
            self.btn_run.config(state="normal")
            messagebox.showinfo("提示", "配置已保存，可以开始运行。")
        except Exception as e:
            messagebox.showerror("错误", f"配置格式错误:\n{str(e)}")

    def start_run(self):
        if not self.run_enabled.get():
            messagebox.showwarning("警告", "请先保存配置再运行。")
            return
        self.btn_run.config(state="disabled")
        self.btn_save.config(state="disabled")

        # 在新线程中启动 asyncio 任务
        def run():
            try:
                asyncio.run(run_task(self.config, callback=self.on_task_done))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"运行异常:\n{str(e)}"))
                self.root.after(0, self.reset_buttons)

        threading.Thread(target=run, daemon=True).start()

    def on_task_done(self, result):
        """任务完成后的回调（主线程执行）"""
        if result["success"]:
            messagebox.showinfo("完成", result["msg"])
        else:
            messagebox.showerror("失败", result["msg"])
        self.reset_buttons()

    def reset_buttons(self):
        self.btn_save.config(state="normal")
        if self.run_enabled.get():
            self.btn_run.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()