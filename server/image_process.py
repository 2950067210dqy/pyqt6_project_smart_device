import csv
import os
import random
import shutil
import time
from threading import Thread

from cv2 import imread
from loguru import logger

from config.global_setting import global_setting
from util.time_util import time_util

report_logger = logger.bind(category="report_logger")
class report_writing:
    """
    将处理的坐标写入csv文件
    """

    def __init__(self, file_path,file_name_preffix,file_name_suffix):
        self.csv_file = None
        self.csv_writer = None
        self.encoding = 'gbk'

        self.file_name_preffix = file_name_preffix
        self.file_name_suffix = file_name_suffix
        self.file_direct_path=file_path
        self.file_path = file_path+self.file_name_preffix+time_util.get_format_file_from_time(time.time())+self.file_name_suffix

    def get_latest_file(self, folder_path):
        # 获取文件夹内所有文件的完整路径
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if
                 os.path.isfile(os.path.join(folder_path, f))]

        if not files:  # 如果文件夹为空
            return None

        # 使用 max 函数找到修改时间最新的文件
        latest_file = max(files, key=os.path.getmtime)
        return latest_file
    def csv_create(self):
        if not os.path.exists(self.file_direct_path):
            os.makedirs(self.file_direct_path)
        with open(self.file_path, mode='w', newline='', encoding=self.encoding) as file:
            self.csv_file = file
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(["日期", "时间", "设备号", "数量"])

    # 更新或添加数据
    def update_data(self,date,time,equipment_number,nums):
        # 读取现有数据
        current_data = self.csv_read()


        # 如果设备号已存在，更新数据，否则添加
        current_data[equipment_number] = {
            "日期": date,
            "时间": time,
            "设备号": equipment_number,
            "数量": nums,
        }

        # 写回 CSV
        self.csv_write_multiple( current_data)
    # 定义一个函数来读取现有的 CSV 数据
    def csv_read(self):
        data = {}
        """
        data数据结构
        {
        '001': {'日期': '2025-06-24', '时间': '10:00', '设备号': '001', '数量': '10'},
        '002': {'日期': '2025-06-24', '时间': '10:20', '设备号': '002', '数量': '15'}
        }
        """
        try:
            with open(self.file_path, mode='r', encoding=self.encoding) as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # 使用设备号作为唯一标识
                    if "设备号" in row.keys():
                        data[row['设备号']] = row
        except FileNotFoundError:
            # 如果文件不存在，返回一个空的字典
            pass
        return data

    def csv_read_not_dict(self):

        """
        data数据结构
        [
         {'日期': '2025-06-24', '时间': '10:00', '设备号': '001', '数量': '10'},
         {'日期': '2025-06-24', '时间': '10:20', '设备号': '002', '数量': '15'}
        ]
        """
        data=[]
        try:
            with open(self.file_path, mode='r', encoding=self.encoding) as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data.append(row)
                print(data)
        except FileNotFoundError:
            # 如果文件不存在，返回一个空的字典
            pass
        return data
    def csv_write_multiple(self,data):
        with open(self.file_path, mode='w', encoding=self.encoding, newline='') as file:
            fieldnames = ['日期', '时间', '设备号', '数量']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data.values())
    def csv_write(self, date,time,equipment_number,nums):
        # 先读在写
        with open(self.file_path, mode='a', newline='', encoding=self.encoding) as file:
            self.csv_file = file
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([date, time, equipment_number, nums])

    def csv_close(self):
        if self.csv_file is not None:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
