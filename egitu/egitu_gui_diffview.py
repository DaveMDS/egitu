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


from efl.elementary.entry import Entry, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED
from efl.elementary.icon import Icon
from efl.elementary.image import Image
from efl.elementary.list import List
from efl.elementary.panes import Panes
from efl.elementary.table import Table

from egitu_utils import options, theme_resource_get, format_date, GravatarPict, \
    EXPAND_BOTH, FILL_BOTH


class DiffViewer(Table):
    def __init__(self, parent, repo, commit=None):
        self.repo = repo
        self.commit = None

        Table.__init__(self, parent,  padding=(5,5))
        self.show()

        self.picture = GravatarPict(self)
        self.picture.show()
        self.pack(self.picture, 0, 0, 1, 1)

        self.entry = Entry(self, text="Unknown")
        # self.entry.line_wrap = ELM_WRAP_NONE
        self.entry.size_hint_weight = EXPAND_BOTH
        self.entry.size_hint_align = FILL_BOTH
        self.pack(self.entry, 1, 0, 1, 1)
        self.entry.show()

        panes = Panes(self, content_left_size = 0.3, horizontal=True,
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.pack(panes, 0, 1, 2, 1)
        panes.show()

        self.diff_list = List(self, size_hint_weight=EXPAND_BOTH,
                                    size_hint_align=FILL_BOTH)
        self.diff_list.callback_selected_add(self.change_selected_cb)
        panes.part_content_set("left", self.diff_list)

        self.diff_entry = Entry(self, editable=False, scrollable=True,
                    size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH,
                    line_wrap=ELM_WRAP_NONE)
        panes.part_content_set("right", self.diff_entry)

        if commit:
            self.commit_set(repo, commit)

    def commit_set(self, repo, commit):
        self.repo = repo
        self.commit = commit
        text = ''
        if commit.commit_date:
            date = format_date(commit.commit_date)
            text += '%s @ %s<br>' % (commit.author, date)
        if commit.title:
            text += '<b>%s</b><br>' % (commit.title)
        if commit.sha:
            text += '%s<br>' % (commit.sha)
        self.entry.text = text

        self.picture.email_set(commit.author_email)


        self.diff_list.clear()
        self.diff_entry.text = ''
        repo.request_changes(self.changes_done_cb, commit1=commit)

    def changes_done_cb(self, success, lines):
        for mod, name in lines:
            if mod in ('M', 'A', 'D'):
                icon_name = 'mod_{}.png'.format(mod.lower())
                icon = Icon(self, file=theme_resource_get(icon_name))
                it = self.diff_list.item_append(name, icon)
            else:
                it = self.diff_list.item_append('[{}] {}'.format(mod, name))
            it.data['change'] = mod, name
        self.diff_list.go()

    def change_selected_cb(self, li, item):
        mod, path = item.data['change']
        self.repo.request_diff(self.diff_done_cb, None,
                               commit1=self.commit, path=path)
        self.diff_entry.line_wrap = \
            ELM_WRAP_MIXED if options.diff_text_wrap else ELM_WRAP_NONE
        self.diff_entry.text = '<info>Loading diff, please wait...</info>'

    def diff_done_cb(self, lines):
        # TODO use a buffer instead of immutable string
        text = ''
        for line in lines:
            if line[0] == '+':
                tag = 'line_added'
            elif line[0] == '-':
                tag = 'line_removed'
            elif line[0] == ' ':
                tag = None
            else:
                tag = 'line_changed'

            if tag:
                text += '<{0}>{1}</{0}><br>'.format(tag, utf8_to_markup(line))
            else:
                text += '{0}<br>'.format(utf8_to_markup(line))

        self.diff_entry.text = \
            '<code><font={0} font_size={1}>{2}</font></code>' \
            .format(options.diff_font_face, options.diff_font_size, text)


