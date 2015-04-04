# tv-renamer

Batch file renamer in python2/3 for tv episodes.

Uses the Trakt api (**API token required**) to scan a directory of your choice for tv episodes.
Uses Python's built in string formatting to rename files.

Path scrubbing thanks to [Flexget](https://github.com/Flexget/Flexget).

Example:
```shell
$ python app.py -t '{show_title} {ep_season}x{ep_number} - {ep_title}.{ext}'
Sherlock - Is this the correct show? [Y/N] y
Renamed sherlock.s02e01.720p.mp4 -> Sherlock 2x01 - A Scandal in Belgravia.mp4
Renamed sherlock.s02e02.whatever.mkv -> Sherlock 2x02 - The Hounds of Baskerville.mkv
Renamed sherlock.s02e03.720p.x264.mkv -> Sherlock 2x03 - The Reichenbach Fall.mkv
```

## Todo:
* get logging in place
* handle errors better
* refactor some
