# Kindle Setup for E-Display 

## Overview

The intent of the Kindle setup is to:

* Display an image pulled from the server so that the Kindle software is as simple as possible.  All updates to the image generation can be performed on the server.
* Put the Kindle to sleep between image updates so that the battery lasts as long as possible.  Note that the server returns the time to sleep to the Kindle, so the Kindle can be put to sleep for a variable amount of time depending on day of week and time of day.  If things are working properly, you should be able to to get several weeks of runtime between charges.

The Kindle setup consists of:

1. Performing a jailbreak of the Kindle so we can install our own software.
1. Shutting down all unneeded Kindle services.
1. Installing the software.
1. Running the software.

## Kindle Device

For the initial installation, the software is running on 2x Paper White Kindles.  

You can determine the model of your Kindle by:

> :information_source: [Kindle devices by serial number](https://wiki.mobileread.com/wiki/Kindle_Serial_Numbers)

### Kindle Paperwhite 1

* Model: [5th Generation](https://www.androidauthority.com/which-kindle-model-do-i-have-1073996/#:~:text=PW2-,Kindle%20Paperwhite%201,-(2012)) (EY21 / PW)
* Serial number: B024 1604 3103 0B46
* WiFi MAC: F0:4F:7C:50:AA:DC
* Original FW Version: 5.6.1.1 (build 2689890035)
* Screen: 1024x758 at 300 PPI, 8-bit grayscale
    * Resolution per `eips -i` run on Kindle.

### Kindle Software of Interest

The Kindle comes with some very useful software pre-installed.  The following are some of the commands I found useful.

* [eips](https://wiki.mobileread.com/wiki/Eips) - Writes images to screen.
    * This is used by the scripts to display the downloaded images.
* [Power State Info](https://www.mobileread.com/forums/showthread.php?t=221497)
* `gasgauge-info`
    * `-c` - State of charge in percent.
    * `-l` - Battery discharge current with units (mA)
        * Some measurements I made:
            * Backlight on: `-95`
            * Backlight off: `-32`
    * `-k` - Battery temperature with units (Fahrenheit)
    * `-m` - Battery capacity with units (mAh)

## Jailbreak

[Mobileread](https://www.mobileread.com/) has excellent resources for jailbreaking Kindles.  The instructions below are a summary of the steps I took to jailbreak the devices.d  All software required can be found on the Mobileread site.

* The PW devices (PW1) at 5.6.1.1 [must be downgraded to jailbreak](https://www.mobileread.com/forums/showthread.php?t=264432).  Instructions copied here:
    * Download earlier update file from Amazon: [Kindle Paperwhite 1 Update 5.3.3](
https://s3.amazonaws.com/G7G_Firmwar...ndle_5.3.3.bin)
    * Disable wifi on your Paperwhite 1 (airplane mode).
    * Connect your Kindle Paperwhite 1 to your computer (DO NOT DISCONNECT UNTIL LAST STEP!).
    * Copy the bin file you downloaded in step 1 to root folder of PW1.
        NOTE: Failed for me the first time, so copied into root and documents folder.
    * Wait at least 2 minutes after copy has completed.
    * Push and hold power button until your PW1 restarts.  This should take 10-15 seconds.
    * Wait until the PW1 has installed the upgrade (really a downgrade).  The screen will display "Your Kindle sofware is updating", with some additional text.
    * Now you can disconnect from your computer.
    * Verify FW revision from Settings -> Device Info menu.
* Once downgraded, they can be broken out with the [5.0.x to 5.4.4.2 jailbreak](https://www.mobileread.com/forums/showthread.php?t=186645).
* Be sure to restart the device.

## Software Setup

### ssh Access

* Install KUAL.
* Install KUAL Mr Installer
* Enabling SSH
    * Install USB-Networking by:
        * Copying install bin into`/mrpackages`
        * Run KUAL
        * Select KUAL -> Install MR Packages.  Install will happen, then device will reboot.
        * After reboot, USBNetwork menu will be available in KUAL.
    * Copy your public key (~/.ssh/id_rsa.pub) into a "<root>/usbnet/etc/authorized_keys".  You likely need to create the file.
    * Eject the Kindle and disconnect USB.
    * Exit airplane mode to connect to WiFi network.
        * Note: Due to update, will need to reconnect to WiFi network.
    * Configure USB-Neworking
        * Toggle USBNetwork to enable networking.
        * Enable SSH over WiFi
        * USBNetwork Status shoud say `SSH is up (usbms, wifi only)`
    * Use your router DHCP info to determine the address of the new devices.
    * ssh as root the the IP address of the device.
    * On my network, WiFi IP is:
        * 192.168.0.80 for 'home-office'
        * 192.168.0.3 for 'kitchen'

### Install E-Display Scripts

* Edit the `update.sh` script. 
    * Set `HOST` variable to the proper server IP.
    * Set `DEVICE` variable to the name for this device.
         * This string will be displayed on the device, and is used to determine which image to return.
* Copy files to the Kindle:
    * ssh in and create directory: `/mnt/us/digital-display` (or whatever you want to name it).
    * Copy `init.sh` and `update.sh` from the `kindle` directory in tis project to the `digital-display` directory on the device.
        * You can copy with `scp` or use the Kinkle in USB mass storage mode to copy directly from your PC.
    * Copy `tmux` from the `kindle` directory to the `digital-display` directory on the Kindle.
* Run the files
    * Run `init.sh`
    * Run `tmux`
    * Inside of `tmux`, run `update.sh`
    * You can now disconnect and the script will continue to run.

#### References
* [Prevent Kindle from phoning home](https://blitiri.com.ar/p/other/kindle/#id7)
* [Project](https://github.com/snowtechblog/avakindle) where a guy used the RTC to wake and update.
* [Turn off backlight](https://www.mobileread.com/forums/showthread.php?t=200266&highlight=wake+sleep+command)
* [Power management](https://www.mobileread.com/forums/showthread.php?t=268453&highlight=wake+sleep+command)
* [More on sleep](https://www.mobileread.com/forums/showthread.php?t=220810&highlight=wake+sleep+command)

### Run the Scripts

* Run `init.sh` to set up the environment.
* Run `tmux` to start a tmux session.
* Run `update.sh` to start the update script.
* Disconnect.
