#!/bin/bash

# Automatic WLAN-Access-Point setup script
# Copyright by Keysie, October 2015
#
# This script executes four steps prior to starting the access-
# point:
# 1) Stop the ubuntu network manager
# 2) Make sure wlan is not blocked by rfkill
# 3) Set up local IP address to 192.168.10.1
# 4) Start the dhcp server
#
# The the AP will be started. It runs until Ctrl+C is pressed. 
# After this, two commands clean up:
# 1) Stop dhcp again
# 2) Restart ubuntu network manager
#
# Each command's result is stored in a variable which is then
# evaluated to check if the command was successful or not.
 

red=`tput setaf 1`
green=`tput setaf 2`
reset=`tput sgr0`
ok="[${green}ok${reset}]"
error="[${red}error${reset}]"


# ==== result evaluation short ====
eval_short() 
{
	if [ "${#@}" -eq 0 ]
	then
		echo "${ok}"
	else
		echo "${error}"
		echo "${result}"
		exit
	fi
}

# ==== int trap: code to exec after Ctrl+C ====
int_trap() {
echo
echo -n "Stopping DHCP-Server... "
result="$(service isc-dhcp-server stop 2>&1)"
case ${result} in
"isc-dhcp-server stop/waiting")
	echo "${ok}"
	;;
"stop: Unknown instance: ")
	echo "[${green}already stopped${reset}]"
	;;
*)
	echo "${error}"
	echo "${result}"
esac

echo -n "Starting network manager... "
result="$(start network-manager 2>&1)"
case ${result} in
"start: Job is already running: network-manager")
	echo "[${green}already running${reset}]"
	;;
"network-manager start/running, process "[0-9]*)
	pid="$(echo ${result} | grep -P -o '(?<=(start/running, process ))[0-9]*(?=())')"
	echo "[${green}pid=${pid}${reset}]"
	;;
*)
	echo "${error}"
	echo "${result}"
	exit
esac
}

clear
echo "======== FOTOSPOT-AP SETUP =========\n"
echo -n "Stopping network manager... "
result="$(stop network-manager 2>&1 1>/dev/null)"
if [ "${#result}" -eq 0 ]
then
	echo "${ok}"
else
	if [ "${result}" = "stop: Unknown instance: " ]
	then
		echo "[${green}already stopped${reset}]"
	else
		echo "${error}"
		echo "${result}"
		return 1
	fi
fi

echo -n "Unblocking wlan interface... "
result="$(rfkill unblock wlan 2>&1)"
eval_short ${result}

echo -n "Setting ip to 192.168.10.1... "
result="$(ifconfig wlan0 192.168.10.1 2>&1)"
eval_short ${result}

echo -n "Starting DHCP-Server... "
result="$(service isc-dhcp-server start 2>&1)"
case ${result} in
"start: Job is already running: isc-dhcp-server")
	echo "[${green}already running${reset}]"
	;;
"isc-dhcp-server start/running, process "[0-9]*)
	pid="$(echo ${result} | grep -P -o '(?<=(start/running, process ))[0-9]*(?=())')"
	echo "[${green}pid=${pid}${reset}]"
	;;
*)
	echo "${error}"
	echo "${result}"
	exit
esac

echo "Starting Accesspoint..."

trap int_trap INT # This catches Ctrl+C and executes above method

hostapd /etc/hostapd/hostapd.conf
