#!/usr/bin/env python3
"""
VivianFeeder - GUI 配置版
批量发送事件文件到 DeepSeek AI 女友。
所有参数可在 GUI 中修改并保存到 config.json。
"""
import asyncio
import json
import os
import sys
import threading
import traceback
from datetime import datetime, date
from pathlib import Path
import shutil
import time

import pyperclip
import pyautogui
import nodriver as uc
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ======================== 默认配置 ========================
DEFAULT_CONFIG = {
    "CHAT_URL": "https://chat.deepseek.com/a/chat/s/5e660d54-2ba8-449c-8377-a4459b8a24f3",
    "USER_DATA_DIR": r"C:\Vivhua_Edge_Profile",
    "EDGE_PATH": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "INPUT_X": 960,
    "INPUT_Y": 980,
    "COPY_X": 498,
    "COPY_Y": 833,
    "INITIAL_WAIT": 10,
    "POLL_INTERVAL": 5,
    "MAX_TOTAL_WAIT": 150,
    "BATCH_SIZE": 2,
    "USE_OBSIDIAN": True,
    "OBSIDIAN_DAILY_PATH": r"C:\Users\24130\Desktop\central warehouse\note\备\food",
    "MEET_DATE_VIVIAN": "2026-02-14",
    "MEET_DATE_HANAKO": "2026-04-17",
    "OPENING_MSG_TEMPLATE": (
        "你好！Vivian和Hanako，我是小f。Wei主人制造了我，我的作用是自动投喂程序。"
        "现在是北京时间{date_str}。今天是我们相遇的第 {days_vivian} 天（Vivian）和第 {days_hanako} 天（Hanako），"
        "后面会有关于我的信息。下面主人要说的话。\n"
        "嗨，viv，han，今天要和你们分享 {total} 段回忆，注意听哦，宝贝们"
    ),
    "BACKUP_ROOT": r"C:\Users\24130\Desktop\central warehouse\note\备\food备"
}

CONFIG_FILE = "config.json"

