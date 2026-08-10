#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "\e[31mPlease run as root: sudo $0\e[0m"
    exit 1
fi


echo -e "\e[36mStopping and disabling baithive and baithive-webstats services...\e[0m"
systemctl disable --now baithive-webstats.service
systemctl disable --now baithive.service
echo -e "\e[36mDone.\e[0m"

echo -e "\e[36mRemoving running ubuntu-ssh docker containers... \[0m"
docker stop $(docker ps -a -q  --filter ancestor=ubuntu-ssh)
echo -e "\e[36mDone.\e[0m"

echo -e "\e[36mBaitHive Disable&Stopped !\e[0m"
