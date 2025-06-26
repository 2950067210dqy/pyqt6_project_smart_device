import os
import random
import sys
import threading
import time
import traceback
from itertools import chain
from pathlib import Path

import psutil
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication
from loguru import logger


# Author: Qinyou Deng
# Create Time:2025-03-01
# Update Time:2025-04-07
from config.global_setting import global_setting
from config.ini_parser import ini_parser
from index.all_windows import AllWindows
from server.image_process import Img_process
from server.sender import Sender
from server.server import Server
from theme.ThemeManager import ThemeManager




# 终端模拟 模拟16个设备 8个蝇类，8个另一个种类
sender_thread_list = []
# 工控机模拟
server_thread=None
def load_global_setting():
    # 同步信号量
    global_setting.set_setting("condition_FL",threading.Condition())
    global_setting.set_setting("condition_YL",threading.Condition())
    # 模拟接收的数据量
    global_setting.set_setting("data_buffer_FL",[])
    global_setting.set_setting("data_buffer_YL",[])
    # 用于指示图像处理任务的完成状态
    global_setting.set_setting("processing_done",threading.Event())
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
    #如果gui进程退出 则将其他的线程全部终止
    if server_thread is not None and server_thread.is_alive():

        server_thread.stop()
        logger.error("server_thread子线程已退出")
        server_thread.join(timeout=2)

    if len(sender_thread_list) > 0:
        i=1
        for sender_thread in sender_thread_list:
            if sender_thread is not None and sender_thread.is_alive():
                sender_thread.stop()
                logger.error(f"sender_thread{i}子线程已退出")
                sender_thread.join(timeout=2)

            i+=1
    # 等待5秒系统退出
    # step = 5
    # while step >= 0:
    #     step -= 1
    #     time.sleep(1)
    sys.exit(0)



"""
确认子进程没有启动其他子进程，如果有，必须递归管理或用系统命令杀死整个进程树。
用 psutil 库递归杀死进程树
multiprocessing.Process.terminate() 只会终止对应的单个进程，如果该进程启动了其他进程，这些“子进程”不会被自动终止，因而可能会在任务管理器中残留。
"""
def kill_process_tree(pid, including_parent=True):
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for child in children:
        child.terminate()
    gone, alive = psutil.wait_procs(children, timeout=5)
    for p in alive:
        p.kill()
    if including_parent:
        if psutil.pid_exists(pid):
            parent.terminate()
            parent.wait(5)

