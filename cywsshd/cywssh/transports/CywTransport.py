import logging
import os
#import fcntl
import ControlYourWay_v1_p27
#from cStringIO import StringIO
import re
from ..client import *

logger = logging.getLogger('cywsshd')

class CywTransport:
    def __init__(self, server, user, password, network):
        self.__server = server
        self.__user = user
        self.__password = password
        self.__network = network

    def initialize(self):
        r, w = os.pipe()
        self.reader, self.writer = os.fdopen(r, 'r', 0), os.fdopen(w, 'w', 0)

        self.__cyw = ControlYourWay_v1_p27.CywInterface()
        self.__cyw.set_user_name(self.__user)
        self.__cyw.set_network_password(self.__password)
        self.__cyw.set_network_names([self.__network])
        self.__cyw.set_connection_status_callback(self.connection_status_callback)
        self.__cyw.set_data_received_callback(self.data_received_callback)
        self.__cyw.name = 'Cyw Secure Terminal'
        
        logger.info('Connecting to ControlYourWay...')
        self.__cyw.start()                

    def connection_status_callback(self, connected):
        if connected:  # connection was successful
            logger.info('Connection to ControlYourWay successful')
        else:
            logger.error('Unable to connect.')
            self.__cyw = None
        
    def data_received_callback(self, data, data_type, from_who):
        logger.debug(data)
        match = re.match("^session:([^ ]+)", data_type)
        if match is not None:
            session_id = match.group(1)
            
            existing_client = self.__server.client_by_session(session_id)
            
            if existing_client is None:
                logger.info('No clients for incoming message on session-id %s' % session_id)
                new_client = client(self.__server, self, session_id)
                self.__server.add_client(new_client)
                new_client.start()
            else:
                logger.debug('Incoming message on session-id %s' % session_id)
                self.writer.write(data+'\n')

    def write(self, line):
        send_data = ControlYourWay_v1_p27.CreateSendData()
        send_data.data = line
        send_data.data_type = 'data'
        if self.__cyw.connected:
            self.__cyw.send_data(send_data)
        
    def close(self):
        self.reader.close()
        self.writer.close()
