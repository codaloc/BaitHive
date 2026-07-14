# Use a base image with SSH installed (you can choose a different base image if needed)
FROM ubuntu:latest

# Install SSH server
RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get clean

RUN echo 'root:test' | chpasswd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22

# Start SSH service
CMD ["/usr/sbin/sshd", "-D"]