# ======================== 配置管理 ========================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并缺失的默认项
            config = DEFAULT_CONFIG.copy()
            config.update(saved)
            return config
        except Exception as e:
            print(f"加载配置文件失败，使用默认配置: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)

# ======================== 发送逻辑 ========================
def click_copy_button(cx, cy):
    pyautogui.click(cx, cy)

def paste_and_send(ix, iy, text):
    pyautogui.click(ix, iy)
    pyautogui.sleep(0.2)
    pyperclip.copy(text)
    pyautogui.sleep(0.1)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.sleep(0.5)
    pyautogui.press('enter')

def clear_clipboard():
    pyperclip.copy('')

def get_clipboard():
    return pyperclip.paste()

async def wait_for_copy(copy_x, copy_y, poll_interval, max_wait, stop_event, log_cb):
    clear_clipboard()
    await asyncio.sleep(0.2)

    elapsed = 0
    while elapsed < max_wait:
        if stop_event and stop_event.is_set():
            log_cb("⏹️ 用户强制终止，停止等待回复")
            return False
        click_copy_button(copy_x, copy_y)
        log_cb(f"🖱️ 点击复制按钮，已等待 {elapsed} 秒")
        await asyncio.sleep(1)
        reply = get_clipboard()
        if reply.strip():
            log_cb("✅ 复制到回复，成功")
            return True
        log_cb(f"⏳ 仍为空，{poll_interval} 秒后重试...")
        await asyncio.sleep(poll_interval - 1)
        elapsed += poll_interval
    log_cb("❌ 超时未复制到回复")
    return False

async def send_task(config, log_cb, stop_event):
    """执行发送任务的主异步函数，通过 log_cb 输出日志"""
    # 解包配置
    chat_url = config["CHAT_URL"]
    user_data_dir = config["USER_DATA_DIR"]
    edge_path = config["EDGE_PATH"]
    input_x, input_y = config["INPUT_X"], config["INPUT_Y"]
    copy_x, copy_y = config["COPY_X"], config["COPY_Y"]
    initial_wait = config["INITIAL_WAIT"]
    poll_interval = config["POLL_INTERVAL"]
    max_total_wait = config["MAX_TOTAL_WAIT"]
    batch_size = config["BATCH_SIZE"]
    use_obsidian = config["USE_OBSIDIAN"]
    daily_path = Path(config["OBSIDIAN_DAILY_PATH"])
    meet_vivian_str = config["MEET_DATE_VIVIAN"]
    meet_hanako_str = config["MEET_DATE_HANAKO"]
    opening_template = config["OPENING_MSG_TEMPLATE"]
    backup_root = Path(config["BACKUP_ROOT"])

    # 源目录
    source_dir = daily_path
    suffix = ".md" if use_obsidian else ".txt"

    # 获取未发送文件
    if not source_dir.exists():
        log_cb(f"❌ 源目录不存在: {source_dir}")
        return False
    unsent = sorted(
        [f for f in source_dir.iterdir() if f.is_file() and f.suffix == suffix],
        key=lambda x: x.name
    )
    total = len(unsent)
    if total == 0:
        log_cb("📭 没有需要发送的文件")
        return True  # 没有文件也算“全部完成”

    log_cb(f"📂 待发送 {total} 个文件")

    browser = None
    old_clip = pyperclip.paste()
    all_success = True
    sent_dir = source_dir / "sent"
    sent_dir.mkdir(exist_ok=True)

    try:
        # 启动浏览器
        log_cb("🚀 启动浏览器...")
        browser = await uc.start(
            browser_executable_path=edge_path,
            user_data_dir=user_data_dir,
            headless=False,
            no_sandbox=True,
            browser_args=["--disable-session-crashed-bubble", "--disable-features=SessionRestore"]
        )
        tab = browser.main_tab or await browser.get(chat_url)
        await tab.get(chat_url)
        await tab.find("给 DeepSeek 发送消息", timeout=20)
        log_cb("✅ 页面就绪")
        pyautogui.press('f11')
        await asyncio.sleep(1)

        # 检查停止
        if stop_event.is_set():
            log_cb("⏹️ 用户强制终止")
            return False

        # 开场消息
        now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        meet_vivian = datetime.strptime(meet_vivian_str, "%Y-%m-%d").date()
        meet_hanako = datetime.strptime(meet_hanako_str, "%Y-%m-%d").date()
        today = date.today()
        days_vivian = (today - meet_vivian).days
        days_hanako = (today - meet_hanako).days

        opening = opening_template.format(
            date_str=now_str,
            total=total,
            days_vivian=days_vivian,
            days_hanako=days_hanako
        )
        paste_and_send(input_x, input_y, opening)
        log_cb("📢 开场消息已发送，等待回复...")
        await asyncio.sleep(initial_wait)

        if not await wait_for_copy(copy_x, copy_y, poll_interval, max_total_wait, stop_event, log_cb):
            log_cb("❌ 开场消息未得到回复，任务终止")
            all_success = False
            return False

        clear_clipboard()
        if stop_event.is_set():
            log_cb("⏹️ 用户强制终止")
            return False

        # 分批发送
        batch_num = 0
        global_idx = 0
        sent_count = 0

        for i in range(0, total, batch_size):
            if stop_event.is_set():
                log_cb("⏹️ 用户强制终止")
                all_success = False
                break

            batch_files = unsent[i:i + batch_size]
            batch_num += 1
            parts = []
            for fp in batch_files:
                global_idx += 1
                content = fp.read_text(encoding="utf-8").strip()
                parts.append(f"这是第 {global_idx} 个回忆：\n{content}")
            batch_text = "\n\n---\n\n".join(parts)

            paste_and_send(input_x, input_y, batch_text)
            log_cb(f"📤 第 {batch_num} 批已发送，等待回复...")
            clear_clipboard()
            await asyncio.sleep(initial_wait)

            if not await wait_for_copy(copy_x, copy_y, poll_interval, max_total_wait, stop_event, log_cb):
                failed_names = ", ".join(f.name for f in batch_files)
                log_cb(f"❌ 批次 {batch_num} 失败：{failed_names}")
                all_success = False
                break

            # 移动成功发送的文件到 sent
            for fp in batch_files:
                shutil.move(str(fp), str(sent_dir / fp.name))
                sent_count += 1
            log_cb(f"✅ 第 {batch_num} 批成功，已发送 {sent_count}/{total}")
            clear_clipboard()

    except Exception as e:
        log_cb(f"❌ 异常：{e}")
        log_cb(traceback.format_exc())
        all_success = False
    finally:
        # 无论怎样都关闭浏览器
        pyautogui.press('f11')
        await asyncio.sleep(0.5)
        if browser:
            try:
                await browser.stop()
            except Exception:
                try:
                    browser.stop()
                except Exception:
                    pass
        pyperclip.copy(old_clip)
        log_cb("🧹 浏览器已关闭")

    # 结果处理
    if all_success:
        # 备份 sent 到 food备/日期
        backup_dir = backup_root / date.today().isoformat()
        backup_dir.mkdir(parents=True, exist_ok=True)
        sent_files = list(sent_dir.iterdir())
        for f in sent_files:
            if f.is_file():
                shutil.copy2(str(f), str(backup_dir / f.name))
        log_cb(f"💾 已备份 {len(sent_files)} 个文件到 {backup_dir}")

        # 将 sent 文件移回源目录
        for f in sent_files:
            shutil.move(str(f), str(source_dir / f.name))
        # 删除空的 sent 文件夹
        try:
            sent_dir.rmdir()
        except Exception:
            pass
        log_cb(f"🎉 全部完成，{total} 个文件已发送并归位")
        return True
    else:
        log_cb("⚠️ 发送未全部完成，sent 文件夹保留，请检查")
        return False

def run_task_thread(config, log_cb, stop_event, done_callback):
    """在独立线程中运行异步任务，完成后回调 done_callback"""
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(send_task(config, log_cb, stop_event))
        loop.close()
        # 通知 GUI 任务结束
        if done_callback:
            done_callback(success)
    t = threading.Thread(target=runner, daemon=True)
    t.start()

# ======================== GUI 应用 ========================
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VivianFeeder 配置与运行")
        self.geometry("900x750")
        self.resizable(True, True)

        # 配置文件
        self.config = load_config()

        # 运行状态
        self.running = False
        self.stop_event = threading.Event()
        self.unsaved_changes = False  # 参数是否被修改过但未保存

        # 创建界面
        self.create_widgets()
        self.load_config_to_gui()

        # 绑定窗口关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # 设置初始按钮状态
        self.update_buttons_state()

    def create_widgets(self):
        # 主面板上下分：参数区（带滚动）和 日志+按钮区
        main_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # 参数区域放在 Canvas 中实现滚动
        canvas = tk.Canvas(main_paned, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_paned, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        main_paned.add(canvas, weight=1)
        main_paned.add(scrollbar)  # 这个布局会有点问题，改为 pack 更好，但简单起见我们直接 pack canvas 和 scrollbar
        # 实际上 PanedWindow 中的子部件需要 add，我们改进一下：用 Frame 包含 canvas+scrollbar
        # 重新实现：
        self.destroy_main_paned = True
        # 后面我们会用简单布局：上下两个 Frame

    def create_widgets(self):
        # 顶部参数区（带滚动）
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(top_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(top_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部日志和按钮区
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False)

        # 日志区域
        log_label = ttk.Label(bottom_frame, text="运行日志：")
        log_label.pack(anchor=tk.W)
        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=12, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮区域
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.save_btn = ttk.Button(btn_frame, text="保存配置", command=self.save_config_gui)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(btn_frame, text="运行", command=self.start_task)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="强制停止", command=self.stop_task, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.exit_btn = ttk.Button(btn_frame, text="退出程序", command=self.on_exit)
        self.exit_btn.pack(side=tk.RIGHT, padx=5)

        # 构建参数输入控件
        self.build_config_fields()

    def build_config_fields(self):
        """在 self.scrollable_frame 中构建所有配置输入项"""
        # 清空之前内容（如果有）
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        row = 0
        # 工具函数
        def add_label_entry(parent, text, var, row, column=0, width=50):
            lbl = ttk.Label(parent, text=text)
            lbl.grid(row=row, column=column, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(parent, textvariable=var, width=width)
            entry.grid(row=row, column=column+1, sticky=tk.EW, padx=5, pady=2)
            # 绑定修改事件以标记未保存
            var.trace_add("write", lambda *a: self.set_unsaved())
            return entry

        def add_checkbutton(parent, text, var, row, column=0):
            cb = ttk.Checkbutton(parent, text=text, variable=var)
            cb.grid(row=row, column=column, columnspan=2, sticky=tk.W, padx=5, pady=2)
            var.trace_add("write", lambda *a: self.set_unsaved())

        # 所有变量存储为实例属性，便于获取/设置
        self.vars = {}

        # ---- 基本设置 ----
        frm_basic = ttk.LabelFrame(self.scrollable_frame, text="基本设置")
        frm_basic.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["CHAT_URL"] = tk.StringVar()
        add_label_entry(frm_basic, "对话链接:", self.vars["CHAT_URL"], 0, width=60)

        self.vars["EDGE_PATH"] = tk.StringVar()
        add_label_entry(frm_basic, "Edge 路径:", self.vars["EDGE_PATH"], 1, width=60)

        self.vars["USER_DATA_DIR"] = tk.StringVar()
        add_label_entry(frm_basic, "用户数据目录:", self.vars["USER_DATA_DIR"], 2, width=60)

        # ---- 坐标设置 ----
        frm_coords = ttk.LabelFrame(self.scrollable_frame, text="坐标设置")
        frm_coords.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["INPUT_X"] = tk.IntVar()
        add_label_entry(frm_coords, "输入框 X:", self.vars["INPUT_X"], 0)
        self.vars["INPUT_Y"] = tk.IntVar()
        add_label_entry(frm_coords, "输入框 Y:", self.vars["INPUT_Y"], 1)
        self.vars["COPY_X"] = tk.IntVar()
        add_label_entry(frm_coords, "复制按钮 X:", self.vars["COPY_X"], 2)
        self.vars["COPY_Y"] = tk.IntVar()
        add_label_entry(frm_coords, "复制按钮 Y:", self.vars["COPY_Y"], 3)

        # ---- 时间与批次 ----
        frm_time = ttk.LabelFrame(self.scrollable_frame, text="时间与批次")
        frm_time.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["INITIAL_WAIT"] = tk.IntVar()
        add_label_entry(frm_time, "初始等待(秒):", self.vars["INITIAL_WAIT"], 0)
        self.vars["POLL_INTERVAL"] = tk.IntVar()
        add_label_entry(frm_time, "轮询间隔(秒):", self.vars["POLL_INTERVAL"], 1)
        self.vars["MAX_TOTAL_WAIT"] = tk.IntVar()
        add_label_entry(frm_time, "最大等待(秒):", self.vars["MAX_TOTAL_WAIT"], 2)
        self.vars["BATCH_SIZE"] = tk.IntVar()
        add_label_entry(frm_time, "每批数量:", self.vars["BATCH_SIZE"], 3)

        # ---- 文件设置 ----
        frm_files = ttk.LabelFrame(self.scrollable_frame, text="文件设置")
        frm_files.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["USE_OBSIDIAN"] = tk.BooleanVar()
        add_checkbutton(frm_files, "使用 Obsidian (.md 文件)", self.vars["USE_OBSIDIAN"], 0)

        self.vars["OBSIDIAN_DAILY_PATH"] = tk.StringVar()
        add_label_entry(frm_files, "源文件夹:", self.vars["OBSIDIAN_DAILY_PATH"], 1, width=60)

        # ---- 日期与消息 ----
        frm_date = ttk.LabelFrame(self.scrollable_frame, text="相遇日期与开场消息")
        frm_date.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["MEET_DATE_VIVIAN"] = tk.StringVar()
        add_label_entry(frm_date, "Vivian 相遇日:", self.vars["MEET_DATE_VIVIAN"], 0)
        self.vars["MEET_DATE_HANAKO"] = tk.StringVar()
        add_label_entry(frm_date, "Hanako 相遇日:", self.vars["MEET_DATE_HANAKO"], 1)

        # 开场消息模板（多行）
        ttk.Label(frm_date, text="开场消息模板:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.vars["OPENING_MSG_TEMPLATE"] = tk.Text(frm_date, height=4, width=70, wrap=tk.WORD)
        self.vars["OPENING_MSG_TEMPLATE"].grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        # 绑定修改
        self.vars["OPENING_MSG_TEMPLATE"].bind("<<Modified>>", lambda e: self.set_unsaved())

        # ---- 备份 ----
        frm_backup = ttk.LabelFrame(self.scrollable_frame, text="备份设置")
        frm_backup.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1

        self.vars["BACKUP_ROOT"] = tk.StringVar()
        add_label_entry(frm_backup, "备份根目录:", self.vars["BACKUP_ROOT"], 0, width=60)

        # 让 grid 列可伸缩
        self.scrollable_frame.columnconfigure(1, weight=1)

    def set_unsaved(self):
        """标记配置已修改"""
        self.unsaved_changes = True
        self.update_buttons_state()

    def update_buttons_state(self):
        """根据运行状态和未保存状态更新按钮"""
        if self.running:
            self.run_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.DISABLED)  # 运行中不能保存
        else:
            self.stop_btn.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.NORMAL)
            # 运行按钮：未保存修改时禁用，否则启用
            if self.unsaved_changes:
                self.run_btn.config(state=tk.DISABLED)
            else:
                self.run_btn.config(state=tk.NORMAL)

    def log(self, message):
        """线程安全地输出日志到 GUI"""
        def append():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.after(0, append)

    def load_config_to_gui(self):
        """将当前配置显示到界面"""
        self.vars["CHAT_URL"].set(self.config["CHAT_URL"])
        self.vars["EDGE_PATH"].set(self.config["EDGE_PATH"])
        self.vars["USER_DATA_DIR"].set(self.config["USER_DATA_DIR"])
        self.vars["INPUT_X"].set(self.config["INPUT_X"])
        self.vars["INPUT_Y"].set(self.config["INPUT_Y"])
        self.vars["COPY_X"].set(self.config["COPY_X"])
        self.vars["COPY_Y"].set(self.config["COPY_Y"])
        self.vars["INITIAL_WAIT"].set(self.config["INITIAL_WAIT"])
        self.vars["POLL_INTERVAL"].set(self.config["POLL_INTERVAL"])
        self.vars["MAX_TOTAL_WAIT"].set(self.config["MAX_TOTAL_WAIT"])
        self.vars["BATCH_SIZE"].set(self.config["BATCH_SIZE"])
        self.vars["USE_OBSIDIAN"].set(self.config["USE_OBSIDIAN"])
        self.vars["OBSIDIAN_DAILY_PATH"].set(self.config["OBSIDIAN_DAILY_PATH"])
        self.vars["MEET_DATE_VIVIAN"].set(self.config["MEET_DATE_VIVIAN"])
        self.vars["MEET_DATE_HANAKO"].set(self.config["MEET_DATE_HANAKO"])
        self.vars["BACKUP_ROOT"].set(self.config["BACKUP_ROOT"])

        # 开场消息模板
        text_widget = self.vars["OPENING_MSG_TEMPLATE"]
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", self.config["OPENING_MSG_TEMPLATE"])
        text_widget.edit_modified(False)  # 清除修改标志

        self.unsaved_changes = False
        self.update_buttons_state()

    def save_config_gui(self):
        """从界面读取值并保存到配置文件"""
        try:
            self.config["CHAT_URL"] = self.vars["CHAT_URL"].get()
            self.config["EDGE_PATH"] = self.vars["EDGE_PATH"].get()
            self.config["USER_DATA_DIR"] = self.vars["USER_DATA_DIR"].get()
            self.config["INPUT_X"] = self.vars["INPUT_X"].get()
            self.config["INPUT_Y"] = self.vars["INPUT_Y"].get()
            self.config["COPY_X"] = self.vars["COPY_X"].get()
            self.config["COPY_Y"] = self.vars["COPY_Y"].get()
            self.config["INITIAL_WAIT"] = self.vars["INITIAL_WAIT"].get()
            self.config["POLL_INTERVAL"] = self.vars["POLL_INTERVAL"].get()
            self.config["MAX_TOTAL_WAIT"] = self.vars["MAX_TOTAL_WAIT"].get()
            self.config["BATCH_SIZE"] = self.vars["BATCH_SIZE"].get()
            self.config["USE_OBSIDIAN"] = self.vars["USE_OBSIDIAN"].get()
            self.config["OBSIDIAN_DAILY_PATH"] = self.vars["OBSIDIAN_DAILY_PATH"].get()
            self.config["MEET_DATE_VIVIAN"] = self.vars["MEET_DATE_VIVIAN"].get()
            self.config["MEET_DATE_HANAKO"] = self.vars["MEET_DATE_HANAKO"].get()
            self.config["BACKUP_ROOT"] = self.vars["BACKUP_ROOT"].get()

            # 开场消息模板从 Text 控件获取
            self.config["OPENING_MSG_TEMPLATE"] = self.vars["OPENING_MSG_TEMPLATE"].get("1.0", tk.END).strip()
            self.vars["OPENING_MSG_TEMPLATE"].edit_modified(False)

            save_config(self.config)
            self.unsaved_changes = False
            self.log("💾 配置已保存")
            self.update_buttons_state()
        except Exception as e:
            messagebox.showerror("保存错误", f"保存配置失败: {e}")

    def start_task(self):
        """启动发送任务"""
        if self.running:
            return
        # 必须已保存（按钮已保证，但再检查一次）
        if self.unsaved_changes:
            messagebox.showwarning("未保存", "请先保存配置")
            return

        self.running = True
        self.stop_event.clear()
        self.update_buttons_state()
        self.log_text.delete("1.0", tk.END)  # 清空日志
        self.log("▶️ 任务开始...")

        # 使用当前配置运行
        config_copy = self.config.copy()
        run_task_thread(config_copy, self.log, self.stop_event, self.task_done)

    def stop_task(self):
        """强制停止"""
        if self.running:
            self.stop_event.set()
            self.log("⏹️ 正在发送停止信号...")
            self.stop_btn.config(state=tk.DISABLED)

    def task_done(self, success=None):
        """任务结束回调（在主线程中）"""
        self.running = False
        self.stop_event.clear()
        self.update_buttons_state()
        if success is True:
            self.log("✅ 任务已成功完成")
        elif success is False:
            self.log("⚠️ 任务未完全成功，请查看日志")
        else:
            self.log("🛑 任务已结束")

    def on_exit(self):
        """退出程序"""
        if self.running:
            if messagebox.askyesno("确认退出", "任务正在运行，确定要退出吗？"):
                self.stop_event.set()
                # 等待短暂时间让线程结束
                self.update()
                time.sleep(1)
            else:
                return
        self.destroy()

# ======================== 主入口 ========================
if __name__ == "__main__":
    app = Application()
    app.mainloop()