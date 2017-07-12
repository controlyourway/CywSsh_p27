import socket
from thread import *
from ..client import *
import logging

logger = logging.getLogger('cywsshd')

class TcpTransport:
    __ssocket = None
    
    def __init__(self, server, host, port):
        self.__server = server
        self.__host = host
        self.__port = port

    def initialize(self):
        try:
            self.__ssocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__ssocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.__ssocket.bind((self.__host, self.__port))
            self.__ssocket.listen(10)
        except socket.error as msg:
             print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
             return False
             
        start_new_thread(self.__run, ())
        
    def __run(self):
        while not False:#self.__stop:
            conn, addr = self.__ssocket.accept()
            new_client = client(self.__server, TcpTransport.IO(conn), addr)
            self.__server.add_client(new_client)
            new_client.start()        
            
    def write(self, line):
        try:
            self.__socket.sendall(line)
        except socket.error:
            logger.error(traceback.format_exc())
        
    def close(self):
        try:
            self.__ssocket.shutdown(socket.SHUT_RDWR)
            self.__ssocket.close()
        except socket.error:
            pass

    class IO:
        def __init__(self, csocket):
            self.__csocket = csocket
            self.reader = self.__csocket.makefile('r', 0)
            
        def write(self, line):
            try:
                self.__csocket.sendall(line)
            except socket.error:
                pass
            
        def close(self):
            # try:
            logger.info('Closing client socket...')
            self.__csocket.shutdown(socket.SHUT_RDWR)
            self.__csocket.close()
            logger.info('Closed client socket.')
            # except socket.error:
            #     pass
    
            self.reader.close()