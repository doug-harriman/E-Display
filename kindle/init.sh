# init.sh
# Initializes Kindle into image display mode.

# Key content from:
# https://github.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized/blob/master/Kindle/weatherscript.sh

# Disable back light
/bin/echo -n 0 > /sys/devices/system/fl_tps6116x/fl_tps6116x0/fl_intensity

# Disable screen saver
lipc-set-prop -i com.lab126.powerd preventScreenSaver 1

# Stop other Kindle services
export PATH=${PATH}:/sbin
initctl -q stop framework
initctl -q stop tmd  # transfer manager daemon
initctl -q stop phd  # phone home daemon
initctl -q stop webreader
initctl -q stop cmd
# initctl stop volumd # manages device mounting.  May want to leave alone.
initctl -q stop lipc-wait-event
initclt -q stop lab126_gui

# Unverified
# from: https://www.martinpham.com/2023/01/07/reviving-unused-kindle-ebooks/
initclt -q stop x
initclt -q stop otaupd
initclt -q stop todo
initclt -q stop mcsd
initclt -q stop archive
initclt -q stop dynconfig
initclt -q stop dpmd
initclt -q stop appmgrd
initclt -q stop stackdumpd


