from angr/angr
maintainer yans@yancomm.net

run cd /home/angr/angr-dev && /home/angr/.virtualenvs/angr/bin/pip install -e angr-management
run cd /home/angr/angr-dev/angr-management && git pull
user angr
workdir /home/angr/pwd
entrypoint [ "/home/angr/.virtualenvs/angr/bin/python", "-m", "angrmanagement" ]
