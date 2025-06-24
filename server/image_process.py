import csv
import os
import random
import shutil
import time
from threading import Thread

import cv2
from loguru import logger

from config.global_setting import global_setting
report_logger = logger.bind(category="report_logger")
class report_writing:
    """
    将处理的坐标写入csv文件
    """

    def __init__(self, file_path):
        self.csv_file = None
        self.csv_writer = None

        self.file_path = file_path

    def csv_create(self):

        with open(self.file_path, mode='w', newline='', encoding='utf-8') as file:
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
            with open(self.file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # 使用设备号作为唯一标识
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
            with open(self.file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data.append(row)
                print(data)
        except FileNotFoundError:
            # 如果文件不存在，返回一个空的字典
            pass
        return data
    def csv_write_multiple(self,data):
        with open(self.file_path, mode='w', encoding='utf-8', newline='') as file:
            fieldnames = ['日期', '时间', '设备号', '数量']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data.values())
    def csv_write(self, date,time,equipment_number,nums):
        # 先读在写
        with open(self.file_path, mode='a', newline='', encoding='utf-8') as file:
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
    def __init__(self,type,temp_folder,record_folder,report_file_path):
        super().__init__()

        self.path =global_setting.get_setting('server_config')['Storage']['fold_path']
        # YL FL
        self.type = type
        self.is_first_run=True
        if not os.path.exists(self.path+temp_folder):
            os.makedirs(self.path+temp_folder)
        self.temp_folder=temp_folder
        if not os.path.exists(self.path+record_folder):
            os.makedirs(self.path+record_folder)
        self.record_folder=record_folder
        self.report_file_path=report_file_path
        self.data_save = report_writing(file_path=self.path+report_file_path)

        self.running=False

    def get_image_files(self):
        """获取文件夹中的所有图片文件（不递归）"""
        # 常见的图片扩展名列表（可根据需要添加）
        image_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.tiff', '.webp', '.svg', '.heic', '.raw'
        }

        # 获取目录中所有文件（不包含子目录）
        all_files = [f for f in os.listdir(self.path+self.temp_folder)
                     if os.path.isfile(os.path.join(self.path+self.temp_folder, f))]

        # 筛选图片文件
        image_files = [f for f in all_files
                       if os.path.splitext(f)[1].lower() in image_extensions]

        return sorted(image_files)  # 返回排序后的文件列表
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
            # # 为了保持图像识别在图像获取之后，所以第一次运行先阻塞该线程
            if self.is_first_run:
                time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['block_delay']))
            # 1.寻找temp文件夹中的图片
            images = self.get_image_files()
            # 没有文件
            if (len(images)==0):
                report_logger.warning(f"{self.type}无上传数据")
                if self.is_first_run:
                    time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay'])-float(global_setting.get_setting("server_config")['Image_Process']['block_delay']))
                    self.is_first_run=False
                else:
                    time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay']))
                continue
            # 处理并更新报告
            self.data_save.csv_create()
            for image in images:
                name = image.split('_')[0]+'_'+image.split('_')[1]
                nums = self.image_handle(image)
                date= image.split('_')[2].replace("-","")
                time_single = image.split('_')[3].split(".")[0].replace("-", ":")
                # 2.更新报告
                self.data_save.update_data(date, time_single, name, nums)
                report_logger.info(f"完成{name}数据分析")
                # 3.归档
                shutil.move(self.path+self.temp_folder+image, self.path+self.record_folder)
            self.data_save.csv_close()
            if self.is_first_run:
                time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay']) - float(
                    global_setting.get_setting("server_config")['Image_Process']['block_delay']))
                self.is_first_run = False
            else:
                time.sleep(float(global_setting.get_setting("server_config")['Image_Process']['delay']))

            pass
        pass
    def image_handle(self,image_path):
        """
        图像识别算法
        :return:数量
        """
        try:
            imge = cv2.imread(self.path+self.temp_folder+image_path)
        except Exception as e:
            report_logger.error(f"{image_path}图片已损坏")
            return 0
        return random.randint(0,30)
    pass