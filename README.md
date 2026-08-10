<p align="center"><code style="font-family:monospace">
   ▄▄▄                ▄▄▄  ▄▄▄                
  ██▀▀█▄          █▄ █▀██  ██                 
  ██ ▄█▀       ▀▀▄██▄  ██  ██   ▀▀            
  ██▀▀█▄ ▄▀▀█▄ ██ ██   ██████   ██▀█▄ ██▀▄█▀█▄
▄ ██  ▄█ ▄█▀██ ██ ██   ██  ██   ██ ██▄██ ██▄█▀
▀██████▀▄▀█▄██▄██▄██ ▀██▀  ▀██▄▄██  ▀█▀ ▄▀█▄▄▄
</code> </p>

## Containerized Dynamically Created Medium-Interaction Honeypot

### Requirements
```plaintext
python3
python3-venv
sshpass
docker
```

### Installation & Usage
```bash
# 1 - make sure the port 22 is not in use (if needed change the port in /etc/ssh/sshd_config and restart ssh)

# 2 - make sure all requirements are installed (refer to previous section)

# 3 - run the setup script
sudo ./setup.sh

# 4 - start both services or without the statistic webserver
sudo ./start.sh
# or
sudo ./start.sh --no-webstats


# end 
sudo ./stop.sh
```


### Manual installation 
Read `setup.sh`, `start.sh`, `stop.sh` and `uninstall.sh`