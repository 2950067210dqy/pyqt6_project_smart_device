import os
import time
from pathlib import Path

from loguru import logger

from config.global_setting import global_setting
from PyQt6 import QtCore
from PyQt6.QtCore import QRect, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QMainWindow, QTextBrowser, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout, \
    QTextEdit, QPlainTextEdit

from theme.ThemeQt6 import ThemedWidget
from ui.custom_ui.BarChart import BarChartApp
from ui.custom_ui.VideoPlayer import VideoPlayer
from ui.tab7 import Ui_tab7_frame
class Status_thread(QThread):
    # 线程信号
    update_time_thread_doing = pyqtSignal()

    def __init__(self, update_status_main_signal):
        super().__init__()
        # 获取主线程更新界面信号
        self.update_status_main_signal: pyqtSignal = update_status_main_signal
        pass

    def reverse_lines_efficient(self,input_string):
        """
        更高效的内存管理方案（适用于非常大的字符串）
        :param input_string: 输入的多行字符串
        :return: 逆序后的字符串
        """
        # 寻找最后一个换行符的位置
        last_index = len(input_string)
        output_lines = []

        # 从字符串末尾向前处理
        for i in range(len(input_string) - 1, -2, -1):
            if i < 0 or input_string[i] == '\n':
                # 找到一行内容（当前指针位置+1 到 last_index）
                line = input_string[i + 1:last_index]
                output_lines.append(line)
                last_index = i
        length = len(output_lines)
        if length >int(global_setting.get_setting('configer')['Status']['max_line']):
            return '\n'.join(output_lines[1:int(global_setting.get_setting('configer')['Status']['max_line'])])  # 跳过第一个空元素
        else:
            return '\n'.join(output_lines[1:])  # 跳过第一个空元素

    def read_large_log_file(self,filename, chunk_size=10 * 1024 * 1024):  # 默认 10MB 分块
        """
        分批读取大日志文件（避免内存溢出）
        :param filename: 日志文件路径
        :param chunk_size: 每次读取的字节大小
        :return: 生成器产生日志行
        """
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                buffer = ""
                while True:
                    data = file.read(chunk_size)
                    if not data:
                        # 处理缓冲区中的剩余内容
                        if buffer:
                            yield buffer
                        break

                    # 将新数据添加到缓冲区
                    buffer += data

                    # 处理缓冲区中的所有完整行
                    lines = buffer.splitlines()

                    # 最后一个元素可能是不完整的行，保留在缓冲区中
                    buffer = lines.pop() if lines and not data.endswith('\n') else ""

                    # 返回完整的行
                    for line in lines:
                        yield line

        except UnicodeDecodeError:
            # 尝试不同编码
            yield from self.read_large_log_file(filename, chunk_size)

    def run(self):
        while True:
            # 实时获取当前status
            filename ="./log/report_smart_device/report_"+ time.strftime("%Y-%m-%d", time.localtime())+".log"
            str = ""
            for line in self.read_large_log_file( filename):
                # 将status发送信号到绑定槽函数
                str+=line+"\n"
            str_reverse = self.reverse_lines_efficient(str)
            self.update_status_main_signal.emit(str_reverse)
            time.sleep(1)
            # print(formatted_time)
        pass

    pass



