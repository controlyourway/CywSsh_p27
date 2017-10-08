import logging
import os
import platform
import pty
import pwd
import sys
import traceback
import tty
import time
import psutil

from select import select
from subprocess import Popen, PIPE
from thread import *
from threading import Event

WELCOME_MESSAGE_PATH = '/etc/motd'

logger = logging.getLogger('cywsshd')

class virtualterminal:
    __stop = False
    __evt_stopping = Event()
    
    def __init__(self, manager):
        self.__evt_stopping = Event()
        self.__manager = manager

    """ Starts the worker's threads
    """
    def start(self):
        self.__print_welcome()
        self.__spawn_shell_process()
        return self.__evt_stopping

    """ Stops the worker's threads
    """
    def stop(self):
        self.__write('Terminating session...\r\n')
        self.__stop = True 
        
    """ The body of this worker
    """
    def __run(self, process, pin):
        parent = psutil.Process(process.pid)
        sock_reader = self.__manager.get_io().reader
        msg = ''
        errmsg = ''
        while not self.__stop:
            try:
                
                # read from the socket, terminal stdin, or terminal stdout, whichever produces data first
                rs, ws, es = select([sock_reader, process.stdout, process.stderr], [], [], 1)
                for r in rs:
                    if r is sock_reader: # data arrived from socket
                        # read the data
                        c = r.read(1)
                        if len(c) == 0:
                            # a data-length of 0 means that the socket failed to read, must be closed
                            # exit the handler thread
                            self.stop()
                            break
                        elif ord(c) == 4: # ord(c) of 4 means CTRL^D
                        #     # a data-length of 0 means that the socket failed to read, must be closed
                        #     # exit the handler thread
                            logger.info('Received CTRL^D, terminating terminal...')
                            self.__write('\r\n')
                            self.stop()
                            break
                        # elif c == '':
                        #     print 'HERERERER'
                        #     pin.write(c)
                        #     pin.write("\x1B[D")
                            
                        # #    msg = msg[:-1]
                        #     break
                        else:
                            children = parent.children(recursive=False)
                            if len(children) == 0: # echo back to client
                                self.__write(c.replace('\n', '\r\n'))
    
                            pin.write(c)
                            sys.stdout.flush()
                            children = parent.children(recursive=False)
                            self.__manager.get_io().echo(len(children) == 0)
    
                    elif r in [process.stdout, process.stderr]: # data arrived from terminal
                        max = 100
                        def readAllSoFar(stream, max, retVal=''): 
                            while (select([stream],[],[],0)[0]!=[] and len(retVal) <= max):  
                                c = stream.read(1)
                                if len(c) == 0:
                                    break
                                else:
                                    retVal+=c
                            return retVal
                        proc_response = readAllSoFar(r, max)
    
                        if len(proc_response) == 0:
                            self.stop()
                            break
                        #print 'read bytes!'
                        children = parent.children(recursive=False)
                        #print 'has children ' + `len(children)`
                        proc_response = proc_response.replace('\n', '\r\n')
                        #print proc_response
                        self.__write('%s' % proc_response) #send only takes string
                        
                        if len(proc_response) < max and len(children) == 0:
                            self.__write(self.__generate_promptstring())
                        
                        time.sleep(0.005) # Hack currently to fix unknown race condition in CYW library preventing fast output
                        # sys.stderr.flush()
                    # elif r is process.stderr: # error arrived from terminal
                    #     print 'reading from error!'
                    #     errmsg += process.stderr.read(1)
                    #     if len(errmsg) == 0:
                    #         logger.info('Received CTRL^D, terminating terminal...')
                    #         self.stop()
                    #         break
                    #     if errmsg.endswith('>>> '):
                    #         errmsg = errmsg[:-4]
                    #     if errmsg.endswith('\n'):
                    #         self.__write('%s' % errmsg)
                    #         errmsg = ''  
            except Exception as e:
                self.__write('\r\nINTERNAL SERVER ERROR: %s\r\n' % e) #send only takes string
                logger.error(traceback.format_exc())
            
        logger.info('Virtual Terminal has exited.')
        process.stdout.close()
        process.stderr.close()
        process.terminate()
        self.__evt_stopping.set()
        
    """ Spawns the Linux `sh` process, captures its pipes, and creates a thread for routing I/O
    """
    def __spawn_shell_process(self):
        cwd = '/bin/bash --norc'
        pw_record = pwd.getpwnam(self.__manager.get_username())
        user_name      = pw_record.pw_name
        user_home_dir  = pw_record.pw_dir
        user_uid       = pw_record.pw_uid
        user_gid       = pw_record.pw_gid
        env = os.environ.copy()
        env[ 'HOME'     ]  = user_home_dir
        env[ 'LOGNAME'  ]  = user_name
        env[ 'PWD'      ]  = cwd
        env[ 'USER'     ]  = user_name

        logger.debug('Spawning shell process for user %s' % pw_record.pw_name)
        process = Popen(
            '/bin/sh', preexec_fn=self.__demote(user_uid, user_gid), cwd=user_home_dir, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE
        )

        # grab a file descriptor for the virtual terminal, use this to send data to your virtual terminal
        self.pin = process.stdin

        logger.debug('Sending prompt string for user %s' % pw_record.pw_name)
        self.__write(self.__generate_promptstring())
        
        start_new_thread(self.__run, (process, self.pin))
        
    """ Writes output to the client transport
    """
    def __write(self, text):
        self.__manager.get_io().write(text)
        
    # def write(self, message):
    #     self.__write(self.__generate_promptstring())
    #     self.pin.write(msg+'\r\n')
        
    """ Constructs a Linux-bash style command prompt
    """
    def __generate_promptstring(self):
        workdir = os.getcwd()
        if workdir == os.getenv('HOME'):
            workdir = "~"
        return '\r\n%s@%s:%s# ' % (self.__manager.get_username(), platform.node(), workdir)    
    
    """ Writes a welcome message to the client transport
    """
    def __print_welcome(self):
        if os.path.isfile(WELCOME_MESSAGE_PATH):
            logger.info('Sending welcome message from file: %s' % WELCOME_MESSAGE_PATH)
            self.__write('\n')
            with open(WELCOME_MESSAGE_PATH, "r") as welcome_file:
                for line in welcome_file:
                    self.__write(line.strip('\n') + '\r\n')
            self.__write('\r\n\r\n')
            
        
    """ Demote child process to target user and group.
        This ensures Linux fs permissions will be honored.
    """
    def __demote(self, user_uid, user_gid):
        def result():
            os.setgid(user_gid)
            os.setuid(user_uid)
        return result    
