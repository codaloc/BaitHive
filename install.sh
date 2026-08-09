#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo -e "\e[31mPlease run as root: sudo $0\e[0m"
    exit 1
fi


echo -e "\e[36mCreating virtual env and downloading requirements...\e[0m"
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

echo -e "\e[36mBuilding BaitHive ssh docker - this might take some time the first time...\e[0m"
docker build -t ubuntu-ssh .

echo -e "\e[36mGenerating ssh keypair for asyncssh server...\e[0m"
ssh-keygen -f ssh_host_key -N ""

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
systemctl daemon-reload

echo "\n\n\n"
echo -e "\e[36mBaitHive is ready to be started.\e[0m"
echo -e "\e[36muse 'sudo ./start' or 'sudo ./start --no-webstats' to start with or without the statistic web-service (port 19473)\e[0m"
