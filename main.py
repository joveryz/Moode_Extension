# -*- coding:UTF-8 -*-
from __future__ import unicode_literals
from PIL import ImageColor
from PIL import ImageFont
from PIL import ImageDraw
from PIL import Image
from luma.oled.device import ssd1351
from luma.core.render import canvas
from luma.core.interface.serial import spi
import OLED_Driver as OLED
import RPi.GPIO as GPIO
from subprocess import Popen, PIPE
import signal
import subprocess
import re
import socket
import datetime
import math
import time
import os
import sys
import importlib
importlib.reload(sys)


#--------------Global Vars---------------#
is_sigint_up = False
rotate_angle = 0
mpd_music_dir = "/var/lib/mpd/music/"
mpd_host = 'localhost'
mpd_port = 6600
mpd_bufsize = 8192
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
scroll_unit = 4
file_offset = 0
artist_offset = 0
album_offset = 0
audio_state = "Unknown"
audio_rate = "Unknown"
audio_time = "Unknown"
audio_elapsed = "Unknown"
audio_file = "Unknown"
audio_artist = "Unknown"
audio_album = "Unknown"
audio_title = "Unknown"
audio_timebar = 0
audio_device = 0

#--------------Utils---------------#


def getLANIP():
    cmd = "ip addr show eth0 | grep inet  | grep -v inet6 | awk '{print $2}' | cut -d '/' -f 1"
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output[:-1]


def sigint_handler(signum, frame):
    global is_sigint_up
    is_sigint_up = True


def getAudioDevice():
    global audio_device
    cmd = "aplay -l | grep -A 2 'USB' | grep 'Subdevices'"
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    output = re.split(':', str(output))[1]
    if re.split('/', output)[0].strip() == "1":
        audio_device = 1
    else:
        audio_device = 0


def sec2Time(sec):
    cur_time = datetime.timedelta(seconds=float(sec))
    time_details = re.split(':', str(cur_time))
    h = time_details[0]
    m = time_details[1]
    s = time_details[2]
    if h == "0":
        return m + ":" + s
    else:
        return h + ":" + m + ":" + s


def makeFont(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)


def drawText(draw, size, logo, text, color, align, x, y):
    logo_font = makeFont("fa5s.otf", size)
    text_font = makeFont("Deng.ttf", size)
    logo_width, char = logo_font.getsize(logo)
    text_width, char = text_font.getsize(text)
    total_width = logo_width + text_width
    left_align = x
    right_align = OLED.SSD1351_WIDTH - total_width
    center_align = right_align / 2
    if align == "center":
        draw.text((center_align, y), logo, fill=color, font=logo_font)
        draw.text((center_align + logo_width, y),
                  text, fill=color, font=text_font)
    elif align == "left":
        draw.text((left_align, y), logo, fill=color, font=logo_font)
        draw.text((left_align + logo_width, y),
                  text, fill=color, font=text_font)
    elif align == "right":
        draw.text((right_align, y), logo, fill=color, font=logo_font)
        draw.text((right_align + logo_width, y),
                  text, fill=color, font=text_font)


def drawDots(draw, index, total):
    regular_font = makeFont("fa5r.otf", 8)
    solid_font = makeFont("fa5s.otf", 8)
    dots_width, char = regular_font.getsize("\uf111 ")
    last_dot_width, shar = regular_font.getsize("\uf111")
    total_width = dots_width * (total - 1) + last_dot_width
    right_align = OLED.SSD1351_WIDTH - total_width
    center_align = right_align / 2
    for num in range(1, total + 1):
        if num == index:
            draw.text((center_align, 120), "\uf111",
                      fill="WHITE", font=solid_font)
            center_align += dots_width
        else:
            draw.text((center_align, 120), "\uf111",
                      fill="WHITE", font=regular_font)
            center_align += dots_width

#--------------MPD Library---------------#


def initMPD():
    soc.connect((mpd_host, mpd_port))
    soc.recv(mpd_bufsize)
    soc.send('commands\n')
    rcv = soc.recv(mpd_bufsize)


