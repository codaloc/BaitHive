#! .venv/bin/python

import time
from datetime import datetime
from datetime import timedelta
from collections import Counter
from flask import Flask, render_template

app = Flask(
    __name__,
)



def build_creds_leaderboard():
    user_counter = Counter()
    password_counter = Counter()
    cred_counter = Counter()

    with open("logs/credentials.log", "r") as f:
        for line in f:
            cred = line.split(" ")[1]
            cred_counter[cred] += 1
            name = cred.split(":")[0]
            password = cred.split(":")[1]
            user_counter[name] += 1
            password_counter[password] += 1
    return (user_counter.most_common(n=10),
            password_counter.most_common(n=10),
            len(user_counter.keys()),
            len(password_counter.keys()),
            len(cred_counter.keys()),
            cred_counter.total())

def build_cmd_leaderboard():
    cmd_counter = Counter()

    with open("logs/commands.log", "r") as f:
        for line in f:
            cmd = " ".join(line.split(" ")[3:])
            cmd_counter[cmd] += 1

    return (cmd_counter.most_common(n=10),
            len(cmd_counter.keys()),
            cmd_counter.total())

def build_ip_leaderboard():
    ip_counter = Counter()
    attempts_today = 0

    with open("logs/combined.log", "r") as f:
        for line in f:
            ip = line.split(" ")[1]
            ip_counter[ip] += 1

            timest = line.split(" ")[0]
            if float(timest) > time.time() - 86400:
                attempts_today += 1
    last_lines = open("logs/combined.log", "r").readlines()[-10:]
    last_attempts = []
    for line in last_lines:
        timest, ip, creds, status = line.split(" ")
        timest_formatted = datetime.fromtimestamp(float(timest)).strftime("%H:%M:%S.f")[:-2]
        if status == 0:
            res = "killed"
        else:
            res = "trapped"
        last_attempts.append([timest_formatted, ip, creds, res])
        last_attempts = last_attempts[::-1]
    return(
        ip_counter.most_common(n=10),
        len(ip_counter.keys()),
        attempts_today,
        last_attempts
    )

def get_current_trapped_count():
    with open("logs/container_count", "r") as f:
        cc = int(f.read())
    return cc

def get_uptime():
    with open("logs/uptime", "r") as f:
        start_t = float(f.read())
    return str(timedelta(seconds=time.time() - start_t))[:-7]



@app.route('/')
def main():

    top_usernames, top_passwords, unique_users, unique_passwords, unique_creds, creds_count  = build_creds_leaderboard()
    top_cmd, unique_cmd, cmd_count = build_cmd_leaderboard()
    top_ips, unique_ips, attempts_today, last_attempts = build_ip_leaderboard()
    uptime = get_uptime()
    current_cc = get_current_trapped_count()

    ###  Should be SSTI safe... hopefully
    return render_template('main.html',
    uptime = uptime,
    currently_trapped = current_cc,
    logins_today = attempts_today,
    total_attempts = creds_count,
    unique_ips = unique_ips,
    unique_users = unique_users,
    unique_pass = unique_passwords,
    unique_pairs = unique_creds,
    unique_commands = unique_cmd,
    total_commands = cmd_count,
    last_attempts = last_attempts,
    top_passwords = top_passwords,
    top_usernames = top_usernames,
    top_cmd = top_cmd,
    top_ips = top_ips
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=19473)
