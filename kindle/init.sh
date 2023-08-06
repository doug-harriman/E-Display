# init.sh
# Initializes Kindle into image display mode.

# Key content from:
# https://github.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized/blob/master/Kindle/weatherscript.sh

# Disable back light
/bin/echo -n 0 > /sys/devices/system/fl_tps6116x/fl_tps6116x0/fl_intensity

# Disable screen saver
lipc-set-prop -i com.lab126.powerd preventScreenSaver 1

# Stop other Kindle services
stop framework
stop tmd  # transfer manager daemon
stop phd  # phone home daemon
stop webreader
stop cmd

# This bit copied from:
# https://github.com/DDRBoxman/kindle-weather/blob/48fc8984ebcbf3317aab5174889cee378a2bb26c/kindleweather.sh#L57C1-L62C17
trap "" SIGTERM
stop lab126_gui
# NOTE: Let the framework teardown finish, so we don't start before the black screen...
usleep 1250000
# And remove the trap like a ninja now!
trap - SIGTERM

# from: https://www.martinpham.com/2023/01/07/reviving-unused-kindle-ebooks/
stop x
stop otaupd
stop todo
stop archive
stop dynconfig
stop dpmd
stop appmgrd


