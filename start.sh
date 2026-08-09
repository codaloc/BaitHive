#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "\e[31mPlease run as root: sudo $0\e[0m"
    exit 1
fi


echo -e "\e[36mEnabling and starting baithive service...\e[0m"
systemctl enable baithive.service --now
sleep 2
echo "Done."

if [ "$1" != "--no-webstats" ]; then

    echo -e "\e[36mEnabling and starting baithive-webstats service...\e[0m"
    echo -e "\e[36mUse '--no-webstats' to not start the stat webservice next time.\e[0m"
    systemctl enable baithive-webstats.service --now

fi

echo -e "\e[36mDone.\e[0m"

echo -e "\e[36mBaitHive running !\e[0m"
echo -e "\e[36mVisit\e[0m \e]8;;http://127.0.0.1:19473/\e\\127.0.0.1:19473\e]8;;\e\\ \e[0m"
