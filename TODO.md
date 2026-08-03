### Slight stealth
-[ ] change pid 1 process to Nginx or Apache
-[x] set create user with password, then login as this user
-[x] non-random hostname
-[x] change asyncssh banner to something more classic
-[x] remove .rock and .dockerenv
-[x] remove duplicated ssh warning and info messages.
-[x] common username and/or password required

### Monitoring
-[ ] Looking for file opening/modification
  - fake secrets
-[ ] file creation/download
-[x] credentials used
-[x] commands run
-[x] full ssh session transcript 
-[x] logged in different files
-[ ] indication of session in command logs 

### Control
-[ ] TOML settings  
-[ ] no docker mode (connection attempts only)

### Containers
-[x] creation of new docker on connection
-[ ] association of session (IP-wise)
-[ ] same session uses the same docker
-[ ] timeout of docker
-[x] deletion of docker when session is closed

### Convenience
-[x] Does not require the user to be in the docker group
-[x] multiple attacker simultaneously 
-[x] pass signals to container ssh (ctrl+c)
-[ ] report creation commands
  - most likely: passwords, user, commands
