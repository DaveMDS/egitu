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

from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
import time
from datetime import datetime

from efl.evas import Rectangle
from efl.edje import Edje
from efl.elementary.button import Button
from efl.elementary.entry import Entry, utf8_to_markup, ELM_WRAP_NONE
from efl.elementary.table import Table
from efl.elementary.layout import Layout
from efl.elementary.label import Label
from efl.elementary.genlist import Genlist, GenlistItemClass, ELM_LIST_COMPRESS

from egitu.utils import options, theme_file_get, format_date, \
    GravatarPict, EXPAND_BOTH, FILL_BOTH
from egitu.stash import StashDialog
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

        if commit.committer and commit.committer != commit.author:
            committed = '<name>Committed by:</name> <b>{}</b><br>'.format(
                        commit.committer)
        else:
            committed = ''
        text = '<name>{}</name>  <b>{}</b>  {}<br>{}<br>{}'.format(
                commit.sha[:9], commit.author, format_date(commit.commit_date), 
                committed, utf8_to_markup(commit.title))
        en = Entry(self, text=text, line_wrap=ELM_WRAP_NONE,
                   size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.pack(en, 1, 0, 1, 1)
        en.show()


class CommitDagData(object):
    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.obj = None # the edje swallowed in the genlist icon.swallow

class DagGraph(Genlist):
    def __init__(self, parent, app, *args, **kargs):
        self.app = app
        self.repo = None
        self.themef = theme_file_get()
        self.colors = [(0,100,0,100), (0,0,100,100), (100,0,0,100),
                      (100,100,0,100), (0,100,100,100), (100,0,100,100)]

        self._itc = GenlistItemClass(item_style='one_icon',
                                     content_get_func=self._gl_content_get)

        Genlist.__init__(self, parent, homogeneous=True, mode=ELM_LIST_COMPRESS,
                         size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.callback_realized_add(self._gl_item_realized)
        self.callback_selected_add(self._gl_item_selected)

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
        # self._commits_to_load = options.number_of_commits_to_load
        self._commits_to_load = 20000

        self.COLW = 20 # columns width (fixed)
        self.RAWH = 0  # raws height (fetched from genlist on first realize)

        self.clear()

        # create the first fake commit (local changes)
        if not self.repo.status.is_clean:
            c = Commit()
            c.special = 'local'
            c.tags = ['Local changes']
            c.title = None
            c.dag_data = CommitDagData(col=1, row=self._current_row)
            
            self._current_row += 1
            self._first_commit = c

            # self.point_add(c, 1, 0)
            self.item_append(self._itc, c)

        """
        # show stash items (if requested)
        if options.show_stash_in_dag:
            for si in self.repo.stash:
                c = Commit()
                c.special = 'stash'
                c.sha = si.sha
                c.tags = ['Stash']
                c.title = si.desc
                c.author = si.aut
                c.author_email = si.amail
                c.commit_date = datetime.fromtimestamp(si.ts)
                self.point_add(c, 1, self._current_row)
                self._current_row += 1
        """
        self._startup_num = self._visible_commits
        self._startup_time = time.time()
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

    def color_for_column(self, column):
        return self.colors[(column - 1) % len(self.colors)]

    def _populate_progress_cb(self, commit):
        if self._first_commit is None and commit.special is None:
            self._first_commit = commit

        # 1. draw the connection if there are 'open-to' this one
        if commit.sha in self._open_connections:
            # R = self._open_connections.pop(commit.sha)
            R = self._open_connections[commit.sha]
            point_col = min([c[2] for c in R])
            # for child_col, child_row, new_col in R:
                # self.connection_add(child_col, child_row,
                                    # point_col, self._current_row)
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
            r = (point_col, self._current_row,
                 self._find_a_free_column() if i > 0 else point_col)
            if parent in self._open_connections:
                self._open_connections[parent].append(r)
            else:
                self._open_connections[parent] = [r]
            i += 1

        
        # 3. draw the date on column 0 (if the day is changed)
        """
        if self._last_date is None:
            self._last_date = commit.commit_date
            self._last_date_row = self._current_row

        d1, d2 = self._last_date, commit.commit_date
        if d1.month != d2.month or d1.day != d2.day or d1.year != d2.year:
            self.date_add(d1, self._last_date_row, self._current_row)
            self._last_date = commit.commit_date
            self._last_date_row = self._current_row
        """

        # 4. add the commit point to the graph
        """
        self.point_add(commit, point_col, self._current_row)
        """
        commit.dag_data = CommitDagData(point_col, self._current_row)
        self.item_append(self._itc, commit)


        self._visible_commits += 1
        self._current_row += 1

    def _populate_done_cb(self, success):
        # draw the last date piece
        """
        if self._last_date:
            self.date_add(self._last_date, self._last_date_row,
                          self._current_row)
        """
        
        # draw still-open connections lines (and clear the old ones)
        """
        while self._open_connection_lines:
            l = self._open_connection_lines.pop()
            l.delete()
        for key in self._open_connections:
            for child_col, child_row, new_col in self._open_connections[key]:
                l = self.connection_add(child_col, child_row,
                                        child_col, self._current_row)
                self._open_connection_lines.append(l)
        """
        
        print('\n===============================================')
        print('=== DAG: %d revision loaded in %.3f seconds' % \
              (self._visible_commits - self._startup_num,
               time.time() - self._startup_time))
        print('===============================================\n')

        # show the first commit in the diff view
        # if self._first_commit is not None:
            # self.app.win.show_commit(self._first_commit)
            # self._first_commit = None


    def _gl_content_get(self, gl, part, commit):

        ly = Layout(gl, file=(self.themef,'egitu/graph/list_item'))
        commit.dag_data.obj = ly

        # padding rect (to place the point in the right column)
        size = commit.dag_data.col * self.COLW, 10
        r = Rectangle(ly.evas, color=(0,200,0,30),
                      size_hint_min=size, size_hint_max=size)
        ly.part_content_set('pad.swallow', r)

        # local refs
        for head in commit.heads:
            if head == 'HEAD':
                ly.signal_emit('head,show', 'egitu')
            else:
                ref = Layout(gl, file=(self.themef, 'egitu/graph/ref'))
                ref.text_set('ref.text', head)
                ly.box_append('refs.box', ref)
                ref.show()

        # remote refs
        if options.show_remotes_in_dag:
            for head in commit.remotes:
                ref = Layout(gl, file=(self.themef, 'egitu/graph/ref'))
                ref.text_set('ref.text', head)
                ly.box_append('refs.box', ref)
                ref.show()

        # tags
        for tag in commit.tags:
            ref = Layout(gl, file=(self.themef, 'egitu/graph/tag'))
            ref.text_set('tag.text', tag)
            ly.box_append('refs.box', ref)
            ref.show()

        # message
        if commit.title is not None:
            if options.show_message_in_dag and options.show_author_in_dag:
                text = '<b>{}:</b> {}'.format(utf8_to_markup(commit.author),
                                              utf8_to_markup(commit.title))
            elif options.show_author_in_dag:
                text = '<b>{}</b>'.format(utf8_to_markup(commit.author))
            elif options.show_message_in_dag:
                text = utf8_to_markup(commit.title)
            else:
                text = None

            if text:
                lb = Label(gl, text=text)
                ly.box_append('refs.box', lb)
                lb.show()

        return ly

    def _gl_item_realized(self, gl, item):
        commit = item.data

        # on first item realized fetch the items height
        if self.RAWH == 0:
            track = item.track_object
            self.ROWH = track.size[1]
            item.untrack()
        
        # setup item tooltip
        if commit.title is not None:
            item.tooltip_content_cb_set(lambda o, it, tt:
                                        CommitPopup(tt, self.repo, it.data))

        # draw connection lines
        if not commit.sha in self._open_connections:
            return

        ly = commit.dag_data.obj
        row2 = commit.dag_data.row
        col2 = commit.dag_data.col
        i = 0
        for col1, row1, col2__ in self._open_connections[commit.sha]:
            i += 1
            swallow_name = 'conn%d.swallow' % i
            if col1 == col2:
                # a stright line
                l = Edje(self.evas, file=self.themef,
                         group='egitu/graph/connection/vert',
                         color=self.color_for_column(col1))
                l.size = (col2 - col1 + 1 )*self.COLW, (row2 - row1 + 1)*self.ROWH
                l.size_hint_min = l.size
                l.show()
                # point.box_append('connections.box', l)
                ly.part_content_set(swallow_name, l)
            elif col1 > col2:
                # a "fork"
                l = Edje(self.evas, file=self.themef,
                         group='egitu/graph/connection/vert_fork',
                         color=self.color_for_column(col1))
                l.size = (col1 - col2 + 1 )*self.COLW, (row2 - row1 + 1)*self.ROWH
                l.size_hint_min = l.size
                l.show()
                ly.part_content_set(swallow_name+'.fork', l)
            else:
                # a "merge"
                l = Edje(self.evas, file=self.themef, 
                         group='egitu/graph/connection/vert_merge',
                         color=self.color_for_column(col2))
                l.size = (col2 - col1 + 1 )*self.COLW, (row2 - row1 + 1)*self.ROWH
                l.size_hint_min = l.size
                l.show()
                ly.part_content_set(swallow_name, l)

    def _gl_item_selected(self, gl, item):
        commit = item.data
        if commit.special == 'stash':
            for si in self.app.repo.stash:
                if si.sha == commit.sha:
                    StashDialog(self.parent, self.app, si)
                    return
        else:
            self.app.win.show_commit(commit)


class DagGraphTable(Table):
    def __init__(self, parent, app, *args, **kargs):
        self.app = app
        self.repo = None
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
        self._commits_to_load = options.number_of_commits_to_load

        self.clear(True)

        # create the first fake commit (local changes)
        if not self.repo.status.is_clean:
            c = Commit()
            c.special = 'local'
            c.tags = ['Local changes']
            c.title = None
            self.point_add(c, 1, 0)
            # self.connection_add(1, 1, 1, 2)
            self._current_row += 1
            self._first_commit = c

        # show stash items (if requested)
        if options.show_stash_in_dag:
            for si in self.repo.stash:
                c = Commit()
                c.special = 'stash'
                c.sha = si.sha
                c.tags = ['Stash']
                c.title = si.desc
                c.author = si.aut
                c.author_email = si.amail
                c.commit_date = datetime.fromtimestamp(si.ts)
                self.point_add(c, 1, self._current_row)
                self._current_row += 1

        self._startup_num = self._visible_commits
        self._startup_time = time.time()
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
        if self._first_commit is None and commit.special is None:
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

        print('\n===============================================')
        print('=== DAG: %d revision loaded in %.3f seconds' % \
              (self._visible_commits - self._startup_num,
               time.time() - self._startup_time))
        print('===============================================\n')

        # add the "show more" button if necessary
        if self._open_connections:
            bt = Button(self, text="Show more commits", size_hint_align=(0,0))
            bt.callback_clicked_add(self._show_more_clicked_cb)
            self.pack(bt, 0, self._current_row + 1, 10, 2)
            bt.show()

        # show the first commit in the diff view
        if self._first_commit is not None:
            self.app.win.show_commit(self._first_commit)
            self._first_commit = None

    def _show_more_clicked_cb(self, bt):
        bt.delete()
        self._startup_num = self._visible_commits
        self._startup_time = time.time()
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
        p.on_mouse_down_add(self.point_mouse_down_cb, commit)
        if commit.title is not None:
            p.tooltip_content_cb_set(lambda o,tt:
                                     CommitPopup(self, self.repo, commit))
        try: # added in pyefl 1.16
            from efl.elementary import ELM_TOOLTIP_ORIENT_RIGHT
            p.tooltip_orient = ELM_TOOLTIP_ORIENT_RIGHT
        except:
            pass

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
        
        if commit.title is not None:
            if options.show_message_in_dag and options.show_author_in_dag:
                text = '<b>{}:</b> {}'.format(utf8_to_markup(commit.author),
                                              utf8_to_markup(commit.title))
            elif options.show_author_in_dag:
                text = '<b>{}</b>'.format(utf8_to_markup(commit.author))
            elif options.show_message_in_dag:
                text = utf8_to_markup(commit.title)
            else:
                text = None
            
            if text:
                l = Layout(self, file=(self.themef, 'egitu/graph/msg'))
                l.text_set('msg.text', text)
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

    def point_mouse_down_cb(self, obj, event, commit):
        if commit.special == 'stash':
            for si in self.app.repo.stash:
                if si.sha == commit.sha:
                    StashDialog(self.parent, self.app, si)
                    return
        else:
            self.app.win.show_commit(commit)
