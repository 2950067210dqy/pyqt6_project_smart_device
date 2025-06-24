import time

from PyQt6.QtCharts import QChart, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QChartView
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QVBoxLayout, QGraphicsSimpleTextItem
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
        self.data_save = report_writing(file_path=global_setting.get_setting('server_config')['Storage'][
                                                      'fold_path'] + f"/{global_setting.get_setting('server_config')['Image_Process']['report_file_name']}")
        pass


    def run(self):
        while True:
            logger.info("获取图表数据中")
            self.data = self.data_save.csv_read_not_dict()
            self.data_save.csv_close()
            self.update_status_main_signal.emit(self.data)
            time.sleep(float(global_setting.get_setting('server_config')['Image_Process'][
                                                      'delay'])+1)
            # time.sleep(1)
        pass

    pass

# 创建柱状图
class BarChartApp(ThemedWidget):
    update_data_main_signal_gui_update = pyqtSignal(list)
    def __init__(self,parent: QVBoxLayout = None, object_name: str = ""):
        super().__init__()
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
            logger.error(f"server_config配置文件Send_FL-device_nums错误！{e}")
            self.send_nums_YL = 0
        for i in range(self.send_nums_YL ):
            self.yl_data[f'YL_{i+1:06}']=0

        self.categories=None
        self.data_thread=None
        self._init_ui()

    def _init_ui(self):
        self.chart_view = QChartView()
        self.chart_view.setMouseTracking(True)  # 开启鼠标追踪

        self.chart_view.setFixedSize(1600, 400)  # 固定大小

        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)  # 关键设置 抗锯齿
        self.chart_view.setObjectName(f"{self.object_name}")
        self.parent_layout.addWidget(self.chart_view)
        # 初始化图表
        self._init_chart()
        pass
    def _init_chart(self):
        # 创建图表对象

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.setObjectName(f"{self.object_name}_chart")
        self.chart.setTitle("FL 和 YL 分组数量柱状图")

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
        for item in self.data :
            if item["设备号"].startswith("FL"):
                self.fl_data[item["设备号"]]=int(item["数量"])
                pass
            else:
                self.yl_data[item["设备号"]] =int(item["数量"])
                pass
        pass
        try:
            self._set_data_set()
            # 设置序列 和图表类型
            self._set_series()

            # 将数据放入series中 更新数据
            self.set_data_to_series()
            # 设置坐标轴
            self._set_x_axis()
            self._set_y_axis()

            # 为每个数据点添加一个标签
            for i in range(len(self.yl_set)):
                value = self.yl_set.at(i)
                label_item = QGraphicsSimpleTextItem(str(value))
                label_item.setPos(i, value)  # 设置标签的位置
                # label_item.setDefaultTextColor(Qt.black)  # 设置文字颜色
                label_item.setZValue(1)  # 将标签放在顶层
                self.chart.scene().addItem(label_item)
        except Exception as  e:
            logger.error(f"charts报错，原因：{e}")
        pass
    def _set_data_set(self):
        # 创建数据集、
        self.fl_set = QBarSet("FL")

        self.fl_set.append([int(i) for i in list(self.fl_data.values())])
        self.yl_set = QBarSet("YL")
        self.yl_set.append([int(i) for i in list(self.yl_data.values())])


        # 添加数据
        # print(f"fl_data:{self.fl_data}",f"fl_data_values:{self.fl_data.values()}")
        # print(f"yl_data:{self.yl_data}", f"yl_data_values:{self.yl_data.values()}")


        pass
    def _set_series(self):
        # 创建柱状系列
        if self.series is None:
            self.series = QBarSeries()
            self.series.append(self.fl_set)
            self.series.append(self.yl_set)
            self.chart.addSeries(self.series)
        else:
            self.series.clear()
            self.series = QBarSeries()
            self.series.append(self.fl_set)
            self.series.append(self.yl_set)
            self.chart.removeAllSeries()
            self.chart.addSeries(self.series)
        pass



    def set_data_to_series(self):
        pass

    def _set_x_axis(self):
        # 设置 X 轴
        keys = []
        for value in zip(list(self.fl_data.keys()),list(self.yl_data.keys())):
            keys.append(value[0].split("_")[0]+"/"+value[1])

        self.categories = keys
        if self.x_axis is None:
            self.x_axis = QBarCategoryAxis()
            self.x_axis.append(self.categories)
            self.x_axis.setTitleText("设备名称")
            self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)
            self.series.attachAxis(self.x_axis)
        else:
            self.x_axis.clear()
            self.x_axis.append(self.categories)
            self.chart.removeAxis(self.x_axis)
            self.chart.addAxis(self.x_axis, Qt.AlignmentFlag.AlignBottom)
            self.series.detachAxis(self.x_axis)
            self.series.attachAxis(self.x_axis)
        pass

    def _set_y_axis(self):

        # 设置 Y 轴
        if self.y_axis is None:
            self.y_axis = QValueAxis()
            self.y_axis.setTitleText("数量")
            self.y_axis.setRange(0, max(max([int(i) for i in list(self.fl_data.values())]), max([int(i) for i in list(self.yl_data.values())])) + 5)
            self.y_axis.setLabelFormat("%d")
            self.chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)
            self.series.attachAxis(self.y_axis)
        else:

            self.y_axis.setRange(0, max(max([int(i) for i in list(self.fl_data.values())]), max([int(i) for i in list(self.yl_data.values())])) + 5)
            self.y_axis.setLabelFormat("%d")
            self.chart.removeAxis(self.y_axis)
            self.chart.addAxis(self.y_axis, Qt.AlignmentFlag.AlignLeft)
            self.series.detachAxis(self.y_axis)
            self.series.attachAxis(self.y_axis)
        pass

    def set_style(self):
        pass

