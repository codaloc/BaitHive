### Slight stealth
-[ ] change pid 1 process to Nginx or Apache
-[x] set create user with password, then login as this user
-[ ] non-random hostname
-[ ] keyboard-interactive method removal
-[ ] change asyncssh banner to something more classic

### Monitoring
-[ ] Looking for file opening/modification
  - fake secrets
-[ ] file creation/download
-[x} credentials used
-[x] commands run
-[x} full ssh session transcript 
-[x] logged in different files

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
-[ ] pass signals to container ssh (ctrl+c)
-[ ] report creation commands
  - most likely: passwords, user, commands

### Some of the done
-[x] Does not require the user to be in the docker group


