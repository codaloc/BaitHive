import asyncio, asyncssh, bcrypt, sys, subprocess
# from typing import Optional

passwords = {'guest': b'',                # guest account with no password
             'user123': bcrypt.hashpw(b'secretpw', bcrypt.gensalt()),
            }

async def handle_client(process: asyncssh.SSHServerProcess) -> None:
    username = process.get_extra_info('username')
    process.stdout.write(f'Welcome to my SSH server, {username}!\n')
    bc_proc = subprocess.Popen('sshpass -ptest ssh -p 2222 root@localhost', shell=True, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    await process.redirect(stdin=bc_proc.stdin, stdout=bc_proc.stdout,
                           stderr=bc_proc.stderr)
    await process.stdout.drain()
    process.exit(0)
    process.exit(0)

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        peername = conn.get_extra_info('peername')[0]
        print(f'SSH connection received from {peername}.')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc:
            print('SSH connection error: ' + str(exc), file=sys.stderr)
        else:
            print('SSH connection closed.')

    def begin_auth(self, username: str) -> bool:
        # If the user's password is the empty string, no auth is required
        return passwords.get(username) != b''

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        if username not in passwords:
            return False
        pw = passwords[username]
        if not password and not pw:
            return True
        return bcrypt.checkpw(password.encode('utf-8'), pw)

async def start_server() -> None:
    await asyncssh.create_server(MySSHServer, '', 8022,
                                 server_host_keys=['ssh_host_key'],
                                 process_factory=handle_client)

loop = asyncio.new_event_loop()

try:
    loop.run_until_complete(start_server())
except (OSError, asyncssh.Error) as exc:
    sys.exit('Error starting server: ' + str(exc))

loop.run_forever()