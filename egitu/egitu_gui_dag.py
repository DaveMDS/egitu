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
import sys
from datetime import datetime

from efl import elementary
from efl.edje import Edje
from efl.elementary.table import Table
from efl.elementary.frame import Frame
from efl.elementary.layout import Layout

from egitu_utils import options, theme_resource_get, FILL_BOTH
from egitu_gui_commitbox import CommitInfoBox
from egitu_vcs import Commit


class DagGraph(Table):
    def __init__(self, parent, repo, *args, **kargs):
        self.win = parent
        self.repo = repo
        self.themef = theme_resource_get('main.edj')
        # self.points = []
        # self.lines = []
        self._cols = [(), (100,0,0,100), (0,100,0,100), (0,0,100,100),
                          (100,0,0,100), (0,100,0,100), (0,0,100,100)]
        
        Table.__init__(self, parent, homogeneous=False, padding=(0,0))

    def populate(self):
        self._col = self._row = 1
        self._open_connections = {}
        self._first_commit = None

        # first col for the date (TODO)
        from efl.evas import Line, Rectangle
        l = Rectangle(self.evas, color=(0,0,0,100))
        l.size_hint_min = 20, 20
        l.size_hint_align = FILL_BOTH
        self.pack(l, 0, 0, 1, 100)
        l.show()

        # first row for something else (branch names?) (TODO)
        # l = Rectangle(self.evas, color=(0,0,0,100))
        # l.size_hint_min = 20, 20
        # l.size_hint_align = FILL_BOTH
        # self.pack(l, 1, 0, 10, 1)
        # l.show()

        # create the first fake commit (local changes)
        if not self.repo.status.is_clean:
            c = Commit()
            c.title = "Local changes"
            self.point_add(c, self._col, self._row)
            # self.connection_add(1, 1, 1, 2)
            self._row += 1
            self._col -= 1
            self._first_commit = c

        self.repo.request_commits(self._populate_done_cb, self._populate_prog_cb, 100)

    def _populate_prog_cb(self, commit):
        if self._row == 1:
            self._first_commit = commit

        # 1. draw the connection if there are 'open-to' this one
        if commit.sha in self._open_connections:
            R = self._open_connections.pop(commit.sha)
            min_col = min([c[2] for c in R])
            self._col = min_col
            for child_col, child_row, new_col in R:
                self.connection_add(child_col, child_row, self._col, self._row)
        else:
            self._col += 1

        # 2. add an open_connection, one for each parent
        i = 0
        for parent in commit.parents:
            r = (self._col, self._row, self._col + i)
            if parent in self._open_connections:
                self._open_connections[parent].append(r)
            else:
                self._open_connections[parent] = [r]
            i += 1

        # 3. add the commit point
        self.point_add(commit, self._col, self._row)
        self._row += 1

    def _populate_done_cb(self):
        if self._first_commit is not None:
            self.win.show_commit(self._first_commit)

    def update(self):
        self.clear(True)
        self.populate()

    def point_add(self, commit, col, row):
        p = Edje(self.evas, file=self.themef, group='egitu/graph/item',
                 size_hint_align=FILL_BOTH, size_hint_min = (20,20))
        p.signal_callback_add("mouse,in", "base", self.point_mouse_in_cb, commit)
        p.signal_callback_add("mouse,out", "base", self.point_mouse_out_cb, commit)
        p.signal_callback_add("mouse,down,*", "base", self.point_mouse_down_cb, commit)
        p.show()

        if options.show_message_in_dag is True:
            p.part_text_set('label.text', commit.title)
            p.signal_emit('label,show', 'egitu')

        for head in commit.heads:
            if head == 'HEAD':
                p.signal_emit('head,show', 'egitu')
            else:
                l = Layout(self, file=(self.themef, 'egitu/graph/ref'))
                l.part_text_set('ref.text', head)
                l.show()
                p.part_box_append('refs.box', l)
                
        for tag in commit.tags:
            l = Layout(self, file=(self.themef, 'egitu/graph/tag'))
            l.part_text_set('tag.text', tag)
            l.show()
            p.part_box_append('refs.box', l)

        self.pack(p, col, row, 1, 1)

    def connection_add(self, col1, row1, col2, row2):
        # print ("CONNECTION", col1, row1, col2, row2)
        if col1 == col2:
            # a stright line
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert', color=self._cols[col1])
            self.pack(l, col1, row1, col2 - col1 + 1, row2 - row1 + 1)
            
        elif col1 > col2:
            # a "fork"
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert_fork', color=self._cols[col2])
            self.pack(l, col2, row1, col1 - col2 + 1, row2 - row1 + 1)
        else:
            # a "merge"
            l = Edje(self.evas, file=self.themef, size_hint_align=FILL_BOTH,
                    group='egitu/graph/connection/vert_merge', color=self._cols[col2])
            self.pack(l, col1, row1, col2 - col1 + 1, row2 - row1 + 1)

        l.lower()
        l.show()

    def point_mouse_in_cb(self, obj, signal, source, commit):
        if not 'popup_obj' in obj.data:
            obj.data['popup_obj'] = o = CommitInfoBox(self, self.repo, commit, short_sha=True)
            x, y = self.evas.pointer_canvas_xy_get()
            o.pos = x + 10, y + 30
            o.size = 300, 30
            o.show()

    def point_mouse_out_cb(self, obj, signal, source, commit):
        if 'popup_obj' in obj.data:
            obj.data['popup_obj'].delete()
            del obj.data['popup_obj']

    def point_mouse_down_cb(self, obj, signal, source, commit):
        self.win.show_commit(commit)
        print(commit)
