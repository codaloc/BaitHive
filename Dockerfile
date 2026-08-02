FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get clean

RUN echo 'root:default' | chpasswd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN rm -rf .dockerenv .rock

EXPOSE 22

# Start SSH service
CMD ["/usr/sbin/sshd", "-D"]
