import tkinter as tk
from tkinter import ttk
from datetime import datetime
import random
import ctypes
from ctypes import wintypes

# ---------------- 工资计算逻辑 ----------------
def parse_periods(text):
    result = []
    parts = text.split(",")
    for p in parts:
        s, e = p.strip().split("-")
        t1 = datetime.strptime(s, "%H:%M").time()
        t2 = datetime.strptime(e, "%H:%M").time()
        result.append((t1, t2))
    return result

def minutes_between(t1, t2):
    dt1 = datetime.combine(datetime.today(), t1)
    dt2 = datetime.combine(datetime.today(), t2)
    return max(0, int((dt2 - dt1).total_seconds() / 60))

def calc_worked_minutes(periods):
    now = datetime.now().time()
    mins = 0
    for s, e in periods:
        if now >= e:
            # 时段已结束，计算完整时段
            mins += minutes_between(s, e)
        elif now >= s and now < e:
            # 时段进行中，计算从开始到现在的分钟数
            mins += minutes_between(s, now)
        # 如果 now < s，时段还未开始，不计算
    return mins

def seconds_between(t1, t2):
    """计算两个时间之间的秒数"""
    dt1 = datetime.combine(datetime.today(), t1)
    dt2 = datetime.combine(datetime.today(), t2)
    return max(0, int((dt2 - dt1).total_seconds()))

def calc_worked_seconds(periods):
    """计算已工作的秒数"""
    now = datetime.now().time()
    seconds = 0
    for s, e in periods:
        if now >= e:
            # 时段已结束，计算完整时段
            seconds += seconds_between(s, e)
        elif now >= s and now < e:
            # 时段进行中，计算从开始到现在的秒数
            seconds += seconds_between(s, now)
        # 如果 now < s，时段还未开始，不计算
    return seconds

def calc_total_minutes(periods):
    return sum(minutes_between(s, e) for s, e in periods)

def calc_total_seconds(periods):
    """计算总工作秒数"""
    return sum(seconds_between(s, e) for s, e in periods)

