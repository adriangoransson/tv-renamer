import os
import re
import datetime

import requests

from flexget import pathscrub, platform_replaces

# defaults
EXTENSION_LIST = ['mkv', 'mp4', 'wmv', 'm4v', 'avi', 'xvid', 'mpg']
TEMPLATE = '{ep_season}x{ep_number} - {ep_title}.{ext}'
EP_REGEXES = [
    (r'(?P<season>\d{1,2})x(?P<episode>\d{1,2}) ?[&-]? ?'
        r'(?P<double_ep>\d{1,2})?'),
    (r'[Ss](?:eason)? ?(?P<season>\d{1,2}) ?[Ee](?:pisode)? '
        r'?(?P<episode>\d{1,2}) ?[&-]? ?(?P<double_ep>\d{1,2})?')
]

TRAKT_BASE_URL = 'https://api.trakt.tv'


class Renamer(object):
    def __init__(self, TRAKT_API_KEY, extensions=EXTENSION_LIST,
                 template=TEMPLATE, padding=False, dry_run=False,
                 verbosity=False, interactive=False, pathscrub=None):

        if extensions is None:
            extensions = EXTENSION_LIST
        self.extensions = extensions

        if template is None:
            template = TEMPLATE
        self.template = template

        self.padding = padding
        self.dry_run = dry_run
        self.verbosity = verbosity
        self.interactive = interactive
        if pathscrub and pathscrub in platform_replaces:
            self.pathscrub = pathscrub
        else:
            self.pathscrub = None

        if TRAKT_API_KEY is None:
            raise Exception('Missing Trakt API token.')
        else:
            self.SEARCH_URL = '{0}/search/shows.json/{1}'\
                .format(TRAKT_BASE_URL, TRAKT_API_KEY)
            self.SHOW_URL = '{0}/show/season.json/{1}/'.format(TRAKT_BASE_URL,
                                                               TRAKT_API_KEY)

        self.ep_patterns = [re.compile(regex) for regex in EP_REGEXES]
        self.seasons = {}

    def findShow(self, show):
        params = {
            'query': show,
            'limit': 5
        }
        r = requests.get(self.SEARCH_URL, params=params)

        results = []

        for show in r.json():
            results.append({
                           'id': show['tvdb_id'],
                           'title': show['title']
                           })

        return results

    def getExtension(self, file):
        delimiter = file.rfind('.')
        return file[delimiter+1:]

    def filterFiles(self, file):
        if self.getExtension(file) not in self.extensions:
            return False
        return file[0] != '.'

    def parseEpisode(self, file):
        ext = self.getExtension(file)

        for pattern in self.ep_patterns:
            ep_info = re.search(pattern, file)
            # Match
            if ep_info is not None:
                break

        if ep_info is None:
            return None

        episode_number = ep_info.group('episode').zfill(2)
        double_episode = ep_info.group('double_ep')

        ep = {
            'season': ep_info.group('season'),
            'number': episode_number,
            'double_number': None,
            'extension': ext
        }

        # Double episode
        if double_episode:
            double_episode = double_episode.zfill(2)
            ep['double_number'] = '{0}-{1}'.format(episode_number,
                                                   double_episode)

        if self.padding:
            ep['season'] = ep['season'].zfill(2)
        else:
            ep['season'] = int(ep['season'])

        return ep

    def downloadSeasonInformation(self, show_id, season_number):
        season = {}
        r = requests.get('{0}/{1}/{2}'.format(self.SHOW_URL, show_id,
                         season_number))

        for ep in r.json():
            date = datetime.datetime.fromtimestamp(ep['first_aired'])
            year = date.strftime('%Y')
            month = date.strftime('%m')
            day = date.strftime('%d')
            season[ep['episode']] = {
                'title': ep['title'],
                'year': year,
                'month': month,
                'day': day
            }
        self.seasons[season_number] = season

    def renameEpisode(self, file, new_file):
        os.rename(file, new_file)

    def formatEpisode(self, file, ep):
        season = self.seasons[int(ep['season'])]
        ep_info = season[int(ep['number'])]
        if ep['double_number']:
            ep_number = '{0}-{1}'.format(ep['number'], ep['double_number'])
            ep_title = '{0} and {1}'.format(ep_info['title'],
                                            season[int(ep['double_number'])]
                                            ['title'])
        else:
            ep_number = ep['number']
            ep_title = ep_info['title']
        episode_name = self.template.format(show_title=self.show_title,
                                            ep_title=ep_title,
                                            ep_season=ep['season'],
                                            ep_number=ep_number,
                                            ep_year=ep_info['year'],
                                            ep_month=ep_info['month'],
                                            ep_day=ep_info['day'],
                                            ext=ep['extension'])

        episode_path = pathscrub(episode_name, os=self.pathscrub)

        return episode_path

    def parseShowName(self, file):
        for pattern in self.ep_patterns:
            ep_match = re.search(pattern, file)
            # Match
            if ep_match:
                break
        if not ep_match:
            return None
        show = file[:ep_match.start()]
        return show.replace('.', ' ')

    def scanDir(self, extensions=None):
        if not extensions:
            extensions = self.extensions

        directory = os.listdir('.')
        self.files = list(filter(self.filterFiles, directory))
