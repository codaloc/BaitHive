FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get install -y unminimize && \
    apt-get clean

RUN yes | unminimize

RUN echo 'root:default' | chpasswd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN rm -rf .rock

EXPOSE 22

ENTRYPOINT ["sh", "-c", "rm -f /.dockerenv && exec \"$@\"", "--"]

CMD ["/usr/sbin/sshd", "-D"]
