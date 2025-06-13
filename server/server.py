import sys
import socket
import threading
import time
import datetime
import os
import traceback

from Cryptodome.Cipher import AES
from loguru import logger

from config.global_setting import global_setting

report_logger = logger.bind(category="report_logger")

class Server(threading.Thread):
    # Default save directory
    # save_dir = None
    #save_dir = r'D:\Images'

    # Debugging flags
    DEBUG_PRINT_PROGRESS = False
    DEBUG_SHOW_FILE_SIZE = False
    DEBUG_IMAGE_LOAD_ERRORS = False
    # IP = socket.gethostbyname(socket.gethostname())
    # IP = '0.0.0.0'
    # PORT = 8000
    # ADDR = (IP, PORT)



    # Encryption settings
    KEY = b'MySuperSecretKey32BytesLongPassw'  # Must be 32 bytes for AES-256

    def __init__(self,save_dir,IP,port):
        super().__init__()
        self.save_dir =save_dir
        self.IP =IP
        self.PORT = port
        self.running = False
        self.server = None
        self.conns = []
        self.addrs = []
        self.conn_nums = 0
        self.init_state = self.client_init()

        pass
    def client_init(self):
        # 初始化client
        logger.info(f" Server is init")
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((self.IP,self.PORT))
            self.server.listen(1024)
            logger.info(f" Server is listening on {self.IP}:{self.PORT}.block size={1024}")
            return True
        except Exception as e:

            logger.error(f"Server listened on {self.IP}:{self.PORT} Error ,reason:{e}|trace stack :{traceback.print_stack()}")
            return False
            pass
        pass
    def run(self) -> None:
        self.running=True
        while (self.running):
            # 如果初始化client失败，则一直尝试初始化
            if not self.init_state:
                self.init_state = self.client_init()
                if not self.init_state:
                    continue
            try:

                self.handle_client()

                pass
            except Exception as e:
                logger.error(f"Error connection:{e}|trace stack:{traceback.print_stack()}")
                self.init_state=False
                pass
            time.sleep(float(global_setting.get_setting("server_config")['Server']['delay']))
        pass
    def join(self):
        self.running=False
        for conn in self.conns:
            if conn is not None:
               conn.close()
        self.addrs=[]
        self.conns=[]
        self.conn_nums=0
        pass
    def stop(self):
        self.running = False
        for conn in self.conns:
            if conn is not None:
                conn.close()
        self.addrs = []
        self.conns = []
        self.conn_nums = 0
        pass
    def handle_client(self):
        """
        Handles a client connection, receives an encrypted image, decrypts it, and saves it to disk.
        Args:
            self.conn: The client socket connection.
            self.addr: The address of the connected client.
            self.save_dir: Optional directory to save the images. If None, uses current directory.
        """
        conn, addr = self.server.accept()
        self.conns.append(conn)
        self.addrs.append(addr)
        self.conn_nums += 1
        logger.info(f" New connection from {addr} connected| Active connections: {self.conn_nums}")
        # 默认保存路径
        if self.save_dir is None:
            self.save_dir = sys.path[0] + '\\saved'
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

        start_time = time.time()

        now = datetime.datetime.now()
        filename_time = now.strftime("%Y-%m-%d_%H-%M-%S")

        try:

            # Receive the nonce (used instead of IV in GCM mode)
            nonce = conn.recv(16)

            # Receive the tag (for authentication)
            tag = conn.recv(16)

            # Receive the UID (32 bytes string)
            uid_bytes = conn.recv(32)
            uid = uid_bytes.rstrip(b'\x00').decode('utf-8')  # Remove null padding and decode

            # Parse UID format: AAAA-BBBBBB-CCCCC
            type_code=""
            try:
                parts = uid.split('-')
                if len(parts) >= 2:
                    aaaa = parts[0]  # e.g., "AAYL"
                    bbbbbb = parts[1]  # e.g., "000021"

                    # Extract TYPE by removing first two characters from AAAA
                    type_code = aaaa[2:] if len(aaaa) >= 2 else aaaa  # e.g., "YL"

                    # Construct new filename: [TYPE]_[BBBBBB]_%Y-%m-%d_%H-%M-%S.png
                    filename = f"{type_code}_{bbbbbb}_{filename_time}.png"
                else:
                    # Fallback to original UID if parsing fails
                    filename = f"{uid}_{filename_time}.png"
            except Exception as e:
                logger.warning(f"Error parsing UID '{uid}': {e}, using fallback naming")
                filename = f"{uid}_{filename_time}.png"

            # Receive the encrypted image size
            image_size_bytes = conn.recv(4)
            image_size = int.from_bytes(image_size_bytes, byteorder='big')
            if self.DEBUG_SHOW_FILE_SIZE:
                logger.debug(f"image_size:{image_size}")

            type_dir = f"{self.save_dir}\\{type_code}_{global_setting.get_setting('server_config')['Server']['fold_suffix']}" # Create subdirectory based on first two characters of UID
            if not os.path.exists(type_dir):
                os.makedirs(type_dir)
            save_dir = type_dir  # Update save_dir to the new subdirectory
            # Set the filepath directly in saved directory
            filepath = f'{save_dir}\\{filename}'

            # Receive the encrypted image data
            encrypted_data = bytearray()
            # 测试存储不完整图片 后面图像处理的时候报错
            if self.DEBUG_IMAGE_LOAD_ERRORS:
                image_size=100000
            while len(encrypted_data) < image_size:
                packet = conn.recv(min(image_size - len(encrypted_data), int(global_setting.get_setting('server_config')['Server']['patch_size'])))
                if not packet:
                    break
                encrypted_data.extend(packet)

                if self.DEBUG_PRINT_PROGRESS:
                    # if len(encrypted_data)/image_size > last_percent / 100:
                    logger.debug(f'{len(encrypted_data)/image_size*100}%')

            #
            # Decrypt and verify the image data
            cipher = AES.new(self.KEY, AES.MODE_GCM, nonce=nonce)
            try:
                image_data = cipher.decrypt_and_verify(encrypted_data, tag)
                report_logger.info(f"{type_code}{bbbbbb}上传图片")
            except ValueError as e:
                logger.error(f" Authentication failed! Data may have been tampered with: {e}|trace stack :{traceback.print_stack()}")
                image_data= bytearray()
                report_logger.error(f"{type_code}{bbbbbb}上传图片已经损坏")
                # if conn is not None:
                #    conn.close()
                # return
            # Save the decrypted image
            end_time = time.time()
            time_elapsed = round(end_time-start_time,1)

            with open(filepath, "wb") as f:
                f.write(image_data)

            logger.info(f' Saved to {filepath} (UID: {uid}). Time elapsed: {time_elapsed}s')
        except Exception as e:
            logger.error(f" Error processing connection: {e}|trace stack :{traceback.print_stack()}")
            if conn is not None:
                conn.close()
        finally:
            if conn is not None:
                conn.close()



