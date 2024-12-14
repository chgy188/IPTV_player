import tkinter as tk
from tkinter import filedialog
import subprocess
#https://live.fanmingming.com/tv/m3u/ipv6.m3u
import csv
import os
import ctypes
import sys
import requests
import pickle


def add_to_path(path):
    # 获取当前的 PATH 环境变量
    current_path = os.environ['PATH']
    
    # 检查路径是否已经存在于 PATH 中
    if path not in current_path.split(os.pathsep):
        # 将新路径添加到 PATH 中
        new_path = os.pathsep.join([current_path, path])
        
        # 设置新的 PATH 环境变量
        os.environ['PATH'] = new_path
        
        # 使用 ctypes 修改系统的 PATH 环境变量
        system_path = os.environ['PATH']
        # ctypes.windll.kernel32.SetEnvironmentVariableW('PATH', system_path)
        subprocess.run(['setx', 'PATH', system_path], shell=True)
        print(f"Path {path} added to system PATH.")
    else:
        print(f"Path {path} is already in system PATH.")

# 调用函数添加路径


class IPTVPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("IPTV Player")
        
        self.messagebox = tk.messagebox
        # 创建菜单
        menubar = tk.Menu(root)
        root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open M3U File", command=self.open_file)

        # 创建节目列表
        self.group_list = tk.Listbox(root)
        
        self.program_list = tk.Listbox(root)
        
        # 使用 Grid 管理器放置列表框
        self.group_list.grid(row=0, column=0, sticky='nsew')
        self.program_list.grid(row=0, column=1, sticky='nsew')
        # 设置主窗口的行和列权重，以便列表框可以扩展
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)

        # 创建右键菜单
        self.right_click_menu = tk.Menu(root, tearoff=0)
        self.right_click_menu.add_command(label="删除", command=self.remove_program)

        # 绑定右键事件
        self.program_list.bind("<Button-3>", self.show_right_click_menu)

        self.group_list.bind('<<ListboxSelect>>', self.on_group_select)
        self.program_list.bind('<<ListboxSelect>>', self.on_program_select)
        # 创建视频播放窗口
        # self.video_frame = tk.Frame(root, width=640, height=480)
        # self.video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.ffplay_process = None
        if len(channels) > 0:
            self.load_groups('')
    
    def show_right_click_menu(self, event):
        # 显示右键菜单
        self.right_click_menu.post(event.x_root, event.y_root)

    def remove_program(self,group,name):
        # 获取当前选中的program_index
        program_index = self.program_list.curselection()
        # 删除program_lists中的元素
        self.program_list.delete(program_index)
        for channel in channels:
            if channel[0] == group and channel[1] ==name:
                channels.remove(channel)
                break
        with open('channels.pkl', 'wb') as f:
            pickle.dump(channels, f)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("M3U Files", "*.m3u")])
        if file_path:
            self.load_groups(file_path)

    def load_groups(self, file_path):
        global channels
        # 清空节目列表
        self.group_list.delete(0, tk.END)
        self.program_list.delete(0, tk.END)
        # 读取并解析m3u文件
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter='\n')
                channels = []
                for row in reader:
                    for item in row:
                        if item.startswith('#EXTINF:'):
                            parts = item.split(',')
                            if len(parts) >= 2:
                                group = parts[0].split('group-title=')[1].replace('"', '')
                                name= parts[1].strip()
                                channels.append([group, name, None])
                        elif item.startswith('http'):
                            if channels and channels[-1][2] is None:
                                channels[-1][2] = item
                            else:
                                channels.append([None, None, item])
                # 将 channels 数组保存到文件中
            with open('channels.pkl', 'wb') as f:
                pickle.dump(channels, f)        # 提取节目信息
        
        inserted_groups = set()

        for channel in channels:
            if channel:
                group = channel[0]
                if group not in inserted_groups:
                    self.group_list.insert(tk.END, group)
                    inserted_groups.add(group)    
        # 获取列表框中的元素数量
        num_items = self.group_list.size()

        # 设置列表框的高度为元素数量加一
        self.group_list.config(height=num_items + 1)
    
    def is_url_accessible(self,url):
        timeout = 1
        try:
            response = requests.get(url, timeout=timeout)
            # 如果响应状态码为200，则表示URL是可访问的
            if response.status_code == 200:
                return True
        except requests.exceptions.Timeout:
            print("The request timed out")
        except requests.exceptions.RequestException as e:
            # 如果发生异常，则表示URL是不可访问的
            print(f"Error accessing URL: {e}")
        return False

    def play_program(self, program_url):
        
        self.ffplay_process=subprocess.Popen(['ffplay','-v','error','-autoexit', '-i',program_url, '-window_title', 'IPTV', '-x', '800', '-y', '600'])       
        # 定义一个函数来尝试将焦点设置回Tkinter窗口
        



    def on_group_select(self, event):
        global selected_group
        # 获取选中的节目组
        selected_index = self.group_list.curselection()
        if selected_index:
            selected_group = self.group_list.get(selected_index)
            # 清空节目列表
            self.program_list.delete(0, tk.END)

            # 插入该组下的所有节目
            for channel in channels:
                if channel[0] == selected_group:
                    self.program_list.insert(tk.END, channel[1])
            # 获取列表框中的元素数量
            num_items = self.program_list.size()

            # 设置列表框的高度为元素数量加一
            self.program_list.config(height=num_items + 1)

    def on_program_select(self, event):
        # 获取选中的节目
        
        selected_index = self.program_list.curselection()
        selected_name = self.program_list.get(selected_index)
        if self.ffplay_process and self.ffplay_process.poll() is None:
            self.stop_playback()
        for channel in channels:
            if channel[0] == selected_group and channel[1] == selected_name:
                # self.play_program(channel[2])
                if self.is_url_accessible(channel[2]):        
                    self.play_program(channel[2])
                else:
                    if self.messagebox.askokcancel("Attention", "Channel Unavailable,Delete?"):                        
                        self.remove_program(selected_group,selected_name)
        self.root.focus_force()
        return

    def stop_playback(self):
        if self.ffplay_process and self.ffplay_process.poll() is None:
            try:
                self.ffplay_process.terminate()  # 发送终止信号
                self.ffplay_process.wait(timeout=5)  # 等待进程终止，最多等待5秒
            except subprocess.TimeoutExpired:
                self.ffplay_process.kill()  # 如果进程没有终止，强制终止
            finally:
                self.ffplay_process = None



if __name__ == "__main__":
    if os.path.exists('channels.pkl'):
        with open('channels.pkl', 'rb') as f:
            channels = pickle.load(f)
    else:
        channels = []
    
    
    selected_group= None
    root = tk.Tk()
    root.wm_iconbitmap('tv.ico')
    app = IPTVPlayer(root)
    root.mainloop()
