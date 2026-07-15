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


pretty_formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"
)
live_formatter = logging.Formatter(
    "%(asctime)s %(message)s",
    datefmt="%H:%M:%S"
)
minimal_formatter = logging.Formatter(
    "%(asctime)s %(message)s",
    datefmt = "%d/%m-%H:%M:%S"
)

creds_logger = logging.getLogger("credentials")
main_logger = logging.getLogger("main")

creds_handler = logging.FileHandler("logs/credentials.log")
creds_handler.setFormatter(minimal_formatter)
creds_logger.addHandler(creds_handler)
creds_logger.setLevel(logging.INFO)

main_handler_file = logging.FileHandler("logs/main.log")
main_handler_file.setFormatter(pretty_formatter)
main_handler_stdout = logging.StreamHandler(sys.stdout)
main_handler_stdout.setFormatter(live_formatter)
main_logger.addHandler(main_handler_file)
main_logger.addHandler(main_handler_stdout)
main_logger.setLevel(logging.INFO)



def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        res:int = sock.connect_ex(("127.0.0.1", port)) == 0
        return res


async def handle_client(process: asyncssh.SSHServerProcess) -> None:
    server = process.get_extra_info("connection").get_owner()
    username = process.get_extra_info('username')
    password = server.state["password"]
    main_logger.info(f'{username}:{password} successfully connected')

    ### Create the docker container
    random_port = random.randint(1000, 10000)
    while is_port_in_use(random_port):
        random_port = random.randint(1000, 10000)
    main_logger.info("Starting Docker creation")
    docker_command = subprocess.run(
        ["docker", "run", "-d", "--rm", f"-p{random_port}:22", "ubuntu-ssh"],
        capture_output=True,
        text=True,
        check=True
    )
    docker:str = docker_command.stdout.rstrip()
    server.state["docker"] = docker
    main_logger.info(f'docker {docker[:10]}... created, listening on port {random_port}')

    ### randomize the root password
    root_password = random.randbytes(10).hex()
    server.state["docker_root_pass"] = root_password
    root_pass_command = subprocess.run(
        f"sudo docker exec {docker} bash -c \"echo 'root:{root_password}'|chpasswd\"",
        shell = True,
        capture_output=True,
        text=True,
        check=True
    )
    main_logger.info(f'root password on {docker[:10]} has been randomized to {root_password}')


    ### create the user:password used to log in
    user_command = subprocess.run(
        f"sudo docker exec {docker} bash -c \"useradd -m -s /bin/bash {username}; echo '{username}:{password}'|chpasswd\"",
        shell = True,
        capture_output=True,
        text=True,
        check=True
    )
    main_logger.info(f'user {username} has been created on {docker[:10]}')

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
        main_logger.info(f'SSH connection received from {peer_name}.')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            main_logger.warning('SSH connection error: ' + str(exc))
        else:
            main_logger.info(f'SSH Connection closed')

        ### Remove container after
        # only stops the container since it was spawned with --rm
        docker_del_command = subprocess.run(
            f"sudo docker stop {self.state["docker"]}",
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        main_logger.info(f'Container {self.state["docker"][:10]} was removed on closed connection')

    def begin_auth(self, username: str) -> bool:
        # If the user's password is the empty string, no auth is required
        # return passwords.get(username) != b''
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        creds_logger.info(f"{username}:{password}")
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
    main_logger.warning('Error starting server: ' + str(exc))
    sys.exit()

loop.run_forever()