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
from efl.elementary.genlist import Genlist, GenlistItemClass, \
    ELM_LIST_COMPRESS, ELM_GENLIST_ITEM_GROUP

from egitu.utils import options, theme_file_get, format_date, \
    GravatarPict, CommitTooltip, ErrorPopup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ
from egitu.stash import StashDialog
from egitu.vcs import Commit


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

    def populate(self, *args, **kargs):
        self.genlist.populate(*args, **kargs)

    def update(self):
        self.genlist.update()

    def info_label_set(self, text):
        self.label.text = '  ' + text


class CommitDagData(object):
    def __init__(self, col, row):
        self.col = col
        self.row = row
        self.childs = list()  # all the childrens (Commit instance)
        self.date_span = 0    # if >0 then a date item is required

        self.icon_obj = None
        self.rezzed = False
        self.upwards_lines = dict() # 'child Commit': line_obj


class DagGraphList(Genlist):
    def __init__(self, parent, app, *args, **kargs):
        self.app = app
        self.themef = theme_file_get()
        self.colors = [(0,100,0,100), (0,0,100,100), (100,0,0,100),
                      (100,100,0,100), (0,100,100,100), (100,0,100,100)]

        self._itc = GenlistItemClass(item_style='egitu_commit',
                                     text_get_func=self._gl_text_get,
                                     content_get_func=self._gl_content_get)
        self._itcg = GenlistItemClass(item_style='egitu_group_index')

        Genlist.__init__(self, parent, homogeneous=True, mode=ELM_LIST_COMPRESS,
                         size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.callback_realized_add(self._gl_item_realized)
        self.callback_unrealized_add(self._gl_item_unrealized)
        self.callback_selected_add(self._gl_item_selected)

        self._start_ref = None

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

    def _commit_append(self, commit, col):
        commit.dag_data = CommitDagData(col, self._current_row)
        self._current_row += 1
        self._COMMITS[commit.sha] = commit
        return self.item_append(self._itc, commit, self._group_item)

    def update(self):
        selected_item = self.selected_item
        if selected_item:
            self.populate(self._start_ref, selected_item.data.sha)
        else:
            self.populate(self._start_ref)

    def populate(self, start_ref=None, hilight_ref=None):
        if self.app.repo is None:
            return
        self._start_ref = start_ref
        self._current_row = 0
        self._COMMITS = dict()           # 'sha': Commit instance
        self._used_columns = set()       # contain the indexes of used columns
        self._open_connections = dict()  # 'sha':[child1_col, child2_col, child3_col, ...]
        self._open_childs = dict()       # 'sha':[child1, child2, child3, ...]
        self._last_date_commit = None    # last commit that changed the date
        self._hilight_ref = hilight_ref

        self.COLW = 20 # columns width (fixed)
        self.ROWH = 0  # raws height (fetched from genlist on first realize)

        self.parent.info_label_set('Reading repository...')
        self.clear()

        # add the invisible group item
        self._group_item = self.item_append(self._itcg, None,
                                            flags=ELM_GENLIST_ITEM_GROUP)

        self._startup_time = time.time()
        self.app.repo.request_commits(self._populate_done_cb,
                                      self._populate_progress_cb,
                                      ref1=start_ref)

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
        item = self._commit_append(commit, point_col)

        # 5. store all the childrens of this commit
        if commit.sha in self._open_childs:
            commit.dag_data.childs = self._open_childs.pop(commit.sha)

        # 6. search a ref to hilight (if requested)
        if self._hilight_ref:
            if self._hilight_ref in commit.heads or \
               self._hilight_ref in commit.tags or \
               self._hilight_ref == commit.sha:
                item.selected = True
                item.show()
                self._hilight_ref = None

    def _populate_done_cb(self, success, err_msg=None):
        if not success:
            ErrorPopup(self, msg=err_msg)
            self.parent.info_label_set('Error fetching revisions')
            return

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
        if item.data is None: # this is the group item (nothing to do)
            return 

        dag_data = item.data.dag_data
        dag_data.icon_obj = None
        dag_data.rezzed = False
        dag_data.upwards_lines.clear()

        # draw (upwards) connections from realized parents to this one
        commit = item.data
        for parent_sha in commit.parents:
            if parent_sha in self._COMMITS:
                parent = self._COMMITS[parent_sha]
                if parent.dag_data.rezzed:
                    self.draw_connection(parent, commit)
            else:
                pass # parent not yet created ???

    def _gl_item_realized(self, gl, item):
        if item.data is None: # this is the group item (nothing to do)
            return 

        commit = item.data
        commit.dag_data.rezzed = True

        # on first item realized fetch the items height
        if self.ROWH == 0:
            track = item.track_object
            if track:
                self.ROWH = track.size[1]
                item.untrack()

        # setup item tooltip (DISABLED for now, quite broken)
        # if commit.title is not None:
            # item.tooltip_content_cb_set(lambda o,i,t: CommitTooltip(t, i.data))

        # draw connection lines with parents (downwards)
        for parent_sha in commit.parents:
            if parent_sha in self._COMMITS:
                self.draw_connection(commit, self._COMMITS[parent_sha])
            else:
                pass # parent not yet created ???

        # draw connections to unrealized childs (upwards)
        for child in commit.dag_data.childs:
            if not child.dag_data.rezzed:
                self.draw_connection(commit, child)

    def draw_connection(self, commit1, commit2):
        col1, row1 = commit1.dag_data.col, commit1.dag_data.row
        col2, row2 = commit2.dag_data.col, commit2.dag_data.row

        # down-wards connections
        if row1 < row2:
            if col1 == col2:
                # a stright line
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/stright',
                            color=self._color_for_column(col1),
                            size_hint_align=(0.5, 0.0))
            elif col1 > col2:
                # a "fork"
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/fork',
                            color=self._color_for_column(col1),
                            size_hint_align=(1.0, 0.0))
            else:
                # a merge
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/merge',
                            color=self._color_for_column(col2),
                            size_hint_align=(0.0, 0.0))

            # delete the same (upwards) line from parent (if was created)
            upward = commit2.dag_data.upwards_lines.pop(commit1, None)
            if upward is not None:
                upward.delete()

        # up-wards connections
        else:
            if col1 == col2:
                # a stright line
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/stright',
                            color=self._color_for_column(col1),
                            size_hint_align=(0.5, 1.0))
            elif col1 < col2:
                # a "fork"
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/fork',
                            color=self._color_for_column(col2),
                            size_hint_align=(0.0, 1.0))
            else:
                # a merge
                line = Edje(self.evas, file=self.themef,
                            group='egitu/graph/connection/merge',
                            color=self._color_for_column(col1),
                            size_hint_align=(1.0, 1.0))

            # store the line for later deletion
            commit1.dag_data.upwards_lines[commit2] = line

        # calculate size, append to the connections box and show
        line.size_hint_min = (abs(col2 - col1) + 1) * self.COLW, \
                             (abs(row2 - row1) + 1) * self.ROWH
        commit1.dag_data.icon_obj.box_append('connections.box', line)
        line.show()

    def _gl_item_selected(self, gl, item):
        self.app.action_show_commit(item.data)

