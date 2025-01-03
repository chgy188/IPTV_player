import sys
from PyQt5.QtWidgets import QSlider,QTextEdit,QVBoxLayout,QProgressBar,QSizePolicy,QApplication, QMainWindow, QListWidget, QHBoxLayout, QWidget, QMenu, QAction, QMessageBox, QLabel, QFileDialog
from PyQt5.QtGui import QImage,QPixmap, QIcon, QKeyEvent,QMouseEvent
from PyQt5.QtCore import Qt, QThread,pyqtSignal,QObject
import csv
import os
import requests
import pickle
from ffpyplayer.player import MediaPlayer
import time
import threading
import math




class Stream(QObject):
    """Redirects console output to text widget."""
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass

class CustomQListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_click_menu)

    def show_right_click_menu(self, position):
        menu = QMenu(self)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.remove_program)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(position))

    def remove_program(self):
        # 获取当前选中的program_index
        selected_item = self.currentItem()
        if selected_item:
            
            name = selected_item.text()
            # 删除program_lists中的元素
            self.takeItem(self.row(selected_item))
            for channel in channels:
                if channel[0] == selected_group and channel[1] == name:
                    channels.remove(channel)
                    break
            with open('channels.pkl', 'wb') as f:
                pickle.dump(channels, f)

    def keyPressEvent(self, event: QKeyEvent):
        
        if event.key() == Qt.Key_Space:
            if window.player :
                window.player.toggle_pause()
                return  # 消费该事件
        elif event.key() == Qt.Key_Left:
            window.player.seek(-10)
            return  # 消费该事件  
        elif event.key() == Qt.Key_Right:
            window.player.seek(10)
            return  # 消费该事件 
            
        super().keyPressEvent(event)  # 调用父类的方法处理其他按键事件

class CustomSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 获取鼠标点击位置的值
            current_value = int(event.pos().x()//(self.width()/1000))

            self.setValue(current_value)
            
            window.player.seek(current_value / 1000.0 *window.Duration,relative=False)
            # 调用父类的方法以确保其他功能正常工作
            super().mousePressEvent(event)
        else:
            # 对其他鼠标按钮调用父类的方法
            super().mousePressEvent(event)

class FullScreenPlayer(QMainWindow):
    change_program = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        
        self.setWindowTitle('Full Screen Player')
        self.showFullScreen()
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        #获取屏幕尺寸，将image_label的大小设置为屏幕尺寸
        screen = QApplication.desktop().screenGeometry()
        screensize = screen.size()       
        self.image_label.resize(screensize.width(), screensize.height())       
        
        self.setCentralWidget(self.image_label)
        self.installEventFilter(self)
    def mouseDoubleClickEvent(self, event):
        global video_window        
        video_window=window.image_label      
        self.close()
        window.show()
    def eventFilter(self, source, event):
        global video_window
        if event.type() == event.KeyPress:
            if event.key() in [Qt.Key_Enter,Qt.Key_Escape,Qt.Key_Return] :                
                video_window=window.image_label                
                self.close()
                window.show()
            elif event.key() == Qt.Key_Up:                
                self.change_program.emit("up")                
                return True
            elif event.key() == Qt.Key_Down:                
                self.change_program.emit("down")
                return True
            elif event.key() == Qt.Key_Space:
                if window.player:
                    window.player.toggle_pause()
                
                return True
        return super().eventFilter(source, event)
    
class IPTVPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV Player")
        screen = QApplication.primaryScreen().availableGeometry()
        screensize = screen.size()
        self.setFixedSize(int(screensize.width() * 0.68), int(screensize.height() * 0.68))
        # self.move((screensize.width() - self.width()) // 2, (screensize.height() - self.height()) // 2)
        print(f"width:{self.width()},height:{self.height()}")
        
        self.thread = None
        self.stop_event = threading.Event()
        self.Duration = None
        self.create_menu()
        self.create_layout()
        
        self.player = None
        self.full_screen_player = None
        self.current_media = None
        self.position =0
        if len(channels) > 0:
            self.load_groups('')
        self.installEventFilter(self)

        
        # 启用拖拽功能
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].scheme() == 'file':
            file_path = urls[0].toLocalFile()
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == '.m3u':
                self.load_groups(file_path)
            else:
                # self.stop_playback()
                self.current_media = file_path
                self.play_program(self.current_media)
                
    
    def onUpdateText(self, text):
        """Write console output to text edit."""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
        
    def keyPressEvent(self, event:QKeyEvent):
        # 检查事件类型是否为按键按下
        
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # 调用 swap_fullscreen 函数
            self.swap_fullscreen()
            return
        
        # 调用基类的 eventFilter 方法
        super().keyPressEvent(event) 
    def closeEvent(self, event):
        self.stop_playback() 
        self.current_media=None      
        event.accept()
    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Media File", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        check_action = QAction("Check IPTV", self)
        check_action.triggered.connect(self.check_channels)
        file_menu.addAction(check_action)

    def create_layout(self):
        global video_window
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
                
        main_content_layout = QHBoxLayout()
        
        self.group_list = QListWidget()
        self.group_list.setFixedWidth(80)

        self.program_list = CustomQListWidget()
        self.program_list.setFixedWidth(80)

        video_layout = QVBoxLayout()
        

        self.image_label = QLabel(self)
        # self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.messagebox = QMessageBox
        self.progress_bar = QProgressBar(self)        
        self.progress_bar.setVisible(False)
       

        # 添加进度条控件
        self.slider = CustomSlider(self)
        self.slider.setOrientation(Qt.Horizontal) 
        self.slider.setMinimum(0)
        self.slider.setMaximum(1000)  # 设置最大值为1000，可以根据需要调整
        self.slider.setTickInterval(10)
        self.slider.setSingleStep(1)
        # 将slider设置为透明
        self.slider.setStyleSheet("QSlider { background: transparent; }")
        video_layout.addWidget(self.image_label)
        video_layout.addWidget(self.slider)        
        #将slider放在image_label上面
        self.slider.raise_()

        main_content_layout.addWidget(self.group_list)
        main_content_layout.addWidget(self.program_list)        
        main_content_layout.addLayout(video_layout)
        self.video_size = [(self.width() - self.group_list.width() - self.program_list.width()-60), self.height()-40] 
        self.group_list.setVisible(False)
        self.program_list.setVisible(False)
        self.slider.setVisible(False)   
        # 将进度条添加到主布局的顶部
        main_layout.addLayout(main_content_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.setAlignment(self.progress_bar, Qt.AlignCenter) 
         
        
        # self.video_size = [(self.width() - self.group_list.width() - self.program_list.width()-80), self.height()-40] 
        self.image_label.setFixedSize(self.video_size[0], self.video_size[1]) 
        
        self.slider.setFixedWidth(self.video_size[0]) 
        # self.photo = QPixmap('iptv.jpg')  # 替换为实际图像路径
        # self.image_label.setPixmap(self.photo.scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))# self.image_label.setScaledContents(True)        
        video_window = self.image_label
        # 绑定 on_group_select 方法到 self.group_list 的 itemSelectionChanged 信号
        self.group_list.itemSelectionChanged.connect(self.on_group_select)
        self.program_list.itemSelectionChanged.connect(self.on_program_select)
        # 绑定 itemDoubleClicked 信号到 play_fullscreen 方法
        self.image_label.mouseDoubleClickEvent =self.swap_fullscreen
        # 添加 QTextEdit 控件
        self.text_edit = QTextEdit(self)
        
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        self.text_edit.setVisible(False)
        main_layout.addWidget(self.text_edit)

    
    
    def show_right_click_menu(self, event):
        # 显示右键菜单
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.remove_program)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Media File", 
            "", 
            "Media Files (*.m3u *.mp4 *.avi *.mkv *.mov *.flv *.wmv *.mp3 *.wav *.ogg *.flac *.rm *.rmvb *.ts *.m4v *.3gp);;All Files (*)"
        )
        if file_path:
            
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == '.m3u':
                self.load_groups(file_path)
                return
            #如果文件以http开头，则访问该URL，并将返回的内容保存到文件中
            elif file_path.startswith('http'):
                #http://192.168.10.84:35456/tv.php?h=192.168.10.84&p=35455&m=1&t=0
                tempt_file=self.download_url(file_path)
                if  tempt_file is not None:
                    #访问URL并将内容保存到文件中
                    self.load_groups(tempt_file)
                else:
                    print("Failed to download URL")
                    return                   
                   
            else:                
                
                self.play_program(file_path)
                self.program_list.setFocus()
                
              

    def download_url(self, url):
        # 下载URL内容并保存到文件中
        response = requests.get(url)
        if response.status_code == 200:
            with open('temp.m3u', 'wb') as file:
                file.write(response.content)
            return 'temp.m3u'
        else:
            print(f"Failed to download {url}")
            return None
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
             
        self.group_list.setCurrentRow(0)
        self.adjust_list_widget_width(self.group_list)
        self.group_list.show()

        

    def adjust_list_widget_width(self, list_widget):
        max_width = 0
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            max_width = max(max_width, list_widget.fontMetrics().width(item.text()))
        # list_widget.setMinimumWidth(max_width + 20) 
        list_widget.setFixedWidth(max_width + 25)

    def is_url_accessible(self, url):
        timeout = 1
        try:
            response = requests.get(url, timeout=timeout)
            # 如果响应状态码为200，则表示URL是可访问的
            if response.status_code == 200:
                print(f" is accessible")
                return True
        except requests.exceptions.Timeout:
            print(f"--check timeout, deleted")
        except requests.exceptions.RequestException as e:
            # 如果发生异常，则表示URL是不可访问的
            print(f"-check error: {e}, deleted")
        return False

    def check_channels(self):
        
        # 重定向标准输出和标准错误
        sys.stdout = Stream(newText=self.onUpdateText)
        sys.stderr = Stream(newText=self.onUpdateText)
        if not channels:
            print("No channels found. Please load a M3U file first.")
            return
        self.group_list.hide()
        self.program_list.hide()
        self.image_label.hide()
        
        self.text_edit.setVisible(True)
        self.progress_bar.setMaximum(len(channels))  # 设置进度条的最大值
        self.progress_bar.setValue(0)  # 初始化进度条的值
        self.progress_bar.setVisible(True)
        for channel in channels:
            if channel[2] is not None:
                print(f"Checking {channel[0]}-{channel[1]}" , end='')
                if not self.is_url_accessible(channel[2]):
                    #删除不可访问的频道
                    channels.remove(channel)
            self.progress_bar.setValue(self.progress_bar.value() + 1)
            QApplication.processEvents()  # 处理事件，确保进度条更新
        self.progress_bar.setVisible(False)
        self.text_edit.setVisible(False)
        with open('channels.pkl', 'wb') as f:
                pickle.dump(channels, f)
        self.load_groups('')
        self.group_list.setVisible(True)
        self.program_list.setVisible(True)
        self.image_label.setVisible(True)
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
    def play_program(self,program_url,pos=0):
        ff_opts = {
                # 'timeout': 10,  # 增加超时时间
                'analyzeduration': 2000000,  # 增加分析时长
                'probesize': 5000000,  # 增加探测大小                
                # 'refcounted_frames': 1 , # 启用引用计数帧
                'infbuf':True,
                'framedrop':True,
                'stats':True,
                'color_range': 'pc' 
                # 'ss': pos # 设置播放位置
            }
        if self.player:
            self.old_player=self.player
            self.player = MediaPlayer(program_url, thread_lib='python',ff_opts=ff_opts)
            self.old_player.close_player()
        else:
            self.player = MediaPlayer(program_url, thread_lib='python',ff_opts=ff_opts)
        
        if not program_url.startswith('http'):  
                 
            self.slider.setVisible(True)
            self.slider.raise_()
            self.Duration=None    
            
        else:
            self.slider.setVisible(False)
                     
