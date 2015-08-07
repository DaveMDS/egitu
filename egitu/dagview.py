#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014-2015 Davide Andreoli <dave@gurumeditation.it>
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
import sys
from datetime import datetime

from efl.edje import Edje
from efl.elementary.button import Button
from efl.elementary.entry import Entry, ELM_WRAP_NONE
from efl.elementary.table import Table
from efl.elementary.layout import Layout

from egitu.utils import options, theme_file_get, format_date, \
    GravatarPict, EXPAND_BOTH, FILL_BOTH
from egitu.vcs import Commit



class CommitPopup(Table):
    def __init__(self, parent, repo, commit):
        self.repo = repo
        self.commit = commit

        Table.__init__(self, parent,  padding=(5,5))
        self.show()

        pic = GravatarPict(self)
        pic.email_set(commit.author_email)
        self.pack(pic, 0, 0, 1, 1)
        pic.show()

        text = u'<name>{}</name>  <b>{}</b>  {}<br><br>{}'.format(commit.sha[:9],
                commit.author, format_date(commit.commit_date), commit.title)
        en = Entry(self, text=text)
        en.line_wrap = ELM_WRAP_NONE
        en.size_hint_weight = EXPAND_BOTH
        en.size_hint_align = FILL_BOTH
        self.pack(en, 1, 0, 1, 1)
        en.show()