class Img_process(Thread):
    """
    图像识别算法线程
    """

    def __init__(self,types,temp_folder,record_folder, report_fold_name,report_file_name_preffix,report_file_name_suffix):
        """

        :param type:
        :param temp_folder:
        :param record_folder:
        :param report_fold_name: 报告文件夹名称
        :param report_file_name_preffix: 报告文件名称前缀
        :param report_file_name_suffix: 报告文件名称后缀
        """
        super().__init__()

        self.path =global_setting.get_setting('server_config')['Storage']['fold_path']
        # YL FL
        self.types = types
        self.temp_folder = temp_folder
        self.record_folder = record_folder
        for t in self.types:
            if not os.path.exists(self.path+t+"_"+temp_folder):
                os.makedirs(self.path+t+"_"+temp_folder)
            if not os.path.exists(self.path+t+"_"+record_folder):
                os.makedirs(self.path+t+"_"+record_folder)

        self.report_fold_name=report_fold_name
        self.report_file_name_preffix=report_file_name_preffix
        self.report_file_name_suffix=report_file_name_suffix
        self.data_save = report_writing(file_path=self.path+ self.report_fold_name,file_name_preffix=report_file_name_preffix,file_name_suffix=report_file_name_suffix)
        self.running=False

    def get_image_files(self):
        """获取文件夹中的所有图片文件（不递归）"""
        # 常见的图片扩展名列表（可根据需要添加）
        image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.tiff', '.webp', '.svg', '.heic', '.raw'
        }

        # 获取目录中所有文件（不包含子目录）
        all_files = []
        for t in self.types:
            all_files .extend([f for f in os.listdir(self.path+t+"_"+self.temp_folder)
                         if os.path.isfile(os.path.join(self.path+t+"_"+self.temp_folder, f))])

        # 筛选图片文件
        image_files = [f for f in all_files
                       if os.path.splitext(f)[1].lower() in image_extensions]

        return sorted(image_files)  # 返回排序后的文件列表
    def image_process_remains(self):
        # 如果打开软件temp文件夹还有上次上传的图片未处理则直接处理并把数据放到上次的report里
        if self.has_files():
            logger.info("处理上次temp文件夹未处理完的数据")
            self.image_processing()
    # 检查temp目录是否还存在文件
    def has_files(self):
        for t in self.types:
            temp_all_folder = os.path.join(self.path, t + "_" + self.temp_folder)
            if not os.path.exists(temp_all_folder):
                os.makedirs(temp_all_folder)
            # 使用 os.scandir() 遍历目录
            with os.scandir(temp_all_folder) as entries:
                for entry in entries:
                    if entry.is_file():  # 判断是否是文件
                        return True
        return False
    # 运行结束
    def join(self):
        self.running = False

        pass

    def stop(self):
        self.running = False

        # 启动，获取一帧

    def run(self):
        self.running = True
        while (self.running):
                # 处理数据


                # 接收线程与图像处理线程同步
                with global_setting.get_setting("condition"):
                    global_setting.get_setting("condition").wait()
                    if len(global_setting.get_setting("data_buffer")) >= int(
                            global_setting.get_setting("server_config")['Sender_FL']['device_nums'])+int(
                            global_setting.get_setting("server_config")['Sender_YL']['device_nums']):
                        # 如果是大于的说明上一次接收到的数据并不是所有的终端设备发过来的 有缺失
                        if len(global_setting.get_setting("data_buffer")) > int(
                                global_setting.get_setting("server_config")['Sender_YL']['device_nums'])+int(
                            global_setting.get_setting("server_config")['Sender_FL']['device_nums']):
                            report_logger.warning(f"FL或YL有无上传数据")
                            pass
                        # 创建这次的新report文件
                        self.data_save.csv_create()
                        self.image_processing()
                        # 清空数据缓冲区以准备下一轮发送
                        global_setting.set_setting("data_buffer",[])
                        # 给图表更新线程放行
                        global_setting.get_setting("processing_done").set()
                time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay']))

        pass
    def image_processing(self):
        # 1.寻找temp文件夹中的图片
        images = self.get_image_files()
        # 没有文件
        if (len(images) == 0):
            report_logger.warning(f"FL或YL有无上传数据")

            time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay']))
            return
        # 处理并更新报告
        # 获取最新report文件读取
        latest_file_report_path =self.data_save.get_latest_file(
            folder_path=global_setting.get_setting('server_config')['Storage'][
                            'fold_path'] + f"/{global_setting.get_setting('server_config')['Storage']['report_fold_name']}")
        # 没获取到就创建
        if latest_file_report_path is None:
            self.data_save.csv_create()
        else:
            self.data_save.file_path = latest_file_report_path
        for image in images:
            name = image.split('_')[0] + '_' + image.split('_')[1]
            nums = self.image_handle(image)
            date = image.split('_')[2].replace("-", "")
            time_single = image.split('_')[3].split(".")[0].replace("-", ":")
            # 2.更新报告
            self.data_save.update_data(date, time_single, name, nums)
            report_logger.info(f"完成{name}数据分析")
            # 3.归档
            shutil.move(self.path +image.split('_')[0]+"_"+ self.temp_folder + image, self.path +image.split('_')[0]+"_"+self.record_folder)
        self.data_save.csv_close()
    def image_handle(self,image_path):
        """
        图像识别算法
        :return:数量
        """
        try:
            logger.info(f"处理数据{self.path+ image_path.split('_')[0] + '_'+self.temp_folder+image_path}")
            imge = imread(self.path+ image_path.split('_')[0] + '_'+self.temp_folder+image_path)
        except Exception as e:
            report_logger.error(f"{image_path}图片已损坏")
            return 0
        return random.randint(0,30)
    pass