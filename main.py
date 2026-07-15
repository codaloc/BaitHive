#! .venv/bin/python

import sys
import time
import socket
import bcrypt
import random
import logging
import asyncio
import asyncssh
import  subprocess
from typing import Optional

#passwords = {'guest': b'', 'user123': bcrypt.hashpw(b'secretpw', bcrypt.gensalt())}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("logs.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        res:int = sock.connect_ex(("127.0.0.1", port)) == 0
        return res


async def handle_client(process: asyncssh.SSHServerProcess) -> None:
    server = process.get_extra_info("connection").get_owner()
    username = process.get_extra_info('username')
    password = server.state["password"]
    logging.info(f'{username}:{password} successfully connected')

    ### Create the docker container
    random_port = random.randint(1000, 10000)
    while is_port_in_use(random_port):
        random_port = random.randint(1000, 10000)
    logging.info("Starting Docker creation")
    docker_command = subprocess.run(
        ["docker", "run", "-d", "--rm", f"-p{random_port}:22", "ubuntu-ssh"],
        capture_output=True,
        text=True,
        check=True
    )
    docker:str = docker_command.stdout.rstrip()
    server.state["docker"] = docker
    logging.info(f'docker {docker[:10]}... created, listening on port {random_port}')

    ### randomize the root password
    root_password = random.randbytes(10).hex()
    server.state["docker_root_pass"] = root_password
    user_command = subprocess.run(
        f"sudo docker exec {docker} bash -c \"echo 'root:{root_password}'|chpasswd\"",
        shell = True,
        capture_output=True,
        text=True,
        check=True
    )
    logging.info(f'root password on {docker[:10]} has been randomized to {root_password}')


    ### create the user:password used to log in
    user_command = subprocess.run(
        f"sudo docker exec {docker} bash -c \"useradd -m -s /bin/bash {username}; echo '{username}:{password}'|chpasswd\"",
        shell = True,
        capture_output=True,
        text=True,
        check=True
    )
    logging.info(f'user {username} has been created on {docker[:10]}')

    bc_proc = subprocess.Popen(f'sshpass -p{password} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {random_port} {username}@localhost',
                               shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.redirect(stdin=bc_proc.stdin, stdout=bc_proc.stdout, stderr=bc_proc.stderr)
    await process.stdout.drain()
    process.exit(0)

class MySSHServer(asyncssh.SSHServer):

    def __init__(self):
        self.state = {}

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        peer_name = conn.get_extra_info('peername')[0]
        logging.info(f'SSH connection received from {peer_name}.')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            logging.warning('SSH connection error: ' + str(exc))
        else:
            logging.info(f'SSH Connection closed')

    def begin_auth(self, username: str) -> bool:
        # If the user's password is the empty string, no auth is required
        # return passwords.get(username) != b''
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        self.state["username"] = username
        self.state["password"] = password
        # if username not in passwords:
        #     return False
        # pw = passwords[username]
        # if not password and not pw:
        #     return True
        # return bcrypt.checkpw(password.encode('utf-8'), pw)
        return True

async def start_server() -> None:
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh_host_key'],
                                 process_factory=handle_client)

loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(start_server())
except (OSError, asyncssh.Error) as exc:
    logging.warning('Error starting server: ' + str(exc))
    sys.exit()

loop.run_forever()