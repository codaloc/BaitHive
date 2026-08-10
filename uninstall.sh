#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo -e "\e[31mPlease run as root: sudo $0\e[0m"
    exit 1
fi



echo -e "\e[36mRemoving built ubuntu-ssh image \e[0m"
sudo docker rmi ubuntu-ssh || echo "\e[31mOperation failed, maybe the image was never built?\e[0m"


echo -e "\e[36mRemoving ssh keypair \e[0m"
rm ssh_host_key; rm ssh_host_key.pub

echo -e "\e[36mRemoving venv\e[0m"
rm -rf .venv 

echo -e "\e[36m Removing baithive service file...\e[0m"
rm /etc/systemd/system/baithive.service
rm /etc/systemd/system/baithive-webstats.service || echo "Did not find baithive-webstats.service

echo "\n\n\n"
echo -e "\e[36mBaitHive should be reset to a pre-setup.sh state \e[0m"
