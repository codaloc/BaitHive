#!/bin/bash

set -e

if [ "$EUID" -ne 0 ]; then
    echo -e "\e[31mPlease run as root: sudo $0\e[0m"
    exit 1
fi

echo -e "\e[36m Make sure you have all the requirements installed: python3, python3-venv, sshpass, docker\e[0m"
sleep 2

echo -e "\e[36mCreating virtual env and downloading requirements...\e[0m"
python3 -m venv .venv || { echo "\e[31mPython failed to created a venv, make sure python3 and python3-venv are installed \e[0m"; exit 1; }
source .venv/bin/activate || { echo "\e[31mFailed to source venv\e[0m"; exit 1; }
pip install -r requirements.txt || { echo "\e[31m Pip failed to install requirements, make sure python pip is installed \e[0m"; exit 1; }

echo -e "\e[36mBuilding BaitHive ssh docker - this might take some time the first time...\e[0m"
docker build -t ubuntu-ssh . || { echo "\e[31mDocker failed to build the container, make sure docker is installed \e[0m"; exit 1; }

echo -e "\e[36mGenerating ssh keypair for asyncssh server...\e[0m"
ssh-keygen -f ssh_host_key -N "" || { echo "\e[31m ssh-keygen failed to create ssh keypair\e[0m"; exit 1; }

# get CWD
DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "\e[36mCreating baithive service file...\e[0m"
cat > /etc/systemd/system/baithive.service <<EOF
[Unit]
Description=BaitHive Honeypot Service
After=network.target

[Service]
Type=simple
ExecStart=$DIR/main.py
Restart=on-failure
RestartSec=5
WorkingDirectory=$DIR

[Install]
WantedBy=multi-user.target
EOF

echo -e "\e[36mCreating baithive-webstats service file...\e[0m"
cat > /etc/systemd/system/baithive-webstats.service <<EOF
[Unit]
Description=BaitHive Web Stats Overview Service
After=network.target

[Service]
Type=simple
ExecStart=$DIR/webserver.py
Restart=on-failure
RestartSec=5
WorkingDirectory=$DIR

[Install]
WantedBy=multi-user.target
EOF

echo -e "\e[36mReloading systemctl deamon...\e[0m"
systemctl daemon-reload || { echo "\e[31mFailed to reaload systemctl daemon \e[0m"; exit 1; }

echo "\n\n\n"
echo -e "\e[36mBaitHive is ready to be started.\e[0m"
echo -e "\e[36muse 'sudo ./start' or 'sudo ./start --no-webstats' to start with or without the statistic web-service (port 19473)\e[0m"
