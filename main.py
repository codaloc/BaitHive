#! .venv/bin/python

import logging
import asyncio, asyncssh, bcrypt, sys, subprocess
import socket
import random
import time
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
    username = process.get_extra_info('username')
    logging.info(f'{username} successfully connected')

    logging.info(f'generating & checking port')
    random_port = random.randint(1000,10000)
    while is_port_in_use(random_port) == True:
        random_port = random.randint(1000, 10000)

    logging.info("creating docker")
    docker:str = subprocess.run(
        ["docker", "run", "-d", "--rm", f"-p{random_port}:22", "ubuntu-ssh"],
        capture_output=True,
        text=True,
        check=True
    ).stdout

    logging.info(f'docker {docker} created, listening on port {random_port}')

    bc_proc = subprocess.Popen(f'sshpass -ptest ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p {random_port} root@localhost',
                               shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.redirect(stdin=bc_proc.stdin, stdout=bc_proc.stdout, stderr=bc_proc.stderr)
    await process.stdout.drain()
    process.exit(0)
    process.exit(0)

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        peername = conn.get_extra_info('peername')[0]
        logging.info(f'SSH connection received from {peername}.')

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
        logging.info(f'Connection using credentials {username}:{password}')
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