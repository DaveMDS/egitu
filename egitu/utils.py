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

from __future__ import absolute_import

import os
import hashlib
import pickle
import glob
from datetime import datetime
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home

from efl.evas import EVAS_HINT_EXPAND, EVAS_HINT_FILL
from efl.ecore import FileDownload, Exe
from efl.elementary.photo import Photo
from efl.elementary.popup import Popup
from efl.elementary.button import Button
from efl.elementary.entry import Entry, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED


EXPAND_BOTH = EVAS_HINT_EXPAND, EVAS_HINT_EXPAND
EXPAND_HORIZ = EVAS_HINT_EXPAND, 0.0
EXPAND_VERT = 0.0, EVAS_HINT_EXPAND
FILL_BOTH = EVAS_HINT_FILL, EVAS_HINT_FILL
FILL_HORIZ = EVAS_HINT_FILL, 0.5
FILL_VERT = 0.5, EVAS_HINT_FILL


script_path = os.path.dirname(__file__)
config_path = os.path.join(xdg_config_home, 'egitu')
config_file = os.path.join(config_path, 'config.pickle')
recent_file = os.path.join(config_path, 'recent.history')
install_prefix = script_path[0:script_path.find('/lib/python')]
data_path = os.path.join(install_prefix, 'share', 'egitu')

HOMEPAGE = 'https://github.com/davemds/egitu'

AUTHORS = """
<br>
<align=center>

<hilight>Davide Andreoli (davemds)</hilight><br>
dave@gurumeditation.it<br><br>

</align>
"""

INFO = """
<align=center>
<hilight>Egitu</hilight><br>
A Git user interface written in Python-EFL<br>
<br>
<br>
<hilight>Features</hilight><br>
Draw the <b>DAG</b> of the repo<br>
View the <b>diff</b> of each revision<br>
Edit repository <b>description</b><br>
Switch <b>branch</b><br>
<b>Stage/unstage</b> files<br>
<b>Commit</b> staged changes<br>
<b>Revert</b> commits<br>
<b>Discard</b> not committed changes<br>
Cool <b>Gravatar</b> integration<br>
<br>
<br>
<hilight>Shortcuts</hilight><br>
Ctrl+r or F5  refresh the repo<br>
Ctrl+o  open a new repository<br>
Ctrl+q  quit egitu<br>
</align>
"""

LICENSE = """
<align=center>
<hilight>
GNU GENERAL PUBLIC LICENSE<br>
Version 3, 29 June 2007<br><br>
</hilight>

This program is free software: you can redistribute it and/or modify 
it under the terms of the GNU General Public License as published by 
the Free Software Foundation, either version 3 of the License, or 
(at your option) any later version.<br><br>

This program is distributed in the hope that it will be useful, 
but WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
GNU General Public License for more details.<br><br>

You should have received a copy of the GNU General Public License 
along with this program. If not, see<br>
<link><a href=http://www.gnu.org/licenses>http://www.gnu.org/licenses/</a></link>
</align>
"""


class Options(object):
    """ Class to contain application settings """
    def __init__(self):
        self.theme_name = 'default'
        self.date_format = '%d %b %Y %H:%M'
        self.date_relative = True
        self.gravatar_default = 'identicon' # or: mm, identicon, monsterid, wavatar, retro
        self.show_message_in_dag = True
        self.show_remotes_in_dag = True
        self.diff_font_face = 'Mono'
        self.diff_font_size = 10
        self.diff_text_wrap = False

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


def xdg_open(url_or_file):
    Exe('xdg-open "%s"' % url_or_file)

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

def theme_file_get():
    return os.path.join(data_path, 'themes', options.theme_name + '.edj')

def theme_resource_get(fname):
    return os.path.join(data_path, 'themes', options.theme_name, fname)

def recent_history_get():
    c = file_get_contents(recent_file)
    return [l for l in c.split('\n') if l.strip()] if c else None

def recent_history_push(path):
    history = recent_history_get() or []
    if path in history:
        history.remove(path)
    history.insert(0, path)

    file_put_contents(recent_file, '\n'.join(history))

def format_date(d):
    if d is None:
        return ''
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


class GravatarPict(Photo):

    cache_folder = os.path.join(xdg_cache_home, 'gravatar')
    default_file = theme_resource_get('avatar.png')
    jobs = []

    def __init__(self, parent, size=60):
        self.size_min = size

        if not os.path.exists(self.cache_folder):
            os.makedirs(self.cache_folder)

        Photo.__init__(self, parent, style="shadow",
                       size_hint_min=(size,size))

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
        local_path = os.path.join(self.cache_folder, hash_key + '.jpg')

        # downloading yet ?
        if local_path in self.jobs:
            self.file = self.default_file
            return

        # search in local cache
        if os.path.exists(local_path):
            self.file = local_path
            return

        # or download from gravatar
        gravatar_url = "http://www.gravatar.com/avatar/%s?size=%d&d=%s" % \
                        (hash_key, self.size_min, options.gravatar_default)

        # local_path += '.part'
        FileDownload(gravatar_url, local_path, self._download_done_cb, None)
        self.jobs.append(local_path)
        self.file = self.default_file

    def _download_done_cb(self, path, status):
        self.jobs.remove(path)
        if not self.is_deleted() and status == 200:
            self.file = path


