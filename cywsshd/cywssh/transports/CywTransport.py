import logging
import os
import ControlYourWay_p27
import random
import re
import string
import socket
from ..client import *


logger = logging.getLogger('cywsshd')

CYW_DT_DISCOVER_REQUEST = 'DISCOVER-SSH'
CYW_DT_DISCOVER_RESPONSE = 'DISCOVER-RESPONSE-SSH'
CYW_DT_REQUEST = 'REQ-SSH'
CYW_DT_RESPONSE = 'RESP-SSH'
CYW_DT_CONNECT = 'CONNECT-SSH'
CYW_DT_CLOSE = 'CLOSE-SSH'

SESSION_KEY_LENGTH = 20

class CywTransport:
    def __init__(self, server, account_user, account_password, network, secret, device_name):
        self.__server = server
        self.__account_user = account_user
        self.__account_password = account_password
        self.__network = network
        self.__secret = secret
        self.__device_name = device_name;
        self.__pending_session_keys = [] # a list of session keys that MAY be turned into client objects, should a DISCOVER be escalated to a CONNECT

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
        
    def generate_session_key(self):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(SESSION_KEY_LENGTH))

    def data_received_callback(self, data, data_type, from_who):
        #print 'data received'
        data_type_match = re.match("^([^:]+)(:(.+))?$", data_type)
        split_data_type = data_type_match.group(1)
        if split_data_type == CYW_DT_CLOSE:
            session_id = data_type_match.group(3)
            
            existing_client = self.__server.client_by_session(session_id)
            
            if existing_client is None:
                logger.warn('No clients for incoming message on session-id %s' % session_id)
            else:
                logger.info('Client requested connection be closed...')
                existing_client.stop()

        elif split_data_type == CYW_DT_DISCOVER_REQUEST:
            if data == self.__secret:
                # respond with discovery result
                # 1. generate 20-byte unique key
                new_session_key = self.generate_session_key()
                self.__pending_session_keys.append(new_session_key)
                
                # 3. send response back to network
                send_data = ControlYourWay_p27.CreateSendData()
                send_data.data = new_session_key + ',' + self.__device_name
                send_data.data_type = CYW_DT_DISCOVER_RESPONSE
                if self.__cyw.connected:
                    self.__cyw.send_data(send_data)
            else:
                logger.info('Invalid secret key received')
        elif split_data_type == CYW_DT_CONNECT:
            if data in self.__pending_session_keys:
                logger.debug('CONNECT request with secret %s' % data)
                # remove the session key so it cannot be used again for another connection attempt.
                self.__pending_session_keys.remove(data)
                # 2. start a client instance for the new session-id
                # logger.warn('No clients for incoming message on session-id %s' % session_id)
                new_client = client(self.__server, CywTransport.IO(self.__cyw), data)
                self.__server.add_client(new_client)
                new_client.start()
            else:
                logger.warn('Invalid session key %s' % data)
        elif split_data_type == CYW_DT_REQUEST:
            session_id = data_type_match.group(3)
            
            existing_client = self.__server.client_by_session(session_id)
            
            if existing_client is None:
                logger.warn('No clients for incoming message on session-id %s' % session_id)
                # return a disconnect message
                try:
                    send_data = ControlYourWay_p27.CreateSendData()
                    send_data.data = ''
                    send_data.data_type = CYW_DT_CLOSE
                    if self.__cyw.connected:
                        self.__cyw.send_data(send_data)
                except socket.error:
                    logger.error(traceback.format_exc())
                
            else:
                logger.debug('Incoming message on session-id %s' % session_id)
                existing_client.get_io().enqueue(data)
                # echo back
                #existing_client.get_io().write(data)

    # def close(self):
    #     self.reader.close()
    #     self.writer.close()

    class IO:
        echo_substitute = None
        __echo = False
        
        def __init__(self, cyw):
            self.__cyw = cyw
            r, w = os.pipe()
            self.reader, self.__writer = os.fdopen(r, 'rU', 0), os.fdopen(w, 'w', 0)
            
        def echo(self, value = None):
            if value is None:
                return self.__echo
            else:
                self.__echo = value
                
        ### fill the pipe with data that will be processed by any listening threads.
        def enqueue(self, data):
            self.__writer.write(data)
            # if self.__echo:
            #     echo_char = self.echo_substitute
            #     if echo_char is not None:
            #         non_whitespace = data.translate(None, ' \n\t\r')
            #         self.write(echo_char * len(non_whitespace))
            #     else:
            #         self.write(data)
            
        def write(self, line, data_type=CYW_DT_RESPONSE):
            if self.__writer == None:
                return
            try:
                send_data = ControlYourWay_p27.CreateSendData()
                s = line
                b = bytearray()
                b.extend(s)
                send_data.data = list(line)
                send_data.data_type = data_type
                if self.__cyw.connected:
                    self.__cyw.send_data(send_data)
            except socket.error:
                logger.error(traceback.format_exc())
            
        def readline(self, echo=False, substitute=None, timeout=0):
            rs, ws, es = select([self.reader], [], [], timeout)
            line = ''
            c = None
            c_previous = None
            while c != '\n':
                if not (rs or ws or es):
                        raise socket.timeout()
                if self.reader in rs:
                    c = self.reader.read(1)
                    if c != '\n':
                        line += c
                    
                    if self.__echo or substitute != None:
                        echo_char = substitute
                        if c in '\n\r':
                            if c == '\n' and c_previous != '\r':
                                self.write('\r')
                            self.write(c)
                        else:
                            if echo_char is not None:
                                non_whitespace = c.translate(None, '\n\r')
                                self.write(echo_char * len(non_whitespace))
                            else:
                                self.write(c)
                    c_previous = c
                        
            return line
            
        def close(self):
            # send disconnect notification to server
            self.write('closing connection', data_type=CYW_DT_CLOSE)
            self.reader.close()
            self.__writer.close()
            self.reader = None
            self.__writer = None
