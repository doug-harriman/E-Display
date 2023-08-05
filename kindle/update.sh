# update.sh
# General idea: use the Kindle for display only, everything else is handled by the server.
# 1. Kindle wakes up
# 2. Kindle posts its state to the server
# 3. Kindle grabs the latest image from the server (which now include Kindle state)
# 4. Kindle displays the image
# 5. Kindle reads the next wakeup delay from the server
# 6. Kindle goes to sleep

# Server
HOST=http://192.168.0.120:8000

# Device name
DEVICE='home-office'
# DEVICE='kitchen'

# Make sure we're in the right place
cd /mnt/us/digital-display

while true; do

    # Display power state
    echo `powerd_test -s | grep Powerd`

    # Remove the last image
    rm -f image.png

    # Wait a bit.  
    # Seeing issue where not getting image periodically.
    # This wasn't happeneing when there were delays previously.
    sleep 3

    # Put system into a higher power state.
    # Having issues with gasgauge-info not updating when in powersave mode.
    # Governor options: conservative ondemand userspace powersave performance
    #echo "performance" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    #sleep 1

    # Post Kindle's state data
    # gasgauge-info doesn't seem to update when in powersave mode.
    BATTERY_SOC=`gasgauge-info -s`
    TEMPERATURE=`gasgauge-info -k | cut -d " " -f1`

    TEMPERATURE=`cat /sys/devices/system/yoshi_battery/yoshi_battery0/battery_temperature`
    BATTERY_SOC=`cat /sys/devices/system/yoshi_battery/yoshi_battery0/battery_capacity`

    JSON='{"device":"'$DEVICE'","temp":"'$TEMPERATURE'","battery":"'$BATTERY_SOC'"}'
    echo $JSON
    curl -g -X POST ${HOST}/state -H "Content-Type: application/json" -H "Accept: application/json"  -d ${JSON}
    sleep 1

    # Grab the latest file
    curl -m 180 ${HOST}/image/${DEVICE} -o image.png

    # Clear display.  Call twice eliminate shadows of previous image.
    eips -c
    eips -c

    # Test if the file is valid, if not, error message
    if [ ! -f image.png ]; then
        echo "Error: image.png not found"
        eips 16 16 "Error: image.png not found"
    else

        # Display new image
        eips -fg image.png
    fi

    # Pause to let it refresh.
    sleep 2

    # Read next wakeup delay from the server
    DELAY=`curl -m 180  -X GET ${HOST}/delay/${DEVICE} -H 'accept: text/plain'`
    echo "Wakeup delay: $DELAY sec"

    # Test if $DELAY is zero, if so, exit.
    if [ "${DELAY}" = "0" ]; then
        echo "Exiting"
        eips -c
        eips 16 16 "Program Exited"
        exit 0
    fi

    # If we're on charger power do a sleep loop.
    CHARGING=$(powerd_test -s | grep -o "Charging: Yes")
    if [ "$CHARGING" == "Charging: Yes" ]; then

        echo "Device Charging"
        eips -c 
        eips -c 

        # Loop while charging.
        while [ "$CHARGING" == "Charging: Yes" ]
        do
            # Only return to update once off charger.
            eips 16 16 "Charging"
            sleep 5

            # Check charger status again.
            CHARGING=$(powerd_test -s | grep -o "Charging: Yes")
        done

        echo "Charger Removed"

    else
        # Schedule next wakeup
        # '-s' arg is delay in seconds until wake.
        # 15 min * 60 sec = 900
        rtcwake -d /dev/rtc1 -m no -s $DELAY

        # Make sure we're in low power mode.
        echo "powersave" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

        # Go to sleep
        echo "mem" > /sys/power/state

        # Wait a few sec upon waking up.
        echo "Waking up"
        sleep 3
        echo "Ready to go"
    fi

done