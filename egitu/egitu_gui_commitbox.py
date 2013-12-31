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

from efl.elementary.entry import Entry
from efl.elementary.image import Image
from efl.elementary.table import Table
from efl.elementary.frame import Frame

from egitu_utils import theme_resource_get, format_date, GravatarPict, \
    EXPAND_BOTH, FILL_BOTH


def LOG(text):
    print(text)
    # pass


class CommitInfoBox(Frame):
    def __init__(self, parent, repo, commit = None, short_sha=False, show_diff=False):
        self.repo = repo
        self.short_sha = short_sha
        self.show_diff = show_diff
        self.commit = None

        Frame.__init__(self, parent, style='pad_small')

        self.content = tb = Table(self, padding=(5,5))
        tb.show()

        self.picture = GravatarPict(self)
        self.picture.size_hint_align = 0.0, 0.0
        self.picture.show()
        tb.pack(self.picture, 0, 0, 1, 1)
        
        self.entry = Entry(self, text="Unknown")
        self.entry.size_hint_weight = EXPAND_BOTH
        self.entry.size_hint_align = FILL_BOTH
        self.entry.show()
        tb.pack(self.entry, 1, 0, 1, 1)

        if show_diff is True:
            self.diff = Entry(self, editable=False, scrollable=True,
                size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
            self.diff.part_text_set('guide', 'click to show diff')
            self.diff.callback_clicked_add(self.diff_show_cb)
            self.diff.show()
            tb.pack(self.diff, 0, 1, 2, 1)

        if commit:
            self.commit_set(commit)

    def diff_show_cb(self, en):
        def _diff_done_cb():
            pass
        def _diff_line_cb(line):
            # TODO COLOR !!!
            self.diff.entry_append(line + '<br>')

        en.text = ''
        self.repo.request_diff(_diff_done_cb, _diff_line_cb, commit1=self.commit)


    def commit_set(self, commit):
        self.commit = commit
        text = ''
        if commit.commit_date:
            date = format_date(commit.commit_date)
            text += '%s @ %s<br>' % (commit.author, date)
        if commit.title:
            text += '<b>%s</b><br>' % (commit.title)
        if commit.sha:
            text += '%s<br>' % (commit.sha[:7] if self.short_sha else commit.sha)
        self.entry.text = text

        self.picture.email_set(commit.author_email)
        if self.show_diff:
            self.diff.text = ''
        

