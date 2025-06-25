from pathlib import Path

from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QFileDialog, QHBoxLayout, QWidget, QSlider, QLabel
from loguru import logger

from config.global_setting import global_setting
from theme.ThemeQt6 import ThemedWidget


class VideoPlayer(QObject):
    def __init__(self,parent_frame:QWidget, parent_layout:QVBoxLayout,open_video_btn,start_video_btn,stop_video_btn,plainTextEdit,video_slider,video_slider_text):
        super().__init__()
        self.video_slider:QSlider=video_slider
        self.video_slider_text:QLabel=video_slider_text
        self.parent_frame:QWidget = parent_frame
        self.parent_layout:QVBoxLayout = parent_layout

        # 找到视频操作的三个按钮
        self.open_video_btn: QPushButton =open_video_btn
        self.start_video_btn: QPushButton = start_video_btn
        self.stop_video_btn: QPushButton =stop_video_btn

        self.plainTextEdit = plainTextEdit

        # 记录播放总时长和现在时长
        self.video_all_duration =""
        self.video_now_duration=""
        # 创建视频播放器
        self.media_player = QMediaPlayer()

        # 创建音频输出设备
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # 创建视频显示组件
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)



        # 创建主布局
        self.parent_layout.addWidget(self.video_widget)

        self.init_function()



    def open_file(self):
        # self.stop_video()
        # 打开文件对话框选择视频文件
        self.stop_video_btn.setEnabled(True)
        self.start_video_btn.setEnabled(False)
        logger.debug("打开视频")
        try:
            # 获取当前工作目录
            current_directory = Path.cwd()
            open_path = Path.joinpath(current_directory,
                          global_setting.get_setting("server_config")['Storage']['fold_path'],
                       global_setting.get_setting("server_config")['Storage']['video_path'])
            open_path.mkdir(parents=True, exist_ok=True)
            file_path, _ = QFileDialog.getOpenFileName(self.parent_frame, "打开视频文件", open_path.as_posix(), "视频文件 (*.mp4 *.avi *.mkv)")
            if file_path:
                self.plainTextEdit.setPlainText(file_path)
                # print(file_path)
                self.media_player.setSource(QUrl.fromLocalFile(file_path))
                self.media_player.play()
        except Exception as e:
            logger.error(f"打开视频文件错误：{e}")

    def init_function(self):
        # 单击视频暂停/播放的功能
        self.video_widget.mousePressEvent = self.toggle_play_pause

        self.video_slider.sliderMoved.connect(self.set_video_position)
        # 连接信号
        self.media_player.positionChanged.connect(self.update_video_position)
        self.media_player.durationChanged.connect(self.update_video_duration)

        self.init_btn_function()

        pass

    def toggle_play_pause(self, event):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.stop_video()
        else:
            self.start_video()
    def set_video_position(self,position):
        self.media_player.setPosition(position)
        pass
    def update_video_position(self,position):
        self.video_slider.setValue(position)
        minutes, seconds = divmod(position // 1000, 60)  # 转换为分钟和秒
        self.video_now_duration = f"{minutes:02}:{seconds:02}"
        self.display_duration()
        pass
    def update_video_duration(self,duration):
        #视频加载完会执行一次
        self.video_slider.setRange(0, duration)
        minutes, seconds = divmod(duration // 1000, 60)  # 转换为分钟和秒
        self.video_all_duration=f"{minutes:02}:{seconds:02}"
        pass

    def display_duration(self):
        self.video_slider_text.setText(f"{self.video_now_duration}/{self.video_all_duration}")
    def init_btn_function(self):
        self.start_video_btn.setEnabled(False)
        self.stop_video_btn.setEnabled(False)
        self.open_video_btn.clicked.connect(self.open_file)
        self.start_video_btn.clicked.connect(self.start_video)
        self.stop_video_btn.clicked.connect(self.stop_video)
    def start_video(self):
        self.start_video_btn.setEnabled(False)
        self.stop_video_btn.setEnabled(True)
        self.media_player.play()
        pass

    def stop_video(self):
        self.start_video_btn.setEnabled(True)
        self.stop_video_btn.setEnabled(False)
        self.media_player.pause()
        pass

