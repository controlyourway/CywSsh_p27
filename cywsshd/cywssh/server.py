import logging
import re

from client import *
from thread import *

logger = logging.getLogger('cywsshd')

class server:
    __stop = False
    __clients = []
    __transports = []
    
    def __init__(self):
        pass

    """ Starts the worker's threads
    """
    def start(self):
        logger.info('Starting terminal server...')
        start_new_thread(self.__run, ())
        return True
        
    """ Stops the worker's threads
    """
    def stop(self):
        print 'stopping clients'

        while len(self.__clients) > 0:
            client = self.__clients[0]
            client.stop()

    """ The body of this worker
    """
    def __run(self):
        for transport in self.__transports:
            logger.info('Initializing transport %s...' % `transport.__class__.__name__`)
            transport.initialize()
            logger.info('Transport %s initialized.' % `transport.__class__.__name__`)
        logger.info('Terminal server started.')

    """ Finds a client by its session-id
    """
    def client_by_session(self, session_id):
        return next(iter(filter(lambda x: x.session_id == session_id, self.__clients)), None)

    """ Add a transport to the transports collection
    """
    def add_transport(self, transport):
        self.__transports.append(transport)

    """ Add a client to the clients collection
    """
    def add_client(self, client):
        print 'adding client'
        self.__clients.append(client)
        
    """ Remove a client from the clients collection
    """
    def remove_client(self, client):
        isin = client in self.__clients
        self.__clients.remove(client)
