import os
import traceback
from enum import Enum

from loguru import logger


class File_Types(Enum):
    TXT = 'txt'
    CSV = 'csv'
    XLSX = 'xlsx'
    GRAPHY = 'graphy'


class folder_util():
    """
    文件夹工具类
    """
    file_types = ['txt', 'csv']

    def __init__(self):
        pass

    @classmethod
    def create_folder(cls, path):
        """
        创建存储位置文件夹
        :param path 文件夹地址
        :return:
        """
        try:
            # 使用 exist_ok=True 来避免 DirectoryExistsError
            os.makedirs(path, exist_ok=True)
            logger.info(f"目录 '{path}' 创建成功或已存在。")
        except PermissionError:
            logger.error(f"权限错误：无法创建目录 '{path}'。")
        except Exception as e:
            logger.error(f"创建目录时发生错误: {e} |  异常堆栈跟踪：{traceback.print_exc()}")
        pass

    @classmethod
    def create_file_txt(cls, file_path, data):
        """
        创建txt文件
        :param file_path 文件地址
        :param file_type 文件类型
        :param data 数据
        :return:
        """

        try:
            # 以写入模式打开文件，如果文件不存在则创建文件
            with open(file_path, 'a') as file:
                file.write(data + "\n")
                logger.info(f"文件 '{file_path}' 成功创建或写入。")
        except FileExistsError:
            logger.error(f"文件 '{file_path}' 已经存在，无法创建。")
        pass

    @classmethod
    def create_file_csv(cls, file_path, data):
        """
        创建csv文件
        :param file_path 文件地址
        :param file_type 文件类型
        :return:
        """

        pass

    @classmethod
    def is_exist_folder(cls, folder_path):
        """
        判断是否存在文件夹
        :return:True False
        """
        return os.path.exists(folder_path)

    @classmethod
    def is_exist_file(self, file_path):
        """
        判断是否存在文件
        :return:True False
        """
        return os.path.isfile(file_path)
