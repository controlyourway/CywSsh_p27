import logging
import os
import platform
import pty
import pwd
import sys
import traceback
import tty

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
        self.__manager = manager
        pass
    
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
        sock_reader = self.__manager.get_io().reader
        msg = ''
        errmsg = ''
        try:
            while not self.__stop:
                # read from the socket, terminal stdin, or terminal stdout, whichever produces data first
                rs, ws, es = select([sock_reader, process.stdout, process.stderr], [], [])
    
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
                            # a data-length of 0 means that the socket failed to read, must be closed
                            # exit the handler thread
                            self.stop()
                            pin.write(c) # pass on the character
                            break
                        elif c == '':
                            msg = msg[:-1]
                            break
                        elif c == '\n':
                            # deal with clients which send \r\n as terminator - strip the \r
                            if msg.endswith('\r'):
                                msg = msg[:-1]
                            # user hit enter, lets pass everything they typed to the virtual terminal
                            print 'received a newline - dumping to shell'
                            self.__write(self.__generate_promptstring())
                            pin.write(msg+'\n')
                            # clear the line buffer
                            msg = ''
                        else:
                            # append the data to our line buffer
                            #print 'appending to buffer [%s]' % msg
                            msg += c
                            sys.stdout.flush()
        
                    elif r is process.stdout: # data arrived from terminal
                        proc_response = process.stdout.readline()
                        self.__write('%s' % proc_response) #send only takes string
                        # print proc_response,
                        # sys.stderr.flush()
                    elif r is process.stderr: # error arrived from terminal
                        errmsg += process.stderr.read(1)
                        if errmsg.endswith('>>> '):
                            errmsg = errmsg[:-4]
                        if errmsg.endswith('\n'):
                            self.__write('%s' % errmsg)
                            errmsg = ''        
        except Exception as e:
            logger.error(traceback.format_exc())
            
        process.stdout.close()
        process.stderr.close()
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
        
    def write(self, message):
        self.__write(self.__generate_promptstring())
        self.pin.write(msg+'\r\n')
        
    """ Constructs a Linux-bash style command prompt
    """
    def __generate_promptstring(self):
        workdir = os.getcwd()
        if workdir == os.getenv('HOME'):
            workdir = "~"
        return '%s@%s:%s# ' % (self.__manager.get_username(), platform.node(), workdir)    
    
    """ Writes a welcome message to the client transport
    """
    def __print_welcome(self):
        if os.path.isfile(WELCOME_MESSAGE_PATH):
            self.__write('\n')
            with open(WELCOME_MESSAGE_PATH, "r") as welcome_file:
                for line in welcome_file:
                    self.__write(line + '\r\n')
            self.__write('\r\n\r\n')
            
        
    """ Demote child process to target user and group.
        This ensures Linux fs permissions will be honored.
    """
    def __demote(self, user_uid, user_gid):
        def result():
            os.setgid(user_gid)
            os.setuid(user_uid)
        return result    
