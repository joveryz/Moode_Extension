# Moode_Extension
Extensions for Moode, including OLED display, IR control and CD playback.
For now, it is running in a RPi4B with Moode 6.4.0.

# Demo
![](./doc/Demo.jpg)

# Hardware
- Raspberry Pi 4B
- [Argon One Case](https://www.argon40.com/catalog/product/view/id/52/s/argon-one-raspberry-pi-4-case) for RPi4B
- [1.5inch RGB OLED Module](http://www.waveshare.net/wiki/1.5inch_RGB_OLED_Module), made by WAVESHARE
- VS1838B Infrared Receiver Module
- Apple Remote A1294
- CD Drive with usb port

# Wire Connection

## IR Reciver Module
The Argon One Case reserved a place for VS1838B, just connect it.

## OLED Module
![](./doc/OLED.jpg)

|OLED Pin|GPIO Pin|
|-|-|
|VCC|3V3|
|GND|GND|
|DIN|MOSI|
|CLK|SCK|
|CS|CE0|
|DS|24|
|RST|25|

# Installation
## Requirements
- Follow the [instructions](http://www.waveshare.net/wiki/1.5inch_RGB_OLED_Module) to ensure that the OLED module works properly.

- Follow the [instructions](https://stackoverflow.com/questions/57437261/setup-ir-remote-control-using-lirc-for-the-raspberry-pi-rpi) to ensure that the IR reciver module works properly. If you use the default position for IR in Argon One, the gpio pin shoule be set as 23.

- Use `sudo apt-get install eject cdparanoia cdde inotify-tools` to install packages required by CD playback.

## OLED Display
```
cd /home/pi
git clone https://github.com/TongboZhang/Moode_Extension.git
cd Moode_Extension
sudo chmod 755 src/OLEDDisplay/main.py
sudo cp src/OLEDDisplay/oledd.service /etc/systemd/system/

# Test OLED display
sudo systemctl start oledd
# Wait 10 seconds to start the service
sudo systemctl status oledd

# Make OLED service automatically start on boot
sudo systemctl enable oledd
```

## Remote Control
```
sudo cp src/RemoteControl/apple-silver-A1294-lircd.conf /etc/lirc/lircd.conf.d/
sudo cp src/RemoteControl/irexec.lircrc /etc/lirc

# Test LIRC service
sudo systemctl start lircd
sudo systemctl status lircd

# Test IREXEC service
sudo systemctl start irexec
sudo systemctl status irexec

# Make LIRC and IREXEC service automatically start on boot
sudo systemctl enable lircd
sudo systemctl enable irexec
```

## CD Playback

```
sudo chmod 755 geneCD.sh
sudo cp src/CDPlayback/99-srX_change.rules /etc/udev/rules.d/
```

When you insert a CD, it will generate a playlist named CDPlayer automatically.
![](./doc/CDPlayer.jpg)