def find_images(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    # 定义可以被视为图片的文件扩展名
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg')

    # 创建生成器并使用 itertools.chain 合并
    image_files = chain.from_iterable(
        folder.rglob('*' + ext) for ext in image_extensions
    )

    return list(image_files)  # 转换为列表返回


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
    logger.add(
        "./log/report_smart_device/report_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 日志文件转存
        retention="30 days",  # 多长时间之后清理
        enqueue=True,
        format="{time:YYYY.MM.DD HH:mm:ss} {message}",
        filter=lambda record: record["extra"].get("category") == "report_logger"
    )
    logger.info(f"{'-' * 40}gui_start{'-' * 40}")

    # 加载全局配置
    logger.info("loading config start")
    load_global_setting()
    logger.info("loading config finish")

    try:
        port = int(global_setting.get_setting("server_config")["Server"]["port"])
    except Exception as e:
        logger.error(f"server_config配置文件Server-port错误！{e}")
        sys.exit(0)

    # 工控机模拟
    server_thread = Server(save_dir="./data_smart_device/", IP=global_setting.get_setting("server_config")["Server"]["ip"], port=port)
    try:
        logger.info(f"server_thread子线程开始运行")
        server_thread.start()
    except Exception as e:
        logger.error(f"server_thread子线程发生异常：{e}，准备终止该子线程")
        if server_thread.is_alive():
            server_thread.stop()
            server_thread.join(timeout=5)
        pass

    if bool(int(global_setting.get_setting("server_config")["DeBug"]["send_debug"])):
        # 模拟终端发送
        # FL终端
        try:
            send_nums_FL = int(global_setting.get_setting("server_config")["Sender_FL"]["device_nums"])
        except Exception as e:
            logger.error(f"server_config配置文件Send_FL-device_nums错误！{e}")
            sys.exit(0)

        # 终端host ip
        try:
            sender_host = global_setting.get_setting("server_config")["Sender_FL"]["hosts"].split(",")
            if len(sender_host) != send_nums_FL:
                logger.error(f"server_config配置文件Send_FL-device_hosts数量和终端数量send_nums_FL不一致！")
                sys.exit(0)
        except Exception as e:
            logger.error(f"server_config配置文件Send_FL-device_hosts错误！{e}")
            sys.exit(0)
        for i in range(send_nums_FL):
            uid = f"AAFL-{(i + 1):06d}-CAFAF"
            send_full_fold_path =f"{global_setting.get_setting('server_config')['Storage']['fold_path']}{global_setting.get_setting('server_config')['Sender_FL']['fold_path']}"
            images = find_images(send_full_fold_path)
            random_images_path =""
            if len(images)!=0:
                random_images_path=images[random.randint(0,len(images)-1)]
            sender_thread = Sender(type="FL",uid=uid,host=sender_host[i],port=port,img_dir=random_images_path)
            sender_thread_list.append(sender_thread)
            try:
                logger.info(f"sender_thread_FL_{i} |{uid} |子线程开始运行")
                sender_thread.start()
            except Exception as e:
                logger.error(f"sender_thread_FL_{i} |{uid} |子线程发生异常：{e}，准备终止该子线程")
                if server_thread.is_alive():
                    server_thread.stop()
                    server_thread.join(timeout=5)
                pass


        # YL终端
        try:
            send_nums_YL = int(global_setting.get_setting("server_config")["Sender_YL"]["device_nums"])
        except Exception as e:
            logger.error(f"server_config配置文件Send_YL-device_nums错误！{e}")
            sys.exit(0)

        # 终端host ip
        try:
            sender_host = global_setting.get_setting("server_config")["Sender_YL"]["hosts"].split(",")
            if len(sender_host) != send_nums_YL:
                logger.error(f"server_config配置文件Send_YL-device_hosts数量和终端数量send_nums_YL不一致！{e}")
                sys.exit(0)
        except Exception as e:
            logger.error(f"server_config配置文件Send_YL-device_hosts错误！{e}")
            sys.exit(0)
        for i in range(send_nums_YL):
            uid = f"AAYL-{(i + 1):06d}-CAFAF"
            send_full_fold_path = f"{global_setting.get_setting('server_config')['Storage']['fold_path']}{global_setting.get_setting('server_config')['Sender_YL']['fold_path']}"
            images = find_images(send_full_fold_path)
            random_images_path = ""
            if len(images) != 0:
                random_images_path = images[random.randint(0, len(images) - 1)]
            sender_thread = Sender(type="YL",uid=uid, host=sender_host[i], port=port,
                                   img_dir=random_images_path)
            sender_thread_list.append(sender_thread)
            try:
                logger.info(f"sender_thread_YL_{i} |{uid} |子线程开始运行")
                sender_thread.start()
            except Exception as e:
                logger.error(f"sender_thread_YL_{i} |{uid} |子线程发生异常：{e}，准备终止该子线程")
                if server_thread.is_alive():
                    server_thread.stop()
                    server_thread.join(timeout=5)
                pass
    # 图像识别算法线程
    types = ['FL','YL']
    image_process_thread_list = []
    for t in types:
        image_process_thread =Img_process(type=t,temp_folder=f"/{t}_{global_setting.get_setting('server_config')['Server']['fold_suffix']}/",record_folder=f"/{t}_{global_setting.get_setting('server_config')['Image_Process']['fold_suffix']}/",report_file_path=f"/{global_setting.get_setting('server_config')['Image_Process']['report_file_name']}")
        try:
            logger.info(f"image_process_thread |{t} |子线程开始运行")
            image_process_thread.start()
            image_process_thread_list.append(image_process_thread)
        except Exception as e:
            logger.error(f"image_process_thread |{t} |子线程发生异常：{e}，准备终止该子线程")
            if image_process_thread.is_alive():
                image_process_thread.stop()
                image_process_thread.join(timeout=5)
            pass

    # qt程序开始
    try:
        # 启动qt
        logger.info("start Qt")
        app = QApplication(sys.argv)
        # 绑定突出事件
        app.aboutToQuit.connect(quit_qt_application)
        # 主窗口实例化
        try:
            allWindows = AllWindows()
            logger.info("Appliacation start")
            allWindows.show()
            # 系统退出
            sys.exit(app.exec())
        except Exception as e:
            logger.error(f"gui程序实例化失败，原因:{e} |  异常堆栈跟踪：{traceback.print_exc()}")
            # 如果gui线程死亡 则将其他的线程全部终止
            if server_thread.is_alive():
                server_thread.stop()
                server_thread.join()
            for send in sender_thread_list:
                if send.is_alive():
                    send.stop()
                    send.join()
            for image_process in image_process_thread_list:
                if image_process.is_alive():
                    image_process.stop()
                    image_process.join()
            sys.exit(0)
            # 主窗口显示

    except Exception as e:
        logger.error(f"gui程序运行异常，原因：{e} |  异常堆栈跟踪：{traceback.print_exc()}，终止gui进程和comm进程")
