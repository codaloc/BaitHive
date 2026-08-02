# BaitHive
## Containerized Dynamically Created Medium-Interaction Honeypot


```bash

# Create venv
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Build the docker container
sudo docker build -t ubuntu-ssh .

# Create keypair
ssh-keygen -f ssh_host_key -N ""

# start the server
sudo ./main.py
```