class DiffedEntry(Entry):
    """ An entry with highlighted diff content """
    def __init__(self, parent):
        wrap = ELM_WRAP_MIXED if options.diff_text_wrap else ELM_WRAP_NONE
        Entry.__init__(self, parent,
                       scrollable=True, editable=False, line_wrap=wrap,
                       text="<info>Loading diff, please wait...</info>",
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)

    def lines_set(self, lines):
        markup = ''
        from_fname = to_fname = None

        for line in lines:
            if from_fname and to_fname:
                if from_fname == '/dev/null':
                    action = 'A'
                elif to_fname == '/dev/null':
                    action = 'D'
                else:
                    action = 'M'
                markup += '<br><subtitle>' + action + ' ' + to_fname + '</subtitle><br>'
                from_fname = to_fname = None

            if line.startswith(('diff', 'index', 'new')):
                pass
            elif line.startswith('---'):
                from_fname = line[4:]
            elif line.startswith('+++'):
                to_fname = line[4:]
            elif line.startswith('@@'):
                markup += '<hilight>'+utf8_to_markup(line)+'</hilight><br>'
            elif line[0] == '+':
                markup += '<line_added>'+utf8_to_markup(line)+'</line_added><br>'
            elif line[0] == '-':
                markup += '<line_removed>'+utf8_to_markup(line)+'</line_removed><br>'
            else:
                markup += utf8_to_markup(line)+'<br>'

        if markup.startswith('<br>'): # remove the first "<br>"
            markup = markup[4:]
        self.text = u'<code><font={0} font_size={1}>{2}</font></code>'.format(
                      options.diff_font_face, options.diff_font_size, markup)


class ErrorPopup(Popup):
    def __init__(self, parent, title, msg):
        Popup.__init__(self, parent)
        self.part_text_set('title,text', title)
        self.part_text_set('default', '<align=left>'+msg+'</align>')

        b = Button(self, text='Close')
        b.callback_clicked_add(lambda b: self.delete())
        b.show()

        self.part_content_set('button1', b)
        self.show()


class ConfirmPupup(Popup):
    def __init__(self, parent, title=None, msg=None, ok_cb=None):
        Popup.__init__(self, parent)
        self.part_text_set('title,text', title or 'Are you sure?')
        self.part_text_set('default', msg or 'Please confirm')

        b = Button(self, text='Cancel')
        b.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', b)
        b.show()
        
        b = Button(self, text='Ok')
        b.callback_clicked_add(lambda b: ok_cb())
        self.part_content_set('button2', b)
        b.show()

        self.show()


class KeyBindings(object):
    """ A simple class to manage Shortcuts in elm applications

    Used like this:
    
    binds = KeyBindings(elm_window, verbose=True)
    binds.bind_add(('F5', 'Control+r'), my_callback)
    
    def my_callback(src, key, event):
        print("Shortcut pressed: %s" % key)
    
    """

    def __init__(self, win, verbose=False):
        """Initialize the KeyBinding class.
        
        Args:
            win (ElmObject): the elm object to use as base for connecting
                events, usually your main window object.
            verbose (bool): If True then all unhandled key combination will
                be printed out.
        
        """
        self._binds = {}
        self.verbose = verbose
        win.elm_event_callback_add(self._elm_events_cb)

    def bind_add(self, keys, cb, *args, **kargs):
        """Add a new Shortcut -> Callback combination.
        
        Args:
            keys (string or strings sequence): The keys that will trigger the 
                shortcut, examples: 's', 'Control+s', 'Control+Shift+s',
                'Control+Shift+Alt+s', 'F5', etc...
                Can be a single string or a sequence of strings to bind the
                same callback to multiple keys.
            cb (callable): the function to call when the shortcut keys will be
                pressed. Signature: cb(src, key, event, *args, **kargs) -> bool
                The callback should return True if it has consumed the event,
                False otherwise.
        Note:
            Any other positional or keywords arguments will be passed back in
            the callback

        """
        if callable(cb):
            if isinstance(keys, (list, tuple)):
                for key in keys:
                    self._binds[key] = (cb, args, kargs) 
            else:
                self._binds[keys] = (cb, args, kargs) 
        else:
            raise TypeError('cb must be callable')

    def _elm_events_cb(self, win, src, event_type, event):
        from efl.evas import EVAS_CALLBACK_KEY_DOWN, EVAS_EVENT_FLAG_ON_HOLD

        if not event_type == EVAS_CALLBACK_KEY_DOWN:
            return False

        key = ''
        for mod in ('Control', 'Shift', 'Alt'):
            if event.modifier_is_set(mod):
                key += mod + '+'
        key += event.keyname

        if key in self._binds:
            cb, args, kargs = self._binds[key]
            if cb(src, key, event, *args, **kargs) == True:
                event.event_flags = event.event_flags | EVAS_EVENT_FLAG_ON_HOLD
        elif self.verbose:
            print('Unhandled key: ' + key)

        return True
