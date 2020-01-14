#!/bin/bash

#allow access to cdrom
chmod 644 /dev/sr0

#count with cdparanoia the tracks
tracks=$(cdparanoia -sQ |& grep -P "^\s+\d+\." | wc -l)
rm /var/lib/mpd/playlists/CDPlayer.m3u

#add each track to mpd playlist
for ((i=1; i<=$tracks; i++)); do
   echo cdda:///$i >> /var/lib/mpd/playlists/CDPlayer.m3u
done

