#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单 Git 多仓库一键推送工具
支持保存仓库列表、批量 add、commit、push
"""

import subprocess
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

REPO_LIST_FILE = "repo_list.txt"

def load_repos():
    """加载保存的仓库列表"""
    repos = []
    if os.path.exists(REPO_LIST_FILE):
        with open(REPO_LIST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    repos.append(line)
    return repos

def save_repos(repos):
    """保存仓库列表到文件"""
    with open(REPO_LIST_FILE, "w", encoding="utf-8") as f:
        for r in repos:
            f.write(r + "\n")

def run_command(cmd, cwd=None):
    """
    运行命令并返回 (success, output)
    """
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            shell=True, encoding="utf-8"
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except Exception as e:
        return False, str(e)


class GitPusherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Git 多仓库一键推送")
        self.geometry("700x600")
        self.running = False

        # --- 仓库列表区 ---
        frame_list = ttk.LabelFrame(self, text="仓库列表（每行一个绝对路径）")
        frame_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.repo_text = scrolledtext.ScrolledText(frame_list, height=8)
        self.repo_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # 加载已保存列表
        for repo in load_repos():
            self.repo_text.insert(tk.END, repo + "\n")

        btn_frame = ttk.Frame(frame_list)
        btn_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(btn_frame, text="保存列表", command=self.save_repo_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="添加当前目录", command=self.add_current_dir).pack(side=tk.LEFT, padx=5)

        # --- Commit 消息 ---
        frame_msg = ttk.Frame(self)
        frame_msg.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(frame_msg, text="Commit 消息").pack(side=tk.LEFT)
        self.msg_var = tk.StringVar(value="auto update")
        ttk.Entry(frame_msg, textvariable=self.msg_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # --- 按钮 ---
        frame_btn = ttk.Frame(self)
        frame_btn.pack(fill=tk.X, padx=5, pady=5)
        self.push_btn = ttk.Button(frame_btn, text="🚀 一键推送所有仓库", command=self.start_push)
        self.push_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_btn, text="退出", command=self.on_exit).pack(side=tk.RIGHT, padx=5)

        # --- 日志区 ---
        frame_log = ttk.LabelFrame(self, text="运行日志")
        frame_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = scrolledtext.ScrolledText(frame_log, height=12, state="normal")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def log(self, msg):
        """线程安全添加日志"""
        def _append():
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
        # 如果已在主线程，直接调用；否则通过 after 调度
        try:
            if threading.current_thread() is threading.main_thread():
                _append()
            else:
                self.after(0, _append)
        except RuntimeError:
            # 极端情况，主线程已退出
            pass

    def save_repo_list(self):
        """保存文本框内容到文件"""
        repos = self.repo_text.get(1.0, tk.END).strip().splitlines()
        save_repos(repos)
        self.log("💾 仓库列表已保存")

    def add_current_dir(self):
        """添加当前工作目录到列表"""
        cur = os.getcwd()
        self.repo_text.insert(tk.END, cur + "\n")
        self.log(f"➕ 已添加 {cur}")

    def start_push(self):
        """启动推送（在新线程中）"""
        if self.running:
            return

        # 获取仓库列表（以文本框当前内容为准）
        repos = [
            line.strip()
            for line in self.repo_text.get(1.0, tk.END).splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not repos:
            messagebox.showwarning("无仓库", "请先添加至少一个仓库路径")
            return

        self.running = True
        self.push_btn.config(state=tk.DISABLED)
        self.log_text.delete(1.0, tk.END)
        self.log("▶️ 开始推送...")

        msg = self.msg_var.get().strip()
        if not msg:
            msg = "auto update"

        def worker():
            success_count = 0
            total = len(repos)
            for repo in repos:
                self.log(f"\n--- 处理 {repo} ---")
                if not os.path.isdir(repo):
                    self.log(f"❌ 目录不存在 {repo}")
                    continue
                if not os.path.isdir(os.path.join(repo, ".git")):
                    self.log(f"❌ 不是 Git 仓库 {repo}")
                    continue

                # git add .
                self.log("➕ git add .")
                ok, out = run_command("git add .", cwd=repo)
                if not ok:
                    self.log(f"❌ add 失败: {out}")
                    continue

                # git commit
                self.log(f"📝 git commit -m \"{msg}\"")
                ok, out = run_command(f'git commit -m "{msg}"', cwd=repo)
                # commit 可能返回 "nothing to commit"，此时不算失败
                if not ok and "nothing to commit" not in out.lower():
                    self.log(f"⚠️ commit 可能失败: {out}")

                # git push
                self.log("📤 git push")
                ok, out = run_command("git push", cwd=repo)
                if ok:
                    self.log(f"✅ 推送成功 {repo}")
                    success_count += 1
                else:
                    self.log(f"❌ 推送失败: {out}")

            self.log(f"\n🎉 完成！成功推送 {success_count}/{total} 个仓库")
            self.running = False
            # 恢复按钮（在主线程中执行）
            self.after(0, lambda: self.push_btn.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def on_exit(self):
        """关闭窗口"""
        self.destroy()


if __name__ == "__main__":
    app = GitPusherApp()
    app.mainloop()