class Tab_7(ThemedWidget):
    update_status_main_signal_gui_update = pyqtSignal(str)
    def __init__(self, parent=None, geometry: QRect = None, title=""):
        super().__init__()
        # 类型 0 是Qframe 1是Qmainwindow
        self.type = 1
        self.video_component=None
        # 实例化ui
        self._init_ui(parent, geometry, title)
        # 实例化自定义ui
        self._init_customize_ui()
        # 实例化功能
        self._init_function()
        # 加载qss样式表
        self._init_style_sheet()
        pass

        # 实例化ui

    def _init_ui(self, parent=None, geometry: QRect = None, title=""):
        # 将ui文件转成py文件后 直接实例化该py文件里的类对象  uic工具转换之后就是这一段代码
        # 有父窗口添加父窗口
        if parent != None and geometry != None:
            self.frame = QWidget(parent=parent) if self.type == 0 else QMainWindow(parent=parent)
            self.frame.setGeometry(geometry)
        else:
            self.frame = QWidget() if self.type == 0 else QMainWindow(parent=parent)
        self.ui = Ui_tab7_frame()
        self.ui.setupUi(self.frame)

        self._retranslateUi()
        pass

    # 实例化自定义ui
    def _init_customize_ui(self):
        self.init_charts()
        self.init_videos()


        pass

    def init_videos(self):
        # 找到video的layout
        video_layout: QVBoxLayout = self.frame.findChild(QVBoxLayout, "video_layout")
        # 找到video_button
        open_video_btn: QPushButton = self.frame.findChild(QPushButton, "open_video_btn")

        start_video_btn: QPushButton =  self.frame.findChild(QPushButton, "start_video_btn")
        stop_video_btn: QPushButton =  self.frame.findChild(QPushButton, "stop_video_btn")
        plainTextEdit:QPlainTextEdit = self.frame.findChild(QPlainTextEdit, "plainTextEdit")
        self.video_component = VideoPlayer(parent_frame=self.frame,parent_layout=video_layout,open_video_btn=open_video_btn,start_video_btn=start_video_btn,stop_video_btn=stop_video_btn,plainTextEdit=plainTextEdit)
        pass

    def init_charts(self):
        # 找到charts的layout
        charts_layout: QVBoxLayout = self.frame.findChild(QVBoxLayout, "charts_layout")
        # 找到 scrollarea
        scrollArea: QScrollArea = self.frame.findChild(QScrollArea, "scrollArea")
        scrollArea.setWidgetResizable(True)
        # 找到 scrollarea_container
        scrollarea_container: QWidget = self.frame.findChild(QWidget, "scrollAreaWidget")

        sub_layout = QVBoxLayout(scrollarea_container)
        sub_layout.setObjectName(f"layout_sub")
        self.charts = BarChartApp(parent=sub_layout, object_name="charts_data")

        scrollarea_container.setLayout(sub_layout)
        pass
    # 实例化功能
    def _init_function(self):
        self.show_status()
        self.btn_functions()
        pass

    def btn_functions(self):
        # 按钮功能
        # 找到btn
        openFL_btn: QPushButton = self.frame.findChild(QPushButton, "openFL_btn")
        openReport_btn: QPushButton = self.frame.findChild(QPushButton, "openReport_btn")
        openSL_btn: QPushButton = self.frame.findChild(QPushButton, "openSL_btn")
        openYL_btn: QPushButton = self.frame.findChild(QPushButton, "openYL_btn")

        openSL_btn.clicked.connect(self.openSL_Folder)
        openFL_btn.clicked.connect(self.openFL_Folder)
        openReport_btn.clicked.connect(self.openReport_Folder)
        openYL_btn.clicked.connect(self.openYL_Folder)
        pass

    def openSL_Folder(self):

        pass

    def openFL_Folder(self):
        # 获取当前工作目录
        current_directory = Path.cwd()
        open_direct = Path.joinpath(current_directory,
                                    global_setting.get_setting("server_config")['Storage']['fold_path'],"FL_"+global_setting.get_setting("server_config")['Image_Process']['fold_suffix'])
        open_direct.mkdir(parents=True, exist_ok=True)
        os.startfile(open_direct)  # 替换为你要打开的文件夹路径
        pass

    def openReport_Folder(self):
        # 获取当前工作目录
        current_directory = Path.cwd()
        open_direct = Path.joinpath(current_directory,
                                    global_setting.get_setting("server_config")['Storage']['fold_path'],
                                     global_setting.get_setting("server_config")['Image_Process']['report_file_name'])
        # open_direct.mkdir(parents=True, exist_ok=True)
        os.startfile(open_direct)  # 替换为你要打开的文件夹路径
        pass

    def openYL_Folder(self):
        # 获取当前工作目录
        current_directory = Path.cwd()
        open_direct = Path.joinpath(current_directory,
                                    global_setting.get_setting("server_config")['Storage']['fold_path'],
                                    "YL_" + global_setting.get_setting("server_config")['Image_Process']['fold_suffix'])
        open_direct.mkdir(parents=True, exist_ok=True)
        os.startfile(open_direct)  # 替换为你要打开的文件夹路径
        pass
    def show_status(self):
        # 将更新status信号绑定更新status界面函数
        self.update_status_main_signal_gui_update.connect(self.update_status_handle)
        # 启动子线程
        self.status_thread = Status_thread(update_status_main_signal=self.update_status_main_signal_gui_update)
        logger.info("status update thread start")
        self.status_thread.start()

    def update_status_handle(self, text=""):
        # 找到状态栏
        status_broswer :QTextBrowser= self.frame.findChild(QTextBrowser, "statusBrowser")
        if status_broswer is None:
            logger.warning("未找到status_broswer")
            return
        status_broswer.setText(text)
        pass
    # 将ui文件转成py文件后 直接实例化该py文件里的类对象  uic工具转换之后就是这一段代码 应该是可以统一将文字改为其他语言
    def _retranslateUi(self, **kwargs):
        _translate = QtCore.QCoreApplication.translate

    # 添加子组件
    def set_child(self, child: QWidget, geometry: QRect, visible: bool = True):
        child.setParent(self.frame)
        child.setGeometry(geometry)
        child.setVisible(visible)
        pass

    # 显示窗口
    def show(self):
        self.frame.show()
        pass





