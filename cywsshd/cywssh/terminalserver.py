import re
from thread import *
from client import *
import ControlYourWay_v1_p27
from telnetreaderwriter import *
import logging
from cywreaderwriter import *

logger = logging.getLogger('cywsshd')

class terminalserver:
    __stop = False
    __clients = []
    __transports = []
    
    def __init__(self):
        pass

    def client_by_session(self, session_id):
        return next(iter(filter(lambda x: x.session_id == session_id, self.__clients)), None)

    def __run(self):
        for transport in self.__transports:
            logger.info('Initializing transport %s...' % `transport.__class__.__name__`)
            transport.initialize()
            logger.info('Transport %s initialized.' % `transport.__class__.__name__`)
        logger.info('Terminal server started.')
            
    def add_transport(self, transport):
        self.__transports.append(transport)

    def start(self):
        logger.info('Starting terminal server...')
        start_new_thread(self.__run, ())
        return True
        
    def stop(self):
        print 'stopping clients'

        while len(self.__clients) > 0:
            client = self.__clients[0]
            client.stop()

    def add_client(self, client):
        self.__clients.append(client)
        
    def remove_client(self, client):
        print ' removing client from list'
        self.__clients.remove(client)