def sendMPDCommand(command):
    soc.send(command + "\n")
    rcv = soc.recv(mpd_bufsize)
    return rcv


def parseAudioRate(audio_str):
    audio_str = audio_str.replace("audio: ", "")
    audio_details = re.split(':', audio_str)
    audio_bit = audio_details[1] + "bit"
    audio_rate = audio_details[0]
    if audio_details[0] == '22050':
        audio_rate = '22.05k'
    elif audio_details[0] == '32000':
        audio_rate = '32k'
    elif audio_details[0] == '44100':
        audio_rate = '44.1k'
    elif audio_details[0] == '48000':
        audio_rate = '48k'
    elif audio_details[0] == '88200':
        audio_rate = '88.2k'
    elif audio_details[0] == '96000':
        audio_rate = '96k'
    elif audio_details[0] == '176400':
        audio_rate = '176.4k'
    elif audio_details[0] == '192000':
        audio_rate = '192k'
    elif audio_details[0] == '352800':
        audio_rate = '352.8k'
    elif audio_details[0] == '384000':
        audio_rate = '384k'
    elif audio_details[0] == '705600':
        audio_rate = '705.6k'
    elif audio_details[0] == '768000':
        audio_rate = '768k'
    else:
        audio_bit = ""
    if audio_bit == "":
        return audio_rate.upper()
    else:
        return audio_rate.upper() + "/" + audio_bit


def getDetails():
    song_list = sendMPDCommand("currentsong").splitlines()
    state_list = sendMPDCommand("status").splitlines()
    global audio_state, audio_rate, audio_time, audio_elapsed, audio_file, audio_artist, audio_album, audio_title, audio_timebar
    audio_artist = "Unknown"
    audio_album = "Unknown"
    audio_title = "Unknown"
    for line in range(0, len(state_list)):
        if state_list[line].startswith("state: "):
            audio_state = state_list[line].replace("state: ", "")
            if audio_state != "play":
                return
        elif state_list[line].startswith("audio: "):
            audio_rate = parseAudioRate(state_list[line])
        elif state_list[line].startswith("time: "):
            audio_time = state_list[line].split(":")[2]
            audio_elapsed = state_list[line].split(":")[1]
            audio_timebar = math.ceil(
                float(audio_elapsed) / float(audio_time) * OLED.SSD1351_WIDTH)
            audio_time = sec2Time(audio_time)
            audio_elapsed = sec2Time(audio_elapsed)
    for line in range(0, len(song_list)):
        if song_list[line].startswith("file: "):
            audio_file = song_list[line].replace("file: ", "")
            audio_file = audio_file.split("/")[-1]
        elif song_list[line].startswith("Artist: "):
            audio_artist = song_list[line].replace("Artist: ", "")
        elif song_list[line].startswith("Album: "):
            audio_album = song_list[line].replace("Album: ", "")
        elif song_list[line].startswith("Title: "):
            audio_title = song_list[line].replace("Title: ", "")

#-------------Display Functions---------------#


def dateScreen():
    image = Image.new("RGB", (OLED.SSD1351_WIDTH,
                              OLED.SSD1351_HEIGHT), "BLACK")
    draw = ImageDraw.Draw(image)
    cur_time = time.strftime("%H:%M:%S %a", time.localtime())
    cur_date = time.strftime("%Y-%m-%d", time.localtime())
    cur_ip = getLANIP()
    drawText(draw, 15, "", "moOde Audio", "WHITE", "center", 0, 5)
    drawText(draw, 20, "", cur_date, "WHITE", "center", 0, 30)
    drawText(draw, 20, "", cur_time, "WHITE", "center", 0, 51)
    drawText(draw, 15, "\uf6ff ", cur_ip, "WHITE", "left", 5, 80)
    drawText(draw, 15, "\uf83e ", "Goldenwave II", "WHITE", "left", 5, 96)
    drawDots(draw, 1, 3)
    OLED.Display_Image(image.rotate(rotate_angle))


