import os
import time
from functools import partial
from unittest import case

from PyQt6.QtCharts import QChart, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QChartView, QHorizontalBarSeries
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QVBoxLayout, QGraphicsSimpleTextItem, QPushButton, QHBoxLayout
from loguru import logger

from config.global_setting import global_setting
from server.image_process import report_writing
from theme.ThemeQt6 import ThemedWidget


class Data_thread(QThread):
    # 线程信号
    update_time_thread_doing = pyqtSignal(list)

    def __init__(self, update_status_main_signal):
        super().__init__()
        # 获取主线程更新界面信号
        self.update_status_main_signal: pyqtSignal = update_status_main_signal

        self.data= []

        self.data_save = report_writing(

            file_path=global_setting.get_setting('server_config')['Storage'][
                                                      'fold_path'] + f"/{global_setting.get_setting('server_config')['Storage']['report_fold_name']}", file_name_preffix=global_setting.get_setting('server_config')['Storage']['report_file_name_preffix'],
            file_name_suffix=global_setting.get_setting('server_config')['Storage']['report_file_name_suffix'])
        pass


    def run(self):
        while True:
            # 等待图像处理线程处理完在运行
            global_setting.get_setting("processing_done").wait()
            logger.info("获取图表数据中")
            # 获取最新report文件读取
            latest_file_report_path = self.data_save.get_latest_file(
                folder_path=global_setting.get_setting('server_config')['Storage'][
                                'fold_path'] + f"/{global_setting.get_setting('server_config')['Storage']['report_fold_name']}")
            self.data_save.file_path=latest_file_report_path
            self.data = self.data_save.csv_read_not_dict()
            self.data_save.csv_close()
            self.update_status_main_signal.emit(self.data)
            global_setting.get_setting("processing_done").clear()  # 清除事件以供下次使用
            time.sleep(float(global_setting.get_setting('server_config')['Image_Process'][
                                                      'delay']))
            # time.sleep(1)
        pass

    pass

