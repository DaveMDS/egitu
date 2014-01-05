#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of Egitu.
#
# Egitu is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# Egitu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Egitu.  If not, see <http://www.gnu.org/licenses/>.

import os
import hashlib
import pickle
import glob
from datetime import datetime
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home

from efl.evas import EVAS_HINT_EXPAND, EVAS_HINT_FILL
from efl.ecore import FileDownload
from efl.elementary.image import Image


EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5


script_path = os.path.dirname(__file__)
config_path = os.path.join(xdg_config_home, 'egitu')
config_file = os.path.join(config_path, 'config.pickle')
recent_file = os.path.join(config_path, 'recent.history')


class Options(object):
    """ Class to contain application settings """
    def __init__(self):
        self.theme_name = 'default'
        self.date_format = '%d %b %Y %H:%M'
        self.date_relative = True
        self.gravatar_default = 'identicon' # or: mm, identicon, monsterid, wavatar, retro
        self.show_message_in_dag = False
        self.show_remotes_in_dag = True
        self.diff_font_face = 'Sans'
        self.diff_font_size = 10

    def load(self):
        try:
            # load only attributes (not methods) from the instance saved to disk
            saved = pickle.load(open(config_file, 'rb'))
            for attr in dir(self):
                if attr[0] != '_' and not callable(getattr(self, attr)):
                    if hasattr(saved, attr):
                        setattr(self, attr, getattr(saved, attr))
        except:
            pass

    def save(self):
        # save this whole class instance to file
        with open(config_file, 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

options = Options()


def file_get_contents(path):
    try:
        with open(path) as f:
            return f.read()
    except:
        return None

def file_put_contents(path, contents):
    try:
        with open(path, 'w') as f:
            f.write(contents)
        return True
    except:
        return False
    
def theme_resource_get(fname):
    return os.path.join(script_path, 'themes', options.theme_name, fname)

def recent_history_get():
    c = file_get_contents(recent_file)
    return filter(None, c.split('\n')) if c else None

def recent_history_push(path):
    history = recent_history_get() or []
    if path in history:
        history.remove(path)
    history.insert(0, path)

    file_put_contents(recent_file, '\n'.join(history))

def format_date(d):
    if options.date_relative is False:
        return d.strftime(options.date_format)

    diff = datetime.now() - d
    s = diff.seconds
    if diff.days > 2 or diff.days < 0:
        return d.strftime(options.date_format)
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(int(diff.days))
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(int(s))
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{} minutes ago'.format(int(s/60))
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(int(s/3600))

class GravatarPict(Image):

    cache_folder = os.path.join(xdg_cache_home, 'gravatar')
    default_file = theme_resource_get('avatar.png')

    def __init__(self, parent, size=50):
        self.size_min = size

        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

        Image.__init__(self, parent)
        self.size_hint_min = self.size_min, self.size_min

    @staticmethod
    def clear_icon_cache():
        filelist = glob.glob(os.path.join(GravatarPict.cache_folder, '*.jpg'))
        for f in filelist:
            os.remove(f)
        
    def email_set(self, email):
        if not email:
            self.file = self.default_file
            return

        hash_key = hashlib.md5(email.encode('utf-8').lower()).hexdigest()

        # search in local cache
        local_path = os.path.join(self.cache_folder, hash_key + '.jpg')
        if os.path.exists(local_path):
            self.file = local_path
            return

        # or download from gravatar
        gravatar_url = "http://www.gravatar.com/avatar/%s?size=%d&d=%s" % \
                        (hash_key, self.size_min, options.gravatar_default)
        
        FileDownload(gravatar_url, local_path, self._download_done_cb, None)
        self.file = self.default_file

    def _download_done_cb(self, path, status):
        if status == 200:
            self.file = path
