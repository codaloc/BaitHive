#! .venv/bin/python

import sys
import socket
import bcrypt
import random
import logging
import asyncio
import datetime
import asyncssh
import  subprocess
from pathlib import Path
from typing import Optional
#passwords = {'guest': b'', 'user123': bcrypt.hashpw(b'secretpw', bcrypt.gensalt())}


DOCKER_HOSTNAME = "dell-devbox"


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

Path("logs").mkdir(exist_ok=True, parents=True)
creds_logger = logging.getLogger("credentials")
creds_handler = logging.FileHandler("logs/credentials.log")
creds_handler.setFormatter(minimal_formatter)
creds_logger.addHandler(creds_handler)
creds_logger.setLevel(logging.INFO)

main_logger = logging.getLogger("main")
main_handler_file = logging.FileHandler("logs/main.log")
main_handler_file.setFormatter(pretty_formatter)
main_handler_stdout = logging.StreamHandler(sys.stdout)
main_handler_stdout.setFormatter(live_formatter)
main_logger.addHandler(main_handler_file)
main_logger.addHandler(main_handler_stdout)
main_logger.setLevel(logging.INFO)

cmd_std_in_logger = logging.getLogger("cmd_input")
cmd_in_logger_file = logging.FileHandler("logs/commands.log")
cmd_in_logger_file.setFormatter(pretty_formatter)
cmd_std_in_logger.addHandler(cmd_in_logger_file)
cmd_std_in_logger.setLevel(logging.INFO)


class LineLogger:
    def __init__(self, logger):
        self.logger = logger
        self.buf = bytearray()

    def feed(self, data: bytes):
        self.buf.extend(data)

        while True:
            # Look for either CR or LF
            for sep in (b"\r", b"\n"):
                idx = self.buf.find(sep)
                if idx != -1:
                    line = self.buf[:idx]
                    del self.buf[:idx + 1]
                    self.logger.info("%s", line.decode(errors="replace"))
                    break
            else:
                break

    def flush(self):
        if self.buf:
            self.logger.info("%s", self.buf.decode(errors="replace"))
            self.buf.clear()

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        res:int = sock.connect_ex(("127.0.0.1", port)) == 0
        return res

def session_name(ip:str, docker_name:str) -> str:
    return ip + "-" + docker_name[:6]


### Log and pipe
async def intercept(reader, writer, line_logger=None, session_file=None):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            ### logs sessions strait to a file
            if session_file:
                session_file.write(data)
                session_file.flush()
            ### Uses LineLogger to buffer command until \n or \r
            elif line_logger:
                line_logger.feed(data)

            writer.write(data)

            if hasattr(writer, "drain"):
                await writer.drain()
    finally:
        if hasattr(writer, "write_eof"):
            writer.write_eof()


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
        ["docker", "run", "-d", "--rm", f"-p{random_port}:22", "--hostname", DOCKER_HOSTNAME, "ubuntu-ssh"],
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


    ### Connect asyncSSH to docker ssh
    ssh_proc = await asyncio.create_subprocess_exec(
        "sshpass",
        f"-p{password}",
        "ssh",
        "-tt", ## important, forces TTY
        "-o", "StrictHostKeyChecking=no", ## ignore any previously saved key (for localhost)
        "-o", "UserKnownHostsFile=/dev/null", ## and doesn't save the new one
        "-o", "LogLevel=QUIET", ## hides "connection closed...", "Permanently added..."
        "-p", str(random_port),
        f"{username}@localhost",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    ### Open session logging file and create it if needed
    logdir = "./logs/sessions"
    Path(logdir).mkdir(exist_ok=True, parents=True)
    logfile = open(f"{logdir}/{session_name(process.get_extra_info('peername')[0], docker)}.session", "ab")
    logfile.write(f"\n\x1b[31m{datetime.datetime.now()} - {username}:{password} - {docker}:{process.get_extra_info('peername')[1]}\n\x1b[0m".encode("utf-8"))
    cmd_in_line_logger = LineLogger(cmd_std_in_logger)

    ### start all interceptions
    # sent by the client, relayed to server
    stdin_task = asyncio.create_task(intercept(process.stdin, ssh_proc.stdin, line_logger=cmd_in_line_logger))
    # sent by the server, relayed to client
    stderr_task = asyncio.create_task(intercept(ssh_proc.stdout, process.stdout, session_file=logfile))
    # sent by the server, relayed to client
    stdout_task = asyncio.create_task(intercept(ssh_proc.stderr, process.stderr, session_file=logfile))



    ### wait until ssh closes
    rc = await ssh_proc.wait()

    ### abort all tasks
    stdin_task.cancel()
    stdout_task.cancel()
    stderr_task.cancel()

    ### wait for tasks to end
    await asyncio.gather(
        stdin_task,
        stdout_task,
        stderr_task,
        return_exceptions=True,
    )

    process.exit(rc)
    logfile.close()

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
                                 process_factory=handle_client,
                                 encoding=None
                                 )

loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(start_server())
    main_logger.info("SSH distributor running !")
except (OSError, asyncssh.Error) as exc:
    main_logger.warning('Error starting server: ' + str(exc))
    sys.exit()

loop.run_forever()