### Slight stealth
-[ ] change pid 1 process to Nginx or Apache
-[ ] set create user with password, then login as this user
-[ ] non-random hostname
-[ ] keyboard-interactive method removal
-[ ] change asyncssh banner to something more classic

### Monitoring
-[ ] Looking for file opening/modification
  - fake secrets
-[ ] file creation/download
-[ ] commands run (and output?)
-[ ] different files for logging
  - user:pass
  - commands

### Control
-[ ] TOML settings  
-[ ] no docker mode (connection attempts only)

### Containers
-[ ] creation of new docker on connection
-[ ] association of session (IP-wise)
-[ ] same session uses the same docker
-[ ] timeout of docker
-[ ] deletion of docker when session is closed

### Convenience
-[ ] pass signals to container ssh (ctrl+c)
-[ ] report creation commands
  - most likely: passwords, user, commands

### Some of the done
-[] Does not require the user to be in the docker group


