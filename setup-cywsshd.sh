#!/bin/bash
# check if sudo is used
if [ "$(id -u)" != 0 ]; then
  echo 'Sorry, you need to run this script with sudo'
  exit 1
fi

# Create a log file of the build as well as displaying the build on the tty as it runs
exec > >(tee build-cywsshd.log)
exec 2>&1

pip install websocket-client
pip install psutil

# extract scripts to sbin
#tar -xzvf cywsshd.tar.gz -C /usr/sbin/
# copy all the files to the correct folder
yes | cp -rf ./cywsshd/* /usr/sbin/

echo -n "Enter your ControlYourWay username and press [ENTER]: "
read username

echo -n "Enter your ControlYourWay password and press [ENTER]: "
read password

echo -n "Enter your ControlYourWay network name and press [ENTER]: "
read network

echo -n "Enter a Discover password and press [ENTER]: "
read discoverPassword

echo -n "Enter the device name (name that will be returned when a discovery response is sent) and press [ENTER]: "
read deviceName

# create configuration file
cat > /etc/cywsshd.config <<- EOM
{
    "transports": ["TCP", "CYW"],
    "cywuser": "$username",
    "cywpass": "$password",
    "cywnetwork": "$network",
    "cywdiscoversecret": "$discoverPassword",
    "cywdevicename": "$deviceName"
}
EOM


# create auto-start script
cat > /lib/systemd/system/cywssh.service <<- EOM
[Unit]
Description=Control Your Way Terminal Service
After=multi-user.target

[Service]
Type=idle
ExecStart=/bin/sh -c '/usr/bin/python /usr/sbin/cywsshd.py -d'

[Install]
WantedBy=multi-user.target
EOM

chmod 644 /lib/systemd/system/cywssh.service

systemctl daemon-reload
systemctl enable cywssh.service
systemctl start cywssh.service