# 创建柱状图
class BarChartApp(ThemedWidget):
    data_types=["蜚蠊","蝇类","鼠类"]
    update_data_main_signal_gui_update = pyqtSignal(list)
    def __init__(self,parent: QVBoxLayout = None, object_name: str = ""):
        super().__init__()
        # 图表按钮存放
        self.chart_btns={}
        self.choose_type_index=0
        self.orgin_title_suffix="数量柱状图"
        self.orgin_title=f"{self.data_types[self.choose_type_index]}{self.orgin_title_suffix}"
        # 父布局
        self.parent_layout = parent
        # obejctName
        self.object_name = object_name
        # 图表对象
        self.chart: QChart = None
        # 数据系列对象 可能有多个数据源 所以设置为列表
        self.series:QBarSeries = None
        # x轴
        self.x_axis: QBarCategoryAxis = None
        # y轴
        self.y_axis: QValueAxis = None
        # dataset
        self.fl_set=None
        self.yl_set=None
        # 数据
        self.data = []
        self.fl_data = {}
        self.yl_data = {}
        self.sl_data={}
        # 实例化data
        try:
            self.send_nums_FL = int(global_setting.get_setting("server_config")["Sender_FL"]["device_nums"])
        except Exception as e:
            logger.error(f"server_config配置文件Send_FL-device_nums错误！{e}")
            self.send_nums_FL = 0
        for i in range( self.send_nums_FL):
            self.fl_data[f'FL_{i+1:06}']=0
        try:
            self.send_nums_YL = int(global_setting.get_setting("server_config")["Sender_YL"]["device_nums"])
        except Exception as e:
            logger.error(f"server_config配置文件Send_YL-device_nums错误！{e}")
            self.send_nums_YL = 0
        for i in range(self.send_nums_YL ):
            self.yl_data[f'YL_{i+1:06}']=0

        try:
            self.send_nums_SL = int(global_setting.get_setting("server_config")["Sender_SL"]["device_nums"])
        except Exception as e:
            logger.error(f"server_config配置文件Send_SL-device_nums错误！{e}")
            self.send_nums_SL = 0
        for i in range(self.send_nums_SL):
            self.sl_data[f'SL_{i + 1:06}'] = 0
        self.categories=None
        self.data_thread=None
        self._init_ui()
        self.init_function()

    def _init_ui(self):
        self.chart_view = QChartView()
        self.chart_view.setMouseTracking(True)  # 开启鼠标追踪

        self.chart_view.setFixedSize(300, 300)  # 固定大小

        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)  # 关键设置 抗锯齿
        self.chart_view.setObjectName(f"{self.object_name}")


        self.init_chart_btn()
        # 初始化图表
        self._init_chart()
        pass
    def init_chart_btn(self):
        # 实例化图表按钮
        chart_main_layout = QVBoxLayout()
        chart_main_layout.setObjectName(f"chart_main_layout")

        chart_btn_layout = QHBoxLayout()
        chart_btn_layout.setObjectName("chart_btn_layout")
        i=0
        for  type in self.data_types:

            self.chart_btns[type] = QPushButton(type)
            self.chart_btns[type].setObjectName(f"{type}_btn")
            chart_btn_layout.addWidget(self.chart_btns[type])
            if i==0:
            #     默认按钮
                self.chart_btns[type].setEnabled(False)
            else:
                self.chart_btns[type].setEnabled(True)
            i+=1


        chart_layout = QVBoxLayout()
        chart_layout.setObjectName(f"chart_layout")
        chart_layout.addWidget(self.chart_view)
        chart_main_layout.addLayout(chart_btn_layout)
        chart_main_layout.addLayout(chart_layout)
        self.parent_layout.addLayout(chart_main_layout)
        pass


    def _init_chart(self):
        # 创建图表对象

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.setObjectName(f"{self.object_name}_chart")
        self.chart.setTitle(self.orgin_title)

        self.get_data_start()
        # self._set_data_set()
        # # 设置序列 和图表类型
        # self._set_series()
        #
        # # 将数据放入series中 更新数据
        # self.set_data_to_series()
        # # 设置坐标轴
        # self._set_x_axis()
        # self._set_y_axis()

        # 设置样式
        self.set_style()
        # 添加到视图
        self.chart_view.setChart(self.chart)
    def init_function(self):
        i=0
        for btn_name in self.chart_btns:
            self.chart_btns[btn_name].clicked.connect(partial(self. chart_btn_click, i,btn_name))
            i+=1
        # 实例化按钮功能
        pass
    def chart_btn_click(self,id=0,name=data_types[0]):

        # 更改选择索引
        self.choose_type_index=id
        i=0
        for btn_name,btn in self.chart_btns.items():
            if i==id:
                btn.setEnabled(False)
            else:
                btn.setEnabled(True)
            i+=1
        pass
        # 更新图表
        nums=1

        match self.choose_type_index:
            case 0:
                nums=self.send_nums_FL
            case 1:
                nums=self.send_nums_YL
            case 2:
                nums = self.send_nums_SL
            case _:
                pass
        self.chart_view.setFixedSize(300, 200+50*(nums))  # 固定大小
        self.orgin_title=f"{self.data_types[self.choose_type_index]}{self.orgin_title_suffix}"
        self.update_charts()
    def get_data_start(self):
        # 将更新status信号绑定更新status界面函数
        self.update_data_main_signal_gui_update.connect(self.get_data)
        # 启动子线程
        self.data_thread = Data_thread(update_status_main_signal=self.update_data_main_signal_gui_update)
        logger.info("charts data update thread start")
        self.data_thread.start()

    def get_data(self,data):

        # self.fl_data = {item["设备号"]: item["数量"] for item in self.data if item["设备号"].startswith("FL")}
        # self.yl_data = {item["设备号"]: item["数量"] for item in self.data if item["设备号"].startswith("YL")}
        self.data = data
        self.update_charts()
    def update_charts(self):
        # 更新图表
        title = ""
        for item in self.data:
            if item["设备号"].startswith("FL"):
                self.fl_data[item["设备号"]] = int(item["数量"])
                pass
            elif item["设备号"].startswith("YL"):
                self.yl_data[item["设备号"]] = int(item["数量"])
            else:
                self.sl_data[item["设备号"]] = int(item["数量"])
            title = item['日期'] + "-"+ item['时间']
        self.chart.setTitle(title  + self.orgin_title)
        try:
            self._set_data_set()
            # 设置序列 和图表类型
            self._set_series()

            # 将数据放入series中 更新数据
            self.set_data_to_series()
            # 设置坐标轴
            self._set_x_axis()
            self._set_y_axis()
        except Exception as e:
            logger.error(f"charts报错，原因：{e}")
        pass
    def _set_data_set(self):
        # 创建数据集、


        fl_set_temp =[int(i) for i in list(self.fl_data.values())]
        yl_set_temp =[int(i) for i in list(self.yl_data.values())]
        sl_set_temp = [int(i) for i in list(self.sl_data.values())]
        # 柱状图横向过后，数据标签x轴从上往下是大到小的设备号排列，我们需要逆转一下从小到大排列 相应的数据也要逆转
        fl_set_temp.reverse()
        yl_set_temp.reverse()
        sl_set_temp.reverse()
        self.fl_set = QBarSet("FL")
        self.fl_set.append(fl_set_temp)
        self.yl_set = QBarSet("YL")
        self.yl_set.append(yl_set_temp)
        self.sl_set = QBarSet("SL")
        self.sl_set.append(sl_set_temp)

        # 添加数据
        # print(f"fl_data:{self.fl_data}",f"fl_data_values:{self.fl_data.values()}")
        # print(f"yl_data:{self.yl_data}", f"yl_data_values:{self.yl_data.values()}")
        # print(f"extenal_list_data:{extenal_list_data}")

        pass
    def _set_series(self):
        # 创建柱状系列
        if self.series is None:
            self.series = QHorizontalBarSeries()
            match self.choose_type_index:
                case 0: self.series.append(self.fl_set)
                case 1: self.series.append(self.yl_set)
                case 2: self.series.append(self.sl_set)
                case _: pass
            self.chart.addSeries(self.series)
        else:
            self.series.clear()
            self.series = QHorizontalBarSeries()
            match self.choose_type_index:
                case 0:
                    self.series.append(self.fl_set)
                case 1:
                    self.series.append(self.yl_set)
                case 2:
                    self.series.append(self.sl_set)
                case _:
                    pass
            self.chart.removeAllSeries()
            self.chart.addSeries(self.series)
        # 显示数据标签
        self.series.setLabelsVisible(True)  # 开启数据标签
        # self.series.setLabelsFormat("{value}")  # 数据标签格式
        pass



    def set_data_to_series(self):
        pass

    def _set_x_axis(self):
        # 设置 X 轴
        if self.x_axis is None:
            self.x_axis = QValueAxis()
            self.x_axis.setTitleText("生物数量（个）")
            self.x_axis.setRange(0, max(max([int(i) for i in list(self.fl_data.values())]),
                                        max([int(i) for i in list(self.yl_data.values())]),max([int(i) for i in list(self.sl_data.values())])) + 5)
            self.x_axis.setLabelFormat("%d")
            self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignTop)
            self.series.attachAxis(self.x_axis)
        else:

            self.x_axis.setRange(0, max(max([int(i) for i in list(self.fl_data.values())]),
                                        max([int(i) for i in list(self.yl_data.values())]),max([int(i) for i in list(self.sl_data.values())])) + 5)
            self.x_axis.setLabelFormat("%d")
            self.chart.removeAxis(self.x_axis)
            self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignTop)
            self.series.detachAxis(self.x_axis)
            self.series.attachAxis(self.x_axis)
        pass

    def _set_y_axis(self):
        # 设置 Y 轴
        # 短的数据项后边补充0
        # extenal_list_data= self.extend_and_return_new_lists_insert_elem(list(self.fl_data.keys()),"FL",list(self.yl_data.keys()),"YL")
        # keys = []
        # for value in zip(extenal_list_data['FL'], extenal_list_data['YL']):
        #     keys.append(value[0].split("_")[0] + "/" + value[1].split("_")[0]+f"{int(value[1].split('_')[1])}")
        # 柱状图横向过后，数据标签x轴从上往下是大到小的设备号排列，我们需要逆转一下从小到大排列
        keys = []
        choose_data_keys=[]
        match self.choose_type_index:
            case 0:choose_data_keys=list(self.fl_data.keys())
            case 1:choose_data_keys=list(self.yl_data.keys())
            case 2:choose_data_keys = list(self.sl_data.keys())
            case _:pass
        for value in  choose_data_keys:
            keys.append(value)
        keys.reverse()
        self.categories = keys
        if self.y_axis is None:
            self.y_axis = QBarCategoryAxis()
            self.y_axis.append(self.categories)
            self.y_axis.setTitleText("设备名称")
            self.chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)
            self.series.attachAxis(self.y_axis)
        else:
            self.y_axis.clear()
            self.y_axis.append(self.categories)
            self.chart.removeAxis(self.y_axis)
            self.chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)
            self.series.detachAxis(self.y_axis)
            self.series.attachAxis(self.y_axis)
        pass


    def set_style(self):
        pass



