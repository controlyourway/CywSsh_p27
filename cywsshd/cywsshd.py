import os
import sys
import signal
import json
import logging
from logging.handlers import RotatingFileHandler
from cywssh import *
from cywssh.transports import *
import socket

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

# try:
#     raise socket.timeout('ss')
# except socket.timeout:
#     print 'got a timeout'
    
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
    
server = server()

if "transports" in cfg:
    if "transports" in cfg and "TCP" in cfg["transports"]:
        # enable telnet as a physical transport layer
        logger.info("Constructing and registering TCP transport")
        server.add_transport(TcpTransport(server, '', 8081))
    
    if "transports" in cfg and "CYW" in cfg["transports"]:
        # enable CYW as a physical transport layer
        logger.info("Constructing and registering CYW transport")
        server.add_transport(CywTransport(server, cfg['cywuser'], cfg['cywpass'], cfg['cywnetwork'], cfg['cywdiscoversecret'], cfg['cywdevicename']))
else:
    logger.error('No transports have been configured. Re-run setup')
    sys.exit(-1)
    
if not server.start():
    sys.exit()

try:
    signal.pause()
except KeyboardInterrupt:
    pass