class DagGraph(Table):
    def __init__(self, parent, *args, **kargs):
        self.repo = None
        self.win = parent
        self.themef = theme_file_get()
        self.colors = [(0,100,0,100), (0,0,100,100), (100,0,0,100),
                      (100,100,0,100), (0,100,100,100), (100,0,100,100)]

        Table.__init__(self, parent, homogeneous=True, padding=(0,0))

    def populate(self, repo):
        self.repo = repo
        self._current_row = 0
        self._used_columns = set()
        self._open_connections = dict()
        self._open_connection_lines = list()
        self._first_commit = None
        self._last_date = None
        self._last_date_row = 1
        self._visible_commits = 0
        self._commits_to_load = 100  # TODO make configurable

        self.clear(True)

        # create the first fake commit (local changes)
        if not self.repo.status.is_clean:
            c = Commit()
            c.title = "Local changes"
            c.tags = ['Local changes']
            self.point_add(c, 1, 0)
            # self.connection_add(1, 1, 1, 2)
            self._current_row += 1
            self._first_commit = c

        self.repo.request_commits(self._populate_done_cb,
                                  self._populate_progress_cb,
                                  max_count=self._commits_to_load)

    def _find_a_free_column(self):
        # set is empty, add and return "1"
        if len(self._used_columns) == 0:
            self._used_columns.add(1)
            return 1

        # search the lowest not-present number (a hole)
        max_num = max(self._used_columns)
        for x in range(1, max_num):
            if not x in self._used_columns:
                self._used_columns.add(x)
                return x

        # or append and return a new number
        x = max_num + 1
        self._used_columns.add(x)
        return x

    def _populate_progress_cb(self, commit):
        if self._current_row == 0:
            self._first_commit = commit

        # 1. draw the connection if there are 'open-to' this one
        if commit.sha in self._open_connections:
            R = self._open_connections.pop(commit.sha)
            point_col = min([c[2] for c in R])
            for child_col, child_row, new_col in R:
                self.connection_add(child_col, child_row,
                                    point_col, self._current_row)
            # if is a fork we can release the columns
            if len(R) > 1:
                for c in R:
                    if c[2] != point_col:
                        self._used_columns.remove(c[2])
        else:
            # point need a new free column
            point_col = self._find_a_free_column()

        # 2. add an open_connection, one for each parent
        i = 0
        for parent in commit.parents:
            r = (point_col,
                 self._current_row,
                 self._find_a_free_column() if i > 0 else point_col)
            if parent in self._open_connections:
                self._open_connections[parent].append(r)
            else:
                self._open_connections[parent] = [r]
            i += 1

        # 3. draw the date on column 0 (if the day is changed)
        if self._last_date is None:
            self._last_date = commit.commit_date
            self._last_date_row = self._current_row

        d1, d2 = self._last_date, commit.commit_date
        if d1.month != d2.month or d1.day != d2.day or d1.year != d2.year:
            self.date_add(d1, self._last_date_row, self._current_row)
            self._last_date = commit.commit_date
            self._last_date_row = self._current_row

        # 4. add the commit point to the graph
        self.point_add(commit, point_col, self._current_row)
        self._visible_commits += 1
        self._current_row += 1

    def _populate_done_cb(self, success):
        # draw the last date piece
        if self._last_date:
            self.date_add(self._last_date, self._last_date_row,
                          self._current_row)

        # draw still-open connections lines (and clear the old ones)
        while self._open_connection_lines:
            l = self._open_connection_lines.pop()
            l.delete()
        for key in self._open_connections:
            for child_col, child_row, new_col in self._open_connections[key]:
                l = self.connection_add(child_col, child_row,
                                        child_col, self._current_row)
                self._open_connection_lines.append(l)

        # add the "show more" button if necessary
        if self._open_connections:
            bt = Button(self, text="Show more commits", size_hint_align=(0,0))
            bt.callback_clicked_add(self._show_more_clicked_cb)
            self.pack(bt, 0, self._current_row + 1, 10, 2)
            bt.show()

        # show the first commit in the diff view
        if self._first_commit is not None:
            self.win.show_commit(self._first_commit)
            self._first_commit = None

    def _show_more_clicked_cb(self, bt):
        bt.delete()
        self.repo.request_commits(self._populate_done_cb,
                                  self._populate_progress_cb,
                                  max_count=self._commits_to_load,
                                  skip=self._visible_commits)

    def date_add(self, date, from_row, to_row):
        ly = self.child_get(0, from_row)
        if ly is None:
            ly = Layout(self, file=(self.themef, 'egitu/graph/date'),
                        size_hint_align=FILL_BOTH)
        fmt = '%d %b' if to_row - from_row > 2 else '%d'
        ly.part_text_set('date.text', date.strftime(fmt))
        self.pack(ly, 0, from_row, 1, to_row - from_row)
        ly.show()

    def point_add(self, commit, col, row):
        p = Layout(self, file=(self.themef,'egitu/graph/item'))
        p.signal_callback_add("mouse,down,*", "base",
                              self.point_mouse_down_cb, commit)
        p.tooltip_content_cb_set(lambda o,tt:
                CommitPopup(self, self.repo, commit))

        if options.show_message_in_dag is True:
            l = Layout(self, file=(self.themef, 'egitu/graph/msg'))
            l.text_set('msg.text', commit.title)
            p.box_append('refs.box', l)
            l.show()

        for head in commit.heads:
            if head == 'HEAD':
                p.signal_emit('head,show', 'egitu')
            else:
                l = Layout(self, file=(self.themef, 'egitu/graph/ref'))
                l.text_set('ref.text', head)
                p.box_append('refs.box', l)
                l.show()

        if options.show_remotes_in_dag:
            for head in commit.remotes:
                l = Layout(self, file=(self.themef, 'egitu/graph/ref'))
                l.text_set('ref.text', head)
                p.box_append('refs.box', l)
                l.show()

        for tag in commit.tags:
            l = Layout(self, file=(self.themef, 'egitu/graph/tag'))
            l.text_set('tag.text', tag)
            p.box_append('refs.box', l)
            l.show()

        self.pack(p, col, row, 1, 1)
        p.show()

    def color_for_column(self, column):
        return self.colors[(column - 1) % len(self.colors)]

    def connection_add(self, col1, row1, col2, row2):
        # print ("CONNECTION", col1, row1, col2, row2)
        if col1 == col2:
            # a stright line
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert',
                    color=self.color_for_column(col1))
            self.pack(l, col1, row1, col2 - col1 + 1, row2 - row1 + 1)

        elif col1 > col2:
            # a "fork"
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert_fork',
                    color=self.color_for_column(col1))
            self.pack(l, col2, row1, col1 - col2 + 1, row2 - row1 + 1)
        else:
            # a "merge"
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert_merge',
                    color=self.color_for_column(col2))
            self.pack(l, col1, row1, col2 - col1 + 1, row2 - row1 + 1)

        l.lower()
        l.show()

        return l

    def point_mouse_down_cb(self, obj, signal, source, commit):
        self.win.show_commit(commit)
