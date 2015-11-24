#!/bin/bash

DSTPATH=/usr/local/eyefiserver
PYTHONPATH=/usr/bin
RCDPATH=/usr/local/eyefiserver/rc.d

# Make sure script is run as root or sudo

if [ "$(whoami)" != "root" ]
then
	echo 
	echo "Error! Must run as root!"
	echo
	exit 0
fi


# This code is executed only if server is 
# started verbosely on foreground and the
# user presses Ctrl+C to terminate.
# It makes sure the server is shut down
# properly. (Same code as stop.sh)

int_trap()
{
	echo "Stopping Eye-Fi Server"

	${RCDPATH}/S99EyeFiServer.sh stop
	sleep 1

	result="$(sudo netstat -pln | grep 59278)"
	len=${#result}

	if [ ${len} -eq 0 ]
	then
		echo "Successfully stopped"
	else
		echo "Something still listening on port"
		echo "(Might be some other program)"
	fi
}


# This method is used to start server verbosely.
# It is placed here because used in different
# places.

start_verbose()
{
	trap int_trap INT # <-- TRAP for Ctrl+C
	echo "Starting Eye-Fi Server verbosely"
	${PYTHONPATH}/python ${DSTPATH}/bin/eyefiserver.py ${DSTPATH}/etc/eyefiserver.conf ${DSTPATH}/var/eyefiserver.log
}


# Check if there is another process sitting
# on port 59278. If yes, send SIGTERM until
# it is gone. In most cases, this process
# is python itself
# This feature is also the reason why script
# has to be run as root

echo -n "Checking if socket is unused... "

result="$(sudo netstat -pln | grep 59278)"
len=${#result}

if [ ${len} != 0 ]
then
	echo "error"
else
	echo "ok"
fi

while [ ${len} != 0 ]
do
	echo -n "- Trying to kill process..."
	pid="$(echo ${result} | grep -P -o '(?<=(LISTEN ))[0-9]*(?=(/python))')"   
 	echo ${pid}
	sudo kill -6 ${pid}
	sleep 1

	result="$(sudo netstat -pln | grep 59278)"
	len=${#result}

	if [ ${len} != 0 ]
	then
		echo "- Process still running"
	else
		echo "- Sucessfully terminated"
	fi
done

echo 


# Determine whether to start server verbosely on foreground
# or as a daemon. If argument -v is provided, script does 
# not ask. If not, user is asked what to do.
# Trap in start_verbose catches Ctrl+C from user and ensures
# the server is propperly shut down.

if [ "$1" == "-v" ]
then
	start_verbose
else

	echo -n "Run server in foreground verbosely? [Y/n]:"
	read verb

	if [ "${verb}" == "" ] || [ "${verb}" == "y" ] || [ "${verb}" == "Y" ]
	then
		start_verbose
	else
		echo "Starting Eye-Fi Server in background"
		${RCDPATH}/S99EyeFiServer.sh start
	fi
fi

