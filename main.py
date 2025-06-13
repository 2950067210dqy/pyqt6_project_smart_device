import os
import sys
import time
import traceback

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication
from loguru import logger


# Author: Qinyou Deng
# Create Time:2025-03-01
# Update Time:2025-04-07
from config.global_setting import global_setting
from config.ini_parser import ini_parser
from index.all_windows import AllWindows
from server.sender import Sender
from server.server import Server
from theme.ThemeManager import ThemeManager


def load_global_setting():
    # 加载gui配置存储到全局类中
    ini_parser_obj = ini_parser()
    configer = ini_parser_obj.read("./gui_smart_device_configer.ini")
    if configer is None:
        logger.error(f"./gui_smart_device_configer.ini配置文件读取失败")
        quit_qt_application()
    global_setting.set_setting("configer", configer)
    # 读取server配置文件
    server_configer = ini_parser_obj.read("./server_config.ini")
    if server_configer is None:
        logger.error(f"./server_config.ini配置文件读取失败")
        quit_qt_application()
    global_setting.set_setting("server_config", server_configer)
    # 风格默认是dark  light
    global_setting.set_setting("style", configer['theme']['default'])
    # 主题管理
    theme_manager = ThemeManager()
    global_setting.set_setting("theme_manager", theme_manager)
    # qt线程池
    thread_pool = QThreadPool()
    global_setting.set_setting("thread_pool", thread_pool)
    pass


def quit_qt_application():
    """
    退出QT程序
    :return:
    """
    logger.info(f"{'-' * 40}quit Qt application{'-' * 40}")
    #
    # 等待5秒系统退出
    step = 5
    while step >= 0:
        step -= 1
        time.sleep(1)
    sys.exit(0)


def start_qt_application():
    """
    qt程序开始
    :return: 无
    """
    # 启动qt
    logger.info("start Qt")
    app = QApplication(sys.argv)
    # 绑定突出事件
    app.aboutToQuit.connect(quit_qt_application)
    # 主窗口实例化
    try:
        allWindows = AllWindows()
    except Exception as e:
        logger.error(f"gui程序实例化失败，原因:{e} |  异常堆栈跟踪：{traceback.print_exc()}")
        return
        # 主窗口显示
    logger.info("Appliacation start")
    allWindows.show()
    # 系统退出
    sys.exit(app.exec())
    pass





if __name__ == "__main__" and os.path.basename(__file__) == "main.py":
    # 移除默认的控制台处理器（默认id是0）
    # logger.remove()
    # 加载日志配置
    logger.add(
        "./log/gui_smart_device/gui_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 日志文件转存
        retention="30 days",  # 多长时间之后清理
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} |{process.name} | {thread.name} |  {name} : {module}:{line} | {message}"
    )
    logger.info(f"{'-' * 40}gui_start{'-' * 40}")

    # 加载全局配置
    logger.info("loading config start")
    load_global_setting()
    logger.info("loading config finish")

    # 终端模拟 模拟8个设备
    send_nums = 8
    sender_thread = Sender()
    # 工控机模拟
    server_thread=Server()
    # qt程序开始
    try:
        start_qt_application()
    except Exception as e:
        logger.error(f"gui程序运行异常，原因：{e} |  异常堆栈跟踪：{traceback.print_exc()}，终止gui进程和comm进程")
