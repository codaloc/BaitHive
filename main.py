#! .venv/bin/python

import os
import sys
import time
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

DOCKER_HOSTNAME = "dell-devbox"
SSH_PORT = 22
LOGS_FOLDER = "logs"
SERVER_VERSION_BANNER = "OpenSSH_10.4"
REQUIRE_COMMON_USERNAME = False
REQUIRE_COMMON_PASSWORD = False


class LineLogger:
    def __init__(self, logger):
        self.logger = logger
        self.buf = bytearray()

    def feed(self, data: bytes):
        self.buf.extend(data)

        while True:
            cr = self.buf.find(b"\r")
            lf = self.buf.find(b"\n")

            # if cr/lf found, leave everything at the end of the buffer
            if cr == -1 and lf == -1:
                break

            if cr == -1:
                idx = lf
            elif lf == -1:
                idx = cr
            else:
                idx = min(cr, lf)

            # gets content of buf before the cr/lf
            line = self.buf[:idx]
            # logs it
            self.logger.info("%s", line.decode(errors="replace"))
            # deleted it with the extra cr/lf
            del self.buf[:idx + 1]


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

    containers.append([docker, process.get_extra_info('peername')[0], time.time()])

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
    logdir = "./"+LOGS_FOLDER+"/sessions"
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

    with open(LOGS_FOLDER + "/container_count", "w") as cc_file:
        cc_file.write(str(len(containers)))

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
        self.state["ip"] = peer_name
        main_logger.info(f'SSH connection received from {peer_name}.')
        conn_ip_logger.info(f'{peer_name}')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            main_logger.warning('SSH connection error: ' + str(exc))
        else:
            main_logger.info(f'SSH Connection closed')


        if self.state["docker"]:
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

            # Remove docker from list
            for container in containers:
                if container[0] == self.state["docker"]:
                    containers.remove(container)

            # Modify docker count

            with open(LOGS_FOLDER + "/container_count", "w") as cc_file:
                cc_file.write(str(len(containers)))

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        creds_logger.info(f"{username}:{password}")
        self.state["username"] = username
        self.state["password"] = password
        if (username not in common_username) and REQUIRE_COMMON_USERNAME:
            main_logger.info(f'Username failed and was required.')
            comb_logger.info(f"{self.state["ip"]} {username}:{password} 0")
            return False
        elif (password not in common_passwords) and REQUIRE_COMMON_PASSWORD:
            main_logger.info(f'Password failed and was required.')
            comb_logger.info(f"{self.state["ip"]} {username}:{password} 0")
            return False
        # needed because setting the linux password won't work on a empty string
        elif (password == ''):
            comb_logger.info(f"{self.state["ip"]} {username}:{password} 0")
            return False


        comb_logger.info(f"{self.state["ip"]} {username}:{password} 1")
        return True

async def start_server() -> None:
    await asyncssh.create_server(MySSHServer, '', SSH_PORT,
                                 server_host_keys=['ssh_host_key'],
                                 process_factory=handle_client,
                                 encoding=None,
                                 server_version=SERVER_VERSION_BANNER
                                 )



containers = []

if os.geteuid() != 0:
    print("This must be run as root to spawn docker containers", file=sys.stderr)
    sys.exit(1)


with open("most_common_passwords.txt", "r") as pass_file:
    common_passwords = [line.rstrip("\n") for line in pass_file]
with open("most_common_username.txt", "r") as user_file:
    common_username = [line.rstrip("\n") for line in user_file]
with open(LOGS_FOLDER + "/uptime", "w") as uptime_file:
    uptime_file.write(str(time.time()))


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
unix_formatter = logging.Formatter(
    "%(created).2f %(message)s",
)

Path(LOGS_FOLDER).mkdir(exist_ok=True, parents=True)
creds_logger = logging.getLogger("credentials")
creds_handler = logging.FileHandler(LOGS_FOLDER + "/credentials.log")
creds_handler.setFormatter(minimal_formatter)
creds_logger.addHandler(creds_handler)
creds_logger.setLevel(logging.INFO)

main_logger = logging.getLogger("main")
main_handler_file = logging.FileHandler(LOGS_FOLDER + "/main.log")
main_handler_file.setFormatter(pretty_formatter)
main_handler_stdout = logging.StreamHandler(sys.stdout)
main_handler_stdout.setFormatter(live_formatter)
main_logger.addHandler(main_handler_file)
main_logger.addHandler(main_handler_stdout)
main_logger.setLevel(logging.INFO)

cmd_std_in_logger = logging.getLogger("cmd_input")
cmd_in_logger_file = logging.FileHandler(LOGS_FOLDER + "/commands.log")
cmd_in_logger_file.setFormatter(pretty_formatter)
cmd_std_in_logger.addHandler(cmd_in_logger_file)
cmd_std_in_logger.setLevel(logging.INFO)

conn_ip_logger = logging.getLogger("conn_ips")
conn_ip_logger_file = logging.FileHandler(LOGS_FOLDER + "/ips.log")
conn_ip_logger_file.setFormatter(unix_formatter)
conn_ip_logger.addHandler(conn_ip_logger_file)
conn_ip_logger.setLevel(logging.INFO)

comb_logger = logging.getLogger("combined")
comb_logger_file = logging.FileHandler(LOGS_FOLDER + "/combined.log")
comb_logger_file.setFormatter(unix_formatter)
comb_logger.addHandler(comb_logger_file)
comb_logger.setLevel(logging.INFO)

loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(start_server())
    main_logger.info("SSH distributor running !")
except (OSError, asyncssh.Error) as exc:
    main_logger.warning('Error starting server: ' + str(exc))
    sys.exit()

loop.run_forever()