#!/bin/bash

DSTPATH=/usr/local/eyefiserver
PYTHONPATH=/usr/bin
RCDPATH=/usr/local/eyefiserver/rc.d

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


