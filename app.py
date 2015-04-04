# TODO:
# * implement logging module
# * Better error handling
from __future__ import print_function
import argparse
import json

# import our worker class
from renamer import Renamer

# Python 2-3 compatability
try:
    input = raw_input
except NameError:
    pass

# Argparse stuff
description = '''Rename TV show episodes.'''

epilog = ('The following values will be read from configuration file'
          ' if not provided:')
epilog += '''
    extensions      a list of file extensions
    interactive     boolean
    padding         boolean
    scrub           string. "windows", "mac" or "linux"
    template        string
    api_key         string

Available variables for custom templates:
    show_title      show title
    ep_title        episode title
    ep_season       season number
    ep_number       episode number
    ep_year         airdate year (YYYY)
    ep_month        airdate month (MM)
    ep_day          airdate day (DD)
    ext             extension
'''

# Argparse setup
parser = argparse.ArgumentParser(description=description,
                                 formatter_class=argparse.
                                 RawDescriptionHelpFormatter,
                                 epilog=epilog)

parser.add_argument('show', nargs='?',
                    help='specify a show. Will try to auto detect if omitted.')

parser.add_argument('-d', '--dry-run', action='store_true',
                    help='do a trial run with no renaming.')

parser.add_argument('-a', '--add-extension', action='append',
                    metavar='EXTENSION', dest='extension_list',
                    help='append extension to the default list.'
                    ' (mkv, mp4, wmv, m4v, avi, xvid, mpg)')

parser.add_argument('-e', '--extension', action='append', dest='extensions',
                    help='pass custom extension(s).')

parser.add_argument('-i', '--interactive', action='store_true',
                    help='Approve all files before renaming.')

parser.add_argument('-p', '--padding', action='store_true',
                    help='save season with double digits (01x01 - Pilot). '
                    'This option does not affect episodes of season 10 '
                    'and above.')

parser.add_argument('-s', '--scrub', help='clean filename to work on all '
                    'filesystems. Can be windows (strictest), mac (some '
                    'restrictions) or linux (no restrictions). This will '
                    'be automatically detected if not specified.',
                    metavar='OS')

parser.add_argument('-t', '--template', help='pass a custom naming template '
                    'Defaults to {ep_season}x{ep_number} - {ep_title}.{ext}.')

parser.add_argument('-v', '--verbosity', action='count', default=0,
                    help='verbosity, from less to more. -v, -vv, -vvv.')

parser.add_argument('-c', '--config', metavar='FILE', dest='custom_config',
                    help='Custom config file. Defaults to ./config.json.')

parser.add_argument('--api-key', dest='api_key', help='Trakt API key.')

args = parser.parse_args()

# Don't care about IOError below if config hasn't been explicitly set
if args.custom_config:
    args.config = args.custom_config
else:
    args.config = 'config.json'

config_keys = [
    'extensions',
    'interactive',
    'padding',
    'scrub',
    'template',
    'api_key'
]
config = {}
try:
    with open(args.config, 'r') as config_file:
        for key, value in json.load(config_file).items():
            if key in config_keys:
                config[key] = value
except IOError:
    if args.custom_config:
        exit('Config file "{0}"" does not exist'.format(args.config))
except ValueError:
    exit('Invalid JSON in "{0}"'.format(args.config))

# Command line input overwrites config values
for key, value in vars(args).items():
    if value is not None or key not in config:
        config[key] = value

# Verify that user template is valid
if config['template']:
    try:
        config['template'].format(show_title='', ep_title='', ep_season='',
                                  ep_number='', ep_year='', ep_month='',
                                  ep_day='', ext='')
    except KeyError:
        exit('Invalid template')

# A custom extension overrides the append-to-default
if config['extensions']:
    extensions = config['extensions']
else:
    extensions = config['extension_list']

renamer = Renamer(config['api_key'], extensions=extensions,
                  template=config['template'], padding=config['padding'],
                  dry_run=config['dry_run'], verbosity=config['verbosity'],
                  interactive=config['interactive'], pathscrub=config['scrub'])

shows = None
renamer.scanDir()
files = renamer.files
if not files:
    exit('No files found with matching extension')
if config['show']:
    shows = renamer.findShow(config['show'])
else:
    i = 0
    show = None
    while not show and i < 3 and i < len(files):
        show = renamer.parseShowName(files[i])
        i += 1
    if show:
        shows = renamer.findShow(show)

if not shows:
    exit('No show found')

choice1 = None
choice2 = None

while choice1 != 'y' and choice1 != 'n':
    choice1 = input('{0} - Is this the correct show? [Y/N] '.format(
                    shows[0]['title'])).lower()

if choice1 == 'y':
    show = shows[0]
else:
    while choice2 is None and choice2 != 'n':
        print()
        for i, show in enumerate(shows):
            print('[{0}] - {1}'.format(i, show['title']))
        print()
        choice2 = input('Is any of these shows correct? [num/N] '.format(
                        shows[0]['title'])).lower()
        if choice2 == 'n':
            exit('Try to rerun this script and pass SHOW manually')
        try:
            choice2 = int(choice2)
            shows[choice2]
        except ValueError:
            choice2 = None
        except IndexError:
            choice2 = None
    show = shows[choice2]

renamer.show_title = show['title']
errors = []

for file in files:
    new_file = None
    ep = renamer.parseEpisode(file)
    ep_season = int(ep['season'])
    ep_number = int(ep['number'])
    try:
        renamer.seasons[ep_season]
    except KeyError:
        renamer.downloadSeasonInformation(show['id'], ep_season)
    try:
        new_file = renamer.formatEpisode(file, ep)
    except KeyError:
        errors.append(file)
        if not config['dry_run']:
            print('No episode information for {0}'.format(file))
            choice3 = input('Continue? [y/N] ').lower()
            if choice3 != 'y':
                exit()

    message = '{0} -> {1}'.format(file, new_file)
    if config['dry_run']:
        print('[DRY RUN] {0}'.format(message))
    elif config['interactive']:
        choice4 = input('Rename {0} to {1}? [y/N] '.format(file, new_file))
        if choice4 == 'y':
            renamer.renameEpisode(file, new_file)
    else:
        renamer.renameEpisode(file, new_file)
        print('Renamed {0}'.format(message))

if errors:
    print()
    print('Finished with errors')
    for file in errors:
        print('No episode information for {0}'.format(file))
