# Control Your Way Python Secure Shell
### Python 2.7

## Introduction

This application works with our terminal applications to give the user a Secure Shell interface over the internet using the Control Your Way service.
It uses the linux user credentials to log in, as if you are directly connected to the device. Security is inforced in the following way:
1. The only way to discover a ssh device is to know its discover password. 
2. The ssh device will only respond to your session ID, other devices connected to the same network will not see any data returned by the ssh device.
3. As part of the discovery response a cleint key will be returned. The client must send all messages to the session ID of the ssh device so that other devices
on the network cannot see messaged sent to the ssh device. The correct client key must be sent with all messages to the ssh device, otherwise the message will be
discarded.

## Install

On Ubuntu, run the following command first to allow pip to install the correct Python libraries:
**sudo apt-get install python-pip**
Clone or download the files and go to the directory where the files are located. Run the following command:
**sudo ./setup-cywsshd.sh**
You will be asked for the following details during installation:
1. CYW username
2. CYW password
3. CYW network name
4. Discover password, this is the password that must be sent with a discovery message for this device to share its details.
5. Device name, when the password sent with the discover message matches the Discover password then this application will respond with the device name and the session ID.

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

Rolling logs are stored in /var/log/cywsshd.log

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

To uninstall this application:

**sudo ./uninstall.sh**
