# Control Your Way Python Secure Shell
### Python 2.7

##Introduction
This application works with our terminal applications to give the user a Secure Shell interface over the network using the Control Your Way service.

##Install
Clone or download the files and go to the directory where the files are located. Run the following command:
**sudo ./setup-cywsshd.sh**
You will be asked for your CYW username/password/network name during installation.
These are stored in plaintext in /etc/cywsshd.config

Once this is done, the service should be installed, and running.
Run this to check

**service cywssh status**

NOTE: The server currently supports 2 transport mechanisms - pure TCP, and CYW.
The TCP transport will listen on TCP port 8081, and you can connect to it with telnet.
I will add an option to the config soon to disable this by default.

USAGE:
Connect to your CYW network using one of your clients, and enter "session:XXX" into the data-type, where XXX is any random key of your choosing. This must stay the same during your terminal session. Hit SEND with any message (the message data does not matter for the first request).
The terminal server will not recognize it at first, so it will prompt for a login.

Logs are stored in /etc/cywsshd.log

TODO:
1.	more code comments/logging
2.	configuration option to turn off TCP transport
3.	timeout to kill sessions when idle
4.	configuration for idle time

If you are having problems with this application it is handy to be able to run it in a terminal to see the output. To do this run the following commands:
1. Stop the service:

**service cywssh stop**

2. Run it as an interactive program:

**python /usr/sbin/cywsshd.py**

If the credentials in cywsshd.config changes, you can restart the service by using:

**service cywssh restart**
