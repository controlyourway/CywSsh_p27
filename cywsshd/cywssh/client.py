from thread import *
import pwd
import spwd
import crypt
import time
from subprocess import Popen, PIPE
import sys
import os
import pty
import tty
from select import select
import platform
from virtualterminal import *
import logging

logger = logging.getLogger('cywsshd')

MAX_USERNAME_ATTEMPTS = 10
MAX_AUTH_ATTEMPTS = 3

class client:
    __is_authenticated = False
    __username = ''
    __session_id = ''
    
    def get_io(self):
        return self.__io
    def get_username(self):
        return self.__username
        
    def enqueue(self, message):
        self.__io.enqueue(message)
        
    def write(self, message):
        self.__terminal.write(message)
    
    def __init__(self, server, io, session_id):
        self.__server = server
        self.__io = io
        self.session_id = session_id
        self.__server.add_client(self)
        self.__spawn_time = os.times()[4]
        self.__terminal = virtualterminal(self)

    def __run(self):
        if self.__authenticate():
            logger.info('Entering terminal session for user (%s).' % self.__username)
            self.__terminal.start().wait() # wait for client or server to break connection
            
            print 'Exited terminal session for user (%s).' % self.__username
        self.__io.close()
        self.__server.remove_client(self)
        
    def __request_username(self):
        attempt = 0
        self.__username = ''
        while self.__username == '' and attempt < MAX_USERNAME_ATTEMPTS:
            attempt += 1
            logger.info('Requesting username from client, attempt %d/%d...' % (attempt, MAX_USERNAME_ATTEMPTS))
            self.__io.write('login: ')
            while True:
                line = self.__io.reader.readline()
                if line is None:
                    break
                line = line.rstrip('\r\n')
                if line is not None and line <> '':
                    self.__username = line
                    logger.info('Client provided a username: %s' % self.__username)
                else:
                    logger.info('Client provided a blank username.')
                break
        return self.__username is not None and self.__username != ''

    def report_ids(self, msg):
        print 'uid, gid = %d, %d; %s' % (os.getuid(), os.getgid(), msg)
    
    def __authenticate(self):
        attempt = 0
        
        if not self.__request_username():
            return

        while not self.__is_authenticated and attempt < MAX_AUTH_ATTEMPTS:
            if (os.times()[4] - self.__spawn_time) > 60: # 60 seconds allowed for login process
                self.__io.write('Your connection timed out.\n')
                return
            
            attempt += 1
            
            if self.__username == '':
                return
            
            password = ''
        
            logger.info('Requesting password from client, attempt %d/%d...' % (attempt, MAX_AUTH_ATTEMPTS))
            self.__io.write('password: ') #send only takes string
            while True:
                line = self.__io.reader.readline()
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
                        self.__io.write('Permission denied, please try again.\n')
                        break
                    
                    salt = crypted.rsplit('$', 1)[0] + '$'
                    cryptline = crypt.crypt(line, salt)
                    if cryptline == crypted:
                        logger.info('Client password for user (%s) correct.' % self.__username)
                        # successful auth
                        self.__is_authenticated = True
                    elif attempt < MAX_AUTH_ATTEMPTS:
                        logger.info('Client password for user (%s) incorrect.' % self.__username)
                        time.sleep(3)
                        self.__io.write('Permission denied, please try again.\n')

                break
        return self.__is_authenticated
        
    def start(self):
        start_new_thread(self.__run, ())

    def stop(self):
        print 'client asking terminal to stop'
        self.__terminal.stop()
        self.__io.close()
        self.__conn = None