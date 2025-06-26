
# Author: Qinyou Deng
import os
import sys
import threading

import psutil
from PyQt6.QtCore import QThreadPool
from loguru import logger


from config.global_setting import global_setting
from config.ini_parser import ini_parser

from server.sender import Sender
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
    global_setting.set_setting("configer", configer)
    # 读取server配置文件
    server_configer = ini_parser_obj.read("./server_config.ini")
    if server_configer is None:
        logger.error(f"./server_config.ini配置文件读取失败")
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





if __name__ == "__main__" and os.path.basename(__file__) == "main_send.py":
    # 移除默认的控制台处理器（默认id是0）
    # logger.remove()
    # 加载日志配置
    logger.add(
        "./log/gui_smart_device/send_{time:YYYY-MM-DD}.log",
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



    try:
        port = int(global_setting.get_setting("server_config")["Server"]["port"])
    except Exception as e:
        logger.error(f"server_config配置文件Server-port错误！{e}")
        sys.exit(0)
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
        sender_thread = Sender(type="FL",uid=uid,host=sender_host[i],port=port,img_dir=f"{global_setting.get_setting('server_config')['Storage']['fold_path']}{global_setting.get_setting('server_config')['Sender_FL']['fold_path']}1803.{655+i%3}.050.png")
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
        sender_thread = Sender(type="YL",uid=uid, host=sender_host[i], port=port,
                               img_dir=f"{global_setting.get_setting('server_config')['Storage']['fold_path']}{global_setting.get_setting('server_config')['Sender_YL']['fold_path']}1803.{655 + i % 3}.050.png")
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

