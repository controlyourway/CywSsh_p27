import os
import sys
import signal
import json
import logging
from logging.handlers import RotatingFileHandler
from cywssh import *
from cywssh.transports import *

LOG_FILENAME = '/var/log/cywsshd.log'

# Set up a specific logger with our desired output level
logger = logging.getLogger('cywsshd')

# Add a file handler
filehandler = RotatingFileHandler(LOG_FILENAME, maxBytes=2000, backupCount=10)
# create a logging format
filehandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(filehandler)

# Add a console handler
consolehandler = logging.StreamHandler()
consolehandler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
logger.addHandler(consolehandler)

logger.setLevel(logging.DEBUG)

def signal_handler(signal, frame):
    logger.info('Shutting down')
    server.stop()
    logger.info('Service terminated. Exiting')
    
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

if not os.path.isfile('/etc/cywsshd.config'):
    print 'Could not load cywsshd.config from /etc'
    
with open('/etc/cywsshd.config') as json_data:
    cfg = json.load(json_data)
    
server = terminalserver()#'', 8081)

# enable telnet as a physical transport layer
server.add_transport(TcpTransport(server, '', 8081))

# enable CYW as a physical transport layer
server.add_transport(CywTransport(server, cfg['cywuser'], cfg['cywpass'], cfg['cywnetwork']))

if not server.start():
    sys.exit()

try:
    signal.pause()
except KeyboardInterrupt:
    pass

#server.stop()