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
from efl.elementary.box import Box
from efl.elementary.table import Table
from efl.elementary.layout import Layout
from efl.elementary.label import Label
from efl.elementary.genlist import Genlist, GenlistItemClass, ELM_LIST_COMPRESS

from egitu.utils import options, theme_file_get, format_date, \
    GravatarPict, EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ
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
        self.childs = list()  # all the childrens (Commit instance)
        self.date_span = 0 # if >0 then a date item is required

        self.icon_obj = None
        self.used_swallows = 0
        self.rezzed = False
        self.fixed_childs = dict() # 'child Commit': line_obj


class DagGraph(Box):
    def __init__(self, parent, app):
        Box.__init__(self, parent)

        self.genlist = DagGraphList(self, app)
        self.pack_end(self.genlist)
        self.genlist.show()

        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        self.pack_end(hbox)
        hbox.show()

        self.label = Label(self, size_hint_expand=EXPAND_BOTH,
                           size_hint_align=(0.0,0.5))
        hbox.pack_end(self.label)
        self.label.show()

        self.show()

    def populate(self, *args):
        self.genlist.populate(*args)

    def info_label_set(self, text):
        self.label.text = '  ' + text


class DagGraphList(Genlist):
    def __init__(self, parent, app, *args, **kargs):
        self.app = app
        self.repo = None
        self.themef = theme_file_get()
        self.colors = [(0,100,0,100), (0,0,100,100), (100,0,0,100),
                      (100,100,0,100), (0,100,100,100), (100,0,100,100)]

        self._itc = GenlistItemClass(item_style='egitu_commit',
                                     text_get_func=self._gl_text_get,
                                     content_get_func=self._gl_content_get)

        Genlist.__init__(self, parent, homogeneous=True, mode=ELM_LIST_COMPRESS,
                         size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.callback_realized_add(self._gl_item_realized)
        self.callback_unrealized_add(self._gl_item_unrealized)
        self.callback_selected_add(self._gl_item_selected)

    def commit_append(self, commit, col):
        commit.dag_data = CommitDagData(col, self._current_row)
        self._current_row += 1
        self._COMMITS[commit.sha] = commit
        return self.item_append(self._itc, commit)

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

    def _color_for_column(self, column):
        return self.colors[(column - 1) % len(self.colors)]

    def populate(self, repo):
        self.repo = repo
        self._current_row = 0
        self._used_columns = set()
        self._open_connections = dict()  # 'sha':[child1_col, child2_col, child3_col, ...]
        self._open_childs = dict()       # 'sha':[child1, child2, child3, ...]
        self._last_date_commit = None    # last commit that changed the date
        self._head_found = False

        self._COMMITS = dict()
        self._fix_idler = None

        self.COLW = 20 # columns width (fixed)
        self.ROWH = 0  # raws height (fetched from genlist on first realize)

        self.parent.info_label_set('Reading repository...')
        self.clear()

        # create the first fake commit (local changes)
        if not self.repo.status.is_clean:
            c = Commit()
            c.special = 'local'
            c.tags = ['Local changes']
            self.commit_append(c, 1).selected = True
            self._head_found = True

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
                self.commit_append(c, 1)

        self._startup_time = time.time()
        self.repo.request_commits(self._populate_done_cb,
                                  self._populate_progress_cb,
                                  max_count=999999)

    def _populate_progress_cb(self, commit):

        # 1. find the column to use
        if commit.sha in self._open_connections:
            childs_cols = self._open_connections.pop(commit.sha)
            point_col = min(childs_cols)
            # if child was a fork we can release the columns
            if len(childs_cols) > 1:
                for col in childs_cols:
                    if col != point_col:
                        self._used_columns.remove(col)
            # no parents, release the column
            if len(commit.parents) < 1:
                self._used_columns.remove(point_col)
        else:
            # point need a new free column
            point_col = self._find_a_free_column()

        # 2. add an open_connection, one for each parent
        for i, parent in enumerate(commit.parents):
            parent_col = point_col if i == 0 else self._find_a_free_column()
            if parent in self._open_connections:
                self._open_connections[parent].append(parent_col)
            else:
                self._open_connections[parent] = [parent_col]

            # also remember this commit for later childrends population
            if parent in self._open_childs:
                self._open_childs[parent].append(commit)
            else:
                self._open_childs[parent] = [commit]

        # 3. store date span information (if the day is changed)
        if self._last_date_commit is None:
            self._last_date_commit = commit
        else:
            d1, d2 = self._last_date_commit.commit_date, commit.commit_date
            if d1.month != d2.month or d1.day != d2.day or d1.year != d2.year:
                self._last_date_commit.dag_data.date_span = \
                    self._current_row - self._last_date_commit.dag_data.row
                self._last_date_commit = commit

        # 4. add the commit to the graph
        # NOTE: this will create DagData and increment _current_row
        item = self.commit_append(commit, point_col)

        # 5. store all the childrens of this commit
        if commit.sha in self._open_childs:
            commit.dag_data.childs = self._open_childs.pop(commit.sha)

        if not self._head_found and 'HEAD' in commit.heads:
            item.selected = True
            item.show()

    def _populate_done_cb(self, success):
        # store the last date information
        if self._last_date_commit:
            self._last_date_commit.dag_data.date_span = \
                self._current_row - self._last_date_commit.dag_data.row

        # update the status bar
        self.parent.info_label_set('%d revisions loaded in %.2f seconds' % (
                        self._current_row, time.time() - self._startup_time))

    def _gl_text_get(self, gl, part, commit):
        if options.show_author_in_dag and part == 'egitu.text.author':
            return commit.author
        elif options.show_message_in_dag and part == 'egitu.text.title':
            return commit.title

    def _gl_content_get(self, gl, part, commit):
        if part == 'egitu.swallow.pad':
            # padding rect (to place the point in the right column)
            size = commit.dag_data.col * self.COLW, 10
            r = Rectangle(gl.evas, color=(0,0,0,0),
                          size_hint_min=size, size_hint_max=size)
            return r

        elif part == 'egitu.swallow.icon':
            # the icon object (+ swallows for the connection lines)
            icon = Layout(gl, file=(self.themef,'egitu/graph/icon'))
            commit.dag_data.icon_obj = icon
            if 'HEAD' in commit.heads:
                icon.signal_emit('head,show', 'egitu')
            return icon

        elif part == 'egitu.swallow.refs':
            box = Box(gl, horizontal=True)
            # local refs
            for head in commit.heads:
                ref = Layout(gl, file=(self.themef, 'egitu/graph/ref'))
                ref.text_set('ref.text', head)
                box.pack_end(ref)
                ref.show()
            # remote refs
            if options.show_remotes_in_dag:
                for head in commit.remotes:
                    ref = Layout(gl, file=(self.themef, 'egitu/graph/ref'))
                    ref.text_set('ref.text', head)
                    box.pack_end(ref)
                    ref.show()
            # tags
            for tag in commit.tags:
                ref = Layout(gl, file=(self.themef, 'egitu/graph/tag'))
                ref.text_set('tag.text', tag)
                box.pack_end(ref)
                ref.show()
            return box

        elif commit.dag_data.date_span and part == 'egitu.swallow.date':
            dt = Edje(gl.evas, file=self.themef, group='egitu/graph/date')
            dt.size_hint_min = self.COLW, commit.dag_data.date_span * self.ROWH
            fmt = '%d %b' if commit.dag_data.date_span > 2 else '%d'
            dt.part_text_set('date.text', commit.commit_date.strftime(fmt))
            return dt

    def _gl_item_unrealized(self, gl, item):
        dag_data = item.data.dag_data
        dag_data.icon_obj = None
        dag_data.used_swallows = 0
        dag_data.rezzed = False
        dag_data.fixed_childs.clear()

        # draw (upwards) connections from realized parents to this one
        commit = item.data
        for parent_sha in commit.parents:
            if parent_sha in self._COMMITS:
                parent = self._COMMITS[parent_sha]
                if parent.dag_data.rezzed:
                    line = self.draw_connection(parent, commit)
                    parent.dag_data.fixed_childs[commit] = line
                    # TODO factorize this creations !!!
            else:
                pass # parent not yet created ???

    def _gl_item_realized(self, gl, item):
        commit = item.data
        commit.dag_data.rezzed = True

        # on first item realized fetch the items height
        if self.ROWH == 0:
            track = item.track_object
            if track:
                self.ROWH = track.size[1]
                item.untrack()

        # setup item tooltip
        if commit.title is not None:
            item.tooltip_content_cb_set(lambda o, it, tt:
                                        CommitPopup(tt, self.repo, it.data))

        # draw connection lines with parents (downwards)
        for parent_sha in commit.parents:
            if parent_sha in self._COMMITS:
                parent = self._COMMITS[parent_sha]
                self.draw_connection(commit, parent)

                # remove (upwards) lines from parents
                for fixed in list(parent.dag_data.fixed_childs):
                    if fixed == commit:
                        line = parent.dag_data.fixed_childs[fixed]
                        line.delete()
                        del parent.dag_data.fixed_childs[fixed]
                        # TODO update swallows count and factorize !!!
            else:
                pass # parent not yet created ???

        # draw connections to unrealized childs (upwards)
        for child in commit.dag_data.childs:
            if not child.dag_data.rezzed:
                line = self.draw_connection(commit, child)
                commit.dag_data.fixed_childs[child] = line
                # TODO factorize this creations !!!

    def draw_connection(self, commit1, commit2):
        col1, row1 = commit1.dag_data.col, commit1.dag_data.row
        col2, row2 = commit2.dag_data.col, commit2.dag_data.row
        swal_num = commit1.dag_data.used_swallows
        ly = commit1.dag_data.icon_obj

        if col1 == col2:
            # a stright line
            line = Edje(self.evas, file=self.themef,
                        group='egitu/graph/connection/vert',
                        color=self._color_for_column(col1))
            if row1 < row2:
                ly.signal_emit('connection,stright,down,%d' % swal_num, 'egitu')
            else:
                ly.signal_emit('connection,stright,up,%d' % swal_num, 'egitu')
        elif col1 > col2:
            if row1 < row2:
                # a "fork" (down)
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/vert_fork',
                            color=self._color_for_column(col1))
            
                ly.signal_emit('connection,fork,down,%d' % swal_num, 'egitu')
            else:
                # a "merge" (up)
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/vert_merge',
                            color=self._color_for_column(col1))
                ly.signal_emit('connection,merge,up,%d' % swal_num, 'egitu')
        else: # col1 < col2
            if row1 < row2:
                # a "merge" (down)
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/vert_merge',
                            color=self._color_for_column(col2))
                ly.signal_emit('connection,merge,down,%d' % swal_num, 'egitu')
            else:
                # a "fork" (up)
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/vert_fork',
                            color=self._color_for_column(col2))
                ly.signal_emit('connection,fork,up,%d' % swal_num, 'egitu')

        
        line.size = (abs(col2 - col1) + 1) * self.COLW, \
                    (abs(row2 - row1) + 1) * self.ROWH
        line.size_hint_min = line.size
        try:
            ly.content_set('conn.swallow.%d' % swal_num, line)
        except:
            print(swal_num)
        ly.edje.message_signal_process()
        # ly.edje.calc_force()
        commit1.dag_data.used_swallows += 1

        return line

    def _gl_item_selected(self, gl, item):
        commit = item.data
        if commit.special == 'stash':
            for si in self.app.repo.stash:
                if si.sha == commit.sha:
                    StashDialog(self.parent, self.app, si)
                    return
        else:
            self.app.win.show_commit(commit)

"""
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
"""
