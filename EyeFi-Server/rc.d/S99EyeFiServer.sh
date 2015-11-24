#!/bin/sh
#
# Startup script for eyefiserver.py
#
# Stop myself if running
PIDFILE=/var/run/eyefiserver.pid
DSTPATH=/usr/local/eyefiserver
PYTHONPATH=/usr/bin

#
start() {
nohup ${PYTHONPATH}/python ${DSTPATH}/bin/eyefiserver.py ${DSTPATH}/etc/eyefiserver.conf ${DSTPATH}/var/eyefiserver.log > /dev/null 2>&1 &
 # write pidfile
 echo $! > $PIDFILE
 echo "EyeFiServer started"
}
#
stop() {
 [ -f ${PIDFILE} ] && kill `cat ${PIDFILE}`
 # remove pidfile
 rm -f $PIDFILE 
 echo "EyeFiServer stopped"
}
#
case "$1" in
       start)
               start
       ;;
       stop)
               stop
       ;;
       restart)
               stop
               sleep 1
               start
       ;;
       *)
               echo "Usage: $0 (start|stop|restart)"
               exit 1
       ;;
esac
# End
