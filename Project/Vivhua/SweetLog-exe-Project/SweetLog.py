#!/usr/bin/env python3
import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import pyperclip
import pyautogui
import nodriver as uc
from datetime import datetime, date
from pathlib import Path
import json

# ========== 固定配置（无需在 GUI 改动） ==========
USER_DATA_DIR = r"C:\Vivhua_Edge_Profile"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
INPUT_X, INPUT_Y = 960, 980
COPY_X, COPY_Y = 498, 833
# =================================================

CONFIG_FILE = Path("config.json")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 消息发送器")
        self.root.geometry("600x400")

        # 默认参数
        self.defaults = {
            "save_dir": r"C:\Users\24130\Desktop\Project",
            "chat_url": "https://chat.deepseek.com/a/chat/s/98ec8394-b47b-4e74-9af3-20ec231f56a3",
            "message": "这是小f自动发送的测试消息。"
        }
        # 尝试从 config.json 加载上次保存的配置
        self.config = self.load_config()

        # ---- 界面控件 ----
        tk.Label(root, text="保存文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.save_dir_var = tk.StringVar(value=self.config.get("save_dir", self.defaults["save_dir"]))
        self.entry_save_dir = tk.Entry(root, textvariable=self.save_dir_var, width=50)
        self.entry_save_dir.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(root, text="浏览", command=self.browse_folder).grid(row=0, column=2, padx=5)

        tk.Label(root, text="网站链接:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.chat_url_var = tk.StringVar(value=self.config.get("chat_url", self.defaults["chat_url"]))
        self.entry_chat_url = tk.Entry(root, textvariable=self.chat_url_var, width=50)
        self.entry_chat_url.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(root, text="发送消息:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.message_var = tk.StringVar(value=self.config.get("message", self.defaults["message"]))
        self.entry_message = tk.Entry(root, textvariable=self.message_var, width=50)
        self.entry_message.grid(row=2, column=1, padx=5, pady=5)

        # 按钮
        self.btn_run = tk.Button(root, text="保存配置并运行", command=self.start_task)
        self.btn_run.grid(row=3, column=1, pady=10, sticky="w")
        self.btn_exit = tk.Button(root, text="退出程序", command=root.quit)
        self.btn_exit.grid(row=3, column=1, pady=10, sticky="e")

        self.running = False

    def load_config(self):
        """加载配置文件"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_config(self):
        """保存当前参数到配置文件"""
        config = {
            "save_dir": self.save_dir_var.get(),
            "chat_url": self.chat_url_var.get(),
            "message": self.message_var.get()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def browse_folder(self):
        """选择保存文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.save_dir_var.set(folder)

    def start_task(self):
        """保存配置并启动后台任务"""
        if self.running:
            messagebox.showwarning("提示", "任务正在运行中，请稍候...")
            return

        # 保存当前配置
        self.save_config()

        # 禁用运行按钮，防止重复点击
        self.btn_run.config(state=tk.DISABLED, text="运行中...")
        self.running = True

        # 获取参数
        save_dir = self.save_dir_var.get()
        chat_url = self.chat_url_var.get()
        message = self.message_var.get()

        # 启动后台线程执行异步任务
        thread = threading.Thread(target=self.run_async_task, args=(save_dir, chat_url, message), daemon=True)
        thread.start()

    def run_async_task(self, save_dir, chat_url, message):
        """在后台线程中运行异步主函数"""
        try:
            # 新建一个事件循环给这个线程
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.async_main(save_dir, chat_url, message))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"发生异常：{e}"))
        finally:
            # 在主线程恢复按钮状态
            self.root.after(0, self.task_done)

    def task_done(self):
        """任务结束后恢复界面"""
        self.running = False
        self.btn_run.config(state=tk.NORMAL, text="保存配置并运行")

    async def wait_for_copy(self, max_wait=90):
        """点击复制按钮，等待剪贴板出现内容并返回"""
        pyperclip.copy('')
        for i in range(max_wait):
            pyautogui.click(COPY_X, COPY_Y)
            await asyncio.sleep(1)
            text = pyperclip.paste().strip()
            if text:
                return text
        return None

    async def async_main(self, save_dir_str, chat_url, message):
        old_clip = pyperclip.paste()
        browser = None
        try:
            browser = await uc.start(
                browser_executable_path=EDGE_PATH,
                user_data_dir=USER_DATA_DIR,
                headless=False,
                no_sandbox=True
            )
            tab = browser.main_tab or await browser.get(chat_url)
            await tab.get(chat_url)
            await tab.find("给 DeepSeek 发送消息", timeout=20)
            pyautogui.press('f11')
            await asyncio.sleep(1)

            # 发送消息
            pyperclip.copy(message)
            pyautogui.click(INPUT_X, INPUT_Y)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')
            print("消息已发送，等待 AI 回复...")

            # 获取回复
            reply = await self.wait_for_copy()
            if reply:
                save_dir = Path(save_dir_str)
                save_dir.mkdir(parents=True, exist_ok=True)
                start_date = self.get_or_create_start_date(save_dir)
                today = date.today()

                def fmt_cn(d: date) -> str:
                    return d.strftime("%Y年%m月%d日")

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
                self.root.after(0, lambda: messagebox.showinfo("成功", f"回复已保存至:\n{file_path}"))
            else:
                self.root.after(0, lambda: messagebox.showwarning("超时", "未获取到 AI 回复，请检查网络或页面状态。"))

        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror("出错", str(err)))
        finally:
            pyautogui.press('f11')
            if browser:
                try:
                    await browser.stop()
                except Exception:
                    pass
            pyperclip.copy(old_clip)
            print("浏览器已关闭")

    def get_or_create_start_date(self, save_dir: Path) -> date:
        """读取起始日期，若无则创建并返回今天"""
        state_file = save_dir / "start_date.txt"
        today = date.today()
        if state_file.exists():
            try:
                start_str = state_file.read_text().strip()
                return datetime.strptime(start_str, "%Y-%m-%d").date()
            except:
                pass
        state_file.write_text(today.isoformat())
        return today

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()