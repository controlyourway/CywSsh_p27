import crypt
import logging
import os
import spwd
import time
import socket

from thread import *
from virtualterminal import *

logger = logging.getLogger('cywsshd')

MAX_USERNAME_ATTEMPTS = 10
MAX_AUTH_ATTEMPTS = 3
TIMEOUT_AUTH = 10

class client:
    __is_authenticated = False
    __username = ''
    __session_id = ''
    
    def __init__(self, server, io, session_id):
        self.__server = server
        self.__io = io
        self.session_id = session_id
        self.__spawn_time = os.times()[4]
        self.__terminal = virtualterminal(self)

    """ Starts the worker's threads
    """
    def start(self):
        start_new_thread(self.__run, ())

    """ Stops the worker's threads
    """
    def stop(self):
        print 'client asking terminal to stop'
        self.__terminal.stop()
        self.__io.close()
        self.__conn = None
        
    """ The body of this worker
    """
    def __run(self):
        try:
            try:
                if self.__authenticate():
                    logger.info('Entering terminal session for user (%s).' % self.__username)
                    self.__terminal.start().wait() # wait for client or server to break connection
                    
                    logger.info('Exited terminal session for user (%s).' % self.__username)
                else:
                    logger.warn('Authentication failed for session (%s).' % self.session_id)
            except:
                logger.error(traceback.format_exc())
            
            print 'sending close message'
            self.__io.write('closing connection', data_type='CLOSE-SSH')
            #self.__io.close()
            self.__server.remove_client(self)
        except:
            logger.error(traceback.format_exc())

    def get_io(self):
        return self.__io
        
    def get_username(self):
        return self.__username
        
    def enqueue(self, message):
        self.__io.enqueue(message)
        
    def write(self, message):
        self.__terminal.write(message)
        
    def __request_username(self):
        attempt = 0
        self.__username = ''
        while self.__username == '' and attempt < MAX_USERNAME_ATTEMPTS:
            attempt += 1
            logger.info('Requesting username from client, attempt %d/%d...' % (attempt, MAX_USERNAME_ATTEMPTS))
            self.__io.write('login: ')
            while True:
                #line = self.__io.reader.readline()
                try:
                    line = self.__io.readline(timeout=TIMEOUT_AUTH)
                    print 'got a line ' + line
                    if line is None:
                        break
                    line = line.rstrip('\r\n')
                    if line is not None and line <> '':
                        self.__username = line
                        logger.info('Client provided a username: %s' % self.__username)
                    else:
                        logger.info('Client provided a blank username.')
                    break
                except socket.timeout:
                    logger.info('Timeout while reading username.')
                    # explicitly exhaust the retry attempts
                    attempt = MAX_USERNAME_ATTEMPTS
                    self.__io.write('Your connection timed out.')
                    break;
        return self.__username is not None and self.__username != ''

    def report_ids(self, msg):
        print 'uid, gid = %d, %d; %s' % (os.getuid(), os.getgid(), msg)
    
    def __authenticate(self):
        attempt = 0
        
        if not self.__request_username():
            return

        while not self.__is_authenticated and attempt < MAX_AUTH_ATTEMPTS:
            attempt += 1
            
            if self.__username == '':
                return
            
            password = ''
        
            logger.info('Requesting password from client, attempt %d/%d...' % (attempt, MAX_AUTH_ATTEMPTS))
            self.__io.write('\r\npassword: ') #send only takes string
            print 'setting echo substitiue'
            self.__io.echo_substitute = '*' # echo asterisks for password
            try:
                while True:
                    try:
                        line = self.__io.readline(timeout=TIMEOUT_AUTH)
                        if line is None:
                            break
                        if line is not None:
                            logger.info('Client provided a password')
                            line = line.rstrip('\r\n')
                            # get crypt password for user account
                            try:
                                crypted = spwd.getspnam(self.__username)[1]
                            except KeyError:
                                logger.info('Client user (%s) did not exist in shadowpassword file.' % self.__username)
                                time.sleep(3)
                                self.__io.write('Permission denied, please try again.\r\n')
                                break
                            
                            salt = crypted.rsplit('$', 1)[0] + '$'
                            cryptline = crypt.crypt(line, salt)
                            if cryptline == crypted:
                                logger.info('Client password for user (%s) correct.' % self.__username)
                                # successful auth
                                self.__is_authenticated = True
                            else:
                                logger.info('Client password for user (%s) incorrect.' % self.__username)
                                #time.sleep(3)
                                if attempt < MAX_AUTH_ATTEMPTS:
                                    self.__io.write('Permission denied, please try again.\r\n')
                                else:
                                    self.__io.write('Permission denied.\r\n')
                    except socket.timeout:
                        # explicitly exhaust the retry attempts
                        attempt = MAX_USERNAME_ATTEMPTS
                        logger.info('Timeout while reading password.')
                        self.__io.write('Your connection timed out.')
                    break
            finally:
                self.__io.echo_substitute = None
        return self.__is_authenticated
