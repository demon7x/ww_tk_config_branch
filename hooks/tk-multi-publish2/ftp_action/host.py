# :coding: utf-8

from ftputil import ftputil
from datetime import datetime
import os

class ftpHost(ftputil.FTPHost):
    def __init__(self,ftp_host, ftp_user, ftp_pass):
        ftputil.FTPHost.__init__(self,ftp_host,ftp_user,ftp_pass)

        try:
            # 연결 상태 확인
            self.listdir("/")
            print("westworld ftp server connected!!!")
        except ftputil.ftp_error.FTPOSError:
            print("westworld ftp server connection failed!!!")
            
        self._set_root()
        self._check_log_folder()

    def _check_log_folder(self):
        self.__log_path = self._root + "log"
        if not self.path.exists(self.__log_path):
            self.makedirs(self.__log_path)

    def _ftp_log(self, item):
        root_dir = os.path.expanduser('~')
        log_dir = os.path.join(root_dir, '.log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_name = datetime.today().strftime("%Y%m%d") + '_ftp' + '.log'
        log_file_path = os.path.join(log_dir, file_name)
        with open(log_file_path, 'a') as file:
            for log in item:
                file.write(str(log) + '\n')
        
        self.upload(log_file_path, os.path.join(self.__log_path, file_name), mode='b')
    
    def _set_root(self):
        self._root = self.getcwd()

    def _upload(self, src, dest):
        self.upload(src,dest,mode='b')
        print(src, "===> TO WESTWORLD PUBLISH ===>", dest)