# 设置进度条的最大值
       
        
    def run(self):           
        
        if self.player:     
            
            while not self.stop_event.is_set() and self.player:
                
                size=video_window.size() 
                self.player.set_size(size.width(), size.height()) 
                
                frame, val = self.player.get_frame()
                if self.Duration is None:
                    self.Duration=self.player.get_metadata()["duration"]# self.position = pos  # 初始化播放位置
                if val == 'eof':
                    break
                elif frame is None:
                    time.sleep(0.01)
                    
                else:
                    image, t = frame
                    if  self.Duration and self.Duration>0 and not math.isnan(t) :                        
                        # print(f"Duration:{self.Duration},Position:{t}")                    
                        self.slider.setValue(int(t/self.Duration* 1000)) 
                        
                    img_data = image.to_bytearray()[0]                                   
                    width, height = image.get_size()                    
                    qimage = QImage(img_data, width, height, QImage.Format_RGB888)                      
                    pixmap = QPixmap.fromImage(qimage)                        
                    video_window.setPixmap(pixmap)

                    time.sleep(val)
                    
            self.player.close_player()
        
    def start_playback(self,run):
    # 在单独的线程中运行播放程序
        self.thread = QThread()
        self.worker = Worker(run)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_worker_finished)  # 连接信号到槽函数
        self.thread.start()
    
    def on_worker_finished(self):       
        self.slider.setValue(0)        
        self.stop_playback()
        if self.current_media:
            # video_window.setFixedHeight(self.height())                        
            self.check_or_play_program(self.current_media)
    def swap_fullscreen(self,event=None):
        global video_window
        if self.thread and self.thread.isRunning():
            
            self.hide() 
            
            # 新建一个全屏窗口播放视频
            self.full_screen_player = FullScreenPlayer()        
            self.full_screen_player.change_program.connect(self.switch_program)  
            video_window = self.full_screen_player.image_label            
            self.full_screen_player.show()
                   

    def on_group_select(self):
        global selected_group
        # 获取选中的节目组
        items = self.group_list.selectedItems()
        if not items:
            return
        selected_group = items[0].text()
        # 清空节目列表
        self.program_list.clear()

        # 插入该组下的所有节目
        for channel in channels:
            if channel[0] == selected_group:
                self.program_list.addItem(channel[1])
        
        self.adjust_list_widget_width(self.program_list)
        self.program_list.show()
        self.image_label.show()
        self.program_list.setCurrentRow(0)
        self.program_list.setFocus()

    def on_program_select(self):
        # 获取选中的节目
        
        items = self.program_list.selectedItems()
        if items:
            
            url=self.find_url(items)
            if url:
                
                self.current_media = url
                
                self.check_or_play_program(url)
            
    def find_url(self,items):
        for channel in channels:
            if channel[0] == selected_group and channel[1] == items[0].text():
                return channel[2]
        return None
    
    def check_or_play_program(self,url):
        # if self.is_url_accessible(url):            
        #     # 停止之前的播放线程
        #     # self.stop_playback()
        #     # self.image_label.show()
        #     self.current_media = url
        #     self.play_program(url)
        #     if not (self.thread and self.thread.isRunning()):
        #         self.start_playback(self.run)
            
        # else:
        #     if self.messagebox.question(self, "Attention", "Channel Unavailable,Delete?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
        #         self.program_list.remove_program()
        self.current_media = url
        self.play_program(url)
        if not (self.thread and self.thread.isRunning()):
            self.start_playback(self.run)
            

    def switch_program(self,str):
        if self.full_screen_player and self.full_screen_player.isVisible():
            current_row = self.program_list.currentRow()
            if str=='up':        
                new_row = (current_row - 1) % self.program_list.count()
            else:
                new_row = (current_row + 1) % self.program_list.count()
            self.program_list.setCurrentRow(new_row)
           
        

    def stop_playback(self):
        if self.thread and self.thread.isRunning():
            self.stop_event.set()
            self.thread.quit()
            self.thread.wait()
            self.stop_event.clear()

class Worker(QThread):

    finished = pyqtSignal()
    def __init__(self, function):
        super().__init__()
        self.function = function
    def run(self):
        self.function()
        self.finished.emit() 

if __name__ == "__main__":
    if os.path.exists('channels.pkl'):
        with open('channels.pkl', 'rb') as f:
            channels = pickle.load(f)
    else:
        channels = []
    selected_group = None
    video_window=None
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("tv.ico"))

    app.setStyleSheet("QListWidget::item:selected { background-color: lightblue; }")
    
    window = IPTVPlayer()
    window.show()
    app.exec_()
    # sys.exit(app.exec_())
