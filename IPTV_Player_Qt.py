import sys
from PyQt5.QtWidgets import QSizePolicy,QApplication, QMainWindow, QListWidget, QHBoxLayout, QWidget, QMenu, QAction, QMessageBox, QLabel, QFileDialog
from PyQt5.QtGui import QImage,QPixmap
from PyQt5.QtCore import Qt, QThread
import csv
import os
import requests
import pickle
from ffpyplayer.player import MediaPlayer
import time
import threading

class CustomQListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_click_menu)

    def show_right_click_menu(self, position):
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.parent().remove_program)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(position))

class FullScreenPlayer(QMainWindow):
    def __init__(self, pixmap,play_program_func,channel_Url,close_func):
        super().__init__()
        self.initUI(pixmap)
        self.play_program_func = play_program_func
        self.channel_Url = channel_Url
        self.close_func = close_func
    def initUI(self, pixmap):
        self.setWindowTitle('Full Screen Player')
        self.showFullScreen()
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        #获取屏幕尺寸，将image_label的大小设置为屏幕尺寸
        screen = QApplication.desktop().screenGeometry()
        screensize = screen.size()
        print(f"screensize: {screensize.width()}, {screensize.height()}")
        self.image_label.resize(screensize.width(), screensize.height())
        self.setCentralWidget(self.image_label)
    def mouseDoubleClickEvent(self, event):
        #关闭play_program_func

        self.close_func()
        window.play_program(window.image_label,self.channel_Url)
        window.show()
        self.close()
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_func()
            window.play_program(window.image_label,self.channel_Url)
            window.show()
            self.close()
        else:
            super().keyPressEvent(event)
    def start_playing(self):
        self.play_program_func(self.image_label,self.channel_Url)

class IPTVPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV Player")
        screen = QApplication.primaryScreen().availableGeometry()
        screensize = screen.size()
        self.resize(int(screensize.width() * 0.8), int(screensize.height() * 0.8))
        self.move((screensize.width() - self.width()) // 2, (screensize.height() - self.height()) // 2)
        self.thread = None
        self.stop_event = threading.Event()
        self.messagebox = QMessageBox
        self.create_menu()
        self.create_layout()
        self.current_channel = None
        self.player = None
        self.full_screen_player = None
        if len(channels) > 0:
            self.load_groups('')

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open M3U File", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

    def create_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        
        self.group_list = QListWidget()
        self.group_list.setFixedWidth(80)
        self.program_list = CustomQListWidget()
        self.program_list.setFixedWidth(80)
        self.image_label = QLabel(self)
       
        main_layout.addWidget(self.group_list)
        main_layout.addWidget(self.program_list)
        main_layout.addWidget(self.image_label)
        
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # print(f"selfWidth: {self.width()}, group: {self.group_list.width()},program: {self.program_list.width()},image: {self.image_label.width()}")
        
        self.video_size = [(self.width() - self.group_list.width() - self.program_list.width()), self.height()] 
        self.image_label.resize(self.video_size[0], self.video_size[1])      
        self.photo = QPixmap('iptv.jpg')  # 替换为实际图像路径
        self.image_label.setPixmap(self.photo.scaled(self.image_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))# self.image_label.setScaledContents(True)        
        
        # 绑定 on_group_select 方法到 self.group_list 的 itemSelectionChanged 信号
        self.group_list.itemSelectionChanged.connect(self.on_group_select)
        self.program_list.itemSelectionChanged.connect(self.on_program_select)
        # 绑定 itemDoubleClicked 信号到 play_fullscreen 方法
        self.image_label.mouseDoubleClickEvent =self.swap_fullscreen
    

    
    def show_right_click_menu(self, event):
        # 显示右键菜单
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.remove_program)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def remove_program(self):
        # 获取当前选中的program_index
        selected_item = self.program_list.currentItem()
        if selected_item:
            group = self.group_list.currentItem().text()
            name = selected_item.text()
            # 删除program_lists中的元素
            self.program_list.takeItem(self.program_list.row(selected_item))
            for channel in channels:
                if channel[0] == group and channel[1] == name:
                    channels.remove(channel)
                    break
            with open('channels.pkl', 'wb') as f:
                pickle.dump(channels, f)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open M3U File", "", "M3U Files (*.m3u)")
        if file_path:
            self.load_groups(file_path)

    def load_groups(self, file_path):
        global channels
        # 清空节目列表
        self.group_list.clear()
        self.program_list.clear()
        # 读取并解析m3u文件
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter='\n')
                channels = []
                for row in reader:
                    for item in row:
                        if item.startswith('#EXTINF:'):
                            parts = item.split(',')
                            if len(parts) == 2:
                                group = parts[0].split('group-title=')[1].replace('"', '')
                                name = parts[1].strip()
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
                    self.group_list.addItem(group)
                    inserted_groups.add(group)    
        # 获取列表框中的元素数量
        # num_items = self.group_list.count()

        # 设置列表框的高度为元素数量加一
        # self.group_list.setMaximumHeight(num_items * 20)
        self.adjust_list_widget_width(self.group_list)
        self.group_list.show()
        

    def adjust_list_widget_width(self, list_widget):
        max_width = 0
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            max_width = max(max_width, list_widget.fontMetrics().width(item.text()))
        # list_widget.setMinimumWidth(max_width + 20) 
        list_widget.setFixedWidth(max_width + 15)

    def is_url_accessible(self, url):
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

    def play_program(self, image,program_url):
        
        self.player = MediaPlayer(program_url)
        # self.image=image# size = self.image_label.size()
        def run(image_label=image):
            # print(f"selfWidth: {self.width()}, group: {self.group_list.width()},program: {self.program_list.width()},image: {self.image_label.width()}")

            # player_size=self.image_label.size()
            player_size=image_label.size()
            while not self.stop_event.is_set() and self.player:
                self.player.set_size(player_size.width(), player_size.height()) 
                frame, val = self.player.get_frame()
                if val == 'eof':
                    break
                elif frame is None:
                    time.sleep(0.01)
                    # print ('not ready')
                else:
                    image, t = frame
                    # print (val, t, img.get_pixel_format(), img.get_buffer_size())    
                    form=image.get_pixel_format()   
                    img_data = bytes(image.to_bytearray()[0])
                    width, height = image.get_size()
                    if form== 'rgb24':
                    # 创建QImage对象
                        qimage = QImage(img_data, width, height, QImage.Format_RGB888)                        
                        # pixmap = QPixmap.fromImage(qimage.scaled(size.width(), size.height(), Qt.KeepAspectRatio))
                        pixmap = QPixmap.fromImage(qimage)
                        image_label.setPixmap(pixmap)
                    else:
                        print('unsupported format')
                        self.player.close_player()
                        break
                    
                    time.sleep(val)
                # time.sleep(0.1)
            self.player.close_player()
        # 在单独的线程中运行播放程序
        self.thread = QThread()
        self.worker = Worker(run)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
    
    def swap_fullscreen(self,event=None):
        if self.thread and self.thread.isRunning():
            self.stop_playback()
            self.hide() 
            # 新建一个全屏窗口播放视频
            self.full_screen_player = FullScreenPlayer(self.photo, self.play_program, self.current_channel,self.stop_playback)        
            self.full_screen_player.start_playing()
            self.full_screen_player.show() 
               
       

    def on_group_select(self):
        global selected_group
        # 获取选中的节目组
        items = self.group_list.selectedItems()
        selected_group = items[0].text()
        # 清空节目列表
        self.program_list.clear()

        # 插入该组下的所有节目
        for channel in channels:
            if channel[0] == selected_group:
                self.program_list.addItem(channel[1])
        # 获取列表框中的元素数量
        # num_items = self.program_list.count()

        # # 设置列表框的高度为元素数量加一
        # # self.program_list.setMaximumHeight(num_items * 20)
        self.adjust_list_widget_width(self.program_list)
        self.program_list.show()
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.show()

    def on_program_select(self):
        # 获取选中的节目
        items = self.program_list.selectedItems()
        selected_name = items[0].text()
        for channel in channels:
            if channel[0] == selected_group and channel[1] == selected_name:
                # print(selected_name)
                self.current_channel = channel[2]
                if self.is_url_accessible(channel[2]):
                    # 停止之前的播放线程
                    self.stop_playback()
                    self.image_label.show()
                    self.play_program(self.image_label,channel[2])
                else:
                    if self.messagebox.question(self, "Attention", "Channel Unavailable,Delete?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                        self.remove_program()
                break

    def stop_playback(self):
        if self.thread and self.thread.isRunning():
            self.stop_event.set()
            self.thread.quit()
            self.thread.wait()
            self.stop_event.clear()

class Worker(QThread):
    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        self.function()

if __name__ == "__main__":
    if os.path.exists('channels.pkl'):
        with open('channels.pkl', 'rb') as f:
            channels = pickle.load(f)
    else:
        channels = []
    selected_group = None
    app = QApplication(sys.argv)
    # app.setWindowIcon(QIcon("tv.ico"))

    app.setStyleSheet("QListWidget::item:selected { background-color: lightblue; }")
    
    window = IPTVPlayer()
    window.show()
    sys.exit(app.exec_())
