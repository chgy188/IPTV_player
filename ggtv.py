#version 1.4
# 2025.1.29
#自动识别互联网文件类型
#修复了切换全屏退出的问题 2025.2.11
#工具栏布局美化 2025.2.11
#显示视频转移到主线程 2025。2.15
import sys
from PySide6.QtWidgets import QCheckBox,QDialog,QDialogButtonBox,QComboBox,QLineEdit,QToolBar, QPushButton, QSlider, QTextEdit, QVBoxLayout, QProgressBar, QSizePolicy, QApplication, QMainWindow, QListWidget, QHBoxLayout, QWidget, QMenu, QMessageBox, QLabel, QFileDialog, QInputDialog
from PySide6.QtGui import QKeySequence, QShortcut,QWheelEvent, QImage, QPixmap, QIcon, QKeyEvent, QMouseEvent, QPalette, QColor,QAction
from PySide6.QtCore import  Qt, Signal,QTimer,QRunnable, QThreadPool, QMutex,QObject,QPropertyAnimation, QPropertyAnimation, QEasingCurve
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from ffpyplayer.player import MediaPlayer
from ffpyplayer.writer import MediaWriter
from ffpyplayer.tools import set_log_callback
from ffpyplayer.pic import SWScale
import time
import threading
import json
import re
import math
import os

# # 设置代理服务器地址和端口
# os.environ['http_proxy'] = 'http://127.0.0.1:10809'
# os.environ['https_proxy'] = 'http://127.0.0.1:10809'

class WorkerSignals(QObject):
    result = Signal(str,str, str, bool)
    progress = Signal(str,str)

class UrlTester(QRunnable):
    def __init__(self, catogory,name, url, timeout=5):
        super().__init__()
        self.catogory = catogory
        self.name = name
        self.url = url
        self.timeout = timeout
        self.signals = WorkerSignals()
        self._is_stopped = False  # 用于控制任务是否停止

    def run(self):
        if self._is_stopped:
            return
        try:
            response = requests.get(self.url, timeout=self.timeout)
            status = response.status_code == 200
        except Exception:
            status = False
        self.signals.progress.emit(self.catogory,self.name)
        self.signals.result.emit(self.catogory,self.name, self.url, status)
        
    def stop(self):
        self._is_stopped = True  # 标记任务为停止状态

class CustomQListWidget(QListWidget):
    change_program= Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_click_menu)
        self.parent=parent
        
     

    def show_right_click_menu(self, position):
        menu = QMenu(self)         
        add_fav_action = QAction("收藏/取消", self)
        add_fav_action.triggered.connect(self.add_fav)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.remove_program)
        copy_url = QAction("拷贝链接", self)
        copy_url.triggered.connect(self.url_clipboard)
        menu.addAction(add_fav_action)
        menu.addAction(copy_url)
        menu.addAction(delete_action)
        menu.exec(self.mapToGlobal(position))
        
    def add_fav(self):
        selected_item = self.currentItem()
        if selected_item:
            name = selected_item.text()
            if self.parent.selected_group !="我的收藏":
                if "我的收藏" not in self.parent.main_channels.keys():    #在self.channels中添加该组下的该节目                    
                    self.parent.main_channels["我的收藏"]={}
                    self.parent.group_list.insertItem(0,"我的收藏")
                self.parent.main_channels["我的收藏"][name]=self.parent.channels[self.parent.selected_group][name]  
                QMessageBox.information(self, "提示", "我的收藏成功")  
                self.parent.save_config()        
            else:
                del self.parent.main_channels["我的收藏"][name]
                self.takeItem(self.row(selected_item))
                QMessageBox.information(self, "提示", "取消我的收藏成功")      
    
    def url_clipboard(self):
        selected_item = self.currentItem()
        if selected_item:
            name = selected_item.text()
            QApplication.clipboard().setText(self.parent.channels[self.parent.selected_group][name])

         

    def remove_program(self):
        if self.parent.channels==self.parent.main_channels:
            
            selected_item = self.currentItem()
            if selected_item:
                name = selected_item.text()
                #在self.channels中删除该组下的该节目
                del self.parent.channels[self.parent.selected_group][name]            
                #删除该节目的列表
                self.takeItem(self.row(selected_item)) 
                self.parent.save_config()
            

class CustomSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #e0e0e0;
                height: 8px;
                background: #e0e0e0;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #b0bec5; /* Light Blue color */
                border: 1px solid #b0bec5;
                width: 16px;
                margin: -2px 0;
                border-radius: 8px;
            }

            QSlider::handle:horizontal:hover {
                background: #81c784; /* Light Green color */
                border: 1px solid #81c784;
            }

            QSlider::handle:horizontal:pressed {
                background: #4caf50; /* Green color */
                border: 1px solid #4caf50;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 使用 position() 方法获取鼠标位置
            current_value = int(event.position().x() // (self.width() / 1000))
            self.setValue(current_value)
            if window.Duration:
                window.player.seek(current_value / 1000.0 * window.Duration, relative=False)
                super().mousePressEvent(event)
            
        else:
            super().mousePressEvent(event)

class CustomQLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self.show_right_click_menu)
        self.parent=parent
    def mouseMoveEvent(self, event):
        # 获取鼠标位置
        self.parent.show_slider()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self.parent.channels:                
                # self.parent.toggle_list_animate()
                self.parent.toggle_list()
            super().mousePressEvent(event)
        else:
            #显示右键菜单
            self.show_fav_menu(event.pos())
        super().mousePressEvent(event)
    def show_fav_menu(self, position):
        menu = QMenu(self)         
        add_fav_action = QAction("收藏", self)
        add_fav_action.triggered.connect(self.add_fav)        
        menu.addAction(add_fav_action)        
        menu.exec(self.mapToGlobal(position))

    def add_fav(self):
        
        if self.parent.input_path is not None:          
            text, ok = QInputDialog.getText(self, '提示', '起个名字')  
            if ok and text != '':
                if "我的收藏" not in self.parent.main_channels.keys():    #在self.channels中添加该组下的该节
                    self.parent.main_channels["我的收藏"]={}
                    # self.parent.group_list.insertItem(0,"我的收藏")
                self.parent.main_channels["我的收藏"][text]=self.parent.input_path
                self.parent.save_config()

            
class IPTVPlayer(QMainWindow):

    player_frame=Signal(QImage)
    player_end=Signal()
 
    def __init__(self):
        super().__init__()
        self.close_flag=False
        self.player_frame.connect(self.update_image_label)
        self.player_end.connect(self.player_end_slot)
        self.m3u_dict= {}
        self.set_dark_theme()       
        # 加载配置文件
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            
            # 加载 channels 列表
            self.main_channels = config.get('channels',  {'我的收藏': {}})            
            # 加载当前样式
            current_theme = config.get('current_theme', 'dark')
            selected_group_index = config.get('selected_group_index', 0)
            selected_program_index = config.get('selected_program_index', 0)
            self.current_m3u= config.get('current_m3u', None)
            # 加载 m3u_dict 列表
            self.m3u_dict = config.get('m3u_dict', {})
            if current_theme == 'dark':
                self.set_dark_theme()
            else:
                self.set_light_theme()
        except FileNotFoundError:
            self.main_channels = {'我的收藏': {}}
            selected_group_index = None
            selected_program_index = None
            self.set_dark_theme()
            self.current_m3u= None
        
        if self.current_m3u is not None:
            self.setWindowTitle(f"蝈蝈直播TV-当前直播源：{self.current_m3u}")
            
        else:
            self.setWindowTitle(f"蝈蝈直播TV")                    
        
        screen = QApplication.primaryScreen().availableGeometry()
        screensize = screen.size()       
        self.setMinimumSize(int(screensize.width() * 0.72), int(screensize.width() * 0.72 / 1.78))        
        self.move((screensize.width() - self.width()) // 2, (screensize.height() - self.height()) // 2)
                
        self.thread = None
        self.lock = threading.Lock()
        self.running=False
        self.player = None
        self.mutex = QMutex()  # 用于线程安全的锁        
        self.current_media = None
        self.input_path=None
        
        self.Duration = None
        self.record = False
        self.frame_rate = (0, 0)
        self.vid_size = (0, 0)
        self.tv=True
        self.create_layout()
        self.create_menu()
        self.http_proxy=config.get('http_proxy', '')
        self.https_proxy=config.get('https_proxy', '')
        self.proxy_enable=config.get('proxy_enable', False)
        if self.proxy_enable:
            os.environ['http_proxy'] = self.http_proxy
            os.environ['https_proxy'] = self.https_proxy
        else:
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''
        self.workers = []  # 存储所有工作线程           
        self.installEventFilter(self)
        self.setAcceptDrops(True)
        # 添加计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.hide_slider)
        self.slider.setVisible(False)
        set_log_callback(self.player_log_callback)

        # 创建一个快捷键Ctrl+V
        shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        shortcut.activated.connect(self.paste_from_clipboard)
        # self.normal_margin = self.main_layout.getContentsMargins()
        
        if self.count_channel_num(self.main_channels) > 0:
            self.channels = self.main_channels
            self.load_groups('')
        if selected_group_index is not None:
            if 0 <=selected_group_index < self.group_list.count():
                self.group_list.setCurrentRow(selected_group_index)
                
        if selected_program_index is not None:            
            if 0 <= selected_program_index < self.program_list.count():
                self.program_list.setCurrentRow(selected_program_index)
        if self.count_channel_num(self.main_channels) > 0:
            self.list_container.setVisible(False)
            self.swap_fullscreen()
            self.hide_slider()
        self.setFocus() 
    

    def player_log_callback(self,message,level):        
        if message:
            message = message.strip()
            # print(message)                    
            # if self.current_media in message:
            self.running = False                
            self.switch_program("down")  
            self.running = True          
    

    def player_callback(self, selector, val):               
        if selector == 'eof':
            self.player_end.emit()            
            

    def player_end_slot(self):
        self.slider.setValue(0)
        self.input_path=None        
        if self.current_media:
            self.play_path(self.current_media,tv=True)

    def toggle_list_animate(self):
        self.player.toggle_pause()
        if self.list_container.pos().x() == 0:
            self.animation.setStartValue(self.list_container.pos())
            self.animation.setEndValue(self.list_container.pos() - self.list_container.rect().topRight())
            
            self.animation.start()
        else:
            self.animation.setStartValue(self.list_container.pos())
            self.animation.setEndValue(self.list_container.pos() + self.list_container.rect().topRight())
            
            self.animation.start()
        self.player.toggle_pause()
    
    
    def paste_from_clipboard(self):
        # 获取系统剪贴板
        clipboard = QApplication.clipboard()        
        self.treat_media(clipboard.text())    
            
    def screen_shot(self):
        #将self.image 保存为图片文件
        current_time = time.strftime("%Y%m%d%H%M%S")
        self.qimage.save(f"{self.selected_group}-{self.selected_channel}-{current_time}screenshot.png")
        QMessageBox.information(self, "截图", f"{self.selected_group}-{self.selected_channel}-{current_time}.png", QMessageBox.Ok)
    def show_slider(self):        
        self.setCursor(Qt.ArrowCursor)
        self.list_container.setVisible(True)
        if not self.tv:
            self.slider.setVisible(True)            
        self.timer.start(5000)  # 设置计时器为1秒后触发

    def toggle_list(self):
        self.player.toggle_pause()
        if self.list_container.isVisible(): 
            self.list_container.setVisible(False)            
            self.timer.start(5000)
        else:            
            self.list_container.setVisible(True)           
            self.timer.stop()
        self.player.toggle_pause()
    def hide_slider(self):
        if self.player:
            self.player.toggle_pause()        
        self.slider.setVisible(False)        
        self.list_container.setVisible(False)
        if self.player:
            self.player.toggle_pause()        
        self.setCursor(Qt.BlankCursor)
        self.timer.stop()
    

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        
        urls = event.mimeData().urls()
        if urls and urls[0].scheme() == 'file':
            file_path = urls[0].toLocalFile()               
            self.play_path(file_path)
            self.Duration = None           


    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.image_label.isVisible():
                self.swap_fullscreen()
            return
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.swap_fullscreen()                
            elif not self.image_label.isVisible():
                self.stop_check=True                
                for worker in self.workers:
                    worker.stop()
                self.thread_pool.clear()  # 清理线程池中的未完成任务
                self.stop_test()
                if self.player:
                    self.player.toggle_pause()               
            return
        elif event.key() == Qt.Key_Up:
            if self.image_label.isVisible():
                self.switch_program('up')
            return
        elif event.key() == Qt.Key_Down:
            if self.image_label.isVisible():
                self.switch_program('down')
            return
        elif event.key() == Qt.Key_Space:            
            self.player.toggle_pause()
            return
        elif event.key() == Qt.Key_Right:  
            if self.image_label.isVisible():          
                self.player.seek(10, relative=True)
            return
        elif event.key() == Qt.Key_Left:
            if self.image_label.isVisible():
                self.player.seek(-10, relative=True)
            return
        elif event.key() == Qt.Key_P:
            if self.image_label.isVisible():
                self.screen_shot()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.player:
            self.running = False
            self.thread.join()
            self.player.close_player()
        if self.image_label.isVisible():            
         # 保存当前选中的组和节目
            self.save_config()
            self.close_flag=True
            super().closeEvent(event)
        else:
            QMessageBox.warning(self, "提示", "请先ESC停止检测再退出!", QMessageBox.Ok)
            event.ignore() 

    def save_config(self):
        selected_group_index = self.group_list.currentRow()
        selected_program_index = self.program_list.currentRow()        
        # 保存当前样式（假设样式信息存储在某个变量中）
        current_theme = "dark" if self.app.palette().color(QPalette.Window).name() == "#353535" else "light"        
        # 保存 channels 列表
        channels_data = self.main_channels
        
        # 创建一个字典来存储所有需要保存的数据
        data_to_save = {
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "proxy_enable": self.proxy_enable,
            "current_m3u": self.current_m3u,
            "m3u_dict": self.m3u_dict,
            "selected_group_index": selected_group_index,
            "selected_program_index": selected_program_index,
            "current_theme": current_theme,
            "channels": channels_data            
                            }        
        # 将数据保存到文件
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        open_action = QAction("打开直播源/媒体文件", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        # 添加设置代理服务器选项
        settings_menu = menubar.addMenu("设置")
        proxy_settings_action = QAction("设置代理服务器", self)
        proxy_settings_action.triggered.connect(self.show_proxy_settings_dialog)
        settings_menu.addAction(proxy_settings_action)

        self.toggle_toolbar_action = QAction("显示/隐藏录制工具栏", self, checkable=True)
        self.toggle_toolbar_action.setChecked(False)
        self.toggle_toolbar_action.triggered.connect(self.toggle_toolbar)
        file_menu.addAction(self.toggle_toolbar_action)

        theme_menu = menubar.addMenu("主题")
        toggle_theme_action = QAction("切换主题", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        theme_menu.addAction(toggle_theme_action)
        about_menu = menubar.addMenu("关于")
        help_action = QAction("帮助", self)
        help_action.triggered.connect(self.show_help_dialog)
        about_menu.addAction(help_action)
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)        

        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(0)
        self.toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.m3u_name_label = QLabel("当前直播源", self)
        
        self.switch_combo_box = QComboBox(self)        
        self.switch_combo_box.setFixedWidth(int(self.width()*0.1))

        self.reload_button = QPushButton("加载", self)
        self.reload_button.clicked.connect(self.load_m3u)
        
        self.edit_button = QPushButton("编辑", self)
        self.edit_button.clicked.connect(self.edit_m3u)
        
        self.delete_button = QPushButton("删除", self)
        self.delete_button.clicked.connect(self.delete_m3u)
        self.check_button = QPushButton("检测", self)
        self.check_button.clicked.connect(self.check_channels)
        self.record_button = QPushButton("录制", self)
        self.record_button.clicked.connect(self.record_video)
        self.record_button.setEnabled(False)

        if self.m3u_dict: 
            self.switch_combo_box.addItems(self.m3u_dict.keys())
            self.switch_combo_box.setCurrentText(self.current_m3u)
            self.reload_button.setEnabled(True)
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            
        else:
            self.switch_combo_box.addItems(['无']) 
            self.reload_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)         

        self.post_secret=self.get_post_secret()
        if self.post_secret is not None:
             # 创建输入框
            self.search_input = QLineEdit()
            
            self.search_input.setFixedWidth(int(self.width()*0.2))
            self.search_input.setPlaceholderText("输入查询内容")

            # 创建查询按钮
            search_button = QPushButton("在线搜索")
            search_button.clicked.connect(self.on_search_clicked)
            

            # 创建恢复按钮
            self.restore_button = QPushButton("切回直播源")
            self.restore_button.clicked.connect(self.on_restore_clicked)
            self.restore_button.setEnabled(False)
            
            #插入一个spacer
            spacer = QWidget()
            self.toolbar_layout.addWidget(self.m3u_name_label,1)
            self.toolbar_layout.addWidget(self.switch_combo_box,4)      
            self.toolbar_layout.addWidget(self.reload_button,1)  
            self.toolbar_layout.addWidget(self.edit_button,1)
            self.toolbar_layout.addWidget(self.check_button,1)
            self.toolbar_layout.addWidget(self.delete_button,1)        
            self.toolbar_layout.addWidget(self.search_input,4)
            self.toolbar_layout.addWidget(search_button,1)            
            self.toolbar_layout.addWidget(self.restore_button,1)
            self.toolbar_layout.addWidget(spacer,3)
            self.toolbar_layout.addWidget(self.record_button,1)
            toolbar_widget = QWidget()
            toolbar_widget.setLayout(self.toolbar_layout)
            self.toolbar.addWidget(toolbar_widget)
            
            
            # self.toolbar.hide()
    def show_proxy_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("设置代理服务器")

        layout = QVBoxLayout()

        self.use_proxy_checkbox = QCheckBox("使用代理服务器")
        if self.proxy_enable:
            self.use_proxy_checkbox.setChecked(True)
        else:
            self.use_proxy_checkbox.setChecked(False)

        http_label = QLabel("HTTP代理地址:")
        self.http_proxy_edit = QLineEdit()
        self.http_proxy_edit.setText(self.http_proxy)

        https_label = QLabel("HTTPS代理地址:")
        self.https_proxy_edit = QLineEdit()
        self.https_proxy_edit.setText(self.https_proxy)

        layout.addWidget(self.use_proxy_checkbox)
        layout.addWidget(http_label)
        layout.addWidget(self.http_proxy_edit)
        layout.addWidget(https_label)
        layout.addWidget(self.https_proxy_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        layout.addWidget(button_box)
        dialog.setLayout(layout)

        if dialog.exec() == QDialog.Accepted:
            self.set_proxy_settings()

    def set_proxy_settings(self):
        if self.use_proxy_checkbox.isChecked():
            self.proxy_enable=True
            http_proxy = self.http_proxy_edit.text()
            https_proxy = self.https_proxy_edit.text()
            QMessageBox.information(self, "提示", "代理服务器已开启,请重启软件", QMessageBox.Ok)
        else:
            self.proxy_enable=False
            http_proxy = ''
            https_proxy = ''
            QMessageBox.information(self, "提示", "代理服务器已关闭，请重启软件", QMessageBox.Ok)
        os.environ['http_proxy'] = http_proxy
        os.environ['https_proxy'] = https_proxy        
        self.http_proxy = self.http_proxy_edit.text()
        self.https_proxy = self.https_proxy_edit.text()
        self.save_config()

        

    def on_search_clicked(self):
        #恢复按钮可用
        self.restore_button.setEnabled(True)
        search_text = self.search_input.text()
        if search_text:
            if hasattr(self, 'pages'):
                num_pages = len(self.pages)
                if num_pages>0:
                    # actions = self.toolbar.actions()
                    # toolbar_widget_count = len(actions)  # toolbar_widget_count = 10

                    # 计算需要删除的小部件的起始索引
                    start_index = max(0, self.toolbar_layout.count() - num_pages-1)  # start_index = 5

                    # 删除最后五个小部件
                    for i in range(self.toolbar_layout.count() - 2, start_index - 1, -1):
                        widget = self.toolbar_layout.itemAt(i).widget()
                        self.toolbar_layout.removeWidget(widget)
                        widget.deleteLater()
            self.result_dict,self.pages=self.search_channels(search_text)
            self.channels = self.result_dict
            self.load_groups('') 
            for index,url in  self.pages.items():
                # 用列表序号创建分页按钮                    
                self.page_button = QPushButton()
                self.page_button.setText(index)
                self.page_button.clicked.connect(self.on_page_clicked)
                 # 将按钮添加到工具栏,并放在录制按钮之前                
                self.toolbar_layout.insertWidget(self.toolbar_layout.count()-2,self.page_button)

    def on_page_clicked(self):
        pages={}
        page_button = self.sender()
        page_text = page_button.text()
        result = {}
        url = 'https://tonkiang.us/'+self.pages[page_text]

        # 设置User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
            'cookie': 'REFERER=37880374'  
            }
        try:
        # 发送GET请求
            response = requests.get(url, headers=headers)
            # 检查请求是否成功
            if response.status_code == 200:
                # 使用BeautifulSoup解析HTML内容
                soup = BeautifulSoup(response.text, 'html.parser')            
                # # 打印整个HTML文档的内容
                # print(soup.prettify())
                # 查找<a href='?page=1&iptv=电影&l=e270e5ed00'>的链接内容
                links = soup.find_all('a', href=re.compile(r'\?page=\d+&iptv=\S+&l=\S+'))
                #将链接的文本内容转换为字典
                for link in links:
                    pages[link.get_text(strip=True)]=link['href']
                
                names = soup.find_all('div', class_='tip', attrs={'data-title': 'Play with PC'})
                rnames = [name.get_text(strip=True) for name in names]
                # 查找所有class为jsdv的tba元素
                urls = soup.select('tba:not(.imgw)')
                rurls = [url.get_text(strip=True) for url in urls]
                #将names和urls转换为字典
                channels_dic = dict(zip(rnames, rurls))
                # 遍历找到的元素并打印其内容
                result[self.search_input.text()]=channels_dic
                self.channels = result
                
                self.load_groups('')
                #删除所有分页按钮
                num_pages = len(self.pages)
                if num_pages>0:
                    start_index = max(0, self.toolbar_layout.count() - num_pages-1)  # start_index = 5

                    # 删除最后五个小部件
                    for i in range(self.toolbar_layout.count() - 2, start_index - 1, -1):
                        widget = self.toolbar_layout.itemAt(i).widget()
                        self.toolbar_layout.removeWidget(widget)
                        widget.deleteLater()  
                # 添加分页按钮
                self.pages=pages
                for index,page in  self.pages.items():
                    # 用列表序号创建分页按钮                    
                    self.page_button = QPushButton()
                    self.page_button.setText(index)
                    self.page_button.clicked.connect(self.on_page_clicked)
                    self.toolbar_layout.insertWidget(self.toolbar_layout.count()-2,self.page_button)
            
                return  
            else:
                QMessageBox(f"请求失败，状态码: {response.status_code}")
                return {},[] 
        except requests.exceptions.RequestException as e:
            QMessageBox(f"请求失败,检查网络连接")
            return {},[]
    
    def search_channels(self, search_text):
        pages={}
        result = {}
        url = 'https://tonkiang.us/?'

        # 设置User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
            'referer':'https://tonkiang.us/',

        }
        data={
            'seerch': search_text,
            'Submit':  '+',
            'city': self.post_secret
        }
        try:# 发送GET请求
            response = requests.post(url, headers=headers,data=data,timeout=5)
            # 检查请求是否成功
            if response.status_code == 200:
                # 使用BeautifulSoup解析HTML内容
                soup = BeautifulSoup(response.text, 'html.parser')            
                # # 打印整个HTML文档的内容
                # 查找<a href='?page=1&iptv=电影&l=e270e5ed00'>的链接内容
                links = soup.find_all('a', href=re.compile(r'\?page=\d+&iptv=\S+&l=\S+'))
                for link in links:
                    pages[link.get_text(strip=True)]=link['href']
                names = soup.find_all('div', class_='tip', attrs={'data-title': 'Play with PC'})
                rnames = [name.get_text(strip=True) for name in names]
                # 查找所有class为jsdv的tba元素
                urls = soup.select('tba:not(.imgw)')
                rurls = [url.get_text(strip=True) for url in urls]
                #将names和urls转换为字典
                channels_dic = dict(zip(rnames, rurls))
                # 遍历找到的元素并打印其内容
                result[search_text]=channels_dic
                # print(result)
                return result,pages   
            else:
                QMessageBox(f"请求失败，状态码: {response.status_code}")
                return {},[]
        except Exception as e:
            QMessageBox(f"请求失败,检查网络连接")
            return {},[]
            
    def on_restore_clicked(self):
       #如果self.main_group=self.channels，则不恢复
        if self.channels==self.main_channels:
            self.channels=self.result_dict
        else:
            self.channels = self.main_channels        
        self.load_groups('')
    

    def show_help_dialog(self):
        QMessageBox.information(self,"帮助", "支持媒体文件拖拽播放\n\n支持Ctrl+V播放粘贴板地址\n\n支持在线搜索\n\n支持视频录制\n\n支持频道可用测试\n\n鼠标：\n\n单击视频显示频道菜单\n\n双击全屏\n\n鼠标滚轮切换频道\n\n快捷键：\n\n回车：全屏/退出全屏\n\n空格：暂停/播放\n\n左右键：快退/快进10秒\n\nP：截图\n\nESC：退出全屏")
    def show_about_dialog(self):
        QMessageBox.information(self,"关于", "蝈蝈直播TV 1.4\n\nCopyright © 2024-2025 蝈蝈直播TV\n\n作者: Robin Guo\n\n本软件遵循GPLv3协议开源,请遵守开源协议。\n\nhttps://github.com/chgy188/IPTV_player")
    def load_m3u(self):
        if self.player:
            self.player.toggle_pause()
        if self.switch_combo_box.currentText() in self.m3u_dict:
            result=self.load_groups(self.m3u_dict[self.switch_combo_box.currentText()])
            if not result:
                QMessageBox.warning(self, "提示", "加载直播源失败！", QMessageBox.Ok)
            #窗口标题显示当前选择的m3u名称
            self.setWindowTitle(f"蝈蝈直播TV - {self.switch_combo_box.currentText()}")
            self.reload_button.setEnabled(True)
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        self.current_m3u = self.switch_combo_box.currentText()
        self.save_config()
        if self.player:
            self.player.toggle_pause()
        
        
    def edit_m3u(self):
        #打开input对话框，编辑频道Url
        url, ok = QInputDialog.getText(self, '编辑直播源', "修改直播源",QLineEdit.Normal,f"{self.m3u_dict[self.switch_combo_box.currentText()]}")
        if ok and url:
            self.m3u_dict[self.switch_combo_box.currentText()] = url
            self.save_config()
    
    def delete_m3u(self):
        del self.m3u_dict[self.switch_combo_box.currentText()]
        self.switch_combo_box.removeItem(self.switch_combo_box.currentIndex())
        self.save_config()    
    
    def toggle_toolbar(self, state):
        if state:
            self.toolbar.show()
        else:
            self.toolbar.hide()

    def create_layout(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)       
        
        self.group_list = QListWidget()        
        self.group_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.group_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.program_list = CustomQListWidget(self)        
        self.program_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.program_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.program_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.group_list.itemSelectionChanged.connect(self.on_group_select)
        self.program_list.change_program.connect(self.switch_program)        
        self.program_list.itemSelectionChanged.connect(self.on_program_select)
        # self.program_list.setFixedWidth(80)
        self.list_layout = QHBoxLayout()
        self.list_layout.addWidget(self.group_list)
        self.list_layout.addWidget(self.program_list)

        # 创建一个容器QWidget来承载列表布局
        self.list_container = QWidget(self.central_widget)
        self.list_container.setLayout(self.list_layout)
        # self.list_container.setStyleSheet("background: transparent;")
        self.list_container.setStyleSheet("background-color: rgba(0, 0, 0, 64);")
        
        
        
        # 创建动画
        self.animation = QPropertyAnimation(self.list_container, b"pos")
        self.animation.setDuration(10)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        
        video_layout = QVBoxLayout(self.central_widget)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = CustomQLabel(self)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mouseDoubleClickEvent = self.swap_fullscreen
        
        # image = QImage(1024, 768, QImage.Format_ARGB32)                                
        # #彩虹条纹背景填充
        # painter = QPainter(image)
        # # 创建一个 QLinearGradient 对象，定义起始点和结束点
        # gradient = QLinearGradient(0, 0, 1024, 0)  # 从左到右的渐变
        # # 定义颜色列表
        # colors = [
        #     QColor(255, 0, 0),    # Red
        #     QColor(255, 165, 0), # Orange
        #     QColor(255, 255, 0), # Yellow
        #     QColor(0, 128, 0),   # Green
        #     QColor(0, 0, 255),   # Blue
        #     QColor(75, 0, 130),  # Indigo
        #     QColor(238, 130, 238) # Violet
        # ]
        # # 设置渐变颜色
        # for i in range(len(colors)):
        #     position = i / (len(colors) - 1)
        #     gradient.setColorAt(position, colors[i])
        # # image.fill(Qt.white)  # 填充白色背景                               
        # painter.fillRect(image.rect(), gradient)
        # # 结束绘制
        # painter.end()        
        # self.image_label.setPixmap(QPixmap.fromImage(image))       
          
        self.slider = CustomSlider(self)
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)
        self.slider.setTickInterval(10)
        self.slider.setSingleStep(1)        

        video_layout.addWidget(self.image_label)
        video_layout.addWidget(self.slider)        
        
        self.group_list.setVisible(False)
        self.program_list.setVisible(False)
        self.slider.setVisible(False)  
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        # self.progress_bar.setFixedWidth(self.width() - 24)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.text_edit.setVisible(False)
        video_layout.addWidget(self.progress_bar)        
        video_layout.addWidget(self.text_edit)
        
        self.list_container.raise_()
        
        self.adjustSize()

    def resizeEvent(self, event):
        # 调整列表容器高度以适应窗口
        
        # toolbar_height = self.toolBarArea(self.toolBar()).height()
        self.list_container.resize(self.list_container.width(), self.height())
        # self.list_container.move(0, menu_height)  # 避免遮盖菜单栏和工具栏
        super().resizeEvent(event)

    def get_post_secret(self,url= "https://tonkiang.us/ac.php?s=ai&c=ch"):
        # 发送GET请求
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
                'referer':'https://tonkiang.us/?',

            }
        try:
            response = requests.get(url,headers=headers,timeout=5)        
            if response.status_code != 200:
                return None
        except requests.exceptions.ConnectionError as e:
            QMessageBox.critical(self, '错误', f'无法在线搜索,请检查网络连接')
            return None
        return response.text

    def open_file(self): 
        if self.player:
            self.player.toggle_pause()
       
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media File",
            "",
            "Media Files (*.m3u *.mp4 *.avi *.mkv *.mov *.flv *.wmv *.mp3 *.wav *.ogg *.flac *.rm *.rmvb *.ts *.m4v *.3gp);;All Files (*)"
        )
        self.treat_media(file_path)
        if self.player:
            self.player.toggle_pause()
        self.setFocus() 
        
    def treat_media(self, file_path):    
        if file_path:            
            if file_path.startswith("http"): 
                result=self.is_m3u_list(file_path)             
                if  result:# self.setWindowTitle(f"蝈蝈直播TV -当前直播源: {file_path} -加载中...") 
                    if result=='HLS' or result=='OtherMedia':
                        self.input_path = file_path
                        self.play_path(file_path)
                        self.Duration = None
                        return
                    elif result=='badM3U':  
                        QMessageBox.warning(self, "提示", "加载直播源失败,检查格式！", QMessageBox.Ok)
                        return                                                        
                else:
                    QMessageBox.warning(self, "提示", "检查网络！", QMessageBox.Ok)
                    return
            else:                         
                if not file_path.endswith('.m3u'):
                    self.input_path = file_path
                    self.play_path(file_path)
                    self.Duration = None
                    # self.slider.setfocus()
                    return     
            if self.load_groups(file_path):                    
                text, ok = QInputDialog.getText(self, '提示', '直播源加载成功，起个名字')
                if text and ok:            
                    self.m3u_dict[text] = file_path
                    self.switch_combo_box.addItem(text)
                    self.switch_combo_box.setCurrentText(text) 
                    self.current_m3u = text
                    self.reload_button.setEnabled(True)
                    self.edit_button.setEnabled(True)
                    #修改窗口标题
                    self.setWindowTitle(f"蝈蝈直播TV -当前直播源: {text}")
                    self.save_config()
                    return
            else:
                QMessageBox.warning(self, "提示", "导入失败，请检查文件格式", QMessageBox.Ok)
                return                           
             

    def is_m3u_list(self,url):
        try:
            # 对 URL 进行编码处理
            encoded_url = quote(url, safe=':/?')
            headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0'           
            }
            response = requests.get(encoded_url,headers=headers, timeout=5)
            #如果response.type为视频            
            response.raise_for_status()  # 检查请求是否成功
            if  response.headers.get('Content-Type', '').startswith('video'):
                return 'HLS'
            content = response.text
            if content.startswith("#EXTM3U"):
                #判断是否包括"#EXT-X-STREAM-INF"
                if "#EXT-X-VERSION" in content:
                    return 'HLS'
                elif 'http' in content:
                    return 'M3U'
                else:
                    return 'badM3U'
            else:
                return 'OtherMedia'    

        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return False

    def play_path(self, file_path,tv=False):
        if tv:  
            self.current_media = file_path
            self.slider.setVisible(False) 
            self.tv=True         
        else:
            self.slider.setVisible(True)
            self.tv=False
        
        self.play_program(file_path)
        # self.setFocus()

    def download_url(self, url):
        try:    
            response = requests.get(url,timeout=5)
            if response.status_code == 200:
                with open('temp.m3u', 'wb') as file:
                    file.write(response.content)
                return 'temp.m3u'
            else:
                return None
        except requests.exceptions.Timeout as e:
            QMessageBox.critical(self, '错误', f'请求超时，请检查网络连接')
            return None
        except requests.exceptions.ConnectionError as e:
            QMessageBox.critical(self, '错误', f'失败原因：{e}')
            return None
        
    def load_groups(self, file_path):         
        if file_path:
            if file_path.startswith('http'):
                file_path = self.download_url(file_path)
                if file_path is None:
                    return False
            try:
                new_channels = {}
                with open(file_path, 'r', encoding='utf-8') as file:
                    lines = file.readlines()                    
                    for line in lines:
                        if line.startswith('#EXTINF:'):
                            parts = line.split(',')                         
                            match = re.search(r'group-title="([^"]+)"', line)
                            if match:
                                category = match.group(1)
                            else:
                                category = '默认分组'
                            name = parts[-1].strip()
                            #将category通过;分割，取每个元素作为key
                            for cat in category.split(';'):
                                if cat not in new_channels:
                                    new_channels[cat] = {}
                                new_channels[cat][name] = None
                        elif line.startswith('http'):
                            for cat in category.split(';'):
                            #如果是多频道，则给name增加序号
                                if new_channels[cat][name] is None:
                                    new_channels[cat][name] = line.rstrip()                                
                                    multichannel = 1
                                    samename = name
                                else:
                                    name = f"{samename}-{multichannel}"
                                    new_channels[cat][name]=line.rstrip()
                                    multichannel += 1
                    if len(new_channels)>0:
                        #把self.channels的收藏保存到cang 到new_channels中
                        if "我的收藏" in self.main_channels:
                            new_channels["我的收藏"] = self.main_channels["我的收藏"]
                        self.main_channels = new_channels
                        self.channels = self.main_channels                     
                    else:
                        QMessageBox.critical(self, '错误', '加载直播源失败，请检查文件格式' )
                        return False
            except Exception as e:
                QMessageBox.critical(self, '错误', f'加载直播源失败：{e},请删除或修改后重试')
                return False       
                   
        self.group_list.clear()
        self.program_list.clear()
        cat_list=list(self.channels.keys())
        if "我的收藏" in cat_list:
            cat_list.remove("我的收藏")
            cat_list.insert(0, "我的收藏")
        self.group_list.addItems(cat_list)        
        self.list_container.setFixedWidth(self.adjust_list_widget_width(self.group_list)+self.program_list.width())       
        self.group_list.setCurrentRow(0)
        self.group_list.show()
        return True
   

    def record_video(self):
        if not self.record:
            if self.frame_rate != (0, 0) and self.vid_size != (0, 0):
                out_opts = {
                    'pix_fmt_in': self.pix_fmt,
                    'width_in': self.vid_size[0],
                    'height_in': self.vid_size[1],
                    'frame_rate': self.frame_rate
                }
                current_time = time.strftime("%Y%m%d%H%M%S")
                self.record_file = f"rec{current_time}.mp4"
                self.writer = MediaWriter(self.record_file, [out_opts])
                self.record = True
                self.record_button.setText("停止")
                self.record_button.setStyleSheet("background-color: red")
                
            else:
                QMessageBox.critical(self, "出错", "请等待视频加载完成")
        else:
            self.record_button.setText("录制")
            self.record_button.setStyleSheet("background-color: green")
            self.record = False
            self.writer.close()
            QMessageBox.information(self, "提示", f"录制完成,文件名为: {self.record_file}")
        self.setFocus()

    def adjust_list_widget_width(self, list_widget):
        max_width = 0
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            max_width = max(max_width, list_widget.fontMetrics().horizontalAdvance(item.text()))
           
        contents_margins = list_widget.contentsMargins()
        horizontal_padding = contents_margins.left() + contents_margins.right()+14
        # 添加一些额外的宽度以适应边距和滚动条
        # print(f"max_width: {max_width}-{ horizontal_padding}")
        max_width += horizontal_padding        
        list_widget.setFixedWidth(max_width)
        return max_width   
        
        
     

    def check_channels(self):        
        if not self.channels:
            QMessageBox.critical(self, "错误", "请先加载m3u列表.")
            return
        if self.player:
            self.player.toggle_pause()
        self.selected_program_index = self.program_list.currentRow()
        self.stop_check=False
        self.text_edit.clear()
        self.completed = 0
        #禁用text_edit鼠标点击事件
        self.text_edit.mousePressEvent = lambda event: None
        self.menuBar().setDisabled(True)
        self.menuBar().hide()
        self.toolbar.hide()
        self.group_list.hide()
        self.program_list.hide()
        self.image_label.hide()
        #禁用text_edit鼠标点击事件
        self.text_edit.mousePressEvent = lambda event: None
        self.text_edit.setVisible(True)
       
        self.channels_num = self.count_channel_num(self.channels)
        
        self.progress_bar.setMaximum(self.channels_num)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.checking_channels=self.channels.copy()
        #遍历频道列表，检查每个频道的url是否可访问
        
        QMessageBox.information(self, "提示", "准备开始检查,ESC键停止")
        self.workers.clear()  # 清空之前的线程
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(os.cpu_count() * 2, self.channels_num//20))  # 限制最大线程数
        for catogory, channels in self.checking_channels.items(): 
            channels_to_check = channels.copy()
            for name, url in channels_to_check.items(): 
                if self.stop_check:
                    break
                # 检查线程池的活动线程数
                
                worker = UrlTester(catogory,name, url)
                worker.signals.progress.connect(self.update_progress)
                worker.signals.result.connect(self.update_result)                
                # self.thread_pool.setMaxThreadCount(MAX_THREAD_COUNT)
                self.thread_pool.start(worker)
                self.workers.append(worker)  # 存储工作线程
                # 使用 QTimer 定期检查任务状态
        

    def stop_test(self):
        # 停止所有工作线程
        
        QMessageBox.information(self, "提示", f"检查完成,直播源频道总数：原来 {self.channels_num}个，有效频道：{self.count_channel_num(self.checking_channels)}个")
        self.channels=self.checking_channels
        self.progress_bar.setVisible(False)
        self.text_edit.setVisible(False)
        
        self.load_groups('')
        self.menuBar().show()
        self.group_list.setVisible(True)
        self.program_list.setVisible(True)
        self.image_label.setVisible(True)  
        self.menuBar().setDisabled(False)
        
        self.progress_bar.setVisible(False)
        self.text_edit.setVisible(False)
        
        self.load_groups('')
        self.menuBar().show()
        self.toolbar.show()
        self.group_list.setVisible(True)
        self.program_list.setCurrentRow(self.selected_program_index)
        self.program_list.setVisible(True)
        self.image_label.setVisible(True)  
        self.menuBar().setDisabled(False)
        self.setFocus()   

    def update_progress(self,cat,name):
        self.mutex.lock()
        self.completed += 1
        self.progress_bar.setValue(self.completed)
        self.mutex.unlock()
        
        
        #判断所有频道检查完成或线程池是否为空，则停止检查
        # print(f"{cat},{name},{self.completed}")
        # 打印当前活动的线程数量
        # print(f"当前活动的线程数量: {self.thread_pool.activeThreadCount()}")
        if self.completed == self.channels_num:
            self.stop_test()
        
            

    def update_result(self, catogory,name, url, status):
        result_text = f"{self.completed}/{self.channels_num}-{catogory}{name} -> {'可用' if status else '不可用,删除'}\n"
        self.text_edit.append(result_text)
        if  not status:            
             del self.channels[catogory][name]
  # 追加结果显示
    def count_channel_num(self,channels):
        count = 0
        # for value in channels.values():
        for key, value in channels.items():
            if isinstance(value, dict):
                # 如果值是字典，递归调用函数
                # count += self.count_channel_num(value)
                sub_count = self.count_channel_num(value)
                count += sub_count
                # print(f"Group: {key}, Sub Count: {sub_count}, Total Count: {count}")
            else:
                # 如果值不是字典，计数加1
                count += 1
                # print(f"Channel: {key}, Count: {count}")
        return count

    def play_program(self, program_url, pos=0):
        
        ff_opts = {
            'analyzeduration': 10000000,
            'probesize': 10000000,
            'infbuf': True,
            'framedrop': True,           
            'sync': 'video',
            'out_fmt': 'yuv420p',
            'color_range': 'pc'
        }
        with self.lock:           
            self.player = MediaPlayer(program_url, thread_lib='python',loglevel='quiet', ff_opts=ff_opts,callback=self.player_callback) 
            self.image_label.setText(f"准备播放:{self.selected_channel}\n\r地址:{program_url}") 
            if not self.running:
                self.record_button.setEnabled(True)
                self.running = True                
                self.thread = threading.Thread(target=self.run)
                self.thread.start()

   

    def run(self):
        start_status = self.record
        while self.running:
            with self.lock:
                if self.player:
                    try:                    
                        # size = self.image_label.size()                
                        frame, val = self.player.get_frame()
                                               
                        if frame is None:                         
                            
                        
                        # elif frame is None:                                             
                        #     pixmap = self.image_label.pixmap()
                        #     if pixmap:                             
                        #         image = pixmap.toImage()
                        #     # 使用QPainter在图片上绘制文字
                        #         if image:
                        #             painter = QPainter(image)
                        #             painter.setRenderHint(QPainter.Antialiasing) 
                        #             painter.setPen(QColor(255, 255, 255))  
                        #             painter.setFont(QFont("Arial", 30))  # 设置字体和大小
                        #             text = "加载中..."
                        #             text_width = painter.fontMetrics().horizontalAdvance(text)
                        #             text_height = painter.fontMetrics().height()
                        #             padding = 10  # 文字与边缘的间距
                        #             x = image.width() - text_width - padding  # 右对齐
                        #             y = text_height + padding  # 上对齐
                        #             background_color = QColor(0, 0, 0, 150)  # 黄色背景，透明度150
                        #             painter.fillRect(x, y - text_height, text_width, y, background_color)
                        #             painter.drawText(x, y, text)  # 在图片中心绘制文字
                        #             painter.end()
                        #             pixmap = QPixmap.fromImage(image) 
                        #             scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)                           
                        #             self.image_label.setPixmap(scaled_pixmap)
                            # self.image_label.setText("加载中...")
                            time.sleep(0.01)
                        else:
                            # print(frame,val)
                            metadata = self.player.get_metadata()
                            if self.Duration is None:
                                self.Duration = metadata["duration"]
                            if metadata["frame_rate"] != (0, 0):
                                self.frame_rate = metadata["frame_rate"]
                                self.vid_size = metadata["src_vid_size"]
                            image, t = frame                            
                            self.pix_fmt = image.get_pixel_format()
                            if self.record and self.writer:
                                if not start_status and self.record:
                                    begin = t
                                    self.writer.write_frame(img=image, pts=0, stream=0)
                                    start_status = True
                                else:
                                    t = t - begin
                                    self.writer.write_frame(img=image, pts=t, stream=0)
                            if self.Duration and self.Duration > 0 and not math.isnan(t):
                                self.slider.setValue(int(t / self.Duration * 1000))
                            w, h = image.get_size()                           
                            sws = SWScale(w, h, image.get_pixel_format(), ofmt='rgb24')
                            rgb_image = sws.scale(image)                            
                            img_data = rgb_image.to_bytearray()[0]
                            if w> 0 and h > 0:
                                self.qimage = QImage(img_data, w, h, QImage.Format_RGB888)
                            self.player_frame.emit(self.qimage)
                            # pixmap = QPixmap.fromImage(self.qimage)
                            # caled_pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            # self.image_label.setPixmap(caled_pixmap)
                            time.sleep(val)
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"播放失败: {e}") 
    
    def update_image_label(self, qimage):        
        if not qimage.isNull():
            # painter = QPainter(qimage)
            # painter.setRenderHint(QPainter.Antialiasing) 
            # painter.setPen(QColor(255, 255, 255))  
            # painter.setFont(QFont("Arial", 30))  # 设置字体和大小
            # text = self.selected_channel
            # text_width = painter.fontMetrics().horizontalAdvance(text)
            # text_height = painter.fontMetrics().height()
            # padding = 6  # 文字与边缘的间距
            # x = qimage.width() - text_width - padding  # 右对齐
            # y = text_height + padding  # 上对齐
            # background_color = QColor(0, 0, 0, 150)  # 黄色背景，透明度150
            # painter.fillRect(x, y - text_height, text_width, y, background_color)
            # painter.drawText(x, y, text)  # 在图片中心绘制文字
            # painter.end()            
            pixmap = QPixmap.fromImage(qimage)
            caled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(caled_pixmap)           
    

    def swap_fullscreen(self, event=None):
        self.player.toggle_pause()
        if self.isFullScreen():    
            self.list_container.show()
            self.menuBar().show()
            if not self.toggle_toolbar_action.isChecked():
                self.toolbar.hide()
            else:
                self.toolbar.show()                    
            self.showNormal()
            
        else:
            self.list_container.hide()
            self.menuBar().hide()
            self.toolbar.hide()
            self.showFullScreen()
        self.player.toggle_pause()            

    def on_group_select(self):
        
        items = self.group_list.selectedItems()
        if not items:
            return
        self.selected_group = items[0].text()
        self.program_list.clear()
        self.program_list.addItems(list(self.channels[self.selected_group].keys()))
        self.program_list.show()
        # self.adjust_list_widget_width(self.program_list)
        self.list_container.setFixedWidth(self.adjust_list_widget_width(self.program_list)+self.group_list.width())
        self.image_label.show()
        # self.program_list.setCurrentRow(0)
        self.setFocus()

    def on_program_select(self):
        # 判断是否程序关闭
        if self.close_flag:
            return
        items = self.program_list.selectedItems()
        if not items:
            return
        self.selected_channel= items[0].text()
        if items:
            url = self.channels[self.selected_group][self.selected_channel]
            if url:                
                self.play_path(url,tv=True)
                self.input_path = None
        # self.setFocus()  

    def switch_program(self, str):
        if self.player:
            current_row = self.program_list.currentRow()
            if str == 'up':
                new_row = current_row - 1
                if new_row < 0:
                    new_row = 0
                    return
            else:
                new_row = current_row + 1
                if new_row >= self.program_list.count():                    
                    return
            self.program_list.setCurrentRow(new_row)
            # if self.isFullScreen():
            #     self.program_list.hide()

    

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self.switch_program('up')
        else:
            self.switch_program('down')
        super().wheelEvent(event)

    def toggle_theme(self):
        if self.app.palette().color(QPalette.Window).name() == "#353535":
            self.set_light_theme()
        else:
            self.set_dark_theme()

    def set_light_theme(self):
        app = QApplication.instance()
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }

            QWidget {
                background-color: #f5f5f5;
            }

            QPushButton {
                background-color: #b0bec5; /* Light Blue color */
                color: white;
                border: 1px solid #81c784; /* Light Green color */
                border-radius: 4px;
                padding: 4px 8px;
            }

            QPushButton:hover {
                background-color: #81c784; /* Light Green color */
                border: 1px solid #4caf50; /* Green color */
            }

            QPushButton:pressed {
                background-color: #4caf50; /* Green color */
                border: 1px solid #4caf50; /* Green color */
            }

            QListWidget {
                
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
                color: #333333; /* Dark gray */
                font-size: 24px;
            }

            QListWidget::item {
                padding: 4px;
                border-radius: 4px;
            }

            QListWidget::item:selected {
                background-color: #b0bec5; /* Light Blue color */
                color: white;
                border: 1px solid #81c784; /* Light Green color */
            }

            QListWidget::item:hover {
                background-color: #e0f7fa; /* Light Cyan color */
            }

            QSlider::groove:horizontal {
                border: 1px solid #e0e0e0;
                height: 8px;
                background: #e0e0e0;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #b0bec5; /* Light Blue color */
                border: 1px solid #b0bec5;
                width: 16px;
                margin: -2px 0;
                border-radius: 8px;
            }

            QSlider::handle:horizontal:hover {
                background: #81c784; /* Light Green color */
                border: 1px solid #81c784;
            }

            QSlider::handle:horizontal:pressed {
                background: #4caf50; /* Green color */
                border: 1px solid #4caf50;
            }

            QLabel {
                color: #333333; /* Dark gray */
            }

            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #81c784; /* Light Green color */
                width: 10px;
            }

            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
                color: #333333; /* Dark gray */
            }

            QToolBar {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }

            QMenuBar {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                color: #333333; /* Dark gray */
            }

            QMenuBar::item {
                background-color: transparent;
                color: #333333; /* Dark gray */
                               
            }

            QMenuBar::item:selected {
                background-color: #e0f7fa; /* Light Cyan color */
                color: #333333; /* Dark gray */
            }

            QMenu {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }

            QMenu::item {
                padding: 4px 8px;
                color: #333333; /* Dark gray */
            }

            QMenu::item:selected {
                background-color: #b0bec5; /* Light Blue color */
                color: black;
                border: 1px solid #81c784; /* Light Green color */
            }
        """)
        app.setPalette(app.style().standardPalette())

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        app = QApplication.instance()
        app.setPalette(dark_palette)
        app.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
            }

            QWidget {
                background-color: #353535;
            }

            QPushButton {
                background-color: #b0bec5; /* Light Blue color */
                color: white;
                border: 1px solid #81c784; /* Light Green color */
                border-radius: 4px;
                padding: 4px 8px;
            }

            QPushButton:hover {
                background-color: #81c784; /* Light Green color */
                border: 1px solid #4caf50; /* Green color */
            }

            QPushButton:pressed {
                background-color: #4caf50; /* Green color */
                border: 1px solid #4caf50; /* Green color */
            }

            QListWidget {
                background: rgba(224, 224, 224, 0.8);
                
                border: 1px solid #565656;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff; /* White */
                font-size: 24px;
            }

            QListWidget::item {
                padding: 4px;
                border-radius: 4px;
            }

            QListWidget::item:selected {
                background-color: #565656;
                color: white;
                border: 1px solid #81c784; /* Light Green color */
            }

            QListWidget::item:hover {
                background-color: #565656;
            }

            QSlider::groove:horizontal {
                border: 1px solid #565656;
                height: 8px;
                background: #565656;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #b0bec5; /* Light Blue color */
                border: 1px solid #b0bec5;
                width: 16px;
                margin: -2px 0;
                border-radius: 8px;
            }

            QSlider::handle:horizontal:hover {
                background: #81c784; /* Light Green color */
                border: 1px solid #81c784;
            }

            QSlider::handle:horizontal:pressed {
                background: #4caf50; /* Green color */
                border: 1px solid #4caf50;
            }

            QLabel {
                color: #ffffff; /* White */
            }

            QProgressBar {
                border: 1px solid #565656;
                border-radius: 4px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #81c784; /* Light Green color */
                width: 10px;
            }

            QTextEdit {
                background-color: #444444;
                border: 1px solid #565656;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff; /* White */
            }

            QToolBar {
                background-color: #353535;
                border: 1px solid #565656;
                border-radius: 4px;
            }

            QMenuBar {
                background-color: #353535;
                border: 1px solid #565656;
                border-radius: 4px;
            }

            QMenuBar::item {
                background-color: transparent;
            }

            QMenuBar::item:selected {
                background-color: #565656;
            }

            QMenu {
                background-color: #353535;
                border: 1px solid #565656;
                border-radius: 4px;
            }

            QMenu::item {
                padding: 4px 8px;
            }

            QMenu::item:selected {
                background-color: #565656;
                color: white;
                border: 1px solid #81c784; /* Light Green color */
            }
        """)



if __name__ == "__main__":
    
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("tvgg.ico"))
    
    window = IPTVPlayer()   
    window.app = app

    # 检查是否有命令行参数传递
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        window.treat_media(file_path)
    
    window.show()
    # https://iptv-org.github.io/iptv/index.m3u
    app.exec()