import socket
import time
import traceback
from threading import Thread

from Cryptodome.Cipher import AES
import datetime

from loguru import logger

from config.global_setting import global_setting


class Sender(Thread):
    # FORMAT = "utf-8"
    #
    # # UID - 字符串格式，最大32字节
    # uid = "AAKK-209111-CAFAF"  # Unique ID for the sender
    #
    # # Connection configs
    # img_dir = 'file.png'
    # host = 'localhost'
    # port = 8000

    # Encryption settings
    KEY = b'MySuperSecretKey32BytesLongPassw'  # Must be 32 bytes for AES-256
    def __init__(self,img_dir,host,port,uid,nick_id):
        self.img_dir=img_dir
        self.host  = host
        self.port = port
        self.uid = uid
        self.running=False
        self.client_socket=None
        self.init_state = False
        self.client_init()
        pass
    def client_init(self):
        """
        socket程序初始化
        :return:
        """
        # Connect to the remote PC
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(30)
            client_socket.connect((self.host, self.port))
            client_socket.settimeout(None)
            logger.info(f"Sender{self.nick_id},{self.uid} init success")
            return True
        except Exception as e:
            logger.error(f"Error send{self.nick_id},{self.uid} connecting to server: {e} | trace stack:{traceback.print_exc()}")
            return False
        pass
    def set_image_dir(self,img_dir):
        self.img_dir=img_dir
        pass
    def read_and_Encrypt_image(self):
        # Read the image
        with open(self.img_dir, 'rb') as f:
            image = f.read()

        # Create cipher with GCM mode
        cipher = AES.new(self.KEY, AES.MODE_GCM)

        # Encrypt the image data
        encrypted_data, tag = cipher.encrypt_and_digest(image)
        return encrypted_data,tag,cipher
        pass
    # 运行结束
    def join(self):
        self.running = False
        if self.client_socket is not None:
            self.client_socket.close()
        pass

    def stop(self):
        self.running = False
        if self.client_socket is not None:
            self.client_socket.close()
        # 启动，获取一帧

    def run(self):
        self.running = True
        while(self.running):
            # 如果初始化client失败，则一直尝试初始化
            if not self.init_state:
                self.init_state = self.client_init()
                if not self.init_state:
                    continue
            try:
                self.send_image()
            except Exception as e:
                logger.error(f"Error sender{self.nick_id},{self.uid} to server: {e} | trace stack:{traceback.print_exc()}")
                self.init_state=False
                pass
            time.sleep(float(global_setting.get_setting("server_config")['Sender']['delay']))
            pass
        pass
    def send_image(self):
        '''
        Sends encrypted image to remote server using AES-GCM

        Args:
            img_dir: Image path
            host: Server IP
            port: Server socket port (default: 8000)
            uid_value: Unique identifier string for the sender (default: global uid)

        Usage:
            `send_image('someimage.png','192.168.1.2','8000')`
        '''

        encrypted_data, tag,cipher=self.read_and_Encrypt_image()
        try:

            # Send the nonce (used instead of IV in GCM mode)
            self.client_socket.sendall(cipher.nonce)

            # Send the tag (for authentication)
            self.client_socket.sendall(tag)

            # Send UID as fixed 32-byte string (padded with null bytes if shorter)
            uid_bytes = self.uid.encode('utf-8')[:32]  # Truncate if too long
            uid_padded = uid_bytes.ljust(32, b'\x00')   # Pad with null bytes to 32 bytes
            self.client_socket.sendall(uid_padded)

            # Send the encrypted image size
            encrypted_size = len(encrypted_data)
            self.client_socket.sendall(encrypted_size.to_bytes(4, byteorder='big'))

            # Send the encrypted image data
            self.client_socket.sendall(encrypted_data)
            logger.info(f" Image sent{self.nick_id},{self.uid} successfully to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Error sender{self.nick_id},{self.uid} image to server: {e} | trace stack:{traceback.print_exc()}")
            self.init_state = False
        finally:
            if self.client_socket is not None:
                self.client_socket.close()


