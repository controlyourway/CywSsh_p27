#!/bin/bash
# check if sudo is used
if [ "$(id -u)" != 0 ]; then
  echo 'Sorry, you need to run this script with sudo'
  exit 1
fi

# Create a log file for the uninstall as well as displaying the build on the tty as it runs
exec > >(tee build-cywsshd.log)
exec 2>&1

systemctl stop cywssh.service
systemctl disable cywssh.service

rm /lib/systemd/system/cywssh.service
rm /etc/cywsshd.config
rm -r /usr/sbin/cywssh

systemctl daemon-reload
systemctl reset-failed