def roonScreen():
    image = Image.new("RGB", (OLED.SSD1351_WIDTH,
                              OLED.SSD1351_HEIGHT), "BLACK")
    draw = ImageDraw.Draw(image)
    drawText(draw, 20, "", "Renderers", "WHITE", "center", 0, 18)
    drawText(draw, 20, "", "ROON/HQ/BLE", "WHITE", "center", 0, 42)
    drawText(draw, 15, "\uf6ff ", "192.168.50.200", "WHITE", "center", 0, 80)
    drawText(draw, 15, "\uf83e ", "Goldenwave II", "WHITE", "center", 0, 96)
    drawDots(draw, 3, 3)
    OLED.Display_Image(image.rotate(rotate_angle))


def moodeScreen():
    global audio_state, audio_rate, audio_time, audio_elapsed, audio_file, audio_artist, audio_album, audio_title, audio_timebar
    global file_offset, artist_offset, album_offset
    image = Image.new("RGB", (OLED.SSD1351_WIDTH,
                              OLED.SSD1351_HEIGHT), "BLACK")
    draw = ImageDraw.Draw(image)
    text_font_18 = makeFont("Deng.ttf", 18)
    text_font_20 = makeFont("Deng.ttf", 20)
    if text_font_20.getsize(audio_file)[0] > OLED.SSD1351_WIDTH:
        drawText(draw, 20, "", audio_file, "WHITE", "left", 0 - file_offset, 5)
        file_offset = file_offset + scroll_unit
        if file_offset + OLED.SSD1351_WIDTH - 20 > text_font_20.getsize(audio_file)[0]:
            file_offset = 0
    else:
        drawText(draw, 20, "", audio_file, "WHITE", "center", 0, 5)

    if text_font_18.getsize(audio_artist)[0] > OLED.SSD1351_WIDTH:
        drawText(draw, 18, "", audio_artist, "WHITE",
                 "left", 0 - artist_offset, 30)
        artist_offset = artist_offset + scroll_unit
        if artist_offset + OLED.SSD1351_WIDTH - 20 > text_font_18.getsize(audio_artist)[0]:
            artist_offset = 0
    else:
        drawText(draw, 18, "", audio_artist, "WHITE", "center", 0, 30)

    if text_font_18.getsize(audio_album)[0] > OLED.SSD1351_WIDTH:
        drawText(draw, 18, "", audio_album, "WHITE",
                 "left", 0 - album_offset, 50)
        album_offset = album_offset + scroll_unit
        if album_offset + OLED.SSD1351_WIDTH - 20 > text_font_18.getsize(audio_album)[0]:
            album_offset = 0
    else:
        drawText(draw, 18, "", audio_album, "WHITE", "center", 0, 50)
    drawText(draw, 16, "", audio_rate, "WHITE", "center", 0, 75)
    draw.rectangle([(0, 95), (audio_timebar, 100)],
                   fill="WHITE", outline="WHITE")
    draw.rectangle([(0, 95), (OLED.SSD1351_WIDTH - 1, 100)],
                   fill=None, outline="WHITE")
    drawText(draw, 16, "", audio_elapsed, "WHITE", "left", 0, 101)
    drawText(draw, 16, "", audio_time, "WHITE", "right", 0, 101)
    drawDots(draw, 2, 3)
    OLED.Display_Image(image.rotate(rotate_angle))


#----------------------MAIN-------------------------#
try:

    def main():
        OLED.Device_Init()
        initMPD()
        signal.signal(signal.SIGINT, sigint_handler)
        signal.signal(signal.SIGHUP, sigint_handler)
        signal.signal(signal.SIGTERM, sigint_handler)
        while True:
            getDetails()
            getAudioDevice()
            if audio_state == "play":
                moodeScreen()
            elif audio_device == 0:
                roonScreen()
            else:
                dateScreen()
            if is_sigint_up:
                OLED.Clear_Screen()
                GPIO.cleanup()
                exit(0)
            OLED.Delay(50)
    if __name__ == '__main__':
        main()
except Exception as e:
    print(e)