# ---------------- 工具提示类 ----------------
class ToolTip:
    def __init__(self, widget, text, x_offset=10, y_offset=10):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.x_offset = x_offset
        self.y_offset = y_offset
    
    def showtip(self, event=None):
        """显示工具提示"""
        if self.tipwindow or not self.text:
            return
        
        # 获取鼠标位置或widget位置
        if event:
            x = event.x_root + self.x_offset
            y = event.y_root + self.y_offset
        else:
            x = self.widget.winfo_rootx() + self.x_offset
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + self.y_offset
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        tw.attributes("-alpha", 0.9)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify="left",
                        background="#2a2a2a", foreground="#4CAF50",
                        relief="solid", borderwidth=1,
                        font=("Microsoft YaHei UI", 9),
                        padx=8, pady=4)
        label.pack(ipadx=1)
    
    def hidetip(self):
        """隐藏工具提示"""
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# ---------------- 悬浮小工具 UI ----------------
class FloatingWidget:
    def __init__(self, days, salary, time_periods):
        self.days = days
        self.salary = salary
        self.periods = parse_periods(time_periods)
        self.daily_salary = salary / days
        self.total_minutes = calc_total_minutes(self.periods)
        self.total_seconds = calc_total_seconds(self.periods)
        
        # 鼓励话语列表
        self.encouragements = [
            "💪 加油！你正在创造价值！",
            "✨ 每一分钟都在积累财富！",
            "🚀 坚持就是胜利！",
            "🌟 今天的努力，明天的收获！",
            "💎 专注当下，未来可期！",
            "🔥 你比想象中更强大！",
            "⚡ 时间就是金钱，继续努力！",
            "🎯 目标就在前方，加油！",
            "💼 每一份努力都不会白费！",
            "🌈 坚持到底，胜利属于你！",
            "🎉 你正在做得很棒！",
            "💪 相信自己，你能行！",
            "✨ 每一秒都在进步！",
            "🚀 距离目标越来越近了！",
            "🌟 今天的你比昨天更优秀！"
        ]
        self.tooltip = None  # 工具提示对象

        self.root = tk.Tk()
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes("-alpha", 0.80)    # 更透明

        # 现代化深色主题配色
        self.bg_color = "#1a1a1a"  # 深灰黑背景
        self.card_color = "#252525"  # 卡片背景
        self.text_primary = "#ffffff"  # 主文字
        self.text_secondary = "#b0b0b0"  # 次要文字
        self.text_accent = "#4CAF50"  # 强调色（绿色）
        self.money_color = "#FFD700"  # 金额金色
        self.progress_color = "#4CAF50"  # 进度条绿色
        self.progress_bg = "#2a2a2a"  # 进度条背景
        
        self.root.configure(bg=self.bg_color)
        
        # 创建主容器框架（卡片式设计）
        self.frame = tk.Frame(self.root, bg=self.card_color, relief="flat")
        self.frame.pack(padx=4, pady=4)
        
        # 创建标题栏（带关闭按钮）
        self.header_frame = tk.Frame(self.frame, bg=self.card_color)
        self.header_frame.pack(fill="x", padx=6, pady=(4, 1))
        
        # 关闭按钮（更小）
        self.close_btn = tk.Label(self.header_frame, text="×", font=("Arial", 12, "bold"),
                                  fg=self.text_secondary, bg=self.card_color, 
                                  cursor="hand2", width=1)
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda e: self.root.quit())
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg="#ff4444", bg="#3a3a3a"))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=self.text_secondary, bg=self.card_color))
        
        # 主信息标签（更小的字体）
        self.label = tk.Label(self.frame, text="", font=("Microsoft YaHei UI", 8),
                              fg=self.text_primary, bg=self.card_color, justify="left")
        self.label.pack(padx=8, pady=(0, 4))
        
        # 配置现代化进度条样式（必须在创建进度条之前配置）
        style = ttk.Style()
        style.theme_use('default')
        
        # 获取默认进度条布局并创建自定义布局
        try:
            default_layout = style.layout('TProgressbar')
            style.layout('Modern.TProgressbar', default_layout)
        except:
            # 如果获取布局失败，使用简单的布局定义
            style.layout('Modern.TProgressbar', [
                ('Horizontal.Progressbar.trough', {
                    'sticky': 'nswe',
                    'children': [
                        ('Horizontal.Progressbar.pbar', {
                            'side': 'left',
                            'sticky': 'ns'
                        })
                    ]
                })
            ])
        
        style.configure("Modern.TProgressbar",
                       background=self.progress_color,
                       troughcolor=self.progress_bg,
                       borderwidth=0,
                       lightcolor=self.progress_color,
                       darkcolor=self.progress_color)
        
        # 创建进度条容器
        self.progress_frame = tk.Frame(self.frame, bg=self.card_color)
        self.progress_frame.pack(fill="x", padx=8, pady=(0, 6))
        
        # 创建进度条（更小更细）
        self.progress = ttk.Progressbar(self.progress_frame, length=140, mode='determinate',
                                        maximum=100, style="Modern.TProgressbar")
        self.progress.pack(fill="x", pady=0)

        # 绑定拖动事件到整个框架
        self.frame.bind("<Button-1>", self.start_move)
        self.frame.bind("<B1-Motion>", self.do_move)
        self.header_frame.bind("<Button-1>", self.start_move)
        self.header_frame.bind("<B1-Motion>", self.do_move)
        self.label.bind("<Button-1>", self.start_move)
        self.label.bind("<B1-Motion>", self.do_move)
        self.progress_frame.bind("<Button-1>", self.start_move)
        self.progress_frame.bind("<B1-Motion>", self.do_move)
        
        # 双击关闭
        self.frame.bind("<Double-Button-1>", lambda e: self.root.quit())
        self.label.bind("<Double-Button-1>", lambda e: self.root.quit())
        
        # ESC 键关闭
        self.root.bind("<Escape>", lambda e: self.root.quit())
        
        # 鼠标悬停显示鼓励话语工具提示
        self.frame.bind("<Enter>", self.on_mouse_enter)
        self.frame.bind("<Leave>", self.on_mouse_leave)
        self.label.bind("<Enter>", self.on_mouse_enter)
        self.label.bind("<Leave>", self.on_mouse_leave)
        self.progress_frame.bind("<Enter>", self.on_mouse_enter)
        self.progress_frame.bind("<Leave>", self.on_mouse_leave)

        # 更新窗口以获取实际大小，然后设置到右下角
        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取任务栏高度（使用Windows API或固定值）
        taskbar_height = 80  # 默认使用较大的值确保不被覆盖
        
        try:
            # 尝试使用Windows API获取任务栏信息
            shell32 = ctypes.windll.shell32
            
            class APPBARDATA(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("hWnd", ctypes.c_void_p),
                    ("uCallbackMessage", ctypes.c_uint),
                    ("uEdge", ctypes.c_uint),
                    ("rc", wintypes.RECT),
                    ("lParam", ctypes.c_long),
                ]
            
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            result = shell32.SHAppBarMessage(5, ctypes.byref(abd))  # ABM_GETTASKBARPOS = 5
            
            if result and abd.uEdge == 2:  # ABE_BOTTOM = 2 (任务栏在底部)
                taskbar_height = abd.rc.bottom - abd.rc.top + 10  # 额外加10像素边距
        except:
            pass  # 使用默认值
        
        # 计算右下角位置（留出任务栏和边距）
        margin = 20
        x = screen_width - window_width - margin
        y = screen_height - window_height - taskbar_height - margin
        
        self.root.geometry(f"+{x}+{y}")

        self.update_info()
        self.root.mainloop()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        new_x = event.x_root - self.x
        new_y = event.y_root - self.y
        self.root.geometry(f"+{new_x}+{new_y}")
    
    def on_mouse_enter(self, event):
        """鼠标进入时显示随机鼓励话语工具提示"""
        if not self.tooltip:
            encouragement = random.choice(self.encouragements)
            self.tooltip = ToolTip(self.frame, encouragement)
            self.tooltip.showtip(event)
    
    def on_mouse_leave(self, event):
        """鼠标离开时隐藏工具提示"""
        if self.tooltip:
            self.tooltip.hidetip()
            self.tooltip = None

    def update_info(self):
        worked = calc_worked_minutes(self.periods)
        if self.total_minutes > 0:
            percent = min(100, max(0, (worked / self.total_minutes) * 100))
            earned = self.daily_salary * (worked / self.total_minutes)
        else:
            percent = 0
            earned = 0
        
        # 计算剩余工作时间（精确到秒）
        worked_seconds = calc_worked_seconds(self.periods)
        remaining_seconds = max(0, self.total_seconds - worked_seconds)
        remaining_hours = remaining_seconds // 3600
        remaining_mins = (remaining_seconds % 3600) // 60
        remaining_secs = remaining_seconds % 60
        
        # 根据进度动态调整进度条颜色
        if percent >= 100:
            progress_color = "#4CAF50"  # 完成 - 绿色
        elif percent >= 75:
            progress_color = "#8BC34A"  # 接近完成 - 浅绿
        elif percent >= 50:
            progress_color = "#FFC107"  # 过半 - 黄色
        else:
            progress_color = "#FF9800"  # 刚开始 - 橙色
        
        # 更新进度条颜色
        style = ttk.Style()
        style.configure("Modern.TProgressbar",
                       background=progress_color,
                       troughcolor=self.progress_bg,
                       borderwidth=0,
                       lightcolor=progress_color,
                       darkcolor=progress_color)
        
        # 格式化显示文本（使用emoji增强可读性）
        self.label.config(
            text=f"💰 今日：¥{earned:.2f}\n"
                 f"📊 进度：{percent:.1f}%\n"
                 f"⏳ 剩余：{remaining_hours:02d}:{remaining_mins:02d}:{remaining_secs:02d}",
            fg=self.text_primary
        )
        
        # 更新进度条
        self.progress['value'] = percent

        self.root.after(1000, self.update_info)

# ---------------- 程序入口 ----------------
if __name__ == "__main__":
    # 可直接修改参数
    widget = FloatingWidget(
        days=25,  # 每月工作天数
        salary=10000,  # 月薪
        time_periods="9:00-12:00, 13:30-18:30"
    )
