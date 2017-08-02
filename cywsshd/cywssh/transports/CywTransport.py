import logging
import os
import ControlYourWay_p27
import random
import re
import string
from ..client import *

logger = logging.getLogger('cywsshd')

CYW_DT_DISCOVER_REQUEST = 'DISCOVER-ESH'
CYW_DT_DISCOVER_RESPONSE = 'DISCOVER-RESPONSE-ESH'
CYW_DT_SESSION = 'REQ-SSH:'
CYW_DT_CONNECT = 'CONNECT-SSH'
SESSION_KEY_LENGTH = 20

class CywTransport:
    def __init__(self, server, account_user, account_password, network, secret, device_name):
        self.__server = server
        self.__account_user = account_user
        self.__account_password = account_password
        self.__network = network
        self.__secret = secret
        self.__device_name = device_name;

    def initialize(self):
        self.__cyw = ControlYourWay_p27.CywInterface()
        self.__cyw.set_user_name(self.__account_user)
        self.__cyw.set_network_password(self.__account_password)
        self.__cyw.set_network_names([self.__network])
        self.__cyw.set_connection_status_callback(self.connection_status_callback)
        self.__cyw.set_data_received_callback(self.data_received_callback)
        self.__cyw.name = 'Cyw Secure Terminal'
        
        logger.info('Connecting to ControlYourWay...')
        self.__cyw.start()                

    def connection_status_callback(self, connected):
        if connected:  # connection was successful
            logger.info('Connection to ControlYourWay successful')
            logger.info('Session ID: ' + str(self.__cyw.get_session_id()))
        else:
            logger.error('Unable to connect.')
            self.__cyw = None
        
    def new_session_key(self):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(SESSION_KEY_LENGTH))

    def data_received_callback(self, data, data_type, from_who):
        if data_type == CYW_DT_DISCOVER_REQUEST:
            if data == self.__secret:
                # respond with discovery result
                # 1. generate 20-byte unique key
                self.__last_session_key = self.new_session_key()
                
                # 3. send response back to network
                send_data = ControlYourWay_p27.CreateSendData()
                send_data.data = self.__last_session_key + ',' + self.__device_name
                send_data.data_type = CYW_DT_DISCOVER_RESPONSE
                if self.__cyw.connected:
                    self.__cyw.send_data(send_data)
            else:
                logger.info('Invalid secret key received')
        elif data_type == CYW_DT_CONNECT:
            if data == self.__last_session_key:
                # 2. start a client instance for the new session-id
                # logger.warn('No clients for incoming message on session-id %s' % session_id)
                new_client = client(self.__server, CywTransport.IO(self.__cyw), self.__last_session_key)
                self.__server.add_client(new_client)
                new_client.start()
            else:
                logger.warn('Invalid session key %s' % data)
        else:
            print data_type
            print data
            print '----'
            data_type_match = re.match("^"+CYW_DT_SESSION+"([^ ]+)", data_type)
            if data_type_match is not None:
                session_id = data_type_match.group(1)
                
                existing_client = self.__server.client_by_session(session_id)
                
                if existing_client is None:
                    logger.warn('No clients for incoming message on session-id %s' % session_id)
                else:
                    logger.debug('Incoming message on session-id %s' % session_id)
                    existing_client.get_io().writer.write(data)
                    # echo back
                    existing_client.get_io().write(data)

    def close(self):
        self.reader.close()
        self.writer.close()

    class IO:
        def __init__(self, cyw):
            self.__cyw = cyw
            r, w = os.pipe()
            self.reader, self.writer = os.fdopen(r, 'rU', 0), os.fdopen(w, 'w', 0)
            
        def write(self, line, data_type='RESP-SSH'):
            try:
                send_data = ControlYourWay_p27.CreateSendData()
                send_data.data = line
                send_data.data_type = data_type
                if self.__cyw.connected:
                    self.__cyw.send_data(send_data)
            except socket.error:
                logger.error(traceback.format_exc())
            
        def close(self):
            self.reader.close()
            self.writer.close()
